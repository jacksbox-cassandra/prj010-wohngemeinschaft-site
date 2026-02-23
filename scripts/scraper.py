"""
Main scraper orchestrator for PRJ010 Wohngemeinschaft Property Search

Coordinates the entire scraping process:
- Load configuration and source handlers
- Run each enabled source per city
- Collect, validate, and deduplicate results
- Save to data/{city}/candidates_raw.json
- Merge with existing candidates_enriched.json
- Track status (new/active/updated/inactive)
"""

import os
import sys
import json
import time
import yaml
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the sources directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sources'))

from sources.base import ScraperError
from sources.kleinanzeigen import KleinanzeigenScraper
from sources.immowelt import ImmoweltScraper
from sources.immoscout import ImmoscoutScraper
from dedup import ListingDeduplicator
from validate import ListingValidator

logger = logging.getLogger(__name__)


class PropertyScraper:
    """
    Main orchestrator for property scraping across multiple sources
    """
    
    def __init__(self, config_path: str):
        """
        Initialize scraper with configuration
        
        Args:
            config_path: Path to config.yaml file
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # Initialize components
        self.deduplicator = ListingDeduplicator(self.config)
        self.validator = ListingValidator(self.config)
        
        # Initialize source scrapers
        self.scrapers = self._initialize_scrapers()
        
        # Setup logging
        self._setup_logging()
        
        # Stats tracking
        self.stats = {
            'start_time': time.time(),
            'cities_processed': 0,
            'total_raw_listings': 0,
            'total_valid_listings': 0,
            'total_new_listings': 0,
            'source_stats': {},
            'errors': []
        }
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            # Validate required sections
            required_sections = ['cities', 'sources']
            for section in required_sections:
                if section not in config:
                    raise ValueError(f"Missing required config section: {section}")
                    
            # Handle different config formats
            if 'search_params' not in config and 'search' not in config:
                logger.warning("No search configuration found, using defaults")
                config['search_params'] = {
                    'min_bedrooms': 4,
                    'min_size_sqm': 120
                }
                    
            return config
            
        except Exception as e:
            logger.error(f"Error loading config from {self.config_path}: {e}")
            raise
    
    def _initialize_scrapers(self) -> Dict[str, Any]:
        """Initialize all enabled source scrapers"""
        scrapers = {}
        
        source_classes = {
            'kleinanzeigen': KleinanzeigenScraper,
            'immowelt': ImmoweltScraper,
            'immoscout': ImmoscoutScraper
        }
        
        for source_name, source_config in self.config['sources'].items():
            if source_config.get('enabled', False):
                try:
                    if source_name in source_classes:
                        scrapers[source_name] = source_classes[source_name](self.config)
                        logger.info(f"Initialized {source_name} scraper")
                    else:
                        logger.warning(f"No scraper class found for source: {source_name}")
                except Exception as e:
                    logger.error(f"Failed to initialize {source_name} scraper: {e}")
                    self.stats['errors'].append(f"{source_name} init failed: {e}")
                    
        logger.info(f"Initialized {len(scrapers)} scrapers")
        return scrapers
    
    def _setup_logging(self):
        """Setup logging configuration"""
        # Handle both old and new config formats
        output_config = self.config.get('output', self.config.get('paths', {}))
        log_level = output_config.get('log_level', 'INFO')
        log_file = output_config.get('log_file', output_config.get('logs_dir', 'logs') + '/scraper.log')
        
        # Create logs directory if needed
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def scrape_all_cities(self, cities: Optional[List[str]] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Scrape all configured cities (or specified subset)
        
        Args:
            cities: List of city keys to scrape (None = all cities)
            dry_run: If True, don't save results
            
        Returns:
            Summary statistics
        """
        if cities is None:
            cities = list(self.config['cities'].keys())
            
        logger.info(f"Starting scrape for {len(cities)} cities: {cities}")
        
        all_results = {}
        
        for city in cities:
            try:
                logger.info(f"Processing city: {city}")
                city_results = self.scrape_city(city, dry_run=dry_run)
                all_results[city] = city_results
                self.stats['cities_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing city {city}: {e}")
                self.stats['errors'].append(f"{city}: {e}")
                continue
                
        # Generate final summary
        self._log_final_summary()
        
        return {
            'stats': self.stats,
            'results_by_city': all_results
        }
    
    def scrape_city(self, city: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Scrape a single city across all enabled sources
        
        Args:
            city: City key from config
            dry_run: If True, don't save results
            
        Returns:
            City scraping results
        """
        if city not in self.config['cities']:
            raise ValueError(f"Unknown city: {city}")
            
        logger.info(f"Scraping {city} with {len(self.scrapers)} sources")
        
        # Collect raw listings from all sources
        raw_listings = []
        source_counts = {}
        
        for source_name, scraper in self.scrapers.items():
            try:
                logger.info(f"Running {source_name} for {city}")
                
                source_listings = scraper.search(city)
                raw_listings.extend(source_listings)
                source_counts[source_name] = len(source_listings)
                
                # Update stats
                if source_name not in self.stats['source_stats']:
                    self.stats['source_stats'][source_name] = {'listings': 0, 'requests': 0}
                    
                self.stats['source_stats'][source_name]['listings'] += len(source_listings)
                
                # Get request stats
                request_stats = scraper.get_request_stats()
                self.stats['source_stats'][source_name]['requests'] += request_stats['requests_made']
                
                logger.info(f"{source_name}: {len(source_listings)} listings, "
                           f"{request_stats['requests_made']} requests")
                
            except Exception as e:
                logger.error(f"Error scraping {source_name} for {city}: {e}")
                source_counts[source_name] = 0
                self.stats['errors'].append(f"{city}/{source_name}: {e}")
                continue
                
        logger.info(f"Raw listings for {city}: {sum(source_counts.values())} total")
        self.stats['total_raw_listings'] += len(raw_listings)
        
        if not raw_listings:
            logger.warning(f"No listings found for {city}")
            return {
                'city': city,
                'raw_count': 0,
                'valid_count': 0,
                'new_count': 0,
                'source_counts': source_counts
            }
            
        # Validate listings
        valid_listings = []
        validation_results = []
        
        for listing in raw_listings:
            try:
                is_valid, reasons = self.validator.validate_listing(listing, city)
                
                if is_valid:
                    # Calculate suitability score
                    listing['suitability_score'] = self.validator.calculate_suitability_score(listing)
                    valid_listings.append(listing)
                    
                validation_results.append({
                    'listing_id': listing.get('url', 'unknown'),
                    'valid': is_valid,
                    'reasons': reasons
                })
                
            except Exception as e:
                logger.warning(f"Error validating listing: {e}")
                validation_results.append({
                    'listing_id': listing.get('url', 'unknown'),
                    'valid': False,
                    'reasons': [f"Validation error: {e}"]
                })
                
        logger.info(f"Valid listings for {city}: {len(valid_listings)}/{len(raw_listings)}")
        self.stats['total_valid_listings'] += len(valid_listings)
        
        if not valid_listings:
            logger.warning(f"No valid listings found for {city}")
            return {
                'city': city,
                'raw_count': len(raw_listings),
                'valid_count': 0,
                'new_count': 0,
                'source_counts': source_counts
            }
            
        # Deduplicate listings
        unique_listings = self.deduplicator.deduplicate_listings(valid_listings)
        logger.info(f"Unique listings for {city}: {len(unique_listings)}")
        
        # Load existing listings and update status
        existing_listings = self._load_existing_listings(city)
        if existing_listings:
            logger.info(f"Loaded {len(existing_listings)} existing listings for {city}")
            unique_listings = self.deduplicator.update_listing_status(unique_listings, existing_listings)
            inactive_listings = self.deduplicator.find_inactive_listings(unique_listings, existing_listings)
            
            # Add inactive listings to results
            unique_listings.extend(inactive_listings)
            
        # Count new listings
        new_count = len([l for l in unique_listings if l.get('status') == 'new'])
        self.stats['total_new_listings'] += new_count
        
        logger.info(f"Final results for {city}: {len(unique_listings)} total, {new_count} new")
        
        # Save results
        if not dry_run:
            self._save_results(city, unique_listings, validation_results)
            
        return {
            'city': city,
            'raw_count': len(raw_listings),
            'valid_count': len(valid_listings),
            'unique_count': len(unique_listings),
            'new_count': new_count,
            'source_counts': source_counts,
            'validation_results': validation_results
        }
    
    def _load_existing_listings(self, city: str) -> List[Dict[str, Any]]:
        """Load existing enriched listings for a city"""
        try:
            # Handle both config formats
            output_config = self.config.get('output', self.config.get('paths', {}))
            data_dir = output_config.get('data_dir', 'data')
            enriched_file = output_config.get('enriched_filename', 'candidates_enriched.json')
            
            file_path = Path(data_dir) / city / enriched_file
            
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Handle different data formats
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    if 'listings' in data:
                        return data['listings']
                    elif 'candidates' in data:
                        return data['candidates']
                    else:
                        logger.warning(f"Unknown data format in {file_path}")
                        return []
                else:
                    logger.warning(f"Unexpected data type in {file_path}: {type(data)}")
                    return []
            else:
                logger.info(f"No existing listings file found: {file_path}")
                return []
                
        except Exception as e:
            logger.warning(f"Error loading existing listings for {city}: {e}")
            return []
    
    def _save_results(self, city: str, listings: List[Dict[str, Any]], validation_results: List[Dict[str, Any]]):
        """Save scraping results to files"""
        try:
            # Setup directories - handle both config formats
            output_config = self.config.get('output', self.config.get('paths', {}))
            data_dir = output_config.get('data_dir', 'data')
            city_dir = Path(data_dir) / city
            city_dir.mkdir(parents=True, exist_ok=True)
            
            # Save listings.json (main output file for website generation)
            listings_path = city_dir / 'listings.json'
            
            listings_data = {
                'scraped_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'city': city,
                'count': len(listings),
                'listings': listings
            }
            
            with open(listings_path, 'w', encoding='utf-8') as f:
                json.dump(listings_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved listings: {listings_path}")
            
            # Also save raw candidates (for backward compatibility)
            raw_filename = output_config.get('raw_filename', 'candidates_raw.json')
            raw_path = city_dir / raw_filename
            
            raw_data = {
                'scraped_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'city': city,
                'count': len(listings),
                'listings': listings
            }
            
            with open(raw_path, 'w', encoding='utf-8') as f:
                json.dump(raw_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved raw results: {raw_path}")
            
            # Update enriched candidates (merge with existing)
            enriched_filename = output_config.get('enriched_filename', 'candidates_enriched.json')
            enriched_path = city_dir / enriched_filename
            
            # For now, just copy the raw data as enriched
            # In full implementation, this would preserve existing enrichment data
            enriched_data = {
                'last_updated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'city': city,
                'count': len(listings),
                'listings': listings
            }
            
            with open(enriched_path, 'w', encoding='utf-8') as f:
                json.dump(enriched_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved enriched results: {enriched_path}")
            
            # Save validation report
            validation_path = city_dir / f"validation_report_{int(time.time())}.json"
            
            validation_data = {
                'scraped_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'city': city,
                'total_listings': len(validation_results),
                'valid_listings': len([r for r in validation_results if r['valid']]),
                'validation_results': validation_results
            }
            
            with open(validation_path, 'w', encoding='utf-8') as f:
                json.dump(validation_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error saving results for {city}: {e}")
            raise
    
    def _log_final_summary(self):
        """Log final summary statistics"""
        elapsed = time.time() - self.stats['start_time']
        
        logger.info("=" * 60)
        logger.info("SCRAPING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Runtime: {elapsed:.1f} seconds")
        logger.info(f"Cities processed: {self.stats['cities_processed']}")
        logger.info(f"Total raw listings: {self.stats['total_raw_listings']}")
        logger.info(f"Total valid listings: {self.stats['total_valid_listings']}")
        logger.info(f"Total new listings: {self.stats['total_new_listings']}")
        
        if self.stats['source_stats']:
            logger.info("\nSource Statistics:")
            for source, stats in self.stats['source_stats'].items():
                logger.info(f"  {source}: {stats['listings']} listings, {stats['requests']} requests")
                
        if self.stats['errors']:
            logger.info(f"\nErrors encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors']:
                logger.info(f"  - {error}")
                
        logger.info("=" * 60)


def main():
    """Command line interface for the scraper"""
    parser = argparse.ArgumentParser(description='Property listing scraper for PRJ010')
    
    parser.add_argument('--config', default='config.yaml', 
                       help='Path to configuration file')
    parser.add_argument('--cities', nargs='+', 
                       help='Specific cities to scrape (default: all)')
    parser.add_argument('--dry-run', action='store_true',
                       help="Don't save results, just test scraping")
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Logging level')
    parser.add_argument('--sources', nargs='+',
                       help='Specific sources to run (default: all enabled)')
    
    args = parser.parse_args()
    
    # Setup basic logging for startup
    logging.basicConfig(level=getattr(logging, args.log_level))
    
    try:
        # Initialize scraper
        scraper = PropertyScraper(args.config)
        
        # Filter sources if specified
        if args.sources:
            enabled_sources = {k: v for k, v in scraper.scrapers.items() if k in args.sources}
            scraper.scrapers = enabled_sources
            logger.info(f"Limited to sources: {list(args.sources)}")
            
        # Run scraping
        results = scraper.scrape_all_cities(cities=args.cities, dry_run=args.dry_run)
        
        # Print summary
        print("\nScraping completed successfully!")
        print(f"Cities processed: {results['stats']['cities_processed']}")
        print(f"Total listings: {results['stats']['total_raw_listings']}")
        print(f"Valid listings: {results['stats']['total_valid_listings']}")
        print(f"New listings: {results['stats']['total_new_listings']}")
        
        if results['stats']['errors']:
            print(f"Errors: {len(results['stats']['errors'])}")
            
        return 0
        
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())