# /bizdev/scraping/refresh-source

Re-scrape all districts registered in `scripts/districts.json` and push fresh data to Google Sheets.

## What it does

Runs `scripts/run_scraper.sh` which loops through every district in `scripts/districts.json`, scrapes the
give.do listing pages, and writes results to the corresponding sheet tabs.

## Steps

1. Run the bash script using `mcp__workspace__bash` with `timeout_ms: 120000`:

```bash
bash "/Users/rroy/Documents/dalgo-core/scripts/run_scraper.sh"
```

2. Stream the output so the user can see progress per district.

3. When complete, report:
   - How many districts were scraped
   - How many NGOs were found per district
   - Confirm the sheet was updated
   - Link: https://docs.google.com/spreadsheets/d/1tQI1lpzm2xpjBfMNylC-S7BxLbP5uI6cNunlDxVsXpk/

4. If the script errors, show the full output and suggest the most likely fix
   (missing dependency, Sheets permission, network issue, etc.).
