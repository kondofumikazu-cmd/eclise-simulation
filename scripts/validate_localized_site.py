#!/usr/bin/env python3
"""Validate generated localized pages locally or after GitHub Pages deployment."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"
TRANSLATIONS_ROOT = DATA_ROOT / "translations"
BASE_URL = "https://kondofumikazu-cmd.github.io/eclise-simulation/"
BASE_PATH = "/eclise-simulation/"
EMAIL_HREF = "mailto:kondofumikazu@icloud.com"
FORBIDDEN_NAME_PATTERN = re.compile(
    r"日食・月食シミュレータ(?:ー)?|月食・日食シミュレータ(?!ー)"
)
PLACEHOLDER = re.compile(r"\{[a-z_]+\}|\b(?:TODO|TBD|FIXME|PLACEHOLDER|CHANGEME)\b", re.I)


class PageParser(HTMLParser):
    VOID_ELEMENTS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_attrs: dict[str, str] = {}
        self.titles: list[str] = []
        self._in_title = False
        self.h1_count = 0
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.body_hreflangs: list[str] = []
        self.canonicals: list[str] = []
        self.alternates: dict[str, str] = {}
        self.meta_name: dict[str, str] = {}
        self.meta_property: dict[str, str] = {}
        self.forbidden_elements: list[str] = []
        self.tag_stack: list[str] = []
        self.syntax_errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in self.VOID_ELEMENTS:
            self.tag_stack.append(tag)
        values = {key: value or "" for key, value in attrs}
        if tag == "html":
            self.html_attrs = values
        if tag == "title":
            self._in_title = True
            self.titles.append("")
        if tag == "h1":
            self.h1_count += 1
        if "id" in values:
            self.ids.append(values["id"])
        if tag == "a":
            if "href" in values:
                self.hrefs.append(values["href"])
            if "hreflang" in values:
                self.body_hreflangs.append(values["hreflang"])
        if tag == "link":
            rel = set(values.get("rel", "").split())
            if "canonical" in rel:
                self.canonicals.append(values.get("href", ""))
            if "alternate" in rel:
                self.alternates[values.get("hreflang", "")] = values.get("href", "")
        if tag == "meta":
            if values.get("name"):
                self.meta_name[values["name"]] = values.get("content", "")
            if values.get("property"):
                self.meta_property[values["property"]] = values.get("content", "")
        if tag in {"script", "iframe", "form"}:
            self.forbidden_elements.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if not self.tag_stack:
            self.syntax_errors.append(f"unexpected closing </{tag}>")
        elif self.tag_stack[-1] == tag:
            self.tag_stack.pop()
        else:
            self.syntax_errors.append(
                f"closing </{tag}> does not match <{self.tag_stack[-1]}>"
            )
            if tag in self.tag_stack:
                while self.tag_stack and self.tag_stack[-1] != tag:
                    self.tag_stack.pop()
                if self.tag_stack:
                    self.tag_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._in_title and self.titles:
            self.titles[-1] += data


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def locale_root(item: dict[str, Any]) -> str:
    return BASE_PATH if not item["web_slug"] else f'{BASE_PATH}{item["web_slug"]}/'


def public_url(item: dict[str, Any], kind: str) -> str:
    return "https://kondofumikazu-cmd.github.io" + locale_root(item) + f"{kind}/"


def local_path(item: dict[str, Any], kind: str) -> Path:
    return ROOT / item["web_slug"] / kind / "index.html" if item["web_slug"] else ROOT / kind / "index.html"


def href_to_path(href: str) -> Path | None:
    if href.startswith(BASE_PATH):
        relative = href.removeprefix(BASE_PATH).split("?", 1)[0].split("#", 1)[0]
        target = ROOT / relative
        if href.endswith("/"):
            target /= "index.html"
        return target
    return None


def relative_href_to_path(page: Path, href: str) -> Path | None:
    if (
        not href
        or href.startswith(("#", "mailto:", "https://", "http://"))
        or href.startswith(BASE_PATH)
    ):
        return None
    clean = href.split("?", 1)[0].split("#", 1)[0]
    target = page.parent / clean
    if clean.endswith("/") or target.is_dir():
        target /= "index.html"
    return target.resolve()


def validate_fixed_pages(errors: list[str]) -> None:
    fixed = {
        ROOT / "index.html": {
            "lang": "ja", "canonical": BASE_URL, "og_locale": "ja_JP",
            "alternates": {"ja", "en", "x-default"},
        },
        ROOT / "accessibility" / "index.html": {
            "lang": "ja", "canonical": BASE_URL + "accessibility/", "og_locale": "ja_JP",
            "alternates": {"ja", "en", "x-default"},
        },
        ROOT / "en" / "index.html": {
            "lang": "en", "canonical": BASE_URL + "en/", "og_locale": "en_US",
            "alternates": {"ja", "en", "x-default"},
        },
        ROOT / "en" / "accessibility" / "index.html": {
            "lang": "en", "canonical": BASE_URL + "en/accessibility/", "og_locale": "en_US",
            "alternates": {"ja", "en", "x-default"},
        },
    }
    for path, expected in fixed.items():
        relative = str(path.relative_to(ROOT))
        try:
            text = path.read_text(encoding="utf-8")
        except (FileNotFoundError, UnicodeDecodeError) as error:
            errors.append(f"{relative}: missing or invalid UTF-8: {error}")
            continue
        parser = PageParser()
        parser.feed(text)
        parser.close()
        if not text.lower().startswith("<!doctype html>"):
            errors.append(f"{relative}: missing HTML5 doctype")
        if parser.html_attrs.get("lang") != expected["lang"]:
            errors.append(f"{relative}: html lang mismatch")
        if parser.canonicals != [expected["canonical"]]:
            errors.append(f"{relative}: canonical mismatch")
        if parser.meta_property.get("og:url") != expected["canonical"]:
            errors.append(f"{relative}: og:url mismatch")
        if parser.meta_property.get("og:locale") != expected["og_locale"]:
            errors.append(f"{relative}: og:locale mismatch")
        if set(parser.alternates) != expected["alternates"]:
            errors.append(f"{relative}: ja/en/x-default hreflang set mismatch")
        if set(parser.body_hreflangs) != {"ja", "en"}:
            errors.append(f"{relative}: Japanese/English language picker missing")
        if len(parser.titles) != 1 or not parser.titles[0].strip():
            errors.append(f"{relative}: expected one non-empty title")
        if parser.h1_count != 1:
            errors.append(f"{relative}: expected one h1, found {parser.h1_count}")
        if EMAIL_HREF not in parser.hrefs:
            errors.append(f"{relative}: support email link missing")
        if parser.forbidden_elements:
            errors.append(f"{relative}: forbidden elements {parser.forbidden_elements}")
        if parser.syntax_errors or parser.tag_stack:
            errors.append(
                f"{relative}: HTML tag nesting errors {parser.syntax_errors}; "
                f"unclosed={parser.tag_stack}"
            )
        for required in ("description", "twitter:title", "twitter:description"):
            if not parser.meta_name.get(required):
                errors.append(f"{relative}: missing meta name={required}")
        for required in ("og:site_name", "og:title", "og:description", "og:image", "og:image:alt"):
            if not parser.meta_property.get(required):
                errors.append(f"{relative}: missing meta property={required}")
        for href in parser.hrefs:
            target = relative_href_to_path(path, href)
            if target is not None and not target.exists():
                errors.append(f"{relative}: broken internal link {href}")


def validate_local() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    errors: list[str] = []
    manifest = load_json(DATA_ROOT / "locale-manifest.json")
    locales = manifest["locales"]
    contents = {
        item["app_locale"]: load_json(TRANSLATIONS_ROOT / f'{item["app_locale"]}.json')
        for item in locales
    }
    if len(locales) != 51:
        errors.append(f"manifest: expected 51 locales, found {len(locales)}")
    if len({item["app_locale"] for item in locales}) != len(locales):
        errors.append("manifest: duplicate app_locale")
    if len({item["web_slug"] for item in locales}) != len(locales):
        errors.append("manifest: duplicate web_slug")
    if len({item["store_locale"] for item in locales if item["store_locale"]}) != 50:
        errors.append("manifest: expected 50 unique Store locales")

    expected_hreflang = {item["bcp47"] for item in locales} | {"x-default"}
    expected_urls: set[str] = {
        BASE_URL,
        BASE_URL + "accessibility/",
        BASE_URL + "en/",
        BASE_URL + "en/accessibility/",
    }

    validate_fixed_pages(errors)

    for item in locales:
        locale = item["app_locale"]
        content = contents[locale]
        expected_name = "月食・日食シミュレーター" if locale == "ja" else "Eclipse Simulator"
        if content.get("app_name") != expected_name:
            errors.append(f"data/translations/{locale}.json: invalid app_name")
        if content.get("app_locale") != locale or content.get("bcp47") != item["bcp47"]:
            errors.append(f"data/translations/{locale}.json: locale identity differs from manifest")

        for kind in ("privacy", "support"):
            path = local_path(item, kind)
            expected_url = public_url(item, kind)
            expected_urls.add(expected_url)
            try:
                text = path.read_text(encoding="utf-8")
            except (FileNotFoundError, UnicodeDecodeError) as error:
                errors.append(f"{path.relative_to(ROOT)}: missing or invalid UTF-8: {error}")
                continue
            parser = PageParser()
            parser.feed(text)
            parser.close()
            relative = str(path.relative_to(ROOT))
            if not text.lower().startswith("<!doctype html>"):
                errors.append(f"{relative}: missing HTML5 doctype")
            if parser.html_attrs.get("lang") != item["bcp47"]:
                errors.append(f"{relative}: html lang mismatch")
            if parser.html_attrs.get("dir") != item["direction"]:
                errors.append(f"{relative}: html dir mismatch")
            if len(parser.titles) != 1 or not parser.titles[0].strip():
                errors.append(f"{relative}: expected one non-empty title")
            if parser.h1_count != 1:
                errors.append(f"{relative}: expected one h1, found {parser.h1_count}")
            if len(parser.ids) != len(set(parser.ids)):
                errors.append(f"{relative}: duplicate id")
            if parser.canonicals != [expected_url]:
                errors.append(f"{relative}: canonical mismatch")
            if parser.meta_property.get("og:url") != expected_url:
                errors.append(f"{relative}: og:url mismatch")
            if parser.meta_property.get("og:locale") != item["og_locale"]:
                errors.append(f"{relative}: og:locale mismatch")
            for required in ("description", "twitter:title", "twitter:description"):
                if not parser.meta_name.get(required):
                    errors.append(f"{relative}: missing meta name={required}")
            for required in ("og:title", "og:description", "og:image", "og:image:alt"):
                if not parser.meta_property.get(required):
                    errors.append(f"{relative}: missing meta property={required}")
            if set(parser.alternates) != expected_hreflang:
                errors.append(
                    f"{relative}: hreflang set mismatch; expected {len(expected_hreflang)}, "
                    f"found {len(parser.alternates)}"
                )
            if len(parser.body_hreflangs) != 51 or set(parser.body_hreflangs) != {item["bcp47"] for item in locales}:
                errors.append(f"{relative}: language picker must contain all 51 locales")
            if EMAIL_HREF not in parser.hrefs:
                errors.append(f"{relative}: support email link missing")
            if parser.forbidden_elements:
                errors.append(f"{relative}: forbidden elements {parser.forbidden_elements}")
            if parser.syntax_errors or parser.tag_stack:
                errors.append(
                    f"{relative}: HTML tag nesting errors {parser.syntax_errors}; "
                    f"unclosed={parser.tag_stack}"
                )
            if PLACEHOLDER.search(text):
                errors.append(f"{relative}: unresolved placeholder")
            if former_name := FORBIDDEN_NAME_PATTERN.search(text):
                errors.append(f"{relative}: former app name remains: {former_name.group(0)}")
            for href in parser.hrefs:
                target = href_to_path(href)
                if target is not None and not target.exists():
                    errors.append(f"{relative}: broken internal link {href}")

    try:
        not_found_text = (ROOT / "404.html").read_text(encoding="utf-8")
        not_found = PageParser()
        not_found.feed(not_found_text)
        not_found.close()
        expected_404_links = {
            page_path
            for item in locales
            for page_path in (locale_root(item) + "privacy/", locale_root(item) + "support/")
        }
        missing_404_links = expected_404_links - set(not_found.hrefs)
        if missing_404_links:
            errors.append(f"404.html: missing {len(missing_404_links)} localized page links")
        if not_found.meta_name.get("robots") != "noindex":
            errors.append("404.html: robots noindex missing")
        if EMAIL_HREF not in not_found.hrefs:
            errors.append("404.html: support email link missing")
        if (
            not_found.h1_count != 1
            or not_found.forbidden_elements
            or not_found.syntax_errors
            or not_found.tag_stack
        ):
            errors.append("404.html: invalid heading count or forbidden interactive embed")
    except (FileNotFoundError, UnicodeDecodeError) as error:
        errors.append(f"404.html: missing or invalid UTF-8: {error}")

    try:
        tree = ET.parse(ROOT / "sitemap.xml")
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        actual_urls = {node.text or "" for node in tree.findall("sm:url/sm:loc", namespace)}
        if actual_urls != expected_urls:
            errors.append(
                f"sitemap.xml: URL set mismatch; expected {len(expected_urls)}, found {len(actual_urls)}"
            )
    except (ET.ParseError, FileNotFoundError) as error:
        errors.append(f"sitemap.xml: invalid or missing: {error}")

    for required in (ROOT / "assets" / "styles.css", ROOT / "assets" / "og.png", ROOT / "404.html"):
        if not required.is_file():
            errors.append(f"missing required site file: {required.relative_to(ROOT)}")

    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() not in {".html", ".xml", ".md", ".json", ".css"}:
            continue
        text = path.read_text(encoding="utf-8")
        if former_name := FORBIDDEN_NAME_PATTERN.search(text):
            errors.append(
                f"{path.relative_to(ROOT)}: former app name remains: {former_name.group(0)}"
            )
    return locales, contents, errors


def fetch(url: str) -> tuple[str, int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "EclipseSimulator-local-site-validator/1"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return url, response.status, response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        return url, 0, str(error).encode("utf-8", errors="replace")


def validate_deployed(locales: list[dict[str, Any]], contents: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    expectations: dict[str, tuple[str, str] | None] = {
        BASE_URL + "sitemap.xml": None,
        BASE_URL + "assets/styles.css": None,
        BASE_URL + "assets/og.png": None,
        BASE_URL: None,
        BASE_URL + "accessibility/": None,
        BASE_URL + "en/": None,
        BASE_URL + "en/accessibility/": None,
    }
    for item in locales:
        for kind in ("privacy", "support"):
            expectations[public_url(item, kind)] = (item["app_locale"], kind)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch, url): url for url in expectations}
        for future in as_completed(futures):
            url, status, body = future.result()
            if status != 200:
                errors.append(f"{url}: HTTP {status}; {body[:160].decode('utf-8', errors='replace')}")
                continue
            expected = expectations[url]
            if expected is None:
                continue
            locale, kind = expected
            item = next(entry for entry in locales if entry["app_locale"] == locale)
            content = contents[locale]
            text = body.decode("utf-8", errors="replace")
            if f'<html lang="{item["bcp47"]}" dir="{item["direction"]}">' not in text:
                errors.append(f"{url}: deployed locale attributes do not match")
            if f'<link rel="canonical" href="{url}">' not in text:
                errors.append(f"{url}: deployed canonical does not match")
            if content["app_name"] not in text:
                errors.append(f"{url}: deployed app name does not match")
            if content[kind]["heading"] not in text:
                errors.append(f"{url}: deployed heading does not match")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deployed", action="store_true")
    args = parser.parse_args()
    try:
        locales, contents, errors = validate_local()
    except (OSError, ValueError, KeyError) as error:
        print(f"Site validation failed to initialize: {error}", file=sys.stderr)
        return 1
    if args.deployed and not errors:
        errors.extend(validate_deployed(locales, contents))
    if errors:
        print("Localized site validation failed:\n- " + "\n- ".join(errors), file=sys.stderr)
        return 1
    scope = "local and deployed" if args.deployed else "local"
    print(f"Localized site validation: PASS ({scope}; {len(locales) * 2} localized pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
