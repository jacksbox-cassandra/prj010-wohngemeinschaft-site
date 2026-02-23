# PRJ010 — Property Search Automation Plan

**Created:** 2026-02-23  
**Status:** Implementation In Progress  
**Goal:** Fully automated property search with continuous monitoring, enrichment, and website updates

---

## 1. Current State Analysis

### Existing Infrastructure
- **36 candidates** across 5 cities (Freiburg, Augsburg, Halle, Leipzig, Magdeburg)
- **Data structure:** `data/{city}/candidates_enriched.json`
- **Website:** Static HTML in `docs/`, hosted on GitHub Pages
- **Generator:** `update_html_v3.py` - renders enriched data to HTML
- **Images:** Mixed - some photos, some screenshots, some placeholders

### Current Sources (from sources.json)
- **Major portals:** ImmobilienScout24, Immowelt, Immonet
- **Classifieds:** Kleinanzeigen (eBay)
- **Municipal:** Per-city housing cooperatives (FSB, LWB, etc.)
- **Local Makler:** ~15 agencies documented

### Gaps to Address
1. No automated scraping - all data collected manually
2. No duplicate detection
3. No listing status tracking (active/inactive)
4. Limited image coverage
5. No rent/buy filtering on website
6. Manual website regeneration
7. No notification system

---

## 2. New Data Sources to Add

### WG-Focused / Shared Living
| Source | URL | Notes |
|--------|-----|-------|
| WG-Gesucht | wg-gesucht.de | Large WG listings, API may be blocked |
| WG-Suche | wg-suche.de | Alternative WG portal |
| Habidat | habidat.org | Housing projects cooperative |
| Together Living | togetherliving.de | Intentional communities |

### Local Portals by City

#### Freiburg
- Badische Zeitung Immobilien: bz-immo.de
- Freiburg-Aktiv: freiburg-aktiv.de/immobilien
- Dreisamtäler (local newspaper)

#### Augsburg
- Augsburger Allgemeine Immobilien: immobilien.augsburger-allgemeine.de
- Augsburg City Portal
- Schwäbische Zeitung Immo

#### Leipzig
- LVZ Immobilien: lvz.de/immobilien
- Leipzig.de Wohnungsangebote
- Sachsenimmo: sachsenimmo.de

#### Halle
- MZ Immo (Mitteldeutsche Zeitung)
- Halle-Online Immobilien
- HWG - Hallesche Wohnungsgesellschaft

#### Magdeburg
- Volksstimme Immobilien: volksstimme.de
- WOBAU Magdeburg: wobau-magdeburg.de
- MWG Magdeburg: mwg-magdeburg.de

### Additional Aggregators
- Nestoria.de (meta-search)
- Mitula.de (aggregator)
- Green-Acres (eco-focus, rare)

---

## 3. Scraper Architecture

### Design Principles
1. **Modular source handlers** - each source gets its own parser class
2. **Respectful scraping** - honor robots.txt, rate limits, no bypassing
3. **Resumable** - can continue from where it left off
4. **Deduplication** - hash-based duplicate detection

### Core Components

```
scripts/
├── scraper.py          # Main orchestrator
├── sources/            # Source-specific handlers
│   ├── __init__.py
│   ├── base.py         # Base scraper class
│   ├── immoscout.py
│   ├── immowelt.py
│   ├── kleinanzeigen.py
│   └── ...
├── dedup.py            # Duplicate detection
├── validate.py         # Listing validation
└── utils.py            # Shared utilities
```

### Duplicate Detection Strategy
1. **Primary key:** Normalized URL
2. **Secondary hash:** `sha256(address + price + size)`
3. **Fuzzy matching:** Levenshtein on title + address for cross-source dedup
4. **Status tracking:** Mark listings as `new`, `active`, `updated`, `inactive`

### Validation Criteria (from requirements)
Must pass ALL to be included:
- [ ] 4+ bedrooms OR 4+ rooms + explicit space separation
- [ ] 120+ m² (minimum for 2 families)
- [ ] Has garden/outdoor OR large communal space
- [ ] Public transport reachable (manually verified or API)
- [ ] Within 30km radius of city center

### Data Flow
```
Sources → Raw Scrape → Validation Filter → Dedup → Merge with Existing → Enrichment Queue
```

### Rate Limiting
- 2-5 second delay between requests
- Rotate user agents
- Respect Retry-After headers
- Max 50 requests per source per run

---

## 4. Enrichment Pipeline

### Stage 1: Basic Enrichment
- **URL Validation:** HEAD request to verify listing still active
- **Image Extraction:** Download primary listing image
- **Address Parsing:** Normalize and geocode addresses

### Stage 2: Transport Calculation
**Method:** Use OpenRouteService or Google Maps API
- Input: Property address + city center coordinates
- Output: Transit time in minutes
- Fallback: Estimate based on straight-line distance

### Stage 3: Education Proximity
**Method:** Overpass API (OpenStreetMap) or Google Places
- Query: `amenity=kindergarten` and `amenity=school` within 2km
- Output: Nearest with walking distance/time

### Stage 4: Suitability Scoring
**Algorithm:**
```python
score = 0
# Size (max 2 points)
if size_sqm >= 180: score += 2
elif size_sqm >= 150: score += 1

# Bedrooms (max 2 points)
if bedrooms >= 5: score += 2
elif bedrooms >= 4: score += 1

# Outdoor (max 2 points)
if has_large_garden: score += 2
elif has_balcony_or_terrace: score += 1

# Transport (max 2 points)
if transit_mins <= 15: score += 2
elif transit_mins <= 25: score += 1

# Education (max 1 point)
if school_within_15min: score += 1

# Nature/Quiet (max 1 point)
if near_nature or quiet_area: score += 1

# Total: 0-10
```

### Stage 5: Pros/Cons Generation
- Template-based from feature flags
- LLM-assisted summary for complex cases

---

## 5. Website Update Strategy

### New Features

#### A. Rent/Buy Filter
- Toggle buttons at top of city pages
- URL parameter: `?type=rent` or `?type=buy`
- JavaScript filter (no page reload)

#### B. Sort Options
- Price (low → high, high → low)
- Size (m²)
- Score (best first)
- Date added (newest first)

#### C. Status Badges
- 🆕 NEW - Added in last 48h
- 🔄 UPDATED - Price or details changed
- ⚠️ CHECK - May be inactive (503/404 on verify)
- 🔴 GONE - Confirmed removed

#### D. Image Galleries
- Primary image in card (existing)
- Click to expand lightbox with all images
- Lazy loading for performance

#### E. Mobile Improvements
- Better touch targets
- Swipeable image galleries
- Sticky filter bar

### Smart Regeneration
- Track file hashes to avoid unnecessary git commits
- Only regenerate city pages with data changes
- Generate changelog in commit message

### File Structure Update
```
docs/
├── index.html          # Dashboard
├── {city}.html         # City pages
├── js/
│   ├── filters.js      # Client-side filtering
│   └── gallery.js      # Image lightbox
├── css/
│   └── style.css       # (moved from assets/)
└── assets/
    └── {city}/
        └── photos/
```

---

## 6. Cron Job Configuration

### Schedule
- **Frequency:** Every 2 days (00:00 UTC)
- **Runtime:** ~15-30 minutes estimated

### Workflow
```
1. Pull latest data from git
2. Run scraper.py for all cities
3. Run enrich.py for new/updated listings
4. Run update_html_v3.py (enhanced)
5. Commit changes to docs/
6. Push to GitHub (triggers Pages rebuild)
7. Generate email report
8. Send notification to jacksbot@jacksbox.de
```

### Email Report Contents
- New listings found (with highlights)
- Updated listings
- Removed listings
- Top 5 recommendations
- Any errors/warnings

### Cron Task File
```
CRON-property-search.md
├── Schedule: 0 0 */2 * *
├── Agent: worker
├── Notify: jacksbot@jacksbox.de
└── Script: scripts/run_search.sh
```

---

## 7. Implementation Tasks

### Phase A: Infrastructure (Coder #1)
- [ ] Create `scripts/` directory structure
- [ ] Build base scraper class with rate limiting
- [ ] Implement deduplication module
- [ ] Build validation module
- [ ] Create unified config (`config.yaml`)

### Phase B: Source Handlers (Coder #2)
- [ ] ImmobilienScout24 handler
- [ ] Immowelt handler  
- [ ] Kleinanzeigen handler
- [ ] Immonet handler
- [ ] WG-Gesucht handler (if accessible)

### Phase C: Enrichment (Coder #1)
- [ ] URL verification
- [ ] Image downloader
- [ ] Transport time calculator
- [ ] School finder
- [ ] Scoring algorithm
- [ ] Pros/cons generator

### Phase D: Website (Coder #2)
- [ ] Add filtering JavaScript
- [ ] Add sort functionality
- [ ] Add status badges
- [ ] Update CSS for new features
- [ ] Update generator for new fields

### Phase E: Cron & Deploy (Coordinator)
- [ ] Create run_search.sh wrapper
- [ ] Create CRON-property-search.md
- [ ] Register cron job
- [ ] Test full pipeline
- [ ] Verify GitHub Pages auto-update

---

## 8. Constraints & Ethics

### Technical
- Respect `robots.txt` on all sources
- No credential stuffing or bypasses
- Use official APIs where available
- Graceful handling of blocks

### Data Privacy
- Never publish personal contact details
- Blur/remove agent faces from images
- Anonymize any personal data in listings

### Quality
- All listings must meet validation criteria
- Manual review for edge cases
- Clear provenance tracking

---

## 9. Deliverables Checklist

- [ ] `PLAN-AUTOMATION.md` (this file)
- [ ] `scripts/scraper.py`
- [ ] `scripts/enrich.py`
- [ ] `scripts/sources/*.py`
- [ ] `scripts/config.yaml`
- [ ] `scripts/run_search.sh`
- [ ] Updated `update_html_v3.py`
- [ ] Updated website with filters/galleries
- [ ] `CRON-property-search.md`
- [ ] Working cron job
- [ ] GitHub Pages auto-updates verified
- [ ] Email notification working

---

## 10. Success Criteria

1. **Scraper runs without errors** on all 5 cities
2. **Duplicates detected** across sources
3. **Website regenerates** with new data
4. **GitHub Pages updates** automatically after git push
5. **Email report sent** after each run
6. **Cron executes** reliably every 2 days

---

*Last Updated: 2026-02-23*
