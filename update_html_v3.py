#!/usr/bin/env python3
"""
Update HTML v3 - Unified City Page Generator
Generates consistent HTML pages for all cities from enriched JSON data.
Enhanced with filtering, status badges, and gallery support.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from html import escape

# Configuration
PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
DOCS_DIR = PROJECT_DIR / "docs"
REPORT_DIR = PROJECT_DIR / "report"
ASSETS_DIR = DOCS_DIR / "assets"

CITIES = ["freiburg", "augsburg", "leipzig", "halle", "magdeburg"]

CITY_EMOJIS = {
    "freiburg": "🏔️",
    "augsburg": "🏰",
    "leipzig": "🎵",
    "halle": "🏛️",
    "magdeburg": "🌊"
}

CITY_DISPLAY_NAMES = {
    "freiburg": "Freiburg",
    "augsburg": "Augsburg",
    "leipzig": "Leipzig",
    "halle": "Halle (Saale)",
    "magdeburg": "Magdeburg"
}

# Required fields per listing
REQUIRED_FIELDS = [
    "id", "title", "description", "price", "rooms", "size_sqm",
    "transport", "education", "suitability"
]

OPTIONAL_FIELDS = [
    "garden", "outdoor", "features", "plot_sqm", "bedrooms"
]


def load_enriched_data(city: str) -> dict:
    """Load the enriched candidates JSON for a city."""
    json_path = DATA_DIR / city / "candidates_enriched.json"
    if not json_path.exists():
        print(f"Warning: {json_path} not found")
        return {"candidates": []}
    
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_listing_status(candidate: dict, enriched_date: str) -> str:
    """
    Determine listing status based on fetch date and data.
    Returns: 'new', 'updated', 'inactive', or 'active'
    """
    fetch_date_str = candidate.get("fetchedAt", "")
    if not fetch_date_str:
        return "active"
    
    try:
        # Parse enriched date
        if enriched_date.endswith('+01:00'):
            enriched_datetime = datetime.fromisoformat(enriched_date.replace('+01:00', ''))
        else:
            enriched_datetime = datetime.fromisoformat(enriched_date)
        
        # Check if listing is new (last 48h)
        two_days_ago = enriched_datetime - timedelta(days=2)
        
        # Parse fetch date 
        try:
            fetch_datetime = datetime.fromisoformat(fetch_date_str)
        except:
            # Try alternative date format
            fetch_datetime = datetime.strptime(fetch_date_str, "%Y-%m-%d")
        
        if fetch_datetime >= two_days_ago:
            return "new"
        
        # Check if marked as inactive
        if candidate.get("status") == "inactive":
            return "inactive"
        
        # Check if data was updated (price change, etc)
        if candidate.get("updated"):
            return "updated"
        
        return "active"
        
    except Exception as e:
        return "active"


def get_status_badge_html(status: str) -> str:
    """Get HTML for status badge."""
    badges = {
        "new": '<span class="status-badge status-new">🆕 NEW</span>',
        "updated": '<span class="status-badge status-updated">🔄 UPDATED</span>',
        "inactive": '<span class="status-badge status-inactive">⚠️ INACTIVE</span>',
        "active": ""
    }
    return badges.get(status, "")


def find_image_paths(city: str, candidate_id: str) -> list:
    """
    Find all images for a candidate. Returns list of (path, exists) tuples.
    Checks photos/{id}.jpg first, then screenshots folder, supports multiple images.
    """
    images = []
    
    # Check photos folder first
    photos_dir = ASSETS_DIR / city / "photos"
    photo_path = photos_dir / f"{candidate_id}.jpg"
    if photo_path.exists():
        images.append((f"assets/{city}/photos/{candidate_id}.jpg", True))
    
    # Check for additional numbered images  
    for i in range(2, 6):  # Check for {id}_2.jpg, {id}_3.jpg, etc.
        photo_path = photos_dir / f"{candidate_id}_{i}.jpg"
        if photo_path.exists():
            images.append((f"assets/{city}/photos/{candidate_id}_{i}.jpg", True))
    
    # Check screenshots folder (for Freiburg ImmoScout captures)
    screenshots_dir = ASSETS_DIR / city / "screenshots"
    if screenshots_dir.exists():
        for f in screenshots_dir.iterdir():
            if f.suffix.lower() in ['.jpg', '.jpeg', '.png'] and candidate_id in f.stem:
                images.append((f"assets/{city}/screenshots/{f.name}", True))
    
    # If no images found, return placeholder
    if not images:
        images.append(("assets/placeholder.jpg", False))
    
    return images


def find_image_path(city: str, candidate_id: str) -> tuple:
    """
    Find image for a candidate. Returns (path, exists) tuple.
    Checks photos/{id}.jpg first, then screenshots folder.
    """
    # Check photos folder first
    photos_dir = ASSETS_DIR / city / "photos"
    photo_path = photos_dir / f"{candidate_id}.jpg"
    if photo_path.exists():
        return f"assets/{city}/photos/{candidate_id}.jpg", True
    
    # Check screenshots folder (for Freiburg ImmoScout captures)
    screenshots_dir = ASSETS_DIR / city / "screenshots"
    if screenshots_dir.exists():
        for f in screenshots_dir.iterdir():
            if f.suffix.lower() in ['.jpg', '.jpeg', '.png'] and candidate_id in f.stem:
                return f"assets/{city}/screenshots/{f.name}", True
    
    # Also check if image is specified in the data
    return "assets/placeholder.jpg", False


def get_score_class(score: int) -> str:
    """Get CSS class for score badge."""
    if score >= 8:
        return ""
    elif score >= 6:
        return "medium"
    return "low"


def parse_transport_minutes(transport_data: dict) -> str:
    """Extract transport time in minutes from transport dict."""
    if not transport_data:
        return "—"
    
    to_center = transport_data.get("toCityCenter", "")
    if not to_center:
        return "—"
    
    # Try to extract minutes
    import re
    match = re.search(r'(\d+)\s*min', to_center, re.IGNORECASE)
    if match:
        return f"{match.group(1)} min"
    return to_center


def parse_education_minutes(education_data: dict, key: str) -> str:
    """Extract education walking time from education dict."""
    if not education_data:
        return "—"
    
    value = education_data.get(key, "")
    if not value:
        return "—"
    
    # Try to extract minutes
    import re
    match = re.search(r'~?(\d+)\s*min', value, re.IGNORECASE)
    if match:
        return f"~{match.group(1)} min"
    return value


def has_garden_or_outdoor(candidate: dict) -> bool:
    """Check if candidate has garden/outdoor feature."""
    features = candidate.get("features", [])
    if not features:
        features = []
    
    garden_keywords = ["garden", "garten", "outdoor", "terrasse", "balkon", "pool"]
    
    for feature in features:
        if any(kw in feature.lower() for kw in garden_keywords):
            return True
    
    return False


def format_price(price: float, price_type: str = "buy") -> str:
    """Format price for display with type indication."""
    if not price:
        return "—"
    
    formatted = f"€{price:,.0f}".replace(",", ".")
    
    if price_type == "rent":
        return f"{formatted}/Monat"
    else:  # buy
        return formatted


def truncate_text(text: str, max_len: int = 150) -> str:
    """Truncate text with ellipsis."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(' ', 1)[0] + "…"


def render_candidate_card(candidate: dict, city: str, enriched_date: str) -> str:
    """Render a single candidate card HTML with enhanced features."""
    cid = candidate.get("id", "???")
    title = escape(candidate.get("title", "Untitled"))
    location = escape(candidate.get("location", "—"))
    price = candidate.get("price", 0)
    price_type = candidate.get("priceType", "buy")
    rooms = candidate.get("rooms", 0)
    size_sqm = candidate.get("size_sqm", 0)
    bedrooms = candidate.get("bedrooms")
    description = escape(truncate_text(candidate.get("description", ""), 180))
    
    # Status
    status = get_listing_status(candidate, enriched_date)
    status_badge = get_status_badge_html(status)
    
    # Suitability
    suitability = candidate.get("suitability", {})
    score = suitability.get("score", 0)
    pros = suitability.get("pros", [])
    cons = suitability.get("cons", [])
    
    # Transport & Education
    transport = candidate.get("transport", {})
    education = candidate.get("education", {})
    
    transport_center = parse_transport_minutes(transport)
    kinder_time = parse_education_minutes(education, "nearestKindergarten")
    school_time = parse_education_minutes(education, "nearestSchool")
    
    # Images
    images = find_image_paths(city, cid)
    primary_img = images[0]
    has_gallery = len(images) > 1
    
    listing_url = candidate.get("listingUrl", "#")
    
    # Garden/outdoor
    has_garden = has_garden_or_outdoor(candidate)
    
    # Data attributes for filtering
    data_attrs = f'data-type="{price_type}" data-score="{score}" data-price="{price}" data-size="{size_sqm}" data-id="{cid}"'
    if status != "active":
        data_attrs += f' data-status="{status}"'
    
    # Build HTML
    score_class = get_score_class(score)
    
    # Image section with gallery support
    if primary_img[1]:  # Image exists
        gallery_class = " has-gallery" if has_gallery else ""
        img_html = f'''<div class="candidate-image{gallery_class}" onclick="openGallery('{cid}')">
            <img src="{primary_img[0]}" alt="{cid}" onerror="this.parentElement.innerHTML='🏠'">
            {f'<div class="gallery-badge">📷 {len(images)}</div>' if has_gallery else ''}
        </div>'''
        
        # Hidden gallery images for lightbox
        gallery_data = json.dumps([img[0] for img in images if img[1]])
        img_html += f'<script>window.galleries = window.galleries || {{}}; window.galleries["{cid}"] = {gallery_data};</script>'
    else:
        img_html = '''<div class="candidate-image"><div class="image-placeholder">🏠</div></div>'''
    
    # Pros HTML
    pros_html = ""
    if pros:
        pros_items = "".join(f"<li>{escape(str(p))}</li>" for p in pros[:4])
        pros_html = f'''<div class="pros"><h4>Vorteile</h4><ul>{pros_items}</ul></div>'''
    
    # Cons HTML
    cons_html = ""
    if cons:
        cons_items = "".join(f"<li>{escape(str(c))}</li>" for c in cons[:3])
        cons_html = f'''<div class="cons"><h4>Nachteile</h4><ul>{cons_items}</ul></div>'''
    
    # Meta badges
    meta_items = []
    if size_sqm:
        meta_items.append(f"<span>{size_sqm} m²</span>")
    if rooms:
        meta_items.append(f"<span>{rooms} Zimmer</span>")
    if bedrooms:
        meta_items.append(f"<span>{bedrooms} Schlafzimmer</span>")
    if has_garden:
        meta_items.append(f'<span class="highlight">🌳 Garten/Outdoor</span>')
    
    meta_html = "".join(meta_items)
    
    return f'''
        <div class="candidate-card" {data_attrs}>
            {img_html}
            <div class="candidate-body">
                <div class="candidate-header">
                    <span class="candidate-id">{cid}</span>
                    {status_badge}
                    <span class="candidate-score {score_class}">{score}/10</span>
                </div>
                <h3 class="candidate-title">{title}</h3>
                <p class="candidate-location">📍 {location}</p>
                <p class="candidate-price">{format_price(price, price_type)}</p>
                <div class="candidate-meta">{meta_html}</div>
                {f'<p class="candidate-description">{description}</p>' if description else ''}
                <div class="candidate-pros-cons">
                    {pros_html}
                    {cons_html}
                </div>
                <div class="candidate-info-grid">
                    <div class="info-box">
                        <div class="info-label">🚌 Innenstadt</div>
                        <div class="info-value">{transport_center}</div>
                    </div>
                    <div class="info-box education">
                        <div class="info-label">🏫 Kindergarten / Schule</div>
                        <div class="info-value">{kinder_time} / {school_time}</div>
                    </div>
                </div>
                <a href="{listing_url}" class="btn" target="_blank">Inserat ansehen →</a>
            </div>
        </div>'''


def generate_city_page(city: str, data: dict, missing_fields: dict) -> str:
    """Generate the full HTML page for a city."""
    candidates = data.get("candidates", [])
    city_name = CITY_DISPLAY_NAMES.get(city, city.title())
    emoji = CITY_EMOJIS.get(city, "🏠")
    enriched_date = data.get("enrichedAt", "")
    
    # Count images
    images_found = 0
    images_missing = 0
    for c in candidates:
        images = find_image_paths(city, c.get("id", ""))
        if any(img[1] for img in images):
            images_found += 1
        else:
            images_missing += 1
    
    # Count by type
    buy_count = len([c for c in candidates if c.get("priceType") == "buy"])
    rent_count = len([c for c in candidates if c.get("priceType") == "rent"])
    
    # Find top picks (score >= 9)
    top_picks = [c for c in candidates if c.get("suitability", {}).get("score", 0) >= 9]
    top_picks_html = ""
    if top_picks:
        picks = " | ".join([f"<strong>{c['id']}</strong> - {truncate_text(c['title'], 40)} (€{c.get('price', 0):,.0f})" for c in top_picks[:3]])
        top_picks_html = f'''
        <div class="top-banner">
            <h3>🌟 Top-Empfehlungen für {city_name}</h3>
            <p>{picks}</p>
        </div>'''
    
    # Track missing fields
    city_missing = {}
    for c in candidates:
        cid = c.get("id", "unknown")
        for field in REQUIRED_FIELDS:
            if field == "transport":
                if not c.get("transport") or not c.get("transport", {}).get("toCityCenter"):
                    city_missing.setdefault(field, []).append(cid)
            elif field == "education":
                edu = c.get("education", {})
                if not edu or (not edu.get("nearestKindergarten") and not edu.get("nearestSchool")):
                    city_missing.setdefault(field, []).append(cid)
            elif field == "suitability":
                suit = c.get("suitability", {})
                if not suit or "score" not in suit:
                    city_missing.setdefault(field, []).append(cid)
            elif not c.get(field):
                city_missing.setdefault(field, []).append(cid)
    
    missing_fields[city] = city_missing
    
    # Render candidate cards
    cards_html = "\n".join([render_candidate_card(c, city, enriched_date) for c in candidates])
    
    # Generate page
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Filter bar HTML
    filter_bar_html = f'''
    <div class="filter-bar" id="filterBar">
        <div class="filter-group">
            <label>Typ:</label>
            <button class="filter-btn active" data-filter="all">Alle ({len(candidates)})</button>
            <button class="filter-btn" data-filter="buy">Kauf ({buy_count})</button>
            <button class="filter-btn" data-filter="rent">Miete ({rent_count})</button>
        </div>
        <div class="filter-group">
            <label>Sortieren:</label>
            <select class="sort-select" id="sortSelect">
                <option value="score">Bewertung (hoch → niedrig)</option>
                <option value="price-asc">Preis (niedrig → hoch)</option>
                <option value="price-desc">Preis (hoch → niedrig)</option>
                <option value="size">Größe (groß → klein)</option>
                <option value="id">ID (A → Z)</option>
            </select>
        </div>
        <div class="filter-group search-group">
            <label>Suche:</label>
            <input type="text" class="search-input" id="searchInput" placeholder="Titel oder Ort...">
            <button class="clear-btn" id="clearSearch">✕</button>
        </div>
    </div>'''
    
    return f'''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{city_name} - Wohngemeinschaft Kandidaten</title>
    <link rel="stylesheet" href="assets/style.css">
</head>
<body>
    <header>
        <div class="breadcrumb"><a href="index.html">← Zurück zur Übersicht</a></div>
        <h1>{emoji} {city_name} - {len(candidates)} Kandidaten</h1>
        <p class="header-meta">{images_found} mit Foto • {images_missing} ohne Foto • {buy_count} Kauf • {rent_count} Miete</p>
    </header>

    <div class="container">
        {top_picks_html}
        {filter_bar_html}
        <div class="candidates-grid" id="candidatesGrid">
            {cards_html}
        </div>
        <div class="no-results" id="noResults" style="display: none;">
            <p>Keine Immobilien gefunden, die den Filterkriterien entsprechen.</p>
        </div>
    </div>

    <footer class="page-footer">
        <p>Generiert am {generated_at} • Daten aus candidates_enriched.json</p>
    </footer>
    
    <script src="js/filters.js"></script>
    <script src="js/gallery.js"></script>
</body>
</html>'''


def validate_html_links(city: str) -> list:
    """Check that image links resolve correctly."""
    issues = []
    html_path = DOCS_DIR / f"{city}.html"
    
    if not html_path.exists():
        return [f"HTML file not found: {html_path}"]
    
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    import re
    # Find image src attributes
    img_srcs = re.findall(r'src="(assets/[^"]+)"', content)
    for src in img_srcs:
        full_path = DOCS_DIR / src
        if not full_path.exists() and 'placeholder' not in src:
            issues.append(f"Missing image: {src}")
    
    return issues


def update_index_page():
    """Update the index.html with current data and timestamp."""
    # Read current index.html
    index_path = DOCS_DIR / "index.html"
    if not index_path.exists():
        print(f"Warning: {index_path} not found")
        return
        
    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Calculate total statistics
    total_candidates = 0
    total_buy = 0
    total_rent = 0
    
    for city in CITIES:
        data = load_enriched_data(city)
        candidates = data.get("candidates", [])
        total_candidates += len(candidates)
        
        for candidate in candidates:
            if candidate.get("priceType") == "rent":
                total_rent += 1
            else:
                total_buy += 1
    
    # Update the stats
    import re
    
    # Update total candidates
    content = re.sub(
        r'<div class="number">\d+</div>\s*<div class="label">Kandidaten gesamt</div>',
        f'<div class="number">{total_candidates}</div>\n                <div class="label">Kandidaten gesamt</div>',
        content
    )
    
    # Update timestamp in footer script (more robust pattern)
    generated_at = datetime.now().strftime("%d. %B %Y, %H:%M")
    content = re.sub(
        r"document\.getElementById\('lastUpdate'\)\.textContent = .*?;",
        f"document.getElementById('lastUpdate').textContent = '{generated_at}';",
        content,
        flags=re.DOTALL
    )
    
    # Write back to file
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Updated index.html - {total_candidates} total ({total_buy} buy, {total_rent} rent)")
    print(f"   Updated timestamp: {generated_at}")


def main():
    """Main function to generate all city pages."""
    print("=" * 60)
    print("Wohngemeinschaft Site Generator v3")
    print("=" * 60)
    
    # Ensure report dir exists
    REPORT_DIR.mkdir(exist_ok=True)
    
    missing_fields_report = {}
    files_changed = []
    validation_issues = []
    
    for city in CITIES:
        print(f"\n📍 Processing {city}...")
        
        # Load data
        data = load_enriched_data(city)
        candidates = data.get("candidates", [])
        print(f"   Found {len(candidates)} candidates")
        
        # Generate page
        html = generate_city_page(city, data, missing_fields_report)
        
        # Write HTML
        html_path = DOCS_DIR / f"{city}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        files_changed.append(str(html_path.relative_to(PROJECT_DIR)))
        print(f"   ✓ Generated {html_path.name}")
        
        # Validate
        issues = validate_html_links(city)
        if issues:
            validation_issues.extend(issues)
            for issue in issues:
                print(f"   ⚠ {issue}")
    
    # Write missing fields report
    missing_fields_path = REPORT_DIR / "missing-fields.json"
    
    # Convert to counts
    missing_summary = {}
    for city, fields in missing_fields_report.items():
        city_summary = {}
        for field, ids in fields.items():
            city_summary[field] = {"count": len(ids), "ids": ids}
        missing_summary[city] = city_summary
    
    with open(missing_fields_path, 'w', encoding='utf-8') as f:
        json.dump(missing_summary, f, indent=2)
    files_changed.append(str(missing_fields_path.relative_to(PROJECT_DIR)))
    print(f"\n📋 Missing fields report: {missing_fields_path}")
    
    # Update index page with current stats
    print(f"\n🏠 Updating index page...")
    update_index_page()
    files_changed.append("docs/index.html")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Files changed: {len(files_changed)}")
    for f in files_changed:
        print(f"  - {f}")
    
    if validation_issues:
        print(f"\n⚠ Validation issues: {len(validation_issues)}")
    else:
        print("\n✓ All image links validated")
    
    # Return data for progress report
    return {
        "files_changed": files_changed,
        "missing_fields": missing_summary,
        "validation_issues": validation_issues
    }


if __name__ == "__main__":
    main()
