# PRJ010 — Wohngemeinschaft Property Search

## Objective
Find suitable properties (rent or buy) for two families seeking shared living arrangements in German cities:
- **Freiburg** and surrounding area (~30km)
- **Augsburg** and surrounding area (~30km)
- **Halle** and surrounding area (~30km)
- **Leipzig** and surrounding area (~30km)
- **Magdeburg** and surrounding area (~30km)

## Requirements

### Must-haves
- Minimum 2 bedrooms per family (4+ bedrooms total)
- Private quiet space for each family
- Shared communal space OR large outdoor area (garden/yard)
- Public transport connection to city center
- Proximity to nature preferred
- Some renovation acceptable

### Nice-to-haves
- Near kindergarten/school (walking or short public transport)
- Storage space
- Parking

## Deliverables
1. **Per-candidate reports**: Description, suitability assessment, price, pros/cons, link, 1+ image
2. **Consolidated report**: Summary per city with top recommendations
3. **Static website**: Hosted results for easy browsing (GitHub Pages)

## Data Sources
- Immobilienscout24
- Immowelt
- Immonet
- eBay Kleinanzeigen
- Regional portals
- Local real estate agencies (Makler)
- Facebook groups (city-specific)
- Municipal housing portals
- University housing boards
- Community noticeboards

## Project Structure
```
PRJ010-wohngemeinschaft/
├── README.md          # This file
├── PLAN.md            # Execution plan
├── TASKS.md           # Task breakdown
├── data/              # Raw JSON data per source/city
├── report/            # Markdown reports per city
└── site/              # Static site for GitHub Pages
```

## Status
🟢 **Initial Gathering Complete** — 36 candidates across 5 cities

### Progress
- ✅ Project structure created
- ✅ Source list compiled (20+ sources)
- ✅ Property searches completed (all 5 cities)
- ✅ Initial reports generated
- 🔄 Enrichment in progress
- 🔲 Static site pending

## Owner
Mario (requester) — Coordinator agent orchestrating
