#!/usr/bin/env python3
"""Generate static Privacy and Support pages for every app locale."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"
TRANSLATIONS_ROOT = DATA_ROOT / "translations"
BASE_URL = "https://kondofumikazu-cmd.github.io/eclise-simulation/"
BASE_PATH = "/eclise-simulation/"
OG_IMAGE = BASE_URL + "assets/og.png"
SUPPORT_EMAIL = "kondofumikazu@icloud.com"
ISSUES_URL = "https://github.com/kondofumikazu-cmd/eclise-simulation/issues/new/choose"
APPLE_MAPS_PRIVACY = {
    "ja": "https://www.apple.com/legal/privacy/data/ja/apple-maps/",
    "default": "https://www.apple.com/legal/privacy/data/en/apple-maps/",
}
APPLE_MAPS_TERMS = {
    "ja": "https://www.apple.com/legal/internet-services/maps/terms-jp.html",
    "default": "https://www.apple.com/legal/internet-services/maps/terms-en.html",
}
GITHUB_PRIVACY = {
    "ja": "https://docs.github.com/ja/site-policy/privacy-policies/github-general-privacy-statement",
    "default": "https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement",
}
PRIVACY_SECTIONS = (
    "developer_data_collection",
    "location",
    "apple_maps",
    "on_device_storage",
    "export_and_sharing",
    "support_contact",
    "children",
    "website_and_github_pages",
    "changes",
    "contact",
)
FAQ_KEYS = (
    "location_permission",
    "modern_maps",
    "model_differences",
    "lunar_colour",
    "exports",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def locale_root(item: dict[str, Any]) -> str:
    slug = item["web_slug"]
    return BASE_PATH if not slug else f"{BASE_PATH}{slug}/"


def page_path(item: dict[str, Any], kind: str) -> str:
    return locale_root(item) + f"{kind}/"


def absolute_page_url(item: dict[str, Any], kind: str) -> str:
    return "https://kondofumikazu-cmd.github.io" + page_path(item, kind)


def output_path(item: dict[str, Any], kind: str) -> Path:
    slug = item["web_slug"]
    return ROOT / slug / kind / "index.html" if slug else ROOT / kind / "index.html"


def plain(value: str, content: dict[str, Any]) -> str:
    return html.escape(value.replace("{app_name}", content["app_name"]), quote=True)


def rich(value: str, content: dict[str, Any], item: dict[str, Any]) -> str:
    rendered = html.escape(value, quote=False)
    locale = item["app_locale"]
    app_lang = "ja" if locale == "ja" else "en"
    replacements = {
        "{app_name}": (
            f'<bdi lang="{app_lang}" dir="ltr">{html.escape(content["app_name"])}</bdi>'
        ),
        "{email}": (
            f'<a href="mailto:{SUPPORT_EMAIL}"><bdi dir="ltr">{SUPPORT_EMAIL}</bdi></a>'
        ),
        "{privacy_page}": (
            f'<a href="{page_path(item, "privacy")}">{html.escape(content["links"]["privacy_page"])}</a>'
        ),
        "{support_page}": (
            f'<a href="{page_path(item, "support")}">{html.escape(content["links"]["support_page"])}</a>'
        ),
        "{apple_maps_privacy}": (
            f'<a href="{APPLE_MAPS_PRIVACY.get(locale, APPLE_MAPS_PRIVACY["default"])}">'
            f'{html.escape(content["links"]["apple_maps_privacy"])}</a>'
        ),
        "{apple_maps_terms}": (
            f'<a href="{APPLE_MAPS_TERMS.get(locale, APPLE_MAPS_TERMS["default"])}">'
            f'{html.escape(content["links"]["apple_maps_terms"])}</a>'
        ),
        "{github_privacy}": (
            f'<a href="{GITHUB_PRIVACY.get(locale, GITHUB_PRIVACY["default"])}">'
            f'{html.escape(content["links"]["github_privacy"])}</a>'
        ),
        "{issues_page}": (
            f'<a href="{ISSUES_URL}">{html.escape(content["links"]["issues_page"])}</a>'
        ),
    }
    for token, replacement in replacements.items():
        rendered = rendered.replace(token, replacement)
    return rendered


def head_alternates(locales: list[dict[str, Any]], kind: str) -> str:
    lines = [
        f'  <link rel="alternate" hreflang="{html.escape(item["bcp47"])}" '
        f'href="{absolute_page_url(item, kind)}">'
        for item in locales
    ]
    english = next(item for item in locales if item["app_locale"] == "en")
    lines.append(
        f'  <link rel="alternate" hreflang="x-default" href="{absolute_page_url(english, kind)}">'
    )
    return "\n".join(lines)


def language_picker(
    locales: list[dict[str, Any]],
    contents: dict[str, dict[str, Any]],
    current: dict[str, Any],
    kind: str,
) -> str:
    links: list[str] = []
    for item in locales:
        current_attr = ' aria-current="page"' if item["app_locale"] == current["app_locale"] else ""
        links.append(
            "          <li>"
            f'<a lang="{html.escape(item["bcp47"])}" dir="{item["direction"]}" '
            f'hreflang="{html.escape(item["bcp47"])}" href="{page_path(item, kind)}"{current_attr}>'
            f'{html.escape(contents[item["app_locale"]]["native_name"])}</a></li>'
        )
    label = html.escape(contents[current["app_locale"]]["ui"]["languages"])
    return (
        '      <details class="language-picker">\n'
        f'        <summary>{label}</summary>\n'
        '        <ul class="language-options">\n'
        + "\n".join(links)
        + "\n        </ul>\n      </details>"
    )


def navigation(item: dict[str, Any], content: dict[str, Any], kind: str) -> str:
    locale = item["app_locale"]
    overview = BASE_PATH if locale == "ja" else BASE_PATH + "en/"
    accessibility = BASE_PATH + "accessibility/" if locale == "ja" else BASE_PATH + "en/accessibility/"
    privacy_current = ' aria-current="page"' if kind == "privacy" else ""
    support_current = ' aria-current="page"' if kind == "support" else ""
    return (
        '      <nav aria-label="Primary">\n'
        '        <ul class="nav-list">\n'
        f'          <li><a href="{overview}">{html.escape(content["ui"]["overview"])}</a></li>\n'
        f'          <li><a href="{page_path(item, "support")}"{support_current}>{html.escape(content["ui"]["support"])}</a></li>\n'
        f'          <li><a href="{page_path(item, "privacy")}"{privacy_current}>{html.escape(content["ui"]["privacy"])}</a></li>\n'
        f'          <li><a href="{accessibility}">{html.escape(content["ui"]["accessibility"])}</a></li>\n'
        '        </ul>\n'
        '      </nav>'
    )


def page_head(
    item: dict[str, Any],
    content: dict[str, Any],
    locales: list[dict[str, Any]],
    kind: str,
) -> str:
    section = content[kind]
    title = f'{section["heading"]} — {content["app_name"]}'
    description = plain(section["meta_description"], content)
    url = absolute_page_url(item, kind)
    return f'''<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{description}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{html.escape(content["app_name"], quote=True)}">
  <meta property="og:title" content="{html.escape(title, quote=True)}">
  <meta property="og:description" content="{description}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{OG_IMAGE}">
  <meta property="og:image:alt" content="{html.escape(content["app_name"], quote=True)} — Support, Privacy, Accessibility">
  <meta property="og:locale" content="{item["og_locale"]}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{html.escape(title, quote=True)}">
  <meta name="twitter:description" content="{description}">
  <meta name="twitter:image" content="{OG_IMAGE}">
  <meta name="theme-color" content="#060914">
  <link rel="canonical" href="{url}">
{head_alternates(locales, kind)}
  <link rel="stylesheet" href="{BASE_PATH}assets/styles.css?v=20260829-locales">
  <title>{html.escape(title)}</title>
</head>'''


def shell_start(
    item: dict[str, Any],
    content: dict[str, Any],
    locales: list[dict[str, Any]],
    contents: dict[str, dict[str, Any]],
    kind: str,
) -> str:
    locale = item["app_locale"]
    overview = BASE_PATH if locale == "ja" else BASE_PATH + "en/"
    return f'''<!doctype html>
<!-- Generated by scripts/generate_localized_pages.py; edit data/translations instead. -->
<html lang="{html.escape(item["bcp47"])}" dir="{item["direction"]}">
{page_head(item, content, locales, kind)}
<body>
  <a class="skip-link" href="#main">{html.escape(content["ui"]["skip"])}</a>
  <header class="site-header">
    <div class="header-inner">
      <a class="brand" href="{overview}" aria-label="{plain(content["ui"]["brand_home_aria"], content)}">
        <span class="brand-mark" aria-hidden="true"></span>
        <bdi lang="{'ja' if locale == 'ja' else 'en'}" dir="ltr">{html.escape(content["app_name"])}</bdi>
      </a>
{navigation(item, content, kind)}
{language_picker(locales, contents, item, kind)}
    </div>
  </header>'''


def footer(item: dict[str, Any], content: dict[str, Any], kind: str) -> str:
    other = "support" if kind == "privacy" else "privacy"
    overview = BASE_PATH if item["app_locale"] == "ja" else BASE_PATH + "en/"
    accessibility = BASE_PATH + "accessibility/" if item["app_locale"] == "ja" else BASE_PATH + "en/accessibility/"
    return f'''  <footer class="site-footer">
    <div class="footer-inner">
      <p>{rich(content[kind]["footer"], content, item)}</p>
      <ul class="footer-links">
        <li><a href="{overview}">{html.escape(content["ui"]["overview"])}</a></li>
        <li><a href="{page_path(item, other)}">{html.escape(content["ui"][other])}</a></li>
        <li><a href="{accessibility}">{html.escape(content["ui"]["accessibility"])}</a></li>
      </ul>
    </div>
  </footer>
</body>
</html>
'''


def render_privacy(
    item: dict[str, Any],
    content: dict[str, Any],
    locales: list[dict[str, Any]],
    contents: dict[str, dict[str, Any]],
) -> str:
    sections: list[str] = []
    for key in PRIVACY_SECTIONS:
        section = content["privacy"]["sections"][key]
        paragraphs = "\n".join(f"      <p>{rich(p, content, item)}</p>" for p in section["paragraphs"])
        section_class = ' class="contact-panel"' if key == "contact" else ""
        sections.append(
            f'    <section id="{key}"{section_class} aria-labelledby="{key}-title">\n'
            f'      <h2 id="{key}-title">{html.escape(section["title"])}</h2>\n'
            f'{paragraphs}\n'
            '    </section>'
        )
    return (
        shell_start(item, content, locales, contents, "privacy")
        + f'''\n  <main id="main" class="page-shell content-page">
    <header>
      <p class="eyebrow">{html.escape(content["ui"]["privacy_eyebrow"])}</p>
      <h1>{html.escape(content["privacy"]["heading"])}</h1>
      <p class="lede">{rich(content["privacy"]["lede"], content, item)}</p>
      <p class="meta"><span>{html.escape(content["privacy"]["effective_date_label"])}</span>: <time datetime="2026-08-29">{html.escape(content["privacy"]["effective_date"])}</time></p>
    </header>

{chr(10).join(sections)}
  </main>

'''
        + footer(item, content, "privacy")
    )


def render_support(
    item: dict[str, Any],
    content: dict[str, Any],
    locales: list[dict[str, Any]],
    contents: dict[str, dict[str, Any]],
) -> str:
    details = "\n".join(
        f"        <li>{rich(entry, content, item)}</li>"
        for entry in content["support"]["diagnostics_items"]
    )
    faqs = "\n".join(
        f'''      <article class="faq-item" id="faq-{key}">
        <h3>{html.escape(content["support"]["faqs"][key]["question"])}</h3>
        <p>{rich(content["support"]["faqs"][key]["answer"], content, item)}</p>
      </article>'''
        for key in FAQ_KEYS
    )
    return (
        shell_start(item, content, locales, contents, "support")
        + f'''\n  <main id="main" class="page-shell content-page">
    <header>
      <p class="eyebrow">{html.escape(content["ui"]["support_eyebrow"])}</p>
      <h1>{html.escape(content["support"]["heading"])}</h1>
      <p class="lede">{rich(content["support"]["lede"], content, item)}</p>
    </header>

    <section class="contact-panel" id="support-contact" aria-labelledby="support-contact-title">
      <h2 id="support-contact-title">{html.escape(content["support"]["contact_title"])}</h2>
      <p>{rich(content["support"]["contact_intro"], content, item)}</p>
      <p><strong>{html.escape(content["links"]["email"])}:</strong> <a href="mailto:{SUPPORT_EMAIL}"><bdi dir="ltr">{SUPPORT_EMAIL}</bdi></a></p>
      <div class="actions">
        <a class="button primary" href="mailto:{SUPPORT_EMAIL}">{html.escape(content["support"]["email_button"])}</a>
        <a class="button" href="{ISSUES_URL}">{html.escape(content["support"]["issues_button"])}</a>
      </div>
      <p class="meta">{rich(content["support"]["contact_warning"], content, item)}</p>
    </section>

    <section id="diagnostics" aria-labelledby="diagnostics-title">
      <h2 id="diagnostics-title">{html.escape(content["support"]["diagnostics_title"])}</h2>
      <ul>
{details}
      </ul>
      <p>{rich(content["support"]["privacy_note"], content, item)}</p>
    </section>

    <section id="faq" aria-labelledby="faq-title">
      <h2 id="faq-title">{html.escape(content["support"]["faq_title"])}</h2>
{faqs}
    </section>
  </main>

'''
        + footer(item, content, "support")
    )


def render_404(locales: list[dict[str, Any]], contents: dict[str, dict[str, Any]]) -> str:
    links = []
    for item in locales:
        label = html.escape(contents[item["app_locale"]]["native_name"])
        links.append(
            f'<li><span lang="{item["bcp47"]}" dir="{item["direction"]}">{label}</span>: '
            f'<a href="{page_path(item, "privacy")}">Privacy</a> · '
            f'<a href="{page_path(item, "support")}">Support</a></li>'
        )
    return f'''<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <link rel="stylesheet" href="{BASE_PATH}assets/styles.css?v=20260829-locales">
  <title>ページが見つかりません — 月食・日食シミュレーター</title>
</head>
<body>
  <main id="main" class="page-shell content-page">
    <p class="eyebrow">404</p>
    <h1>ページが見つかりません</h1>
    <p class="lede" lang="en">The requested page could not be found.</p>
    <div class="actions">
      <a class="button primary" href="{BASE_PATH}">日本語ホーム</a>
      <a class="button" href="{BASE_PATH}en/">English home</a>
      <a class="button" href="mailto:{SUPPORT_EMAIL}">サポートメール / Support email</a>
    </div>
    <details class="language-picker not-found-languages">
      <summary>Privacy / Support languages</summary>
      <ul class="language-options">{''.join(links)}</ul>
    </details>
  </main>
</body>
</html>
'''


def render_sitemap(locales: list[dict[str, Any]]) -> str:
    urls = [
        BASE_URL,
        BASE_URL + "accessibility/",
        BASE_URL + "en/",
        BASE_URL + "en/accessibility/",
    ]
    for item in locales:
        urls.extend((absolute_page_url(item, "privacy"), absolute_page_url(item, "support")))
    body = "\n".join(f"  <url><loc>{html.escape(url)}</loc></url>" for url in urls)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{body}
</urlset>
'''


def generate(check: bool) -> None:
    manifest = load_json(DATA_ROOT / "locale-manifest.json")
    locales = manifest["locales"]
    contents = {
        item["app_locale"]: load_json(TRANSLATIONS_ROOT / f'{item["app_locale"]}.json')
        for item in locales
    }
    outputs: dict[Path, str] = {}
    for item in locales:
        content = contents[item["app_locale"]]
        outputs[output_path(item, "privacy")] = render_privacy(item, content, locales, contents)
        outputs[output_path(item, "support")] = render_support(item, content, locales, contents)
    outputs[ROOT / "404.html"] = render_404(locales, contents)
    outputs[ROOT / "sitemap.xml"] = render_sitemap(locales)

    mismatches: list[str] = []
    for path, expected in outputs.items():
        if check:
            actual = path.read_text(encoding="utf-8") if path.exists() else None
            if actual != expected:
                mismatches.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
    if mismatches:
        raise SystemExit("Generated pages are out of date:\n- " + "\n- ".join(mismatches))
    action = "checked" if check else "generated"
    print(f"Localized pages {action}: {len(locales) * 2} pages; sitemap URLs: {4 + len(locales) * 2}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generate(args.check)


if __name__ == "__main__":
    main()
