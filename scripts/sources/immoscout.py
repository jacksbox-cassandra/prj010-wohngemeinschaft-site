"""
ImmobilienScout24 scraper for PRJ010

Handles scraping property listings from immobilienscout24.de
Note: This site has anti-bot protection, so we use web_fetch primarily
and fall back to browser automation if needed.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, quote

from .base import BaseScraper, ScraperError

logger = logging.getLogger(__name__)


class ImmoscoutScraper(BaseScraper):
    """Scraper for immobilienscout24.de property listings"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, 'immoscout')
        self.use_browser = False  # Flag for browser fallback
        
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
            # Search both transaction types: buy and rent
            transaction_types = ['buy', 'rent']
            
            for transaction_type in transaction_types:
                try:
                    # Get max results per transaction type
                    if transaction_type == 'buy':
                        max_per_type = self.config.get('scraper', {}).get('max_results_per_buy', 15)
                    else:  # rent
                        max_per_type = self.config.get('scraper', {}).get('max_results_per_rent', 10)
                        
                    # Build search URL for this city and transaction type
                    search_url = self._build_search_url(city, transaction_type=transaction_type, **kwargs)
                    logger.info(f"Searching ImmobilienScout24 for {city} ({transaction_type}): {search_url}")
                    
                    # Try web_fetch first (lightweight)
                    try:
                        type_listings = self._search_with_web_fetch(search_url, city, max_per_type)
                        # Add transaction type to each listing
                        for listing in type_listings:
                            listing['transaction_type'] = transaction_type
                    except Exception as e:
                        logger.warning(f"web_fetch failed for {transaction_type}, trying browser method: {e}")
                        type_listings = self._search_with_browser(search_url, city, max_per_type)
                        # Add transaction type to each listing
                        for listing in type_listings:
                            listing['transaction_type'] = transaction_type
                    
                    listings.extend(type_listings)
                    logger.info(f"Found {len(type_listings)} {transaction_type} listings for {city}")
                    
                except Exception as e:
                    logger.error(f"Error searching {transaction_type} listings for {city}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error searching ImmobilienScout24 for {city}: {e}")
            raise ScraperError(f"ImmobilienScout24 search failed: {e}")
            
        logger.info(f"Found {len(listings)} total listings for {city}")
        return listings
    
    def _build_search_url(self, city: str, transaction_type: str = 'buy', **kwargs) -> str:
        """Build search URL with parameters"""
        base_url = self.source_config['base_url']
        
        # Get state for this city
        if city not in self.config['location_mapping']:
            raise ScraperError(f"No location mapping found for city: {city}")
            
        state = self.config['location_mapping'][city]['immoscout_state']
        city_config = self.config['cities'][city]
        
        # Build URL based on transaction type
        if transaction_type == 'buy':
            search_url = f"{base_url}/Suche/de/{state}/haus-kaufen"
        else:  # rent
            search_url = f"{base_url}/Suche/de/{state}/haus-mieten"
        
        # Add parameters
        params = []
        
        # Location (use city name as additional filter)
        city_name = quote(city_config['name'])
        params.append(f"geocodes={city_name}")
        
        # Property type
        params.append("objekttyp=haus")
        
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
            params.append(f"anzahl-zimmer={min_rooms}-")
            
        # Sort by relevance
        params.append("sorting=2")
        
        # Add parameters to URL
        if params:
            search_url += "?" + "&".join(params)
            
        return search_url
    
    def _search_with_web_fetch(self, search_url: str, city: str, max_per_type: int = 15) -> List[Dict[str, Any]]:
        """
        Search using direct HTTP requests with proper headers
        
        This method makes direct requests to ImmobilienScout24 search pages
        and parses the HTML to extract listings.
        """
        listings = []
        page = 1
        max_pages = 3  # Limit pages to avoid too many requests
        
        while page <= max_pages and len(listings) < max_per_type:
            try:
                page_url = f"{search_url}&pagenumber={page}" if page > 1 else search_url
                
                # Make request with proper headers
                response = self._make_request(page_url)
                page_listings = self._parse_search_page(response.text, city)
                
                if not page_listings:
                    logger.info(f"No more listings found on page {page}")
                    break
                    
                listings.extend(page_listings)
                logger.info(f"Found {len(page_listings)} listings on page {page}")
                page += 1
                
                # Stop if we have enough listings
                if len(listings) >= max_per_type:
                    listings = listings[:max_per_type]
                    break
                
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                break
                
        return listings
    
    def _parse_search_page(self, html: str, city: str) -> List[Dict[str, Any]]:
        """Parse ImmobilienScout24 search results page and extract listings"""
        listings = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # ImmobilienScout24 uses various selectors for listings
            listing_elements = soup.find_all('li', attrs={'data-id': True})
            
            if not listing_elements:
                # Try alternative selectors
                listing_elements = soup.find_all('div', class_='result-list-entry')
                
            if not listing_elements:
                listing_elements = soup.find_all('article', class_=re.compile(r'.*result.*'))
                
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
    
    def _search_with_browser(self, search_url: str, city: str, max_per_type: int = 15) -> List[Dict[str, Any]]:
        """
        Search using browser automation (fallback for anti-bot protection)
        
        This method uses the browser tool to navigate and extract listings
        when web_fetch is blocked.
        """
        # For now, simulate browser automation - in real implementation would use the browser tool
        logger.warning("browser automation not available - skipping immoscout listings")
        return []
    
    def _parse_web_fetch_content(self, content: str, city: str) -> List[Dict[str, Any]]:
        """Parse listings from web_fetch markdown content"""
        listings = []
        
        try:
            # The content will be markdown extracted from the page
            # Look for patterns that indicate property listings
            lines = content.split('\n')
            
            current_listing = {}
            in_listing = False
            
            for line in lines:
                line = line.strip()
                
                # Look for price indicators
                if re.search(r'[\d.,]+\s*€', line):
                    if current_listing and in_listing:
                        # Save previous listing
                        if 'title' in current_listing:
                            current_listing['city'] = city
                            listings.append(self.get_standardized_listing(current_listing))
                    
                    # Start new listing
                    current_listing = {}
                    in_listing = True
                    
                    # Extract price
                    price_match = re.search(r'([\d.,]+)', line.replace('.', '').replace(',', ''))
                    if price_match:
                        try:
                            current_listing['price'] = int(price_match.group(1))
                        except ValueError:
                            pass
                            
                # Look for titles (usually as links or headers)
                elif re.search(r'^#+\s+', line) or 'http' in line:
                    if in_listing:
                        # Extract URL if present
                        url_match = re.search(r'https?://[^\s)]+', line)
                        if url_match:
                            current_listing['url'] = url_match.group()
                            
                        # Extract title
                        title = re.sub(r'#+\s+', '', line)
                        title = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', title)  # Remove markdown links
                        current_listing['title'] = title.strip()
                        
                # Look for location/address information
                elif any(keyword in line.lower() for keyword in ['stadt', 'ort', 'lage', 'adresse']):
                    if in_listing and 'address' not in current_listing:
                        current_listing['address'] = line
                        
                # Extract room and size information
                elif re.search(r'\d+\s*zimmer|\d+\s*m[²2]', line.lower()):
                    if in_listing:
                        self._extract_details_from_line(line, current_listing)
                        
            # Save last listing
            if current_listing and in_listing and 'title' in current_listing:
                current_listing['city'] = city
                listings.append(self.get_standardized_listing(current_listing))
                
        except Exception as e:
            logger.error(f"Error parsing web_fetch content: {e}")
            
        return listings
    
    def _parse_browser_content(self, content: str, city: str) -> List[Dict[str, Any]]:
        """Parse listings from browser snapshot content"""
        listings = []
        
        try:
            # Browser content will be structured differently
            # Look for aria-labeled elements that represent listings
            lines = content.split('\n')
            
            # This is a simplified parser - in practice, you'd want
            # more sophisticated parsing based on the actual page structure
            for line in lines:
                if 'listing' in line.lower() and ('€' in line or 'eur' in line.lower()):
                    listing = self._extract_listing_from_line(line, city)
                    if listing:
                        listings.append(listing)
                        
        except Exception as e:
            logger.error(f"Error parsing browser content: {e}")
            
        return listings
    
    def _extract_listing_from_line(self, line: str, city: str) -> Optional[Dict[str, Any]]:
        """Extract listing data from a single line of browser content"""
        try:
            listing = {'city': city}
            
            # Extract price
            price_match = re.search(r'([\d.,]+)\s*€', line)
            if price_match:
                try:
                    listing['price'] = int(price_match.group(1).replace('.', '').replace(',', ''))
                except ValueError:
                    pass
                    
            # Extract basic info
            listing['title'] = line[:100]  # Use first part as title
            listing['description'] = line
            
            # Extract room/size details
            self._extract_details_from_line(line, listing)
            
            return self.get_standardized_listing(listing) if 'price' in listing else None
            
        except Exception as e:
            logger.warning(f"Error extracting listing from line: {e}")
            return None
    
    def _extract_details_from_line(self, line: str, listing: Dict[str, Any]):
        """Extract room and size details from a text line"""
        text = line.lower()
        
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
            r'(\d+)[.,]?\d*\s*qm'
        ]
        
        for pattern in size_patterns:
            size_match = re.search(pattern, text)
            if size_match:
                listing['size_sqm'] = int(size_match.group(1))
                break
    
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
            
            # Extract title and URL - look for direct property detail links
            title_link = element.find('a', href=re.compile(r'/expose/'))
            if not title_link:
                title_link = element.find('a', href=re.compile(r'/immobilie/'))
            if not title_link:
                # Try general property links
                title_link = element.find('a', class_=re.compile(r'.*title.*|.*link.*'))
                
            if not title_link:
                return None
                
            listing['title'] = title_link.get_text(strip=True)
            
            # Apply same property filtering as kleinanzeigen
            title_lower = listing['title'].lower()
            
            # STRICT filter: Skip building materials, doors, windows, etc.
            skip_keywords = [
                'haustür', 'tür', 'türen', 'fenster', 'dach', 'heizung', 'sanitär', 
                'boiler', 'wärmepumpe', 'solar', 'kinderspiel', 'spiel', 'garten möbel', 
                'möbel', 'fliesen', 'parkett', 'laminat', 'kamin', 'ofen', 'garage tor',
                'rollladen', 'rolladen', 'markise', 'sonnenschutz', 'carport', 
                'gartenhäuser', 'gartenhaus', 'terrassendach', 'vordach', 'balkon',
                'schiebetür', 'glastür', 'wintergarten kit', 'bausatz', 'baustoff',
                'isolierung', 'dämmung', 'ziegel', 'holz verkauf', 'brennholz'
            ]
            
            # If title contains skip keywords, skip
            if any(keyword in title_lower for keyword in skip_keywords):
                logger.debug(f"Skipping building material/component listing: {title_lower[:50]}")
                return None
                
            # POSITIVE filter: Only include listings that clearly mention properties
            property_keywords = [
                'haus ', 'villa', 'bungalow', 'einfamilienhaus', 'zweifamilienhaus', 
                'reihenhaus', 'doppelhaushälfte', 'wohnung', 'eigenheim', 'immobilie',
                'zimmer wohnung', 'zimmer haus', 'etage', 'stockwerk', 'anwesen',
                'landhaus', 'stadthaus', 'ferienhaus', 'mehrfamilienhaus'
            ]
            
            # Must match at least one property keyword
            if not any(keyword in title_lower for keyword in property_keywords):
                logger.debug(f"No property keywords found, skipping: {title_lower[:50]}")
                return None
            
            raw_href = title_link.get('href', '')
            
            # Ensure we get proper detail URLs
            if '/expose/' in raw_href or '/immobilie/' in raw_href:
                listing['url'] = urljoin(self.source_config['base_url'], raw_href)
            else:
                # Look harder for the correct detail link
                detail_link = element.find('a', href=re.compile(r'/expose/|/immobilie/'))
                if detail_link:
                    listing['url'] = urljoin(self.source_config['base_url'], detail_link.get('href', ''))
                else:
                    listing['url'] = urljoin(self.source_config['base_url'], raw_href)
                    
            # Extract price
            price_elem = element.find('span', class_=re.compile(r'.*price.*'))
            if not price_elem:
                price_elem = element.find('div', class_=re.compile(r'.*price.*'))
            if not price_elem:
                price_elem = element.find(string=re.compile(r'[\d.,]+\s*€'))
                
            if price_elem:
                price_text = price_elem if isinstance(price_elem, str) else price_elem.get_text(strip=True)
                price_match = re.search(r'([\d.,]+)', price_text.replace('.', '').replace(',', ''))
                if price_match:
                    try:
                        listing['price'] = int(price_match.group(1))
                    except ValueError:
                        pass
                        
            # Extract location/address
            location_elem = element.find('div', class_=re.compile(r'.*location.*|.*address.*'))
            if not location_elem:
                location_elem = element.find('span', class_=re.compile(r'.*location.*|.*address.*'))
                
            if location_elem:
                listing['address'] = location_elem.get_text(strip=True)
                
            # Extract image URL
            img_elem = element.find('img')
            if img_elem:
                img_src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy')
                if img_src:
                    listing['image_url'] = urljoin(self.source_config['base_url'], img_src)
                    
            # Extract comprehensive description
            description_parts = [listing.get('title', '')]
            
            # Look for various description elements
            desc_selectors = [
                'div[class*="description"]',
                'p[class*="description"]',
                'div[class*="details"]',
                'div[class*="features"]',
                'ul[class*="features"] li',
                'div[class*="ausstattung"]'
            ]
            
            for selector in desc_selectors:
                elements = element.select(selector)
                for elem in elements:
                    desc_text = elem.get_text(strip=True)
                    if desc_text and len(desc_text) > 5 and desc_text not in description_parts:
                        description_parts.append(desc_text)
            
            # Extract property details from structured data
            data_items = element.find_all(['span', 'div'], attrs={'data-qa': True})
            for item in data_items:
                item_text = item.get_text(strip=True)
                if item_text and len(item_text) > 3 and len(item_text) < 100:
                    description_parts.append(item_text)
            
            # Combine description
            if len(description_parts) > 1:
                listing['description'] = ' | '.join(description_parts)
            else:
                listing['description'] = description_parts[0] if description_parts else listing.get('title', '')
                
            # Enhance description if too short
            if len(listing['description']) < 100:
                all_text = element.get_text(separator=' ', strip=True)
                clean_text = all_text.replace(listing['title'], '').strip()
                if len(clean_text) > 50:
                    listing['description'] = f"{listing['description']} | {clean_text[:300]}..."
            
            # Extract property details from text
            text = f"{listing.get('title', '')} {listing.get('description', '')}"
            self._extract_details_from_line(text, listing)
            
            # Set source and timestamp
            return self.get_standardized_listing(listing)
            
        except Exception as e:
            logger.warning(f"Error parsing ImmobilienScout24 listing: {e}")
            return None


def main():
    """Test the scraper directly"""
    import sys
    import yaml
    import argparse
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    parser = argparse.ArgumentParser(description='Test ImmobilienScout24 scraper')
    parser.add_argument('--city', default='freiburg', help='City to search')
    parser.add_argument('--browser', action='store_true', help='Force browser mode')
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
    scraper = ImmoscoutScraper(config)
    if args.browser:
        scraper.use_browser = True
    
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