"""
Deduplication module for PRJ010 Wohngemeinschaft Property Search

Handles:
- URL normalization and deduplication
- Content-based hashing for cross-source duplicate detection  
- Fuzzy string matching for similar listings
- Status tracking (new/active/updated/inactive)
"""

import hashlib
import re
import logging
from typing import List, Dict, Any, Set, Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class ListingDeduplicator:
    """
    Handles deduplication of property listings across multiple sources
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize deduplicator with configuration
        
        Args:
            config: Full configuration dict from config.yaml
        """
        self.config = config
        self.dedup_config = config.get('deduplication', {})
        self.fuzzy_threshold = self.dedup_config.get('fuzzy_threshold', 0.85)
        
        # Track URLs and hashes we've seen
        self.seen_urls: Set[str] = set()
        self.seen_hashes: Set[str] = set()
        self.listings_by_hash: Dict[str, List[Dict[str, Any]]] = {}
        
    def deduplicate_listings(self, listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicates from a list of listings
        
        Args:
            listings: List of raw listings from scrapers
            
        Returns:
            List of unique listings with duplicate tracking info
        """
        unique_listings = []
        
        for listing in listings:
            try:
                # Step 1: Normalize and check URL
                normalized_url = self._normalize_url(listing.get('url', ''))
                if not normalized_url:
                    logger.warning(f"Skipping listing with invalid URL: {listing.get('title', 'Unknown')}")
                    continue
                    
                if normalized_url in self.seen_urls:
                    logger.debug(f"Duplicate URL found: {normalized_url}")
                    continue
                    
                # Step 2: Generate content hash
                content_hash = self._generate_content_hash(listing)
                
                if content_hash in self.seen_hashes:
                    logger.debug(f"Duplicate content hash found: {content_hash[:8]}...")
                    # Check if it's a cross-source duplicate
                    existing_listings = self.listings_by_hash.get(content_hash, [])
                    self._handle_cross_source_duplicate(listing, existing_listings)
                    continue
                    
                # Step 3: Fuzzy matching check
                fuzzy_duplicate = self._find_fuzzy_duplicate(listing, unique_listings)
                if fuzzy_duplicate:
                    logger.debug(f"Fuzzy duplicate found for: {listing.get('title', '')}")
                    self._merge_duplicate_info(fuzzy_duplicate, listing)
                    continue
                    
                # Step 4: Add to unique listings
                listing['normalized_url'] = normalized_url
                listing['content_hash'] = content_hash
                listing['duplicate_sources'] = [listing.get('source', 'unknown')]
                listing['status'] = 'new'  # Will be updated by status tracking
                
                unique_listings.append(listing)
                self.seen_urls.add(normalized_url)
                self.seen_hashes.add(content_hash)
                
                # Track by hash for cross-source detection
                if content_hash not in self.listings_by_hash:
                    self.listings_by_hash[content_hash] = []
                self.listings_by_hash[content_hash].append(listing)
                
            except Exception as e:
                logger.warning(f"Error processing listing for deduplication: {e}")
                continue
                
        logger.info(f"Deduplication: {len(listings)} input -> {len(unique_listings)} unique")
        return unique_listings
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL for consistent comparison
        
        Removes tracking parameters and standardizes format
        """
        if not url:
            return ''
            
        try:
            parsed = urlparse(url)
            
            # Remove unwanted query parameters
            remove_params = self.dedup_config.get('url_normalize', {}).get('remove_params', [])
            
            if parsed.query:
                params = parse_qs(parsed.query)
                filtered_params = {k: v for k, v in params.items() if k not in remove_params}
                new_query = urlencode(filtered_params, doseq=True)
            else:
                new_query = ''
                
            # Rebuild URL
            normalized = urlunparse((
                parsed.scheme.lower(),
                parsed.netloc.lower(), 
                parsed.path.rstrip('/'),
                parsed.params,
                new_query,
                ''  # Remove fragment
            ))
            
            return normalized
            
        except Exception as e:
            logger.warning(f"Error normalizing URL '{url}': {e}")
            return url.lower().strip()
    
    def _generate_content_hash(self, listing: Dict[str, Any]) -> str:
        """
        Generate SHA256 hash from key listing content
        
        Uses normalized address, price, and size for hashing
        """
        try:
            hash_fields = self.dedup_config.get('hash_fields', [])
            
            # Default fields if not configured
            if not hash_fields:
                hash_fields = ['normalized_address', 'price', 'size_sqm']
                
            hash_components = []
            
            for field in hash_fields:
                value = listing.get(field)
                
                if field == 'normalized_address':
                    # Normalize address for hashing
                    address = listing.get('address', '')
                    value = self._normalize_address(address)
                elif value is not None:
                    value = str(value)
                else:
                    value = ''
                    
                hash_components.append(value)
                
            # Create hash
            hash_string = '|'.join(hash_components)
            content_hash = hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
            
            return content_hash
            
        except Exception as e:
            logger.warning(f"Error generating content hash: {e}")
            # Fallback hash
            fallback_string = f"{listing.get('price', '')}{listing.get('address', '')}"
            return hashlib.sha256(fallback_string.encode('utf-8')).hexdigest()
    
    def _normalize_address(self, address: str) -> str:
        """
        Normalize address string for consistent comparison
        """
        if not address:
            return ''
            
        # Convert to lowercase
        normalized = address.lower()
        
        # Remove common variations
        replacements = {
            'straße': 'str',
            'strasse': 'str', 
            'platz': 'pl',
            'allee': 'allee',
            '  ': ' ',  # Multiple spaces
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
            
        # Remove special characters and extra whitespace
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = ' '.join(normalized.split())
        
        return normalized.strip()
    
    def _find_fuzzy_duplicate(self, listing: Dict[str, Any], existing_listings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find potential duplicate using fuzzy string matching
        
        Compares title and address using Levenshtein similarity
        """
        current_title = listing.get('title', '').lower()
        current_address = self._normalize_address(listing.get('address', ''))
        
        if not current_title and not current_address:
            return None
            
        fuzzy_fields = self.dedup_config.get('fuzzy_fields', ['title', 'address'])
        
        for existing in existing_listings:
            similarity_scores = []
            
            # Compare title if enabled
            if 'title' in fuzzy_fields and current_title:
                existing_title = existing.get('title', '').lower()
                if existing_title:
                    title_similarity = SequenceMatcher(None, current_title, existing_title).ratio()
                    similarity_scores.append(title_similarity)
                    
            # Compare address if enabled
            if 'address' in fuzzy_fields and current_address:
                existing_address = self._normalize_address(existing.get('address', ''))
                if existing_address:
                    address_similarity = SequenceMatcher(None, current_address, existing_address).ratio()
                    similarity_scores.append(address_similarity)
                    
            # Check if any similarity exceeds threshold
            if similarity_scores and max(similarity_scores) >= self.fuzzy_threshold:
                logger.debug(f"Fuzzy match found: {max(similarity_scores):.2f} similarity")
                return existing
                
        return None
    
    def _handle_cross_source_duplicate(self, new_listing: Dict[str, Any], existing_listings: List[Dict[str, Any]]):
        """
        Handle when we find a duplicate across different sources
        """
        if not existing_listings:
            return
            
        # Add source to existing listing's source tracking
        existing = existing_listings[0]
        sources = existing.get('duplicate_sources', [])
        
        new_source = new_listing.get('source', 'unknown')
        if new_source not in sources:
            sources.append(new_source)
            existing['duplicate_sources'] = sources
            
        logger.info(f"Cross-source duplicate: {existing.get('title', '')} found on {sources}")
    
    def _merge_duplicate_info(self, existing_listing: Dict[str, Any], new_listing: Dict[str, Any]):
        """
        Merge information from duplicate listing into existing one
        """
        # Add source tracking
        sources = existing_listing.get('duplicate_sources', [])
        new_source = new_listing.get('source', 'unknown')
        
        if new_source not in sources:
            sources.append(new_source)
            existing_listing['duplicate_sources'] = sources
            
        # Update with any missing or better information
        for field in ['image_url', 'description', 'features']:
            if field not in existing_listing or not existing_listing[field]:
                if field in new_listing and new_listing[field]:
                    existing_listing[field] = new_listing[field]
                    
        # Update with more detailed information if available
        for field in ['rooms', 'bedrooms', 'size_sqm']:
            if field not in existing_listing and field in new_listing:
                existing_listing[field] = new_listing[field]
    
    def update_listing_status(self, current_listings: List[Dict[str, Any]], 
                            previous_listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Update listing status by comparing with previous scrape results
        
        Args:
            current_listings: Newly scraped listings
            previous_listings: Previously scraped listings
            
        Returns:
            Updated listings with status information
        """
        # Create lookup maps
        previous_by_url = {listing['normalized_url']: listing for listing in previous_listings if 'normalized_url' in listing}
        previous_by_hash = {listing['content_hash']: listing for listing in previous_listings if 'content_hash' in listing}
        
        updated_listings = []
        
        for listing in current_listings:
            url = listing.get('normalized_url', '')
            content_hash = listing.get('content_hash', '')
            
            if url in previous_by_url:
                previous = previous_by_url[url]
                
                # Check if content changed
                if content_hash != previous.get('content_hash', ''):
                    listing['status'] = 'updated'
                    listing['previous_hash'] = previous.get('content_hash')
                else:
                    listing['status'] = 'active'
                    
                # Preserve any existing enrichment data
                self._preserve_enrichment_data(listing, previous)
                
            elif content_hash in previous_by_hash:
                # Same content but different URL (rare)
                listing['status'] = 'updated'
                previous = previous_by_hash[content_hash]
                self._preserve_enrichment_data(listing, previous)
                
            else:
                listing['status'] = 'new'
                
            updated_listings.append(listing)
            
        # Mark missing listings as inactive (handled separately)
        
        return updated_listings
    
    def _preserve_enrichment_data(self, current: Dict[str, Any], previous: Dict[str, Any]):
        """
        Preserve enrichment data from previous scrapes
        """
        enrichment_fields = [
            'transport_time_min', 'nearest_school_dist_km', 'suitability_score',
            'pros', 'cons', 'last_enriched', 'enrichment_status'
        ]
        
        for field in enrichment_fields:
            if field in previous and field not in current:
                current[field] = previous[field]
    
    def find_inactive_listings(self, current_listings: List[Dict[str, Any]], 
                             previous_listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find listings that were present before but are missing now
        
        Returns:
            List of listings marked as inactive
        """
        current_urls = {listing.get('normalized_url') for listing in current_listings}
        current_hashes = {listing.get('content_hash') for listing in current_listings}
        
        inactive_listings = []
        
        for previous in previous_listings:
            prev_url = previous.get('normalized_url', '')
            prev_hash = previous.get('content_hash', '')
            
            # Skip if already inactive
            if previous.get('status') == 'inactive':
                continue
                
            # Check if missing from current scrape
            if prev_url not in current_urls and prev_hash not in current_hashes:
                previous['status'] = 'inactive'
                inactive_listings.append(previous)
                
        return inactive_listings


def main():
    """Test the deduplicator"""
    import json
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Test data
    test_config = {
        'deduplication': {
            'url_normalize': {
                'remove_params': ['utm_source', 'ref']
            },
            'hash_fields': ['normalized_address', 'price', 'size_sqm'],
            'fuzzy_threshold': 0.85,
            'fuzzy_fields': ['title', 'address']
        }
    }
    
    test_listings = [
        {
            'source': 'kleinanzeigen',
            'title': 'Schönes Einfamilienhaus mit Garten',
            'url': 'https://kleinanzeigen.de/listing/123?ref=search',
            'address': 'Musterstraße 15, Freiburg',
            'price': 450000,
            'size_sqm': 150
        },
        {
            'source': 'immowelt', 
            'title': 'Einfamilienhaus mit Garten in Freiburg',
            'url': 'https://immowelt.de/expose/456',
            'address': 'Muster Str. 15, 79100 Freiburg',
            'price': 450000,
            'size_sqm': 150
        },
        {
            'source': 'kleinanzeigen',
            'title': 'Moderne Villa am Stadtrand',
            'url': 'https://kleinanzeigen.de/listing/123?utm_source=google',
            'address': 'Gartenweg 8, Freiburg', 
            'price': 680000,
            'size_sqm': 200
        }
    ]
    
    # Test deduplication
    dedup = ListingDeduplicator(test_config)
    unique_listings = dedup.deduplicate_listings(test_listings)
    
    print(f"Input listings: {len(test_listings)}")
    print(f"Unique listings: {len(unique_listings)}")
    
    for i, listing in enumerate(unique_listings, 1):
        print(f"\n{i}. {listing['title']}")
        print(f"   Sources: {listing['duplicate_sources']}")
        print(f"   URL: {listing['normalized_url']}")
        print(f"   Hash: {listing['content_hash'][:8]}...")


if __name__ == '__main__':
    main()