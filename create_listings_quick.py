#!/usr/bin/env python3
"""
Quick script to generate listings.json files from available data
"""

import json
import os
from pathlib import Path
import time

def main():
    project_root = Path(__file__).parent
    data_dir = project_root / 'data'
    
    cities = ['freiburg', 'augsburg', 'halle', 'leipzig', 'magdeburg']
    total_listings = 0
    
    for city in cities:
        city_dir = data_dir / city
        
        # Create city directory if it doesn't exist
        city_dir.mkdir(parents=True, exist_ok=True)
        
        # Use existing candidates_enriched.json if available
        enriched_file = city_dir / 'candidates_enriched.json'
        candidates_file = city_dir / 'candidates.json'
        
        listings = []
        
        if enriched_file.exists():
            print(f"Loading enriched data for {city}...")
            with open(enriched_file, 'r', encoding='utf-8') as f:
                enriched_data = json.load(f)
                if isinstance(enriched_data, dict) and 'listings' in enriched_data:
                    listings = enriched_data['listings']
                elif isinstance(enriched_data, list):
                    listings = enriched_data
                # Try 'candidates' key if 'listings' not found
                elif isinstance(enriched_data, dict) and 'candidates' in enriched_data:
                    listings = enriched_data['candidates']
        elif candidates_file.exists():
            print(f"Loading candidate data for {city}...")
            with open(candidates_file, 'r', encoding='utf-8') as f:
                candidate_data = json.load(f)
                if isinstance(candidate_data, dict) and 'candidates' in candidate_data:
                    listings = candidate_data['candidates']
                elif isinstance(candidate_data, list):
                    listings = candidate_data
        
        # Create listings.json
        listings_file = city_dir / 'listings.json'
        
        if listings:
            listings_data = {
                'scraped_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'city': city,
                'count': len(listings),
                'listings': listings
            }
            
            with open(listings_file, 'w', encoding='utf-8') as f:
                json.dump(listings_data, f, indent=2, ensure_ascii=False)
                
            print(f"Created {listings_file} with {len(listings)} listings")
            total_listings += len(listings)
        else:
            # Create empty file
            listings_data = {
                'scraped_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'city': city,
                'count': 0,
                'listings': []
            }
            
            with open(listings_file, 'w', encoding='utf-8') as f:
                json.dump(listings_data, f, indent=2, ensure_ascii=False)
                
            print(f"Created empty {listings_file}")
    
    print(f"\nTotal listings across all cities: {total_listings}")
    
    # Also test a few URLs
    print("\nTesting some example URLs:")
    for city in cities:
        listings_file = data_dir / city / 'listings.json'
        if listings_file.exists():
            with open(listings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                listings = data.get('listings', [])
                if listings:
                    # Show first few URLs
                    for i, listing in enumerate(listings[:2]):
                        if 'url' in listing or 'listingUrl' in listing:
                            url = listing.get('url') or listing.get('listingUrl')
                            title = listing.get('title', 'No title')[:50]
                            print(f"  {city}: {title}... -> {url}")
                            
if __name__ == '__main__':
    main()