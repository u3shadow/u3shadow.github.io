# u3coding

Static GitHub Pages export generated from local Z-Blog backup. All 215 historical
posts keep their original URL, title, publication date, and body text.

## Local Maintenance

No frontend framework, npm install, or remote deployment is required.

```powershell
python -B scripts/build_site.py
python -B -m unittest discover -s tests -p test_static.py
python -B -m http.server 8765 --bind 127.0.0.1
```

Open `http://127.0.0.1:8765/`. HTTP preview is necessary because the export uses
root-relative asset URLs and JavaScript modules.

- `data/site.json`: brand, public URL, contact, featured article IDs and covers.
- `data/projects.json`: project copy, verified scope, source articles and repository links.
- `data/posts.json`: generated index of dates, URLs, topics and technical keywords.
- `scripts/build_site.py`: incremental refresh of common chrome, metadata and site pages.
- `assets/site/site-theme.css`: final, shared dark/light tokens and component corrections.
- `assets/site/site.js`: theme, mobile menu, filters, TOC, image viewer and code copying.
- `assets/site/diagrams.js`: local Mermaid rendering and theme-aware diagrams.
- `tests/post-baseline.json`: immutable signatures of the 215 original posts.

The generator refuses to proceed if post titles, dates, URLs or original body text
do not match the captured baseline. For intentional future article edits, review
and explicitly update only the corresponding baseline entries. Do not recapture
the entire baseline to hide a regression. The homepage's approved HTML composition
is retained; its curated project/article/recent blocks are refreshed from data.

`email` is deliberately `null` until the owner confirms the address. Public contact
links currently use the known GitHub profile. Set `email` and `emailStatus` in
`data/site.json`, then rebuild to apply the address consistently.

Topics are conservative title-based display labels, not modifications to original
Z-Blog classifications. Uncertain posts stay unclassified. Search covers titles,
excerpts and a small technical-keyword index extracted from each article. Reading
times are explicitly approximate, calculated at 450 text characters per minute.

## Browser Checks

With Playwright available in the development environment and the preview running:

```powershell
node tests/browser.cjs
node tests/posts.cjs
```

The first checks seven pages at 375/768/1280/1920px in both themes and exercises
search, filtering, navigation, TOC and image zoom. The second checks every original
article at mobile and desktop widths in both themes. QA images and reports go to
`../qa/`, outside this website's published directory. Playwright is a test tool,
not a website dependency.

## Vendored Assets

The existing Mermaid dependency is pinned to 11.12.0 and served locally (MIT).
Five Lucide 0.468.0 icons are served locally with their license. No CDN is needed
to view architecture diagrams. To deliberately refresh these exact copies:

```powershell
python -B scripts/vendor_assets.py
```

## Preservation Notes

Do not rerun the historical `work/generate_static_blog.py` as a maintenance build:
it targets a different directory, deletes that output and reimports the backup.
This project does not change `.nojekyll` or GitHub Pages settings, and its build
does not commit, push, publish, or invoke remote deployment.

An already-deleted tracked file, `assets/images/0d23d41c2651.gif`, is intentionally
not restored. Two old posts refer to it. Four other historical missing-image
placeholders also remain; original images are needed to repair those accurately.
