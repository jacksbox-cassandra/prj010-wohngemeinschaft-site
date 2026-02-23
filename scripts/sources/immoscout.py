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
            # Build search URL for this city
            search_url = self._build_search_url(city, **kwargs)
            logger.info(f"Searching ImmobilienScout24 for {city}: {search_url}")
            
            # Try web_fetch first (lightweight)
            try:
                listings = self._search_with_web_fetch(search_url, city)
            except Exception as e:
                logger.warning(f"web_fetch failed, trying browser method: {e}")
                listings = self._search_with_browser(search_url, city)
                
        except Exception as e:
            logger.error(f"Error searching ImmobilienScout24 for {city}: {e}")
            raise ScraperError(f"ImmobilienScout24 search failed: {e}")
            
        logger.info(f"Found {len(listings)} total listings for {city}")
        return listings
    
    def _build_search_url(self, city: str, **kwargs) -> str:
        """Build search URL with parameters"""
        base_url = self.source_config['base_url']
        
        # Get state for this city
        if city not in self.config['location_mapping']:
            raise ScraperError(f"No location mapping found for city: {city}")
            
        state = self.config['location_mapping'][city]['immoscout_state']
        city_config = self.config['cities'][city]
        
        # Build URL for house purchase listings
        search_url = f"{base_url}/Suche/de/{state}/haus-kaufen"
        
        # Add parameters
        params = []
        
        # Location (use city name as additional filter)
        city_name = quote(city_config['name'])
        params.append(f"geocodes={city_name}")
        
        # Property type
        params.append("objekttyp=haus")
        
        # Price range if specified
        search_params = self.config['search_params']
        max_price = kwargs.get('max_price_buy', search_params.get('max_price_buy'))
        if max_price:
            params.append(f"preis-bis={max_price}")
            
        # Minimum rooms
        min_rooms = kwargs.get('min_rooms', search_params.get('min_bedrooms', 4))
        if min_rooms:
            params.append(f"anzahl-zimmer={min_rooms}-")
            
        # Sort by relevance
        params.append("sorting=2")
        
        # Add parameters to URL
        if params:
            search_url += "?" + "&".join(params)
            
        return search_url
    
    def _search_with_web_fetch(self, search_url: str, city: str) -> List[Dict[str, Any]]:
        """
        Search using web_fetch tool (lightweight approach)
        
        This method uses the web_fetch tool to get page content,
        then parses the HTML to extract listings.
        """
        from .. import web_fetch  # Import web_fetch tool function
        
        listings = []
        page = 1
        max_pages = 3  # Limit pages to avoid too many requests
        
        while page <= max_pages:
            try:
                page_url = f"{search_url}&pagenumber={page}" if page > 1 else search_url
                
                # Use web_fetch to get page content
                result = web_fetch(url=page_url, extractMode='markdown')
                
                if result.get('status') == 'error':
                    raise ScraperError(f"web_fetch failed: {result.get('error')}")
                    
                content = result.get('content', '')
                
                # Parse listings from the extracted content
                page_listings = self._parse_web_fetch_content(content, city)
                
                if not page_listings:
                    logger.info(f"No more listings found on page {page}")
                    break
                    
                listings.extend(page_listings)
                logger.info(f"Found {len(page_listings)} listings on page {page}")
                page += 1
                
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                break
                
        return listings
    
    def _search_with_browser(self, search_url: str, city: str) -> List[Dict[str, Any]]:
        """
        Search using browser automation (fallback for anti-bot protection)
        
        This method uses the browser tool to navigate and extract listings
        when web_fetch is blocked.
        """
        from .. import browser  # Import browser tool function
        
        listings = []
        
        try:
            # Open the search URL in browser
            browser_result = browser(action='open', targetUrl=search_url)
            
            if browser_result.get('status') == 'error':
                raise ScraperError(f"Browser open failed: {browser_result.get('error')}")
                
            # Take a snapshot to get page content
            snapshot_result = browser(action='snapshot', refs='aria')
            
            if snapshot_result.get('status') == 'error':
                raise ScraperError(f"Browser snapshot failed: {snapshot_result.get('error')}")
                
            # Parse listings from browser content
            content = snapshot_result.get('content', '')
            listings = self._parse_browser_content(content, city)
            
            # Try to navigate to next page if listings were found
            if listings:
                page = 2
                max_pages = 3
                
                while page <= max_pages:
                    try:
                        # Look for next page button and click it
                        next_result = browser(
                            action='act',
                            request={
                                'kind': 'click',
                                'ref': 'next',  # or whatever selector works
                                'timeMs': 2000
                            }
                        )
                        
                        if next_result.get('status') == 'error':
                            break
                            
                        # Get content from new page
                        snapshot_result = browser(action='snapshot', refs='aria')
                        content = snapshot_result.get('content', '')
                        page_listings = self._parse_browser_content(content, city)
                        
                        if not page_listings:
                            break
                            
                        listings.extend(page_listings)
                        page += 1
                        
                    except Exception as e:
                        logger.warning(f"Error navigating to page {page}: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"Browser automation failed: {e}")
            raise
            
        return listings
    
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
        Parse a single listing element (used by base class)
        
        For ImmobilienScout24, this is mainly used internally
        by the web_fetch and browser parsing methods.
        """
        # This method is required by the base class but the main
        # parsing logic is in the specialized methods above
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