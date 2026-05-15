# /bizdev/scraping/add-district

Register a new give.do district so that `/bizdev/scraping/refresh-source` picks it up on future runs.

## Input: $ARGUMENTS

The district name as it appears in the give.do URL.

Examples:
- `/bizdev/scraping/add-district Kochi`
- `/bizdev/scraping/add-district Bengaluru`

## Steps

### 1. Parse the input

Extract the district name from `$ARGUMENTS`.

### 2. Derive the give.do URL

give.do district URLs follow a consistent pattern:
```
https://give.do/discover/project-district/{DistrictName}/
```

Construct the URL from the district name. Handle spaces with URL encoding if needed
(e.g., "New Delhi" → `New%20Delhi`), but first try the name as-is since most district
names are single words.

### 3. Validate the URL

Fetch the URL using `mcp__workspace__web_fetch` and check:
- The page returns results (look for "Showing X NGOs")
- If the page shows 0 results or errors, tell the user the district name may be wrong
  and suggest checking https://give.do/discover/ for the correct spelling

Extract and show the user:
- Total NGO count found
- A few example NGO names from the first page

### 4. Confirm the sheet tab name

Ask the user: "I'll create a sheet tab called '{DistrictName}'. Is that the right name,
or would you like a different tab name?"

Wait for confirmation.

### 5. Register in districts.json

Read `/Users/rroy/Documents/dalgo-core/workdocs/bizdev/districts.json`,
add the new entry to the `districts` array, and write it back:

```json
{
  "name": "{DistrictName}",
  "url": "https://give.do/discover/project-district/{DistrictName}/",
  "tab": "{TabName}"
}
```

### 6. Confirm

Print:
```
✅ {DistrictName} registered.
   URL : https://give.do/discover/project-district/{DistrictName}/
   Tab : {TabName}
   NGOs: {count} found on give.do

Run /bizdev/scraping/refresh-source to scrape it now along with all other districts.
```
