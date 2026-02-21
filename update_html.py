#!/usr/bin/env python3
import json
import re

def update_html_with_images_and_pros_cons():
    # Load candidates data
    with open('/Users/jacksbot/projects/PRJ010-wohngemeinschaft/data/leipzig/candidates_enriched.json', 'r') as f:
        data = json.load(f)
    
    # Create a mapping of candidate ID to candidate data
    candidates_map = {candidate['id']: candidate for candidate in data['candidates']}
    
    # Read the current HTML
    with open('/Users/jacksbot/projects/PRJ010-wohngemeinschaft/docs/leipzig.html', 'r') as f:
        html_content = f.read()
    
    # Update the table header to include Image and Pros/Cons columns
    old_header = '<tr><th>ID</th><th>Titel</th><th>Lage</th><th>Preis</th><th>Größe</th><th>Zimmer</th><th>Score</th><th>Link</th></tr>'
    new_header = '<tr><th>Bild</th><th>ID</th><th>Titel</th><th>Lage</th><th>Preis</th><th>Größe</th><th>Zimmer</th><th>Score</th><th>Pros/Cons</th><th>Link</th></tr>'
    html_content = html_content.replace(old_header, new_header)
    
    # Update each table row to include image and pros/cons
    tbody_pattern = r'<tbody>(.*?)</tbody>'
    tbody_match = re.search(tbody_pattern, html_content, re.DOTALL)
    
    if tbody_match:
        tbody_content = tbody_match.group(1)
        
        # Extract all table rows
        row_pattern = r'<tr><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td></tr>'
        
        new_rows = []
        for match in re.finditer(row_pattern, tbody_content):
            candidate_id = match.group(1)
            title = match.group(2)
            location = match.group(3)
            price = match.group(4)
            size = match.group(5)
            rooms = match.group(6)
            score_html = match.group(7)
            link_html = match.group(8)
            
            # Get candidate data
            candidate = candidates_map.get(candidate_id, {})
            suitability = candidate.get('suitability', {})
            pros = suitability.get('pros', [])
            cons = suitability.get('cons', [])
            
            # Create image cell
            image_cell = f'<img src="assets/leipzig/photos/{candidate_id}.jpg" alt="{title}" style="width:80px;height:60px;object-fit:cover;border-radius:4px;">'
            
            # Create pros/cons cell
            pros_html = '<br>'.join([f"✓ {pro}" for pro in pros]) if pros else ""
            cons_html = '<br>'.join([f"✗ {con}" for con in cons]) if cons else ""
            pros_cons_cell = f'<div style="font-size:0.8rem;"><div style="color:#16a34a;">{pros_html}</div><div style="color:#ef4444;margin-top:4px;">{cons_html}</div></div>'
            
            # Create new row with image first, then other columns, and pros/cons before link
            new_row = f'<tr><td>{image_cell}</td><td>{candidate_id}</td><td>{title}</td><td>{location}</td><td>{price}</td><td>{size}</td><td>{rooms}</td><td>{score_html}</td><td>{pros_cons_cell}</td><td>{link_html}</td></tr>'
            new_rows.append(new_row)
        
        # Replace the tbody content
        new_tbody = '<tbody>\n                ' + '\n                '.join(new_rows) + '\n            </tbody>'
        html_content = re.sub(tbody_pattern, new_tbody, html_content, flags=re.DOTALL)
    
    # Update the CSS to accommodate the new columns
    css_addition = """
        table { width: 100%; table-layout: fixed; }
        td:nth-child(1) { width: 90px; } /* Image */
        td:nth-child(2) { width: 60px; } /* ID */
        td:nth-child(3) { width: 200px; } /* Title */
        td:nth-child(4) { width: 120px; } /* Location */
        td:nth-child(5) { width: 80px; } /* Price */
        td:nth-child(6) { width: 60px; } /* Size */
        td:nth-child(7) { width: 50px; } /* Rooms */
        td:nth-child(8) { width: 50px; } /* Score */
        td:nth-child(9) { width: 200px; } /* Pros/Cons */
        td:nth-child(10) { width: 50px; } /* Link */
        th, td { padding: 0.8rem; vertical-align: top; }"""
    
    # Insert the additional CSS before the closing </style>
    html_content = html_content.replace('</style>', css_addition + '\n        </style>')
    
    # Write the updated HTML
    with open('/Users/jacksbot/projects/PRJ010-wohngemeinschaft/docs/leipzig.html', 'w') as f:
        f.write(html_content)
    
    print("✓ Updated HTML with images and pros/cons")

if __name__ == "__main__":
    update_html_with_images_and_pros_cons()