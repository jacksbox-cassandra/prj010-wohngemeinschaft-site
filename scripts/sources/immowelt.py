"""
Immowelt scraper for PRJ010

Handles scraping property listings from immowelt.de
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup

from .base import BaseScraper, ScraperError

logger = logging.getLogger(__name__)


class ImmoweltScraper(BaseScraper):
    """Scraper for immowelt.de property listings"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, 'immowelt')
        
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
            # Get max results per type
            max_per_type = self.config.get('scraper', {}).get('max_results_per_type', 15)
            
            # Search both transaction types: buy and rent
            transaction_types = ['buy', 'rent']
            
            for transaction_type in transaction_types:
                try:
                    # Build search URL for this city and transaction type
                    search_url = self._build_search_url(city, transaction_type=transaction_type, **kwargs)
                    logger.info(f"Searching Immowelt for {city} ({transaction_type}): {search_url}")
                    
                    # Fetch and parse search results
                    page = 1
                    max_pages = 5  # Limit to avoid too many requests
                    type_listings = []
                    
                    while page <= max_pages and len(type_listings) < max_per_type:
                        page_url = f"{search_url}?page={page}" if page > 1 else search_url
                        
                        try:
                            response = self._make_request(page_url)
                            page_listings = self._parse_search_page(response.text, city)
                            
                            if not page_listings:
                                logger.info(f"No more listings found on page {page} for {transaction_type}")
                                break
                                
                            # Add transaction type to each listing
                            for listing in page_listings:
                                listing['transaction_type'] = transaction_type
                                
                            type_listings.extend(page_listings)
                            logger.info(f"Found {len(page_listings)} listings on page {page} for {transaction_type}")
                            page += 1
                            
                            # Stop if we have enough listings
                            if len(type_listings) >= max_per_type:
                                type_listings = type_listings[:max_per_type]
                                break
                                
                        except ScraperError as e:
                            logger.error(f"Error scraping page {page} for {transaction_type}: {e}")
                            break
                    
                    listings.extend(type_listings)
                    logger.info(f"Found {len(type_listings)} {transaction_type} listings for {city}")
                    
                except Exception as e:
                    logger.error(f"Error searching {transaction_type} listings for {city}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error searching Immowelt for {city}: {e}")
            raise ScraperError(f"Immowelt search failed: {e}")
            
        logger.info(f"Found {len(listings)} total listings for {city}")
        return listings
    
    def _build_search_url(self, city: str, transaction_type: str = 'buy', **kwargs) -> str:
        """Build search URL with parameters"""
        base_url = self.source_config['base_url']
        city_config = self.config['cities'][city]
        
        # URL encode city name
        city_name = quote(city_config['name'].lower().replace(' ', '-'))
        
        # Build URL based on transaction type
        if transaction_type == 'buy':
            search_url = f"{base_url}/liste/{city_name}/haeuser/kaufen"
        else:  # rent
            search_url = f"{base_url}/liste/{city_name}/haeuser/mieten"
        
        # Add parameters
        params = []
        
        # Property type
        params.append("objektarten=haus")
        
        # Price range if specified
        search_params = self.config.get('search_params', {})
        if transaction_type == 'buy':
            max_price = kwargs.get('max_price_buy', search_params.get('max_price_buy'))
            if max_price:
                params.append(f"preis-bis={max_price}")
        else:  # rent
            max_price = kwargs.get('max_price_rent', search_params.get('max_price_rent', 2000))
            if max_price:
                params.append(f"preis-bis={max_price}")
            
        # Minimum rooms
        search_config = self.config.get('search', {})
        min_rooms = kwargs.get('min_rooms', search_config.get('min_rooms', search_params.get('min_bedrooms', 4)))
        if min_rooms:
            params.append(f"zimmer-ab={min_rooms}")
            
        # Add parameters to URL
        if params:
            search_url += "?" + "&".join(params)
            
        return search_url
    
    def _parse_search_page(self, html: str, city: str) -> List[Dict[str, Any]]:
        """Parse search results page and extract listings"""
        listings = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Immowelt typically uses div elements with specific classes
            listing_elements = soup.find_all('div', class_='listitem_wrap')
            
            if not listing_elements:
                # Try alternative selectors
                listing_elements = soup.find_all('article', class_='property-item')
                
            if not listing_elements:
                # Try another common pattern
                listing_elements = soup.find_all('div', attrs={'data-testid': 'property-item'})
                
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
            title_link = element.find('h2')
            if title_link:
                link_elem = title_link.find('a')
                if link_elem:
                    listing['title'] = link_elem.get_text(strip=True)
                    listing['url'] = urljoin(self.source_config['base_url'], link_elem.get('href', ''))
                    
            # Alternative title extraction
            if 'title' not in listing:
                title_elem = element.find('a', class_='property-title')
                if title_elem:
                    listing['title'] = title_elem.get_text(strip=True)
                    listing['url'] = urljoin(self.source_config['base_url'], title_elem.get('href', ''))
                    
            if 'title' not in listing:
                return None
                
            # Extract price
            price_elem = element.find('span', class_='price')
            if not price_elem:
                price_elem = element.find('div', class_='price-block')
                
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Extract price from text like "450.000 €" or "450.000,00 €"
                price_match = re.search(r'([\d.,]+)', price_text.replace('.', '').replace(',', ''))
                if price_match:
                    try:
                        listing['price'] = int(price_match.group(1))
                    except ValueError:
                        pass
                        
            # Extract location/address
            location_elem = element.find('div', class_='location')
            if not location_elem:
                location_elem = element.find('span', class_='location-name')
                
            if location_elem:
                listing['address'] = location_elem.get_text(strip=True)
                
            # Extract property details from structured data or key-value pairs
            self._extract_property_details_from_element(element, listing)
            
            # Extract image URL
            img_elem = element.find('img')
            if img_elem:
                img_src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy')
                if img_src:
                    listing['image_url'] = urljoin(self.source_config['base_url'], img_src)
                    
            # Extract features and description
            description_parts = []
            
            # Add title
            description_parts.append(listing.get('title', ''))
            
            # Look for property features in various locations
            feature_selectors = [
                'div.features',
                'div.property-features', 
                'div.expose-details',
                'ul.feature-list li',
                'div.ausstattung'
            ]
            
            for selector in feature_selectors:
                elements = element.select(selector)
                for elem in elements:
                    feature_text = elem.get_text(strip=True)
                    if feature_text and feature_text not in description_parts and len(feature_text) > 3:
                        description_parts.append(feature_text)
            
            # Look for detailed description
            desc_selectors = [
                'div.property-description',
                'div.expose-description',
                'div.description-text',
                'p.description'
            ]
            
            for selector in desc_selectors:
                desc_elem = element.select_one(selector)
                if desc_elem:
                    desc_text = desc_elem.get_text(strip=True)
                    if desc_text and len(desc_text) > 10:
                        description_parts.append(desc_text)
                        break  # Take the first good description
            
            # Combine description
            if len(description_parts) > 1:
                listing['description'] = ' | '.join(description_parts)
            elif description_parts:
                listing['description'] = description_parts[0]
            else:
                listing['description'] = listing.get('title', '')
                
            # Extract additional details from text
            self._extract_property_details_from_text(listing)
            
            # Set source and timestamp
            return self.get_standardized_listing(listing)
            
        except Exception as e:
            logger.warning(f"Error parsing Immowelt listing: {e}")
            return None
    
    def _extract_property_details_from_element(self, element, listing: Dict[str, Any]):
        """Extract structured property details from HTML element"""
        try:
            # Look for key-value pairs in structured format
            detail_items = element.find_all('div', class_='property-data-item')
            
            for item in detail_items:
                label_elem = item.find('span', class_='label')
                value_elem = item.find('span', class_='value')
                
                if label_elem and value_elem:
                    label = label_elem.get_text(strip=True).lower()
                    value = value_elem.get_text(strip=True)
                    
                    if 'zimmer' in label:
                        rooms_match = re.search(r'(\d+)[.,]?\d*', value)
                        if rooms_match:
                            listing['rooms'] = float(rooms_match.group(1))
                            
                    elif 'wohnfläche' in label or 'fläche' in label:
                        size_match = re.search(r'(\d+)', value)
                        if size_match:
                            listing['size_sqm'] = int(size_match.group(1))
                            
                    elif 'schlafzimmer' in label:
                        bedroom_match = re.search(r'(\d+)', value)
                        if bedroom_match:
                            listing['bedrooms'] = int(bedroom_match.group(1))
                            
        except Exception as e:
            logger.debug(f"Error extracting structured details: {e}")
    
    def _extract_property_details_from_text(self, listing: Dict[str, Any]):
        """Extract rooms, bedrooms, and size from text"""
        text = f"{listing.get('title', '')} {listing.get('description', '')}"
        text = text.lower()
        
        # Extract number of rooms if not already found
        if 'rooms' not in listing:
            rooms_match = re.search(r'(\d+)[.,]?\d*\s*zimmer', text)
            if rooms_match:
                listing['rooms'] = float(rooms_match.group(1))
                
        # Extract bedrooms if not already found
        if 'bedrooms' not in listing:
            bedroom_match = re.search(r'(\d+)\s*schlafzimmer', text)
            if bedroom_match:
                listing['bedrooms'] = int(bedroom_match.group(1))
                
        # Extract size in square meters if not already found
        if 'size_sqm' not in listing:
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
            'dachboden', 'wintergarten', 'dachterrasse', 'grünfläche',
            'stellplatz', 'carport', 'außenbereich'
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
    
    parser = argparse.ArgumentParser(description='Test Immowelt scraper')
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
    scraper = ImmoweltScraper(config)
    
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