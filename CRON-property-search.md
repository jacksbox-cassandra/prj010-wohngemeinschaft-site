# CRON Task: Property Search Automation

## Task ID
`property-search-update`

## Schedule
```
0 0 */2 * *
```
Every 2 days at midnight (00:00 UTC / 01:00 CET)

## Agent
`worker`

## Project
PRJ010 — Wohngemeinschaft Property Search

## Description
Automated property search across 5 German cities for shared living arrangements.

## Execution Steps

1. **Navigate to project**
   ```bash
   cd /Users/jacksbot/projects/PRJ010-wohngemeinschaft
   ```

2. **Pull latest changes**
   ```bash
   git pull origin main
   ```

3. **Run the search pipeline**
   ```bash
   ./scripts/run_search.sh
   ```

4. **Send email report**
   - Recipient: jacksbot@jacksbox.de
   - Subject: "🏠 Property Search Update - [DATE]"
   - Include:
     - New listings found
     - Updated listings
     - Removed listings
     - Top 5 recommendations
     - Any errors/warnings

## Expected Output

### Success
- `data/{city}/candidates_enriched.json` updated with new listings
- `docs/*.html` regenerated with latest data
- Changes committed and pushed to GitHub
- GitHub Pages automatically rebuilds
- Email report sent

### Failure Handling
- If scraper fails: continue with enrichment of existing data
- If enrichment fails: still regenerate website
- If push fails: send error notification
- Always send email (success or failure report)

## Files Involved
- `scripts/run_search.sh` - Main wrapper script
- `scripts/scraper.py` - Property scraper
- `scripts/enrich.py` - Enrichment pipeline
- `update_html_v3.py` - Website generator
- `data/*/candidates_enriched.json` - Property data
- `docs/` - Generated website

## Notifications
- **On Success:** Email with summary stats
- **On Failure:** Email with error details
- **Recipient:** jacksbot@jacksbox.de

## Constraints
- Respect robots.txt on all sources
- Use rate limiting (2-5 sec between requests)
- Don't bypass anti-bot measures
- Keep runtime under 30 minutes

## Last Run
_Not yet executed_

## History
| Date | Status | New | Updated | Removed | Notes |
|------|--------|-----|---------|---------|-------|
| - | - | - | - | - | Initial setup |

---

## Manual Trigger

To run manually:
```bash
cd /Users/jacksbot/projects/PRJ010-wohngemeinschaft
./scripts/run_search.sh
```

Or via OpenClaw:
```bash
openclaw cron trigger property-search-update
```
