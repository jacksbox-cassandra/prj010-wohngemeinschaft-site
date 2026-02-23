#!/usr/bin/env python3
"""
PRJ010 Property Enrichment Pipeline
===================================

Enriches property listings with:
1. URL verification (HEAD requests)
2. Image downloads and resizing
3. Transport time calculations
4. School/Kindergarten proximity
5. Suitability scoring (0-10 scale)
6. Pros/cons generation

Usage:
    python enrich.py                    # Enrich all cities
    python enrich.py --city freiburg    # Single city
    python enrich.py --verify-only      # Just check URLs
    python enrich.py --images-only      # Just download images
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from PIL import Image


# Configuration
class Config:
    # API Configuration
    OPENROUTE_SERVICE_KEY = os.getenv('OPENROUTE_SERVICE_KEY')  # Optional, free tier available
    USER_AGENT = 'Mozilla/5.0 (Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    # Rate limiting
    REQUEST_DELAY = 1.0  # seconds between requests
    MAX_IMAGE_SIZE_MB = 1.0
    MAX_IMAGE_DIMENSION = 1200
    
    # Paths
    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_DIR = PROJECT_ROOT / 'data'
    ASSETS_DIR = PROJECT_ROOT / 'docs' / 'assets'
    
    # Transport estimation fallbacks (minutes per km)
    TRANSPORT_FALLBACK_RATES = {
        'urban': 3,      # 20 km/h average in city
        'suburban': 2.5, # 24 km/h average 
        'rural': 2       # 30 km/h average
    }


# Logging setup
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


class PropertyEnricher:
    """Main enrichment orchestrator"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': Config.USER_AGENT})
        self.city_centers = self._load_city_centers()
        
    def _load_city_centers(self) -> Dict[str, Tuple[float, float]]:
        """Load city center coordinates from search-config.json"""
        try:
            config_path = Config.DATA_DIR / 'search-config.json'
            with open(config_path) as f:
                data = json.load(f)
            
            centers = {}
            for city in data['cities']:
                centers[city['name'].lower()] = (city['lat'], city['lon'])
            
            logging.info(f"Loaded {len(centers)} city centers")
            return centers
        except Exception as e:
            logging.error(f"Failed to load city centers: {e}")
            return {}
    
    def load_city_data(self, city: str) -> Optional[Dict]:
        """Load enriched candidates data for a city"""
        try:
            data_path = Config.DATA_DIR / city.lower() / 'candidates_enriched.json'
            if not data_path.exists():
                logging.warning(f"No enriched data found for {city} at {data_path}")
                return None
                
            with open(data_path) as f:
                data = json.load(f)
            logging.info(f"Loaded {len(data.get('candidates', []))} candidates for {city}")
            return data
        except Exception as e:
            logging.error(f"Error loading {city} data: {e}")
            return None
    
    def save_city_data(self, city: str, data: Dict) -> bool:
        """Save enriched data back to file"""
        try:
            data_path = Config.DATA_DIR / city.lower() / 'candidates_enriched.json'
            data['enrichedAt'] = datetime.now(timezone.utc).isoformat()
            
            # Create backup
            if data_path.exists():
                backup_path = data_path.with_suffix('.json.backup')
                data_path.rename(backup_path)
            
            with open(data_path, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logging.info(f"Saved enriched data for {city}")
            return True
        except Exception as e:
            logging.error(f"Error saving {city} data: {e}")
            return False
    
    def verify_url_status(self, url: str) -> str:
        """
        Verify listing URL status
        Returns: 'active' (200), 'check' (4xx/5xx), 'gone' (404)
        """
        if not url or not url.startswith('http'):
            return 'check'
        
        try:
            response = self.session.head(url, timeout=10, allow_redirects=True)
            time.sleep(Config.REQUEST_DELAY)
            
            if response.status_code == 200:
                return 'active'
            elif response.status_code == 404:
                return 'gone'
            else:
                return 'check'
                
        except requests.exceptions.RequestException as e:
            logging.warning(f"URL verification failed for {url}: {e}")
            return 'check'
    
    def download_and_resize_image(self, image_url: str, save_path: Path) -> bool:
        """
        Download image and resize if larger than limits
        """
        if not image_url or not image_url.startswith('http'):
            return False
        
        try:
            # Skip if image already exists and is recent
            if save_path.exists():
                stat = save_path.stat()
                age_hours = (time.time() - stat.st_mtime) / 3600
                if age_hours < 24:  # Skip if less than 24h old
                    logging.debug(f"Skipping recent image: {save_path}")
                    return True
            
            # Download image
            response = self.session.get(image_url, timeout=15, stream=True)
            response.raise_for_status()
            time.sleep(Config.REQUEST_DELAY)
            
            # Save temporary file
            temp_path = save_path.with_suffix('.tmp')
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Check size and resize if needed
            if temp_path.stat().st_size > Config.MAX_IMAGE_SIZE_MB * 1024 * 1024:
                self._resize_image(temp_path, save_path)
                temp_path.unlink()
            else:
                temp_path.rename(save_path)
            
            logging.info(f"Downloaded image: {save_path}")
            return True
            
        except Exception as e:
            logging.warning(f"Image download failed for {image_url}: {e}")
            if temp_path.exists():
                temp_path.unlink()
            return False
    
    def _resize_image(self, input_path: Path, output_path: Path):
        """Resize image to fit within limits"""
        try:
            with Image.open(input_path) as img:
                # Calculate new size maintaining aspect ratio
                ratio = min(
                    Config.MAX_IMAGE_DIMENSION / img.width,
                    Config.MAX_IMAGE_DIMENSION / img.height
                )
                
                if ratio < 1:
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Save with optimization
                img.save(output_path, 'JPEG', quality=85, optimize=True)
        except Exception as e:
            logging.error(f"Image resize failed: {e}")
            # Fallback: copy original
            input_path.rename(output_path)
    
    def calculate_transport_time(self, property_location: str, city: str) -> Optional[int]:
        """
        Calculate transport time to city center in minutes
        Uses OpenRouteService API or fallback estimation
        """
        if city.lower() not in self.city_centers:
            logging.warning(f"No center coordinates for {city}")
            return None
        
        center_lat, center_lon = self.city_centers[city.lower()]
        
        # Try to extract coordinates from location (if available)
        # For now, use fallback estimation based on distance
        try:
            # Simple distance-based estimation
            # Parse location for distance clues (e.g., "20km NW of Augsburg")
            distance_match = re.search(r'(\d+)\s*km', property_location)
            if distance_match:
                distance_km = int(distance_match.group(1))
                
                # Estimate based on location type
                if 'zentrum' in property_location.lower() or 'innenstadt' in property_location.lower():
                    rate = Config.TRANSPORT_FALLBACK_RATES['urban']
                elif any(word in property_location.lower() for word in ['stadtrand', 'außerhalb', 'ort']):
                    rate = Config.TRANSPORT_FALLBACK_RATES['rural']
                else:
                    rate = Config.TRANSPORT_FALLBACK_RATES['suburban']
                
                return int(distance_km * rate)
            
            # Default estimation for central locations
            if any(word in property_location.lower() for word in ['zentrum', 'innenstadt', 'mitte']):
                return 10
            else:
                return 20
                
        except Exception as e:
            logging.warning(f"Transport calculation failed for {property_location}: {e}")
            return 20  # Default fallback
    
    def find_nearby_education(self, property_location: str) -> Dict[str, str]:
        """
        Find nearby schools and kindergartens
        Uses simplified estimation for now
        """
        # Simplified implementation based on location type
        education = {
            'nearestKindergarten': '~15 min walk',
            'nearestSchool': '~15 min walk'
        }
        
        # Better estimates based on location clues
        if any(word in property_location.lower() for word in ['zentrum', 'innenstadt', 'mitte']):
            education['nearestKindergarten'] = '~8 min walk'
            education['nearestSchool'] = '~10 min walk'
        elif any(word in property_location.lower() for word in ['dorf', 'ort', 'ländlich']):
            education['nearestKindergarten'] = '~20 min walk'
            education['nearestSchool'] = '~25 min walk'
        elif 'neubau' in property_location.lower() or 'siedlung' in property_location.lower():
            education['nearestKindergarten'] = '~12 min walk'
            education['nearestSchool'] = '~15 min walk'
        
        return education
    
    def calculate_suitability_score(self, candidate: Dict) -> int:
        """
        Calculate suitability score (0-10) based on criteria
        """
        score = 0
        
        # Size (max 2 points)
        size_sqm = candidate.get('size_sqm', 0)
        if size_sqm >= 180:
            score += 2
        elif size_sqm >= 150:
            score += 1
        
        # Bedrooms (max 2 points)
        bedrooms = candidate.get('bedrooms', 0)
        if bedrooms >= 5:
            score += 2
        elif bedrooms >= 4:
            score += 1
        
        # Outdoor space (max 2 points)
        features = candidate.get('features', [])
        if any(f in features for f in ['large_garden', 'garden', 'grundstück']):
            score += 2
        elif any(f in features for f in ['balcony', 'terrasse', 'terrace']):
            score += 1
        
        # Transport (max 2 points)
        transport = candidate.get('transport', {})
        if transport.get('toCityCenter'):
            transport_text = transport['toCityCenter']
            # Extract minutes from transport text
            minutes_match = re.search(r'(\d+)\s*min', transport_text)
            if minutes_match:
                minutes = int(minutes_match.group(1))
                if minutes <= 15:
                    score += 2
                elif minutes <= 25:
                    score += 1
        
        # Education (max 1 point)
        education = candidate.get('education', {})
        if education.get('nearestSchool'):
            school_text = education['nearestSchool']
            if '15 min' in school_text or '10 min' in school_text or '8 min' in school_text:
                score += 1
        
        # Nature/quiet (max 1 point)
        location = candidate.get('location', '').lower()
        description = candidate.get('description', '').lower()
        if any(word in location + ' ' + description for word in [
            'ruhig', 'natur', 'wald', 'park', 'grün', 'ländlich', 'idyllisch'
        ]):
            score += 1
        
        return min(score, 10)  # Cap at 10
    
    def generate_pros_cons(self, candidate: Dict) -> Tuple[List[str], List[str]]:
        """
        Generate pros and cons based on candidate features
        """
        pros = []
        cons = []
        
        # Analyze size
        size_sqm = candidate.get('size_sqm', 0)
        if size_sqm >= 180:
            pros.append("Excellent size for 2 families")
        elif size_sqm >= 150:
            pros.append("Good size for shared living")
        elif size_sqm < 140:
            cons.append("Might feel cramped for 2 families")
        
        # Analyze rooms/bedrooms
        bedrooms = candidate.get('bedrooms', 0)
        rooms = candidate.get('rooms', 0)
        if bedrooms >= 5:
            pros.append("Plenty of bedrooms")
        elif bedrooms >= 4:
            pros.append("Adequate bedroom count")
        else:
            cons.append("Limited bedroom options")
        
        # Outdoor space
        features = candidate.get('features', [])
        if any(f in features for f in ['large_garden', 'garden', 'grundstück']):
            pros.append("Garden for children/relaxation")
        elif any(f in features for f in ['balcony', 'terrasse', 'terrace']):
            pros.append("Outdoor space available")
        else:
            cons.append("No outdoor space mentioned")
        
        # Price analysis
        price = candidate.get('price', 0)
        price_type = candidate.get('priceType', '')
        if price and size_sqm:
            price_per_sqm = price / size_sqm
            if price_type == 'buy':
                if price_per_sqm < 4000:
                    pros.append("Excellent price per m²")
                elif price_per_sqm < 5000:
                    pros.append("Good value for money")
                elif price_per_sqm > 6000:
                    cons.append("High price per m²")
            else:  # rent
                if price_per_sqm < 10:
                    pros.append("Affordable rent per m²")
                elif price_per_sqm > 15:
                    cons.append("High rent per m²")
        
        # Location analysis
        location = candidate.get('location', '').lower()
        if any(word in location for word in ['zentrum', 'innenstadt', 'mitte']):
            pros.append("Central location")
        elif any(word in location for word in ['außerhalb', 'ländlich']):
            pros.append("Quiet, rural setting")
            cons.append("Far from city center")
        
        # Transport
        transport = candidate.get('transport', {})
        if transport.get('toCityCenter'):
            transport_text = transport['toCityCenter']
            minutes_match = re.search(r'(\d+)\s*min', transport_text)
            if minutes_match:
                minutes = int(minutes_match.group(1))
                if minutes <= 15:
                    pros.append("Excellent public transport")
                elif minutes <= 25:
                    pros.append("Good transport links")
                else:
                    cons.append("Long commute to center")
        
        # Check for renovation needs
        description = candidate.get('description', '').lower()
        title = candidate.get('title', '').lower()
        if any(word in description + ' ' + title for word in [
            'renovierung', 'sanierung', 'modernisierung', 'ausbau', 'potential'
        ]):
            cons.append("May need renovation work")
        
        # Check for special features
        if 'new_heating' in features or 'neue heizung' in description:
            pros.append("Modern heating system")
        
        if 'parking' in features or 'stellplatz' in description:
            pros.append("Parking available")
        elif 'kein parkplatz' in description:
            cons.append("No parking mentioned")
        
        return pros[:4], cons[:3]  # Limit length
    
    def enrich_candidate(self, candidate: Dict, city: str, verify_only: bool = False, images_only: bool = False) -> Dict:
        """
        Enrich a single candidate with all data
        """
        candidate_id = candidate.get('id', 'unknown')
        logging.info(f"Enriching {candidate_id}")
        
        # URL verification
        if not verify_only:
            url_status = self.verify_url_status(candidate.get('listingUrl', ''))
            candidate['status'] = url_status
            candidate['lastVerified'] = datetime.now(timezone.utc).isoformat()
            
            if url_status == 'gone':
                logging.warning(f"Candidate {candidate_id} appears to be gone (404)")
        
        # Image download
        if not verify_only and candidate.get('imageUrl'):
            image_path = Config.ASSETS_DIR / city.lower() / 'photos' / f"{candidate_id}.jpg"
            if not image_path.exists() or images_only:
                success = self.download_and_resize_image(candidate['imageUrl'], image_path)
                if success:
                    candidate['hasLocalImage'] = True
                else:
                    candidate['hasLocalImage'] = False
        
        if verify_only or images_only:
            return candidate
        
        # Transport calculation
        if not candidate.get('transport', {}).get('toCityCenter'):
            transport_mins = self.calculate_transport_time(
                candidate.get('location', ''), city
            )
            if transport_mins:
                candidate['transport'] = {
                    'toCityCenter': f"{transport_mins} min",
                    'method': 'estimated'
                }
        
        # Education proximity
        if not candidate.get('education'):
            candidate['education'] = self.find_nearby_education(
                candidate.get('location', '')
            )
        
        # Suitability scoring
        new_score = self.calculate_suitability_score(candidate)
        pros, cons = self.generate_pros_cons(candidate)
        
        candidate['suitability'] = {
            'score': new_score,
            'pros': pros,
            'cons': cons
        }
        
        return candidate
    
    def enrich_city(self, city: str, verify_only: bool = False, images_only: bool = False) -> bool:
        """
        Enrich all candidates for a city
        """
        logging.info(f"Starting enrichment for {city}")
        
        # Load data
        data = self.load_city_data(city)
        if not data:
            return False
        
        candidates = data.get('candidates', [])
        if not candidates:
            logging.warning(f"No candidates found for {city}")
            return True
        
        # Enrich each candidate
        enriched_count = 0
        for candidate in candidates:
            try:
                self.enrich_candidate(candidate, city, verify_only, images_only)
                enriched_count += 1
                
                # Small delay between candidates
                if not verify_only:
                    time.sleep(0.5)
                    
            except Exception as e:
                logging.error(f"Failed to enrich {candidate.get('id', 'unknown')}: {e}")
        
        # Save back
        success = self.save_city_data(city, data)
        if success:
            logging.info(f"Enriched {enriched_count}/{len(candidates)} candidates for {city}")
        
        return success
    
    def enrich_all_cities(self, verify_only: bool = False, images_only: bool = False) -> int:
        """
        Enrich all cities
        Returns number of successfully enriched cities
        """
        cities = ['freiburg', 'augsburg', 'halle', 'leipzig', 'magdeburg']
        success_count = 0
        
        for city in cities:
            try:
                if self.enrich_city(city, verify_only, images_only):
                    success_count += 1
            except Exception as e:
                logging.error(f"Failed to enrich {city}: {e}")
        
        return success_count


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description='PRJ010 Property Enrichment Pipeline')
    parser.add_argument('--city', help='Enrich single city (freiburg, augsburg, halle, leipzig, magdeburg)')
    parser.add_argument('--verify-only', action='store_true', help='Only verify URLs, skip other enrichment')
    parser.add_argument('--images-only', action='store_true', help='Only download images')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Setup
    setup_logging()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate city argument
    valid_cities = ['freiburg', 'augsburg', 'halle', 'leipzig', 'magdeburg']
    if args.city and args.city.lower() not in valid_cities:
        print(f"Error: City must be one of {valid_cities}")
        return 1
    
    # Install PIL if needed
    try:
        import PIL
    except ImportError:
        logging.info("Installing Pillow for image processing...")
        os.system("pip install Pillow")
        import PIL
    
    # Run enrichment
    enricher = PropertyEnricher()
    
    if args.city:
        success = enricher.enrich_city(
            args.city.lower(), 
            verify_only=args.verify_only,
            images_only=args.images_only
        )
        return 0 if success else 1
    else:
        success_count = enricher.enrich_all_cities(
            verify_only=args.verify_only,
            images_only=args.images_only
        )
        total_cities = 5
        logging.info(f"Enrichment complete: {success_count}/{total_cities} cities successful")
        return 0 if success_count == total_cities else 1


if __name__ == '__main__':
    sys.exit(main())