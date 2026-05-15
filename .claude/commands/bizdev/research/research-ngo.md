# /bizdev/research/research-ngo

Research a specific NGO and save a structured brief to `scripts/research/`.

## Input: $ARGUMENTS

The NGO name, as listed on give.do or commonly known.

Examples:
- `/bizdev/research/research-ngo Pallium India`
- `/bizdev/research/research-ngo Trivandrum Don Bosco Veedu Society`

## Output

Saves a markdown file to:
```
workdocs/bizdev/research/{ngo-slug}.md
```

Where `ngo-slug` is the NGO name lowercased with spaces replaced by hyphens
(e.g., `pallium-india.md`).

## Steps

### 1. Find the give.do profile

Search give.do for the NGO:
- Try fetching: `https://give.do/discover/?q={NGO+Name}` 
- Or search web for: `site:give.do {NGO Name}`
- Identify their give.do profile URL (pattern: `give.do/discover/{ID}/{slug}/`)

Fetch the profile page and extract:
- Official name
- HQ location (city, state)
- Registration details (FCRA, 80G, 12A, CSR-1 status)
- Transparency/certification rating
- FY year and Total Revenue
- Total Expenses
- Sector / cause areas
- Brief description

### 2. Research leadership & contacts

Web search for:
- `"{NGO Name}" founder OR "executive director" OR CEO`
- `"{NGO Name}" board members`

Extract:
- Founder(s) with brief background if available
- Current leadership (ED/CEO name and title)
- Any publicly listed contact (email, phone) from their website or give.do

### 3. Research programs & focus areas

From give.do profile + web search:
- What programs do they run?
- Which geographies / states do they operate in?
- Who are their beneficiaries?
- Any notable funders, CSR partners, or government tie-ups mentioned?

### 4. Write the brief

Save to `/Users/rroy/Documents/dalgo-core/workdocs/bizdev/research/{ngo-slug}.md` using this template:

```markdown
# {NGO Name}

**Researched**: {date}
**give.do Profile**: {url}
**Location**: {city, state}

---

## At a Glance

| Field | Value |
|---|---|
| Sector | {sector/cause areas} |
| Founded | {year if known} |
| FY Revenue | {amount} ({FY year}) |
| FY Expenses | {amount} |
| Transparency | {rating} |
| Certifications | {FCRA / 80G / 12A / CSR-1} |

---

## Programs & Focus Areas

{2-4 sentences describing what they do, where they operate, and who they serve.}

**Key programs:**
- {Program 1}
- {Program 2}

**Geographies:** {states/districts}
**Beneficiaries:** {who they serve}

---

## Leadership & Contacts

| Name | Role |
|---|---|
| {Name} | {Founder / Executive Director / etc.} |

**Website**: {url if found}
**Contact**: {email or phone if publicly available}

---

## Notes

{Any other relevant context — funders, CSR partners, notable work, red flags, or open questions.}
```

### 5. Confirm

Tell the user:
```
Research saved to: workdocs/bizdev/research/{ngo-slug}.md

Key findings:
- Revenue: {amount} ({FY})
- Location: {city, state}
- Focus: {1-line summary}
```
