"""
Simplified deduplication module for PRJ010 Wohngemeinschaft Property Search

SIMPLIFIED APPROACH:
- URL-based deduplication only
- No fuzzy matching, no content hashing, no complicated logic
- Use URL hash as unique ID
- Simple and reliable
"""

import hashlib
import logging
from typing import List, Dict, Any, Set

logger = logging.getLogger(__name__)


class ListingDeduplicator:
    """
    Simple URL-based deduplication for property listings
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize deduplicator with configuration
        
        Args:
            config: Full configuration dict from config.yaml
        """
        self.config = config
        
    def deduplicate_listings(self, listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicates from a list of listings using simple URL-based dedup
        
        Args:
            listings: List of raw listings from scrapers
            
        Returns:
            List of unique listings with URL hash as ID
        """
        # Simple URL-based deduplication
        seen_urls = set()
        unique_listings = []
        
        for listing in listings:
            try:
                # Get URL from listing (try different field names)
                url = listing.get('url') or listing.get('listingUrl') or listing.get('link', '')
                
                if not url:
                    logger.warning(f"Skipping listing without URL: {listing.get('title', 'Unknown')}")
                    continue
                
                # Generate URL hash for deduplication and ID
                url_hash = hashlib.sha256(url.encode()).hexdigest()
                
                if url_hash in seen_urls:
                    logger.debug(f"Duplicate URL found: {url}")
                    continue
                
                # Add to unique listings
                seen_urls.add(url_hash)
                listing['id'] = url_hash[:12]  # Use first 12 chars of URL hash as ID
                listing['url_hash'] = url_hash  # Store full hash for reference
                listing['status'] = 'new'  # Will be updated by status tracking
                
                unique_listings.append(listing)
                
            except Exception as e:
                logger.warning(f"Error processing listing for deduplication: {e}")
                continue
                
        logger.info(f"Deduplication: {len(listings)} input -> {len(unique_listings)} unique listings")
        return unique_listings
    
    def update_listing_status(self, new_listings: List[Dict[str, Any]], 
                            existing_listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Update listing status by comparing with existing listings
        
        Args:
            new_listings: Newly scraped listings
            existing_listings: Previously saved listings
            
        Returns:
            Updated listings with correct status
        """
        # Create lookup by URL hash for existing listings
        existing_by_hash = {}
        for listing in existing_listings:
            url_hash = listing.get('url_hash')
            if not url_hash and 'url' in listing:
                # Generate hash for existing listings that don't have it
                url_hash = hashlib.sha256(listing['url'].encode()).hexdigest()
                listing['url_hash'] = url_hash
            if url_hash:
                existing_by_hash[url_hash] = listing
        
        # Update status for new listings
        updated_listings = []
        for listing in new_listings:
            url_hash = listing.get('url_hash')
            
            if url_hash in existing_by_hash:
                existing = existing_by_hash[url_hash]
                
                # Compare key fields to determine if updated
                key_fields = ['price', 'title', 'size_sqm', 'rooms', 'bedrooms']
                has_changes = False
                
                for field in key_fields:
                    old_val = existing.get(field)
                    new_val = listing.get(field)
                    if old_val != new_val and old_val is not None and new_val is not None:
                        has_changes = True
                        break
                
                listing['status'] = 'updated' if has_changes else 'active'
                listing['last_seen'] = listing.get('scraped_at', listing.get('fetchedAt'))
                
                # Preserve enrichment data if available
                if 'suitability' in existing:
                    listing['suitability'] = existing['suitability']
                if 'transport' in existing:
                    listing['transport'] = existing['transport']
                if 'education' in existing:
                    listing['education'] = existing['education']
                
            else:
                listing['status'] = 'new'
                
            updated_listings.append(listing)
        
        logger.info(f"Status update: {len([l for l in updated_listings if l['status'] == 'new'])} new, "
                   f"{len([l for l in updated_listings if l['status'] == 'active'])} active, "
                   f"{len([l for l in updated_listings if l['status'] == 'updated'])} updated")
        
        return updated_listings
    
    def find_inactive_listings(self, new_listings: List[Dict[str, Any]], 
                             existing_listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find listings that existed before but are no longer found
        
        Args:
            new_listings: Newly scraped listings
            existing_listings: Previously saved listings
            
        Returns:
            List of inactive listings
        """
        # Get hashes of new listings
        new_hashes = set()
        for listing in new_listings:
            url_hash = listing.get('url_hash')
            if url_hash:
                new_hashes.add(url_hash)
        
        # Find existing listings not in new results
        inactive_listings = []
        for listing in existing_listings:
            url_hash = listing.get('url_hash')
            if not url_hash and 'url' in listing:
                # Generate hash for existing listings that don't have it
                url_hash = hashlib.sha256(listing['url'].encode()).hexdigest()
                listing['url_hash'] = url_hash
                
            if url_hash and url_hash not in new_hashes:
                # Only mark as inactive if it was previously active
                if listing.get('status') in ['new', 'active', 'updated']:
                    listing['status'] = 'inactive'
                    inactive_listings.append(listing)
        
        logger.info(f"Found {len(inactive_listings)} inactive listings")
        return inactive_listings