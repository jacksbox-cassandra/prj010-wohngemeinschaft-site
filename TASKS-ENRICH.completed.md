TASK 0009 — Enrich all candidates and add images

Owner: Coordinator

Acceptance criteria:
- Every candidate across all five cities has an "enriched" entry (fields: id, title, link, price, rooms, area, garden/outdoor flag, transport_time_to_center_minutes, nearest_kindergarten_pt_minutes, nearest_school_pt_minutes, pros_cons, suitability_note).
- Each candidate has at least one property image stored locally under site/assets/{city}/photos/{candidateId}.jpg (not full-page screenshots; crop/resize if needed). If the listing lacks images, record "no_image_available".
- The site in the docs/ folder is updated to include the enriched data and images (per-city pages list candidates with image, price, key stats, pros/cons, and link to original listing).
- Commit and push changes to the remote repo (origin main).

Instructions:
1) Use project path: /Users/jacksbot/projects/PRJ010-wohngemeinschaft as the working directory.
2) For each city (freiburg, augsburg, leipzig, halle, magdeburg):
   - Load data/{city}/candidates_enriched.json if exists; otherwise load candidates.json and enrich it.
   - If enrichment fields are missing, fetch the missing info by visiting the original listing (use headful Playwright if the site blocks automated fetches).
   - Extract and save a single representative property photo for each candidate to site/assets/{city}/photos/{id}.jpg. Crop/resize to 1200x800 max. Respect robots/ToS and do not collect private contact data.
3) Update docs/ (or docs/{city}.html) to display image thumbnails (linked to full-size image), enriched fields, and pros/cons. Ensure pages are mobile-friendly.
4) Run a local link-check to ensure all links to original listings are live (HTTP 200) and log any dead links to notes/dead_links.md.
5) Commit changes with message "Enrich candidates + add photos" and push to origin main.
6) Leave a progress report in report/progress-RE-ENRICH.md with numbers: total candidates, enriched count, images collected, dead links.

Constraints:
- Do not bypass CAPTCHAs. If a listing site blocks automated fetches, use headful Playwright and record screenshots of the listing page in site/assets/{city}/screenshots/{id}.png (only when needed). Do not include screenshots on the site unless no property photo exists.
- Do not store or publish any sensitive info or scraped contact details.

Start immediately and report back when done.
