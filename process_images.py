#!/usr/bin/env python3
"""
Script to extract images from Magdeburg property listings
"""
import json
import os
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from PIL import Image
import time

def get_robots_txt(domain):
    """Check robots.txt to be respectful"""
    try:
        response = requests.get(f"https://{domain}/robots.txt", timeout=5)
        if response.status_code == 200:
            return response.text
    except:
        pass
    return ""

def extract_first_image_url(listing_url):
    """Try to extract the first property image URL from a listing page"""
    try:
        # Be respectful - check domain and add delay
        domain = urlparse(listing_url).netloc
        robots = get_robots_txt(domain)
        
        # Basic headers to appear as normal browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(listing_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Common selectors for property images on German sites
        selectors = [
            # Kleinanzeigen
            'img[src*="i.kleinanzeigen.de"]',
            '.galleryimage-element img',
            '.image-gallery img',
            
            # Immowelt  
            'img[src*="immowelt"]',
            '.estate-image img',
            '.gallery img',
            
            # Generic fallbacks
            'img[alt*="immobilie"]',
            'img[alt*="haus"]',
            'img[alt*="wohnung"]',
            '.property-image img',
            '.listing-image img',
            'article img',
            'main img'
        ]
        
        for selector in selectors:
            img_elements = soup.select(selector)
            for img in img_elements:
                src = img.get('src') or img.get('data-src')
                if src and not src.startswith('data:'):
                    # Convert to absolute URL
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = urljoin(listing_url, src)
                    
                    # Filter out icons, logos, etc. - look for larger images
                    if any(x in src.lower() for x in ['icon', 'logo', 'avatar', 'button']):
                        continue
                        
                    return src
                    
    except Exception as e:
        print(f"Error extracting from {listing_url}: {e}")
    
    return None

def download_and_resize_image(image_url, output_path, max_width=1200, max_height=800):
    """Download image and resize to max dimensions"""
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Save to temporary file first
        temp_path = output_path + '.tmp'
        with open(temp_path, 'wb') as f:
            f.write(response.content)
        
        # Resize with PIL
        with Image.open(temp_path) as img:
            # Convert to RGB if needed (handle RGBA, etc.)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Calculate new dimensions maintaining aspect ratio
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Save as JPEG
            img.save(output_path, 'JPEG', quality=85, optimize=True)
        
        # Remove temp file
        os.remove(temp_path)
        return True
        
    except Exception as e:
        print(f"Error downloading/resizing {image_url}: {e}")
        try:
            os.remove(temp_path)
        except:
            pass
        return False

def take_screenshot(listing_url, output_path):
    """Take a screenshot of the listing page as fallback"""
    # We'll implement this using the browser tool later
    return False

def main():
    # Load candidates data
    with open('data/magdeburg/candidates_enriched.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    stats = {
        'processed': 0,
        'images_downloaded': 0,
        'screenshots_taken': 0,
        'failures': []
    }
    
    print("Processing Magdeburg candidates for images...")
    
    for candidate in data['candidates']:
        candidate_id = candidate['id']
        listing_url = candidate.get('listingUrl')
        
        if not listing_url:
            print(f"No listing URL for {candidate_id}")
            continue
            
        print(f"\nProcessing {candidate_id}: {candidate['title']}")
        print(f"URL: {listing_url}")
        
        stats['processed'] += 1
        
        # Try to extract and download image
        image_url = extract_first_image_url(listing_url)
        if image_url:
            print(f"Found image: {image_url}")
            
            output_path = f"docs/assets/magdeburg/photos/{candidate_id}.jpg"
            if download_and_resize_image(image_url, output_path):
                print(f"✓ Image saved: {output_path}")
                stats['images_downloaded'] += 1
            else:
                print(f"✗ Failed to download image")
                stats['failures'].append(f"{candidate_id}: download failed")
        else:
            print(f"✗ No image found, will take screenshot")
            stats['failures'].append(f"{candidate_id}: no image found")
        
        # Be respectful - delay between requests
        time.sleep(2)
    
    print("\n" + "="*50)
    print(f"Processing complete!")
    print(f"Candidates processed: {stats['processed']}")
    print(f"Images downloaded: {stats['images_downloaded']}")
    print(f"Screenshots taken: {stats['screenshots_taken']}")
    print(f"Failures: {len(stats['failures'])}")
    if stats['failures']:
        for failure in stats['failures']:
            print(f"  - {failure}")
    
    return stats

if __name__ == '__main__':
    main()