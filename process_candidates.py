#!/usr/bin/env python3
"""
Script to process Halle candidates and add images
"""

import json
import requests
from PIL import Image
import io
import os
import re
from pathlib import Path
import time

# Load candidate data
with open('data/halle/candidates_enriched.json', 'r') as f:
    data = json.load(f)

candidates = data['candidates']

# Create output directories
photos_dir = Path('docs/assets/halle/photos')
screenshots_dir = Path('docs/assets/halle/screenshots') 
photos_dir.mkdir(parents=True, exist_ok=True)
screenshots_dir.mkdir(parents=True, exist_ok=True)

# Counters for tracking
processed = 0
images_saved = 0
screenshots_taken = 0
failures = []

print(f"Processing {len(candidates)} candidates...")

for candidate in candidates:
    candidate_id = candidate['id']
    listing_url = candidate.get('listingUrl')
    
    processed += 1
    print(f"\n[{processed}/{len(candidates)}] Processing {candidate_id}: {candidate['title']}")
    
    if not listing_url:
        print(f"  No listing URL for {candidate_id}")
        failures.append((candidate_id, "No listing URL"))
        continue
    
    try:
        # Add User-Agent to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        print(f"  Fetching: {listing_url}")
        response = requests.get(listing_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            html = response.text
            
            # Extract first image URL from HTML
            # Look for various image patterns
            img_patterns = [
                r'<img[^>]*src="([^"]*\.(?:jpg|jpeg|png|webp))"[^>]*>',
                r'data-src="([^"]*\.(?:jpg|jpeg|png|webp))"',
                r'background-image:\s*url\("([^"]*\.(?:jpg|jpeg|png|webp))"\)',
                r'"image"\s*:\s*"([^"]*\.(?:jpg|jpeg|png|webp))"',
                r'"imageUrl"\s*:\s*"([^"]*\.(?:jpg|jpeg|png|webp))"'
            ]
            
            image_url = None
            for pattern in img_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    # Filter out small icons, logos, etc.
                    for match in matches:
                        if any(skip in match.lower() for skip in ['icon', 'logo', 'avatar', 'btn', 'button']):
                            continue
                        # Make sure URL is absolute
                        if match.startswith('//'):
                            image_url = 'https:' + match
                        elif match.startswith('/'):
                            domain = '/'.join(listing_url.split('/')[:3])
                            image_url = domain + match
                        elif match.startswith('http'):
                            image_url = match
                        else:
                            continue
                        break
                
                if image_url:
                    break
            
            if image_url:
                print(f"  Found image: {image_url}")
                try:
                    # Download and resize image
                    img_response = requests.get(image_url, headers=headers, timeout=10)
                    if img_response.status_code == 200:
                        # Open with PIL and resize
                        img = Image.open(io.BytesIO(img_response.content))
                        
                        # Resize to max 1200x800 while maintaining aspect ratio
                        img.thumbnail((1200, 800), Image.Resampling.LANCZOS)
                        
                        # Save as JPEG
                        output_path = photos_dir / f"{candidate_id}.jpg"
                        if img.mode in ('RGBA', 'LA'):
                            # Convert to RGB for JPEG
                            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                            img = rgb_img
                        
                        img.save(output_path, 'JPEG', quality=85)
                        images_saved += 1
                        print(f"  ✓ Image saved: {output_path}")
                        
                    else:
                        print(f"  Failed to download image: {img_response.status_code}")
                        failures.append((candidate_id, f"Image download failed: {img_response.status_code}"))
                        
                except Exception as e:
                    print(f"  Error processing image: {e}")
                    failures.append((candidate_id, f"Image processing error: {e}"))
            else:
                print(f"  No image found in HTML")
                failures.append((candidate_id, "No image found in HTML"))
        
        elif response.status_code == 410:
            print(f"  Listing no longer exists (410)")
            failures.append((candidate_id, "Listing no longer exists (410)"))
        else:
            print(f"  HTTP Error: {response.status_code}")
            failures.append((candidate_id, f"HTTP {response.status_code}"))
            
    except Exception as e:
        print(f"  Error: {e}")
        failures.append((candidate_id, f"Exception: {e}"))
    
    # Small delay to be respectful
    time.sleep(1)

# Print summary
print(f"\n=== PROCESSING COMPLETE ===")
print(f"Candidates processed: {processed}")
print(f"Images saved: {images_saved}")
print(f"Screenshots taken: {screenshots_taken}")
print(f"Failures: {len(failures)}")

if failures:
    print("\nFailures:")
    for candidate_id, reason in failures:
        print(f"  {candidate_id}: {reason}")

print(f"\nOutput directories:")
print(f"  Photos: {photos_dir}")
print(f"  Screenshots: {screenshots_dir}")