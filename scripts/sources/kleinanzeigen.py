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
            
            # Search both transaction types: buy and rent
            transaction_types = ['buy', 'rent']
            
            for transaction_type in transaction_types:
                try:
                    # Get max results per transaction type
                    if transaction_type == 'buy':
                        max_per_type = self.config.get('scraper', {}).get('max_results_per_buy', 15)
                    else:  # rent
                        max_per_type = self.config.get('scraper', {}).get('max_results_per_rent', 10)
                        
                    # Build search URL for this transaction type
                    search_url = self._build_search_url(location_id, transaction_type=transaction_type, **kwargs)
                    logger.info(f"Searching Kleinanzeigen for {city} ({transaction_type}): {search_url}")
                    
                    # Fetch and parse search results
                    page = 1
                    max_pages = 10  # Increased to find more listings
                    type_listings = []
                    
                    while page <= max_pages and len(type_listings) < max_per_type:
                        page_url = f"{search_url}&page={page}" if page > 1 else search_url
                        
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
            logger.error(f"Error searching Kleinanzeigen for {city}: {e}")
            raise ScraperError(f"Kleinanzeigen search failed: {e}")
            
        logger.info(f"Found {len(listings)} total listings for {city}")
        return listings
    
    def _build_search_url(self, location_id: str, transaction_type: str = 'buy', **kwargs) -> str:
        """Build search URL with parameters"""
        base_url = self.source_config['base_url']
        
        # Build URL based on transaction type - use more specific categories
        if transaction_type == 'buy':
            # For buying houses - use the house category with location 
            search_url = f"{base_url}/s-haus-kaufen/l{location_id}"
        else:  # rent
            # For renting houses 
            search_url = f"{base_url}/s-haus-mieten/l{location_id}"
        
        # Add parameters
        params = []
        
        # Get search configuration
        search_config = self.config.get('search', {})
        search_params = self.config.get('search_params', {})
        
        # Price range if specified
        if transaction_type == 'buy':
            max_price = kwargs.get('max_price_buy', search_params.get('max_price_buy'))
            if max_price:
                params.append(f"priceMax={max_price}")
        else:  # rent
            max_price = kwargs.get('max_price_rent', search_params.get('max_price_rent', 2000))
            if max_price:
                params.append(f"priceMax={max_price}")
                
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
            
            # Extract title and URL - look for direct property links
            title_link = None
            
            # DEBUG: Log all links in element
            all_links = element.find_all('a')
            logger.debug(f"Found {len(all_links)} links in element")
            for i, link in enumerate(all_links[:3]):  # Show first 3
                href = link.get('href', '')
                text = link.get_text(strip=True)[:50]
                logger.debug(f"  Link {i}: href='{href}' text='{text}'")
            
            # First try to find the main property link
            title_link = element.find('a', class_='ellipsis')
            if not title_link:
                title_link = element.find('h2').find('a') if element.find('h2') else None
            if not title_link:
                # Try alternative selectors for the main listing link
                title_link = element.find('a', href=re.compile(r'/s-anzeige/'))
                
            if not title_link:
                logger.debug(f"No title link found, skipping element")
                return None
                
            listing['title'] = title_link.get_text(strip=True)
            
            # Extract the proper detail URL
            raw_href = title_link.get('href', '')
            logger.debug(f"Title link href: '{raw_href}'")
            
            if raw_href.startswith('/s-anzeige/'):
                # This is a direct property detail URL
                listing['url'] = urljoin(self.source_config['base_url'], raw_href)
                logger.debug(f"Found direct detail URL: {listing['url']}")
            else:
                # If it's not a direct link, try to find it within the element
                detail_link = element.find('a', href=re.compile(r'/s-anzeige/'))
                if detail_link:
                    listing['url'] = urljoin(self.source_config['base_url'], detail_link.get('href', ''))
                    logger.debug(f"Found detail URL via search: {listing['url']}")
                else:
                    # Fallback to whatever we have
                    listing['url'] = urljoin(self.source_config['base_url'], raw_href)
                    logger.debug(f"Using fallback URL (might be wrong): {listing['url']}")
            
            # Filter out non-property listings early with more specific criteria
            title_lower = listing['title'].lower()
            
            # Apply VERY strict property filtering
            title_lower = listing['title'].lower()
            
            # STRICT filter: Skip ALL non-property listings
            skip_keywords = [
                # Vehicles
                'aprilia', 'audi', 'bmw', 'mercedes', 'volkswagen', 'opel', 'ford', 'toyota',
                'motorrad', 'auto', 'pkw', 'lkw', 'anhänger', 'wohnmobil', 'wohnwagen',
                'fahrrad', 'e-bike', 'roller', 'moped', 'quad',
                # Building materials/components
                'haustür', 'tür', 'türen', 'fenster', 'dach', 'heizung', 'sanitär', 
                'boiler', 'wärmepumpe', 'solar', 'fliesen', 'parkett', 'laminat', 
                'kamin', 'ofen', 'garage tor', 'rollladen', 'rolladen', 'markise', 
                'sonnenschutz', 'carport', 'schiebetür', 'glastür', 'wintergarten kit', 
                'bausatz', 'baustoff', 'isolierung', 'dämmung', 'ziegel', 'brennholz',
                # Furniture and household items
                'möbel', 'sessel', 'sofa', 'stuhl', 'tisch', 'bett', 'schrank',
                'kühlschrank', 'waschmaschine', 'spülmaschine', 'herd', 'backofen',
                'wanduhr', 'lampe', 'leuchte', 'teppich', 'vorhang', 'gardine',
                'geschirr', 'teller', 'glas', 'besteck', 'topf', 'pfanne',
                'küche', 'einbauküche', 'küchenzeile', 'küchenmöbel',
                # Electronics and gadgets
                'handy', 'smartphone', 'tablet', 'laptop', 'computer', 'fernseher',
                'stereo', 'lautsprecher', 'kopfhörer', 'kamera', 'spielkonsole',
                # Clothing and fashion
                'jeans', 't-shirt', 'pullover', 'jacke', 'mantel', 'kleid', 'rock',
                'schuhe', 'stiefel', 'sandalen', 'handschuhe', 'mütze', 'hut',
                # Toys and games
                'spielzeug', 'puppe', 'teddy', 'bär', 'lego', 'playmobil', 
                'einhorn', 'hüpftier', 'ball', 'puzzle', 'spiel',
                # Garden and outdoor (but not property)
                'rasenmäher', 'gartenschere', 'gießkanne', 'blumentopf', 'dünger',
                'samen', 'pflanze kirschlorbeer', 'hecke', 'baum verkauf',
                # Jobs and services
                'verkäufer', 'job', 'stelle', 'arbeit', 'minijob', 'stellenangebot',
                'nachhilfe', 'unterricht', 'kurs', 'training',
                # Tools and equipment
                'werkzeug', 'bohrer', 'säge', 'hammer', 'schraubenzieher', 'zange',
                'schraubenschlüssel', 'maulschlüssel', 'doppelmaulschlüssel',
                # Animals and pets
                'hund', 'katze', 'kaninchen', 'hamster', 'vogel', 'fisch', 'pferd',
                # Other miscellaneous
                'zu verschenken', 'dampflok', 'tender', 'lok', 'eisenbahn', 'modell'
            ]
            
            # Check if title contains any skip keywords
            if any(keyword in title_lower for keyword in skip_keywords):
                logger.debug(f"Skipping non-property listing: {title_lower[:60]}")
                return None
                
            # POSITIVE filter: Must contain strong property indicators
            strong_property_keywords = [
                'einfamilienhaus', 'zweifamilienhaus', 'mehrfamilienhaus',
                'reihenhaus', 'doppelhaushälfte', 'villa', 'bungalow',
                'landhaus', 'stadthaus', 'ferienhaus', 'eigenheim',
                'immobilie', 'anwesen', 'wohnhaus'
            ]
            
            # Check for strong property keywords first
            has_strong_property = any(keyword in title_lower for keyword in strong_property_keywords)
            
            if has_strong_property:
                logger.debug(f"Strong property keyword found: {title_lower[:60]}")
                # Allow this listing
            else:
                # Check for weaker property indicators with size/room information
                weak_property_keywords = ['haus ', 'wohnung']
                size_indicators = ['m²', 'qm', 'quadratmeter', 'zi.', 'zimmer']
                
                has_weak_property = any(keyword in title_lower for keyword in weak_property_keywords)
                has_size_info = any(keyword in title_lower for keyword in size_indicators)
                
                if has_weak_property and has_size_info:
                    logger.debug(f"Weak property with size info found: {title_lower[:60]}")
                    # Allow this listing
                else:
                    logger.debug(f"No strong property indicators found: {title_lower[:60]}")
                    return None
            
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
            desc_parts = []
            
            # Add title
            desc_parts.append(listing['title'])
            
            # Extract description from dedicated description element
            desc_elem = element.find('p', class_='aditem-main--middle--description')
            if not desc_elem:
                # Try alternative selectors for description
                desc_elem = element.find('div', class_='ad-description')
                if not desc_elem:
                    desc_elem = element.find('span', class_='text-module-begin')
            
            if desc_elem:
                desc_text = desc_elem.get_text(strip=True)
                if desc_text and desc_text != listing['title'] and len(desc_text) > 10:
                    desc_parts.append(desc_text)
            
            # Look for additional feature text in various locations
            feature_selectors = [
                'div.aditem-details',
                'div.aditem-features', 
                'span.aditem-feature',
                'div.ad-detail-description',
                'div.aditem-main--middle--description--text',
                'div.text-module-text',
                'div.ad-keyfacts'
            ]
            
            for selector in feature_selectors:
                elements = element.select(selector)
                for elem in elements:
                    feature_text = elem.get_text(strip=True)
                    if feature_text and feature_text not in desc_parts and len(feature_text) > 5:
                        desc_parts.append(feature_text)
            
            # Look for bullet point features
            feature_list = element.find('ul', class_='features') or element.find('div', class_='feature-list')
            if feature_list:
                features = feature_list.find_all('li')
                for feature in features:
                    feature_text = feature.get_text(strip=True)
                    if feature_text and len(feature_text) > 3:
                        desc_parts.append(f"• {feature_text}")
            
            # Look for key facts or attributes
            keyfacts = element.find_all(['span', 'div'], class_=re.compile(r'.*keyfact.*|.*attribute.*'))
            for fact in keyfacts:
                fact_text = fact.get_text(strip=True)
                if fact_text and len(fact_text) > 3 and fact_text not in desc_parts:
                    desc_parts.append(fact_text)
            
            # Combine all description parts with separator
            if len(desc_parts) > 1:
                listing['description'] = ' | '.join(desc_parts)
            elif desc_parts:
                listing['description'] = desc_parts[0]
            else:
                listing['description'] = listing['title']
                
            # Ensure minimum description length by looking harder
            if len(listing['description']) < 100:
                # Try to extract more text from the entire element
                all_text = element.get_text(separator=' ', strip=True)
                # Remove title to avoid duplication
                clean_text = all_text.replace(listing['title'], '').strip()
                if len(clean_text) > 50:
                    listing['description'] = f"{listing['title']} | {clean_text[:300]}..."
                
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
        text_lower = text.lower()
        
        # Extract number of rooms with more flexible patterns
        rooms_patterns = [
            r'(\d+)[.,](\d+)\s*[-\s]*zimmer',  # 3.5-Zimmer or 3,5 -Zimmer
            r'(\d+)[.,](\d+)\s*zimmer',        # 3.5zimmer
            r'(\d+)\s*zimmer',                 # 4 zimmer
            r'(\d+)[.,](\d+)[-\s]*zi',         # 3.5-zi
            r'(\d+)\s*zi\b'                    # 4 zi
        ]
        
        for pattern in rooms_patterns:
            rooms_match = re.search(pattern, text_lower)
            if rooms_match:
                if len(rooms_match.groups()) == 2:  # Decimal number
                    rooms = float(f"{rooms_match.group(1)}.{rooms_match.group(2)}")
                else:  # Whole number
                    rooms = float(rooms_match.group(1))
                listing['rooms'] = rooms
                break
            
        # Extract bedrooms
        bedroom_patterns = [
            r'(\d+)\s*schlafzimmer',
            r'(\d+)\s*sz\b'
        ]
        
        for pattern in bedroom_patterns:
            bedroom_match = re.search(pattern, text_lower)
            if bedroom_match:
                listing['bedrooms'] = int(bedroom_match.group(1))
                break
            
        # Extract size in square meters with more flexible patterns
        size_patterns = [
            r'(\d+)[.,]?\d*\s*m[²2]',
            r'(\d+)[.,]?\d*\s*qm',
            r'(\d+)[.,]?\d*\s*quadratmeter',
            r'(\d+)\s*m²',
            r'wohnfläche[:\s]*(\d+)',
        ]
        
        for pattern in size_patterns:
            size_match = re.search(pattern, text_lower)
            if size_match:
                listing['size_sqm'] = int(size_match.group(1))
                break
                
        # Extract features that might indicate suitability
        features = []
        
        # Outdoor features
        outdoor_keywords = ['garten', 'garden', 'terrasse', 'balkon', 'outdoor', 'grundstück']
        for keyword in outdoor_keywords:
            if keyword in text_lower:
                features.append(keyword)
                
        # Other property features
        feature_keywords = {
            'garage': ['garage', 'stellplatz', 'parkplatz'],
            'keller': ['keller', 'kellerraum'],
            'dachboden': ['dachboden', 'dachgeschoss'],
            'einbauküche': ['einbauküche', 'ebk'],
            'bad': ['bad', 'badezimmer'],
            'gäste-wc': ['gäste-wc', 'gästewc'],
        }
        
        for feature, keywords in feature_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    features.append(feature)
                    break
        
        if features:
            listing['features'] = list(set(features))  # Remove duplicates
        
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