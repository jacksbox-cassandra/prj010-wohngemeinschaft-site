# PRJ010 Execution Plan

## Phase 1: Setup & Confirmation (Day 1)
- [x] Create project structure
- [ ] Confirm search parameters with Mario (radius, budget, filters)
- [ ] Prepare comprehensive source list per city

## Phase 2: Data Collection (Days 2-5)
For each city (Freiburg, Augsburg, Halle, Leipzig, Magdeburg):
1. Search major portals (ImmobilienScout24, Immowelt, Immonet)
2. Check eBay Kleinanzeigen
3. Search regional/local sources
4. Document FB groups (links only, manual check recommended)
5. Check municipal and university housing boards
6. Store raw results in `data/{city}/`

### Search Criteria
- Bedrooms: 4+ (or 3+ with large additional space)
- Property type: House, large apartment, multi-unit
- Features: Garden/outdoor space, multiple bathrooms preferred
- Radius: 30km from city center (default, awaiting confirmation)
- Price: No cap (default, awaiting confirmation)
- Both rent and purchase options

## Phase 3: Enrichment (Days 5-7)
- Calculate public transport times to city center
- Find nearest kindergarten/school with transport time
- Capture 1+ image per listing
- Score suitability based on must-haves

## Phase 4: Reporting (Days 7-8)
- Generate per-city reports in `report/{city}.md`
- Create consolidated summary report
- Build static site with index and city pages
- Host on GitHub Pages

## Phase 5: Delivery
- Notify Mario with links to:
  - Live site
  - Report files
  - Raw data

## Constraints
- Respect robots.txt and ToS
- No bypassing of site protections
- Use Playwright for interactive/blocked sources
- Do not publish contact data publicly
- Ask Mario if credentials or paid APIs are needed

## Timeline
- Start: 2026-02-21
- Initial candidate gathering: ~Day 5
- Final delivery: ~Day 8
