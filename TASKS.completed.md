# PRJ010 Tasks

## Status Legend
- 🔲 Open
- 🔄 In Progress
- ✅ Done
- ⏸️ Blocked

---

## T001: Confirm Search Parameters
**Status:** ✅ Done
**Assignee:** Coordinator
**Completed:** 2026-02-21

Mario confirmed:
- Search radius: 30km ✓
- Budget cap: None ✓
- Types: Buy + Rent ✓

---

## T002: Prepare Source List
**Status:** ✅ Done
**Assignee:** Researcher
**Completed:** 2026-02-20

Output: `data/sources.json` ✅

---

## T003-T007: Initial Property Search (All Cities)
**Status:** ✅ Done
**Assignee:** Researcher
**Completed:** 2026-02-20

Initial gathering:
- Freiburg: 7 candidates ✓
- Augsburg: 8 candidates ✓
- Halle: 7 candidates ✓
- Leipzig: 8 candidates ✓
- Magdeburg: 7 candidates ✓

**Total: 37 candidates**

---

## T008: Enrich Candidates & ImmoScout24 Browser Access
**Status:** 🔄 In Progress
**Assignee:** Coordinator + Sub-agents
**Started:** 2026-02-21
**Priority:** High

### Progress:
- [x] **Freiburg:** ENRICHED (10 candidates, 4 screenshots)
  - Output: `data/freiburg/candidates_enriched.json`
  - Screenshots: `assets/freiburg/screenshots/`
  - ImmoScout24 browser automation working ✓
  - Top pick: FR006 Littenweiler (Score 10/10)

- [ ] **Augsburg + Leipzig:** Sub-agent working (PRJ010-Enrichment-South)
- [ ] **Halle + Magdeburg:** Sub-agent working (PRJ010-Enrichment-East)

### Data Added:
- Transport time to city center (PT minutes)
- Nearest kindergarten/school (PT minutes)
- Suitability score (1-10)
- Pros/cons notes
- Screenshots for ImmoScout24 listings

---

## T009: Generate City Reports
**Status:** 🔄 In Progress
**Assignee:** Coordinator
**Priority:** Medium

- [x] Freiburg report: `report/freiburg.md` ✅
- [ ] Other cities: Pending enrichment

---

## T010: Build Static Site
**Status:** 🔄 In Progress  
**Assignee:** Coder Sub-agent (PRJ010-StaticSite)
**Started:** 2026-02-21

Building under `site/`:
- index.html - Main overview
- {city}.html - Per-city pages
- assets/ - Screenshots
- .nojekyll - GitHub Pages

---

## T011: Deploy to GitHub Pages
**Status:** 🔲 Open
**Assignee:** Coder
**Priority:** Low
**Depends:** T010

---

## T012: Facebook Groups Access
**Status:** ⏸️ Blocked - Needs Credentials
**Assignee:** Pending Mario

Facebook groups require login. Options:
1. Mario provides credentials for browser automation
2. Mario searches manually and shares links
3. Skip Facebook (other sources sufficient)

See: `notes/facebook-access.md`

---

## T013: Final Handover
**Status:** 🔲 Open
**Assignee:** Coordinator
**Priority:** High
**Depends:** T008, T009, T010

Deliverables:
- [ ] Live site link
- [ ] PDF/MD reports
- [ ] Raw data access
- [ ] Top 5 recommendations per city
