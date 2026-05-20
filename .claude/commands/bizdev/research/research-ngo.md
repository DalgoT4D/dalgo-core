# /bizdev/research/research-ngo

Research a specific NGO and log findings to the Research Google Sheet.

## Input: $ARGUMENTS

The NGO name, exactly as it appears in the scraper sheet.

Examples:
- `/bizdev/research/research-ngo Pallium India`
- `/bizdev/research/research-ngo Trivandrum Don Bosco Veedu Society`

## Output

Upserts a row (keyed by NGO name) into the **"NGO Research"** tab of the
research Google Sheet configured in `workdocs/bizdev/districts.json`.

Columns written:
`NGO Name | Profile URL | Cause Areas | Program Count | Impact Metric Count | Leadership | Researched At`

## Steps

### 1. Verify config

Check that `workdocs/bizdev/districts.json` exists and has a non-empty
`research_sheet_id`. If missing, stop and tell the user to run `/bizdev-setup`
or manually add `"research_sheet_id": "<sheet-id>"` to that file.

### 2. Run the profile scraper

```bash
python3 scripts/give_do_profile_scraper.py "<NGO Name>"
```

The script will:
1. Look up the NGO's give.do Profile URL from the scraper sheet (column "Profile URL"
   across all district tabs).
2. Fetch the profile page and extract:
   - **Cause areas** — category tags on the profile
   - **Program count** — number of program/project cards
   - **Impact metric count** — number of impact stat tiles
   - **Leadership** — names and LinkedIn links from the team section
3. Upsert the results into the "NGO Research" tab of the research sheet.

### 3. Report the result

After the script exits successfully, tell the user:

```
Research logged for: <NGO Name>

- Profile URL:    <url>
- Cause Areas:    <value>
- Programs:       <count>
- Impact Metrics: <count>
- Leadership:     <names>

Sheet: https://docs.google.com/spreadsheets/d/<research_sheet_id>/
```

### Troubleshooting

| Error | Fix |
|---|---|
| `research_sheet_id` not set | Add it to `workdocs/bizdev/districts.json` and share the sheet with the service account |
| NGO not found in any district tab | Run `bash scripts/run_scraper.sh` first to populate the scraper sheet |
| HTTP 403 on profile fetch | give.do may be rate-limiting; wait 60 s and retry |
| Cause areas / counts all "N/A" | give.do may have changed its HTML — inspect the page and update selectors in `scripts/give_do_profile_scraper.py` |
