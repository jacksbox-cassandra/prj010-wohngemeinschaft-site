"""
Base scraper class for PRJ010 Wohngemeinschaft Property Search

Provides common functionality for all source-specific scrapers:
- Rate limiting with random delays
- User agent rotation
- robots.txt respect
- Error handling and retries
- Abstract interface for source implementations
"""

import time
import random
import logging
import requests
from abc import ABC, abstractmethod
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Base exception for scraper-related errors"""
    pass


class RobotsTxtError(ScraperError):
    """Raised when robots.txt disallows access"""
    pass


class RateLimitError(ScraperError):
    """Raised when rate limiting is triggered"""
    pass


class BaseScraper(ABC):
    """
    Abstract base class for property source scrapers
    
    Handles common functionality like rate limiting, user agents, robots.txt
    Subclasses must implement search() and parse_listing() methods
    """
    
    def __init__(self, config: Dict[str, Any], source_name: str):
        """
        Initialize the scraper with configuration
        
        Args:
            config: Full configuration dict from config.yaml
            source_name: Name of this source (e.g., 'kleinanzeigen')
        """
        self.config = config
        self.source_name = source_name
        self.source_config = config['sources'][source_name]
        # Handle both old and new config format
        self.scraping_config = config.get('scraping', config.get('scraper', {}))
        if not self.scraping_config:
            # Default scraping config if none found
            self.scraping_config = {
                'delay_between_requests_sec': 3,
                'delay_variation_sec': 2,
                'max_requests_per_source': 50,
                'request_timeout_sec': 30,
                'max_retries': 3,
                'retry_delay_sec': 5,
                'user_agents': [
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ]
            }
        
        # Request session with common settings
        self.session = requests.Session()
        timeout = self.scraping_config.get('request_timeout_sec', self.scraping_config.get('timeout_seconds', 30))
        self.session.timeout = timeout
        
        # Rate limiting state
        self.last_request_time = 0
        self.request_count = 0
        max_requests = self.scraping_config.get('max_requests_per_source', 50)
        self.max_requests = max_requests
        
        # User agents for rotation  
        user_agents = self.scraping_config.get('user_agents', [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        ])
        self.user_agents = user_agents
        self.current_user_agent_idx = 0
        
        # Robots.txt parser
        self.robots_parser = None
        self._load_robots_txt()
        
    def _load_robots_txt(self):
        """Load and parse robots.txt for this source"""
        try:
            base_url = self.source_config['base_url']
            robots_url = urljoin(base_url, '/robots.txt')
            
            self.robots_parser = RobotFileParser()
            self.robots_parser.set_url(robots_url)
            self.robots_parser.read()
            
            logger.info(f"Loaded robots.txt for {self.source_name}")
            
        except Exception as e:
            logger.warning(f"Could not load robots.txt for {self.source_name}: {e}")
            # Continue without robots.txt checking
            self.robots_parser = None
    
    def _check_robots_txt(self, url: str) -> bool:
        """
        Check if URL is allowed by robots.txt
        
        Args:
            url: URL to check
            
        Returns:
            True if allowed or robots.txt unavailable
            
        Raises:
            RobotsTxtError: If robots.txt explicitly disallows
        """
        if not self.robots_parser:
            return True
            
        # Use current user agent for checking
        user_agent = self._get_current_user_agent()
        
        if not self.robots_parser.can_fetch(user_agent, url):
            raise RobotsTxtError(f"robots.txt disallows access to {url}")
            
        return True
    
    def _get_current_user_agent(self) -> str:
        """Get current user agent and rotate for next request"""
        user_agent = self.user_agents[self.current_user_agent_idx]
        self.current_user_agent_idx = (self.current_user_agent_idx + 1) % len(self.user_agents)
        return user_agent
    
    def _apply_rate_limit(self):
        """
        Apply rate limiting with random delay
        
        Raises:
            RateLimitError: If max requests exceeded
        """
        # Check request limit
        if self.request_count >= self.max_requests:
            raise RateLimitError(f"Max requests ({self.max_requests}) exceeded for {self.source_name}")
        
        # Calculate delay since last request
        base_delay = self.scraping_config.get('delay_between_requests_sec', 
                                             self.scraping_config.get('rate_limit_seconds', 3))
        variation = self.scraping_config.get('delay_variation_sec', 2)
        delay = base_delay + random.uniform(-variation, variation)
        
        # Apply minimum delay
        time_since_last = time.time() - self.last_request_time
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def _make_request(self, url: str, **kwargs) -> requests.Response:
        """
        Make HTTP request with all safeguards applied
        
        Args:
            url: URL to request
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            ScraperError: On various failure conditions
        """
        # Check robots.txt
        self._check_robots_txt(url)
        
        # Apply rate limiting
        self._apply_rate_limit()
        
        # Set user agent
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['User-Agent'] = self._get_current_user_agent()
        
        # Add common headers
        kwargs['headers'].update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Retry logic
        max_retries = self.scraping_config.get('max_retries', 3)
        retry_delay = self.scraping_config.get('retry_delay_sec', 5)
        
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"Requesting {url} (attempt {attempt + 1})")
                response = self.session.get(url, **kwargs)
                
                # Check for common error status codes
                if response.status_code == 429:  # Too Many Requests
                    if attempt < max_retries:
                        logger.warning(f"Rate limited by {self.source_name}, retrying in {retry_delay}s")
                        time.sleep(retry_delay)
                        continue
                    else:
                        raise RateLimitError(f"Rate limited by {self.source_name}")
                        
                elif response.status_code == 403:  # Forbidden
                    raise ScraperError(f"Access forbidden to {url} (possible bot detection)")
                    
                elif response.status_code >= 500:  # Server error
                    if attempt < max_retries:
                        logger.warning(f"Server error {response.status_code}, retrying in {retry_delay}s")
                        time.sleep(retry_delay)
                        continue
                    else:
                        raise ScraperError(f"Server error: {response.status_code}")
                
                # Success or client error (4xx) - don't retry client errors
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                if attempt < max_retries:
                    logger.warning(f"Request failed: {e}, retrying in {retry_delay}s")
                    time.sleep(retry_delay)
                    continue
                else:
                    raise ScraperError(f"Request failed after {max_retries + 1} attempts: {e}")
    
    def get_request_stats(self) -> Dict[str, Any]:
        """Get current request statistics"""
        return {
            'source': self.source_name,
            'requests_made': self.request_count,
            'requests_remaining': self.max_requests - self.request_count,
            'rate_limit_hit': self.request_count >= self.max_requests
        }
    
    @abstractmethod
    def search(self, city: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Search for listings in the given city
        
        Args:
            city: City key from config (e.g., 'freiburg')
            **kwargs: Additional search parameters
            
        Returns:
            List of raw listing dictionaries
            
        Must be implemented by subclasses
        """
        pass
    
    @abstractmethod
    def parse_listing(self, listing_data: Any) -> Optional[Dict[str, Any]]:
        """
        Parse a single listing from raw data into standardized format
        
        Args:
            listing_data: Raw listing data (HTML element, JSON, etc.)
            
        Returns:
            Standardized listing dict or None if parsing fails
            
        Must be implemented by subclasses
        """
        pass
    
    def get_standardized_listing(self, raw_listing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert source-specific listing to standardized format
        
        Standard fields:
        - source: Source name
        - url: Listing URL
        - title: Property title
        - price: Price as integer (EUR)
        - address: Full address string
        - size_sqm: Size in square meters
        - rooms: Number of rooms
        - bedrooms: Number of bedrooms (if specified)
        - description: Property description
        - image_url: Primary image URL
        - features: List of features/amenities
        - scraped_at: ISO timestamp
        """
        # Default implementation - subclasses should override if needed
        return {
            'source': self.source_name,
            'scraped_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            **raw_listing
        }