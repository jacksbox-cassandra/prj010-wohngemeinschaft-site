"""
Kleinanzeigen (eBay Kleinanzeigen) scraper for PRJ010

Handles scraping property listings from kleinanzeigen.de
"""

import re
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup

from .base import BaseScraper, ScraperError

logger = logging.getLogger(__name__)


class KleinanzeigenScraper(BaseScraper):
    """Scraper for kleinanzeigen.de property listings"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, 'kleinanzeigen')
        
    def search(self, city: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for property listings in the specified city
        
        Args:
            city: City key from config
            **kwargs: Additional search parameters
            
        Returns:
            List of raw listing dictionaries
        """
        listings = []
        
        try:
            # Get city-specific configuration
            if city not in self.config['cities']:
                raise ScraperError(f"City '{city}' not found in config")
                
            # For now, we'll use placeholder location IDs
            # In a full implementation, these would be in the config
            location_mapping = {
                'freiburg': '9243',
                'augsburg': '9279', 
                'halle': '9477',
                'leipzig': '9476',
                'magdeburg': '9478'
            }
            
            if city not in location_mapping:
                raise ScraperError(f"No location mapping found for city: {city}")
                
            location_id = location_mapping[city]
            
            # Build search URL
            search_url = self._build_search_url(location_id, **kwargs)
            logger.info(f"Searching Kleinanzeigen for {city}: {search_url}")
            
            # Fetch and parse search results
            page = 1
            max_pages = 5  # Limit to avoid too many requests
            
            while page <= max_pages:
                page_url = f"{search_url}&page={page}" if page > 1 else search_url
                
                try:
                    response = self._make_request(page_url)
                    page_listings = self._parse_search_page(response.text, city)
                    
                    if not page_listings:
                        logger.info(f"No more listings found on page {page}")
                        break
                        
                    listings.extend(page_listings)
                    logger.info(f"Found {len(page_listings)} listings on page {page}")
                    page += 1
                    
                except ScraperError as e:
                    logger.error(f"Error scraping page {page}: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error searching Kleinanzeigen for {city}: {e}")
            raise ScraperError(f"Kleinanzeigen search failed: {e}")
            
        logger.info(f"Found {len(listings)} total listings for {city}")
        return listings
    
    def _build_search_url(self, location_id: str, **kwargs) -> str:
        """Build search URL with parameters"""
        base_url = self.source_config['base_url']
        
        # Build URL for house listings (using immobilien category for broader results)
        search_url = f"{base_url}/s-immobilien/l{location_id}"
        
        # Add parameters
        params = []
        
        # Filter for houses/properties
        params.append("price-type=FIXED")  # Purchase, not rent
        
        # Price range if specified
        search_config = self.config.get('search', {})
        max_price = kwargs.get('max_price_buy', search_config.get('max_price_buy'))
        if max_price:
            params.append(f"maxPrice={max_price}")
                
        # Minimum rooms
        min_rooms = kwargs.get('min_rooms', search_config.get('min_rooms', search_config.get('min_bedrooms', 4)))
        if min_rooms:
            params.append(f"minRooms={min_rooms}")
            
        # Add parameters to URL
        if params:
            search_url += "?" + "&".join(params)
            
        return search_url
    
    def _parse_search_page(self, html: str, city: str) -> List[Dict[str, Any]]:
        """Parse search results page and extract listings"""
        listings = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find listing containers
            # Kleinanzeigen uses article elements with specific classes
            listing_elements = soup.find_all('article', class_='aditem')
            
            if not listing_elements:
                # Try alternative selectors
                listing_elements = soup.find_all('div', class_='ad-listitem')
                
            logger.debug(f"Found {len(listing_elements)} listing elements")
            
            for element in listing_elements:
                try:
                    listing = self.parse_listing(element)
                    if listing:
                        listing['city'] = city
                        listings.append(listing)
                except Exception as e:
                    logger.warning(f"Error parsing individual listing: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing search page: {e}")
            
        return listings
    
    def parse_listing(self, element) -> Optional[Dict[str, Any]]:
        """
        Parse a single listing element into standardized format
        
        Args:
            element: BeautifulSoup element containing listing data
            
        Returns:
            Standardized listing dict or None if parsing fails
        """
        try:
            listing = {}
            
            # Extract title and URL
            title_link = element.find('a', class_='ellipsis')
            if not title_link:
                title_link = element.find('h2').find('a') if element.find('h2') else None
                
            if not title_link:
                return None
                
            listing['title'] = title_link.get_text(strip=True)
            listing['url'] = urljoin(self.source_config['base_url'], title_link.get('href', ''))
            
            # Extract price
            price_elem = element.find('strong', class_='aditem-main--middle--price-shipping--price')
            if not price_elem:
                price_elem = element.find('span', string=re.compile(r'€'))
                
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'([\d.]+)', price_text.replace('.', ''))
                if price_match:
                    listing['price'] = int(price_match.group(1))
                    
            # Extract location
            location_elem = element.find('div', class_='aditem-main--top--left')
            if location_elem:
                location_text = location_elem.get_text(strip=True)
                listing['address'] = location_text
                
            # Extract description/features from title and any additional text
            desc_elem = element.find('p', class_='aditem-main--middle--description')
            if desc_elem:
                listing['description'] = desc_elem.get_text(strip=True)
            else:
                listing['description'] = listing['title']
                
            # Extract image URL
            img_elem = element.find('img')
            if img_elem:
                img_src = img_elem.get('src') or img_elem.get('data-src')
                if img_src:
                    listing['image_url'] = urljoin(self.source_config['base_url'], img_src)
                    
            # Try to extract rooms and size from title/description
            self._extract_property_details(listing)
            
            # Set source and timestamp
            return self.get_standardized_listing(listing)
            
        except Exception as e:
            logger.warning(f"Error parsing Kleinanzeigen listing: {e}")
            return None
    
    def _extract_property_details(self, listing: Dict[str, Any]):
        """Extract rooms, bedrooms, and size from text"""
        text = f"{listing.get('title', '')} {listing.get('description', '')}"
        text = text.lower()
        
        # Extract number of rooms
        rooms_match = re.search(r'(\d+)[.,]?\d*\s*zimmer', text)
        if rooms_match:
            listing['rooms'] = float(rooms_match.group(1))
            
        # Extract bedrooms
        bedroom_match = re.search(r'(\d+)\s*schlafzimmer', text)
        if bedroom_match:
            listing['bedrooms'] = int(bedroom_match.group(1))
            
        # Extract size in square meters
        size_patterns = [
            r'(\d+)[.,]?\d*\s*m[²2]',
            r'(\d+)[.,]?\d*\s*qm',
            r'(\d+)[.,]?\d*\s*quadratmeter'
        ]
        
        for pattern in size_patterns:
            size_match = re.search(pattern, text)
            if size_match:
                listing['size_sqm'] = int(size_match.group(1))
                break
                
        # Extract features that might indicate suitability
        features = []
        
        feature_keywords = [
            'garten', 'terrasse', 'balkon', 'hof', 'garage', 'keller', 
            'dachboden', 'wintergarten', 'dachterrasse', 'grünfläche'
        ]
        
        for keyword in feature_keywords:
            if keyword in text:
                features.append(keyword)
                
        if features:
            listing['features'] = features


def main():
    """Test the scraper directly"""
    import sys
    import yaml
    import argparse
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    parser = argparse.ArgumentParser(description='Test Kleinanzeigen scraper')
    parser.add_argument('--city', default='freiburg', help='City to search')
    parser.add_argument('--max-pages', type=int, default=2, help='Maximum pages to scrape')
    args = parser.parse_args()
    
    # Load config
    config_path = '../config.yaml'
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Config file not found: {config_path}")
        sys.exit(1)
        
    # Test scraper
    scraper = KleinanzeigenScraper(config)
    
    try:
        listings = scraper.search(args.city)
        
        print(f"\nFound {len(listings)} listings for {args.city}")
        for i, listing in enumerate(listings[:5], 1):
            print(f"\n{i}. {listing.get('title', 'No title')}")
            print(f"   Price: {listing.get('price', 'N/A')} EUR")
            print(f"   Location: {listing.get('address', 'N/A')}")
            print(f"   Rooms: {listing.get('rooms', 'N/A')}")
            print(f"   Size: {listing.get('size_sqm', 'N/A')} m²")
            print(f"   URL: {listing.get('url', 'N/A')}")
            
        stats = scraper.get_request_stats()
        print(f"\nRequest stats: {stats}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()