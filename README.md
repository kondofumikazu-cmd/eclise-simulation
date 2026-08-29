# Eclipse Simulator support site

Public support, privacy, accessibility, and product-information pages for
「月食・日食シミュレーター」/ Eclipse Simulator.

GitHub Pages publishes the repository root at:

- Japanese: https://kondofumikazu-cmd.github.io/eclise-simulation/
- English: https://kondofumikazu-cmd.github.io/eclise-simulation/en/
- Support: https://kondofumikazu-cmd.github.io/eclise-simulation/support/
- Privacy: https://kondofumikazu-cmd.github.io/eclise-simulation/privacy/
- Support email: kondofumikazu@icloud.com

The repository adds only plain HTML and CSS: no first-party analytics,
advertising, tracking cookies, forms, or client-side scripts. GitHub Pages may
process technical information needed to host and secure the site, as described
in the localized privacy policies.

Privacy and Support are generated for the app's 51 bundled locales. The 49
non-source translations are machine translations that received an independent
meaning review; they still require native-speaker and legal review. Japanese and
the generic English source were reviewed against the app's 2026-08-29 technical
privacy audit.

## Local generation and validation

The canonical localized content is stored in `data/translations/`, with routing
and App Store locale mappings in `data/locale-manifest.json`.

```sh
python3 scripts/generate_localized_pages.py
python3 scripts/generate_localized_pages.py --check
python3 scripts/validate_localized_site.py
```

After GitHub Pages finishes deploying, verify every expected public URL with:

```sh
python3 scripts/validate_localized_site.py --deployed
```
