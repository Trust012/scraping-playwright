# Web Scraping with Python & Playwright

Three scraping workflows covering the most common real-world challenges:
JavaScript-rendered pages, infinite scroll, and multi-level sites.
Each script cleans, validates and exports structured data to **CSV** and **JSON**.

| Script | Challenge | Target (practice site) | Output |
|---|---|---|---|
| `scrape_quotes_js.py` | JavaScript-rendered content + pagination | quotes.toscrape.com/js | `citations.csv` / `.json` (100 records) |
| `scrape_quotes_scroll.py` | Infinite scroll (AJAX loading) | quotes.toscrape.com/scroll | `citations_scroll.csv` / `.json` (100 records) |
| `scrape_books_multiniveaux.py` | Multi-level crawl: categories → paginated lists → detail pages | books.toscrape.com | `livres.csv` / `.json` (44 records, 0 errors) |

## Techniques used

- **Playwright (Chromium, headless)** to render JavaScript before extraction
- **Explicit waits** (`wait_for_selector`) instead of fixed delays where possible
- **Retries with backoff** on page load failures
- **Infinite scroll handling**: scroll, wait, count new items, stop after several empty rounds, hard safety limit
- **Multi-level crawling** with relative-to-absolute URL resolution (`urljoin`) and pagination
- **Fault tolerance**: failed pages are logged to `erreurs.json` instead of stopping the run
- **Data cleaning & validation**: whitespace/quote normalization, type conversion (price → float, rating → int, stock → int), removal of incomplete records and duplicates (by key / UPC)
- **Polite crawling**: configurable pause between requests, configurable scope (categories, max items)

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

## Run

```bash
python scrape_quotes_js.py
python scrape_quotes_scroll.py
python scrape_books_multiniveaux.py
```

Settings (target categories, limits, retries, pauses) are constants at the top of each script.

## Output fields (`livres.csv`)

`categorie`, `titre`, `prix_gbp`, `en_stock`, `quantite_stock`, `note_sur_5`, `upc`, `description`, `url`

The generated CSV/JSON files are included in the repository as sample outputs.

---

Author: **Julienne Ndereka** — Python developer (scraping, automation, bots, APIs).
The target sites are public sandboxes built for scraping practice.
