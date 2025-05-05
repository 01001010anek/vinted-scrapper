import logging
import re
import time
import random
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('marketplace_scraper')

@dataclass
class User:
    """User/seller information"""
    login: str
    id: str
    rating: Optional[str] = None

@dataclass
class MarketplaceItem:
    """Represents an item from a marketplace"""
    id: str
    title: str
    price: str
    currency: str
    url: str
    condition: str
    seller: Optional[str] = None
    location: Optional[str] = None
    shipping: Optional[str] = None
    image_url: Optional[str] = None
    brand_title: Optional[str] = None
    user: Optional[User] = None

class MarketplaceScraper:
    """
    A general marketplace scraper that can be customized for different sites
    """
    
    def __init__(self, base_url: str):
        """
        Initialize the scraper with the marketplace base URL
        
        Args:
            base_url: The base URL of the marketplace (e.g., "https://www.ebay.com")
        """
        self.base_url = base_url
        self.marketplace = self._identify_marketplace(base_url)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        })
        
        logger.info(f"Initialized scraper for {self.marketplace}")
    
    def _identify_marketplace(self, url: str) -> str:
        """
        Identify which marketplace we're dealing with based on the URL
        
        Args:
            url: The marketplace URL
            
        Returns:
            String identifier for the marketplace
        """
        if "ebay" in url:
            return "ebay"
        elif "amazon" in url:
            return "amazon"
        elif "vinted" in url:
            return "vinted"
        else:
            return "generic"
    
    def _get_search_url(self, params: Dict[str, str]) -> str:
        """
        Build the search URL based on the marketplace and parameters
        
        Args:
            params: Search parameters
            
        Returns:
            Complete search URL
        """
        search_text = params.get("search_text", "").replace(" ", "+")
        price_from = params.get("price_from", "")
        price_to = params.get("price_to", "")
        
        if self.marketplace == "ebay":
            url = f"{self.base_url}/sch/i.html?_nkw={search_text}"
            if price_from and price_to:
                url += f"&_udlo={price_from}&_udhi={price_to}"
            return url
        elif self.marketplace == "amazon":
            url = f"{self.base_url}/s?k={search_text}"
            if price_from and price_to:
                url += f"&price={price_from}-{price_to}"
            return url
        elif self.marketplace == "vinted":
            url = f"{self.base_url}/catalog?search_text={search_text}"
            if price_to:
                url += f"&price_to={price_to}"
            if price_from:
                url += f"&price_from={price_from}"
            return url
        else:
            # Generic search URL, would need to be customized for other sites
            return f"{self.base_url}/search?q={search_text}"
    
    def search(self, params: Dict[str, str]) -> List[MarketplaceItem]:
        """
        Search for items in the marketplace
        
        Args:
            params: Dictionary of search parameters:
                - search_text: The search query
                - price_from: Minimum price
                - price_to: Maximum price
                - per_page: Number of results to return
                
        Returns:
            List of MarketplaceItem objects
        """
        search_url = self._get_search_url(params)
        logger.info(f"Searching at URL: {search_url}")
        
        # Add a random delay to avoid rate limiting
        time.sleep(1 + random.random())
        
        try:
            response = self.session.get(search_url, timeout=15)
            if response.status_code != 200:
                logger.error(f"Failed to get search results: {response.status_code}")
                return []
                
            return self._parse_search_results(response.text, int(params.get("per_page", "10")))
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing search results: {e}")
            return []
    
    def _parse_search_results(self, html_content: str, limit: int = 10) -> List[MarketplaceItem]:
        """
        Parse the HTML content to extract item information
        
        Args:
            html_content: Raw HTML content from the search results page
            limit: Maximum number of items to return
            
        Returns:
            List of MarketplaceItem objects
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        items = []
        
        if self.marketplace == "ebay":
            return self._parse_ebay_results(soup, limit)
        elif self.marketplace == "amazon":
            return self._parse_amazon_results(soup, limit)
        elif self.marketplace == "vinted":
            return self._parse_vinted_results(soup, limit)
        else:
            # Generic parser, would need to be customized
            logger.warning(f"No specific parser for {self.marketplace}, using generic parser")
            return []
    
    def _parse_ebay_results(self, soup: BeautifulSoup, limit: int) -> List[MarketplaceItem]:
        """
        Parse eBay search results
        
        Args:
            soup: BeautifulSoup object of the search results page
            limit: Maximum number of items to return
            
        Returns:
            List of MarketplaceItem objects
        """
        items = []
        results = soup.select('.s-item')
        
        for result in results[:limit]:
            try:
                # Skip the "Shop on eBay" item that sometimes appears first
                if "Shop on eBay" in result.text:
                    continue
                
                # Extract item ID from the URL or data attribute
                item_link = result.select_one('.s-item__link')
                if not item_link:
                    continue
                
                item_url = item_link.get('href', '')
                item_id = self._extract_item_id_from_url(item_url)
                
                # Get title
                title_elem = result.select_one('.s-item__title')
                title = title_elem.text.strip() if title_elem else "Unknown Title"
                
                # Get price
                price_elem = result.select_one('.s-item__price')
                price_text = price_elem.text.strip() if price_elem else "$0.00"
                
                # Extract numeric price and currency
                price_match = re.search(r'([^\d]*)(\d+\.\d+|\d+)', price_text)
                if price_match:
                    currency = price_match.group(1).strip() or "$"
                    price = price_match.group(2)
                else:
                    currency = "$"
                    price = "0.00"
                
                # Get condition
                condition_elem = result.select_one('.SECONDARY_INFO')
                condition = condition_elem.text.strip() if condition_elem else "Not specified"
                
                # Get seller info
                seller_elem = result.select_one('.s-item__seller-info-text')
                seller = seller_elem.text.strip() if seller_elem else None
                
                # Get shipping info
                shipping_elem = result.select_one('.s-item__shipping')
                shipping = shipping_elem.text.strip() if shipping_elem else None
                
                # Get location
                location_elem = result.select_one('.s-item__location')
                location = location_elem.text.strip() if location_elem else None
                
                # Get image URL
                img_elem = result.select_one('.s-item__image-img')
                image_url = img_elem.get('src') if img_elem else None
                
                # Create the item object
                item = MarketplaceItem(
                    id=item_id,
                    title=title,
                    price=price,
                    currency=currency,
                    url=item_url,
                    condition=condition,
                    seller=seller,
                    location=location,
                    shipping=shipping,
                    image_url=image_url
                )
                
                items.append(item)
            except Exception as e:
                logger.error(f"Error parsing eBay item: {e}")
        
        return items
    
    def _parse_amazon_results(self, soup: BeautifulSoup, limit: int) -> List[MarketplaceItem]:
        """
        Parse Amazon search results
        
        Args:
            soup: BeautifulSoup object of the search results page
            limit: Maximum number of items to return
            
        Returns:
            List of MarketplaceItem objects
        """
        items = []
        results = soup.select('[data-component-type="s-search-result"]')
        
        for result in results[:limit]:
            try:
                # Extract item ID
                item_id = result.get('data-asin', '')
                if not item_id:
                    continue
                
                # Get title
                title_elem = result.select_one('h2 a span')
                title = title_elem.text.strip() if title_elem else "Unknown Title"
                
                # Get URL
                link_elem = result.select_one('h2 a')
                relative_url = link_elem.get('href', '') if link_elem else ""
                item_url = self.base_url + relative_url if relative_url.startswith('/') else relative_url
                
                # Get price
                price_elem = result.select_one('.a-price .a-offscreen')
                price_text = price_elem.text.strip() if price_elem else "$0.00"
                
                # Extract numeric price and currency
                price_match = re.search(r'([^\d]*)(\d+\.\d+|\d+)', price_text)
                if price_match:
                    currency = price_match.group(1).strip() or "$"
                    price = price_match.group(2)
                else:
                    currency = "$"
                    price = "0.00"
                
                # Get condition (for Amazon, usually New unless specified)
                condition = "New"
                
                # Get seller info
                seller_elem = result.select_one('.a-row.a-size-base.a-color-secondary')
                seller = seller_elem.text.strip() if seller_elem else None
                
                # Get shipping info
                shipping_elem = result.select_one('.a-row.a-size-base a-color-secondary .a-text-bold')
                shipping = shipping_elem.text.strip() if shipping_elem else "Standard"
                
                # Get image URL
                img_elem = result.select_one('img.s-image')
                image_url = img_elem.get('src') if img_elem else None
                
                # Create the item object
                item = MarketplaceItem(
                    id=item_id,
                    title=title,
                    price=price,
                    currency=currency,
                    url=item_url,
                    condition=condition,
                    seller=seller,
                    shipping=shipping,
                    image_url=image_url
                )
                
                items.append(item)
            except Exception as e:
                logger.error(f"Error parsing Amazon item: {e}")
        
        return items
    
    def _parse_vinted_results(self, soup: BeautifulSoup, limit: int) -> List[MarketplaceItem]:
        """
        Parse Vinted search results
        
        Args:
            soup: BeautifulSoup object of the search results page
            limit: Maximum number of items to return
            
        Returns:
            List of MarketplaceItem objects
        """
        items = []
        # Select item cards from Vinted
        results = soup.select('.feed-grid__item .feed-grid__item-content')
        
        for result in results[:limit]:
            try:
                # Extract item ID and URL
                item_link = result.select_one('.feed-grid__item__link')
                if not item_link:
                    continue
                
                item_url = ""
                if item_link.has_attr('href'):
                    href = item_link['href']
                    if isinstance(href, str):
                        item_url = href if href.startswith('http') else f"{self.base_url}{href}"
                    
                # Extract item ID from URL
                item_id = ""
                if item_url:
                    # Typical Vinted URL format: /items/12345-user-item-title
                    id_match = re.search(r'/items/(\d+)', item_url)
                    if id_match:
                        item_id = id_match.group(1)
                    else:
                        item_id = str(hash(item_url))
                else:
                    # Fallback ID
                    item_id = str(hash(str(result)))
                
                # Get title
                title_elem = result.select_one('.feed-grid__item__title')
                title = title_elem.text.strip() if title_elem else "Unknown Item"
                
                # Get price
                price_elem = result.select_one('.feed-grid__item__price')
                price_text = price_elem.text.strip() if price_elem else "0.00"
                
                # Extract numeric price and currency
                price_match = re.search(r'([^\d]*)(\d+[.,]?\d*)', price_text)
                if price_match:
                    currency = price_match.group(1).strip() or "PLN"
                    price = price_match.group(2).replace(',', '.')
                else:
                    currency = "PLN"
                    price = "0.00"
                
                # Get brand info
                brand_elem = result.select_one('.feed-grid__item__brand')
                brand_title = brand_elem.text.strip() if brand_elem else None
                
                # Get image URL
                img_elem = result.select_one('img.feed-grid__item__photo')
                image_url = None
                if img_elem and img_elem.has_attr('src'):
                    src = img_elem['src']
                    if isinstance(src, str):
                        image_url = src
                
                # Get user info if available
                user = None
                user_elem = result.select_one('.feed-grid__item__user')
                if user_elem:
                    user_name = user_elem.text.strip()
                    user_id = str(hash(user_name))  # Simple hash as ID
                    user = User(login=user_name, id=user_id)
                
                # Create the item object
                item = MarketplaceItem(
                    id=item_id,
                    title=title,
                    price=price,
                    currency=currency,
                    url=item_url,
                    condition="Used",  # Most Vinted items are used
                    brand_title=brand_title,
                    image_url=image_url,
                    user=user
                )
                
                items.append(item)
            except Exception as e:
                logger.error(f"Error parsing Vinted item: {e}")
        
        return items
    
    def _extract_item_id_from_url(self, url: str) -> str:
        """
        Extract the item ID from a marketplace URL
        
        Args:
            url: The item URL
            
        Returns:
            Item ID string
        """
        if not url or not isinstance(url, str):
            return str(hash(str(url)))
            
        if self.marketplace == "ebay":
            # Extract item ID from eBay URL
            match = re.search(r'/itm/(?:[\w-]+/)?(\d+)', url)
            if match:
                return match.group(1)
            else:
                # Generate a unique ID based on the URL to avoid duplicates
                return str(hash(url))
        elif self.marketplace == "amazon":
            # Extract item ID from Amazon URL
            match = re.search(r'/dp/([A-Z0-9]+)', url)
            if match:
                return match.group(1)
            else:
                return str(hash(url))
        elif self.marketplace == "vinted":
            # Extract item ID from Vinted URL
            match = re.search(r'/items/(\d+)', url)
            if match:
                return match.group(1)
            else:
                return str(hash(url))
        else:
            # For other marketplaces, create a hash of the URL
            return str(hash(url))
