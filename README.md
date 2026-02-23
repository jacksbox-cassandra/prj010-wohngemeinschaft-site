# PRJ010 — Wohngemeinschaft Property Search

## 🏠 Overview
Automated property search system for two families seeking shared living arrangements in German cities.

**Live Site:** https://jacksbox-cassandra.github.io/prj010-wohngemeinschaft-site/

## Target Cities (30km radius each)
- **Freiburg** 🏔️
- **Augsburg** 🏰
- **Halle (Saale)** 🏛️
- **Leipzig** 🎵
- **Magdeburg** 🌊

## Requirements

### Must-haves
- Minimum 4+ bedrooms (2 per family)
- Private quiet space for each family
- Shared communal space OR large outdoor area (garden/yard)
- Public transport connection to city center
- Proximity to nature preferred
- Some renovation acceptable

### Nice-to-haves
- Near kindergarten/school (walking or short public transport)
- Storage space
- Parking

## 🤖 Automation System

### Automated Scraping (every 2 days)
```bash
./scripts/run_search.sh
```

### Components
- **Scraper** (`scripts/scraper.py`) - Multi-source property collection
- **Enrichment** (`scripts/enrich.py`) - URL verification, images, transport times, scoring
- **Validation** (`scripts/validate.py`) - Filter by criteria
- **Deduplication** (`scripts/dedup.py`) - Cross-source duplicate detection
- **Website Generator** (`update_html_v3.py`) - Static site generation

### Sources
- ImmobilienScout24
- Immowelt
- Kleinanzeigen (eBay)
- (More sources in `scripts/config.yaml`)

### Configuration
Edit `scripts/config.yaml` to:
- Enable/disable sources
- Adjust search criteria
- Change rate limiting
- Modify scoring weights

## Project Structure
```
PRJ010-wohngemeinschaft/
├── README.md                  # This file
├── PLAN.md                    # Original execution plan
├── PLAN-AUTOMATION.md         # Automation system plan
├── CRON-property-search.md    # Cron job specification
├── scripts/
│   ├── config.yaml           # Central configuration
│   ├── scraper.py            # Main scraper
│   ├── enrich.py             # Enrichment pipeline
│   ├── validate.py           # Validation
│   ├── dedup.py              # Deduplication
│   ├── run_search.sh         # Cron wrapper script
│   └── sources/              # Source handlers
├── data/                      # JSON data per city
├── docs/                      # Static website (GitHub Pages)
│   ├── index.html
│   ├── {city}.html
│   ├── js/                   # Client-side filtering
│   └── assets/               # Images & CSS
├── report/                    # Generated reports
└── logs/                      # Run logs
```

## 📊 Current Status

**🟢 FULLY AUTOMATED**

| Milestone | Status |
|-----------|--------|
| Initial data collection | ✅ 50 candidates |
| Enrichment pipeline | ✅ Built |
| Website with filters | ✅ Live |
| Automated scraping | ✅ Cron job active |
| GitHub Pages | ✅ Auto-deploys |
| Email notifications | ✅ Configured |

### Cron Schedule
- **Frequency:** Every 2 days at midnight (Europe/Berlin)
- **Agent:** worker
- **Notification:** jacksbot@jacksbox.de

## 🚀 Manual Execution

```bash
# Full run
cd /Users/jacksbot/projects/PRJ010-wohngemeinschaft
./scripts/run_search.sh

# Individual commands
python3 scripts/scraper.py --cities freiburg --dry-run
python3 scripts/enrich.py --city freiburg
python3 update_html_v3.py
```

## 📈 Website Features
- Filter by property type (buy/rent)
- Sort by price, size, score
- Search by title/location
- Status badges (New, Updated, Inactive)
- Image gallery with lightbox
- Mobile responsive

## Owner
Mario (requester)

---
*Last updated: 2026-02-23 | Automation by OpenClaw*
