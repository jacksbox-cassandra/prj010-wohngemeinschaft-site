#!/usr/bin/env python3
import json
from bs4 import BeautifulSoup

def update_html_with_images_and_pros_cons():
    # Load candidates data
    with open('/Users/jacksbot/projects/PRJ010-wohngemeinschaft/data/leipzig/candidates_enriched.json', 'r') as f:
        data = json.load(f)
    
    # Create a mapping of candidate ID to candidate data
    candidates_map = {candidate['id']: candidate for candidate in data['candidates']}
    
    # Read the current HTML
    with open('/Users/jacksbot/projects/PRJ010-wohngemeinschaft/docs/leipzig.html', 'r') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the table header and add new columns
    thead = soup.find('thead')
    header_row = thead.find('tr')
    
    # Add Image column at the beginning
    img_th = soup.new_tag('th')
    img_th.string = 'Bild'
    header_row.insert(0, img_th)
    
    # Add Pros/Cons column before the last column (Link)
    proscons_th = soup.new_tag('th')
    proscons_th.string = 'Pros/Cons'
    header_row.insert(-1, proscons_th)
    
    # Find tbody and update each row
    tbody = soup.find('tbody')
    rows = tbody.find_all('tr')
    
    for row in rows:
        cells = row.find_all('td')
        
        # Get candidate ID from first cell
        candidate_id = cells[0].get_text().strip()
        candidate = candidates_map.get(candidate_id, {})
        suitability = candidate.get('suitability', {})
        pros = suitability.get('pros', [])
        cons = suitability.get('cons', [])
        title = candidate.get('title', '')
        
        # Create image cell
        img_cell = soup.new_tag('td')
        img_tag = soup.new_tag('img', 
                               src=f"assets/leipzig/photos/{candidate_id}.jpg", 
                               alt=title,
                               style="width:80px;height:60px;object-fit:cover;border-radius:4px;")
        img_cell.append(img_tag)
        
        # Insert image cell at the beginning
        row.insert(0, img_cell)
        
        # Create pros/cons cell
        proscons_cell = soup.new_tag('td')
        proscons_div = soup.new_tag('div', style="font-size:0.8rem;")
        
        if pros:
            pros_div = soup.new_tag('div', style="color:#16a34a;")
            pros_div.append(soup.new_tag('br').join([f"✓ {pro}" for pro in pros]))
            proscons_div.append(pros_div)
        
        if cons:
            cons_div = soup.new_tag('div', style="color:#ef4444;margin-top:4px;")
            cons_div.append(soup.new_tag('br').join([f"✗ {con}" for con in cons]))
            proscons_div.append(cons_div)
        
        proscons_cell.append(proscons_div)
        
        # Insert pros/cons cell before the last cell (Link)
        row.insert(-1, proscons_cell)
    
    # Update CSS for table layout
    style_tag = soup.find('style')
    additional_css = """
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
        th, td { padding: 0.8rem; vertical-align: top; }
        .proscons-content { font-size: 0.8rem; }
        .proscons-content .pros { color: #16a34a; }
        .proscons-content .cons { color: #ef4444; margin-top: 4px; }
    """
    style_tag.string += additional_css
    
    # Write the updated HTML
    with open('/Users/jacksbot/projects/PRJ010-wohngemeinschaft/docs/leipzig.html', 'w') as f:
        f.write(str(soup.prettify()))
    
    print("✓ Updated HTML with images and pros/cons using BeautifulSoup")

if __name__ == "__main__":
    update_html_with_images_and_pros_cons()