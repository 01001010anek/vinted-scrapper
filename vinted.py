import logging
from typing import List, Dict, Optional
from vinted_scraper import VintedScraper
from dataclasses import dataclass
from vinted_enhanced import VintedEnhanced

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('vinted_scraper')

@dataclass
class User:
    """User/seller information"""
    login: str
    id: str
    rating: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    city: Optional[str] = None
    profile_url: Optional[str] = None
    photo_url: Optional[str] = None
    positive_feedback_count: Optional[int] = None
    negative_feedback_count: Optional[int] = None
    neutral_feedback_count: Optional[int] = None
    total_items_count: Optional[int] = None

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
    photos: Optional[list] = None
    country_code: Optional[str] = None
    country_title: Optional[str] = None
    size_title: Optional[str] = None
    created_at_ts: Optional[int] = None

class VintedAPI:
    """
    Adapter class for the VintedScraper library
    """
    
    def __init__(self, base_url: str = "https://www.vinted.pl"):
        """
        Initialize the Vinted API with the base URL
        
        Args:
            base_url: The base URL for Vinted (default to Polish Vinted)
        """
        self.base_url = base_url
        
        # Inicjalizacja VintedEnhanced do pobierania dodatkowych danych
        self.enhanced = VintedEnhanced()
        logger.info("Zainicjalizowano VintedEnhanced dla dodatkowych danych")
        
        # Dodajemy niestandardowe nagłówki, które symulują zwykłą przeglądarkę
        # Jest to ważne, aby obejść zabezpieczenia przed scrapingiem
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        # Możemy przekazać cookie, jeśli mamy zapisane z poprzedniej sesji
        # (uwaga: cookie wygasają po pewnym czasie)
        try:
            self.scraper = VintedScraper(
                base_url, 
                agent=user_agent
            )
            logger.info(f"Zainicjalizowano scraper Vinted dla {base_url}")
        except Exception as e:
            logger.error(f"Błąd podczas inicjalizacji VintedScraper: {e}")
            logger.info("Próba inicjalizacji z dodatkowym userAgent...")
            
            # Spróbujmy z innym user agentem
            alternate_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15"
            try:
                self.scraper = VintedScraper(
                    base_url, 
                    agent=alternate_agent
                )
                logger.info(f"Pomyślnie zainicjalizowano scraper z alternatywnym user-agentem")
            except Exception as alt_error:
                logger.error(f"Błąd podczas alternatywnej inicjalizacji: {alt_error}")
                # W przypadku braku możliwości inicjalizacji - tworzymy pusty obiekt
                # i będziemy obsługiwać błędy podczas wyszukiwania
                from types import SimpleNamespace
                self.scraper = SimpleNamespace()
                self.scraper.search = lambda **kwargs: []
    
    def search(self, params: Dict[str, str]) -> List[MarketplaceItem]:
        """
        Search for items on Vinted
        
        Args:
            params: Dictionary of search parameters:
                - search_text: The search query
                - price_from: Minimum price
                - price_to: Maximum price
                - per_page: Number of results to return
                
        Returns:
            List of MarketplaceItem objects
        """
        try:
            search_text = params.get("search_text", "")
            price_from = params.get("price_from", "0")
            price_to = params.get("price_to", "")
            limit = int(params.get("per_page", "10"))
            
            logger.info(f"Wyszukiwanie '{search_text}' na Vinted (zakres cen: {price_from}-{price_to} PLN)")
            
            # Dodajemy debug
            logger.info("Inicjalizacja wyszukiwania z biblioteką vinted-scraper")
            
            # Inicjalizuj zmienną przed użyciem
            vinted_items = []
            
            try:
                # Use the specialized library to fetch items - przekazujemy wszystkie parametry jako słownik
                search_params = {
                    "search_text": search_text,
                    "price_from": price_from,
                    "price_to": price_to,
                    "currency": "PLN",
                    "order": "newest_first",
                    "page": "1"
                }
                
                logger.info(f"Parametry wyszukiwania: {search_params}")
                vinted_items = self.scraper.search(params=search_params)
                
                logger.info(f"Znaleziono {len(vinted_items)} przedmiotów na Vinted")
                
                # Dodajmy więcej szczegółów o znalezionych przedmiotach do logów
                for idx, item in enumerate(vinted_items[:3]):  # Pokaż tylko pierwsze 3 dla czytelności
                    logger.info(f"Przedmiot {idx+1}: ID={getattr(item, 'id', 'brak')}, Tytuł={getattr(item, 'title', 'brak')}")
                    
                # Sprawdźmy wszystkie dostępne atrybuty pierwszego przedmiotu
                if vinted_items and len(vinted_items) > 0:
                    sample_item = vinted_items[0]
                    logger.info("Dostępne atrybuty pierwszego przedmiotu:")
                    for attr_name in dir(sample_item):
                        if not attr_name.startswith('_'):  # Pomijamy atrybuty prywatne
                            try:
                                attr_value = getattr(sample_item, attr_name)
                                if not callable(attr_value):  # Pomijamy metody
                                    logger.info(f"  - {attr_name}: {attr_value}")
                            except Exception as e:
                                logger.info(f"  - {attr_name}: <błąd podczas pobierania: {e}>")
                                
                    # Logujemy szczegółowe informacje o kraju przedmiotu
                    logger.info(f"Kraj przedmiotu: code={getattr(sample_item, 'country_code', 'brak')}, title={getattr(sample_item, 'country_title', 'brak')}")
                                
                    # Sprawdźmy szczegóły o użytkowniku, jeśli są dostępne
                    if hasattr(sample_item, 'user') and sample_item.user:
                        logger.info("Atrybuty użytkownika:")
                        for attr_name in dir(sample_item.user):
                            if not attr_name.startswith('_'):
                                try:
                                    attr_value = getattr(sample_item.user, attr_name)
                                    if not callable(attr_value):
                                        logger.info(f"  - user.{attr_name}: {attr_value}")
                                except Exception as e:
                                    logger.info(f"  - user.{attr_name}: <błąd podczas pobierania: {e}>")
                
            except Exception as search_error:
                logger.error(f"Błąd podczas wyszukiwania z biblioteką vinted-scraper: {search_error}")
                # Spróbujmy wypisać szczegóły błędu
                import traceback
                logger.error(traceback.format_exc())
            
            # Convert to our standard format
            result_items = []
            for item in vinted_items[:limit]:
                try:
                    # Extract user information if available
                    user = None
                    if hasattr(item, 'user') and item.user:
                        # Get user photo URL
                        user_photo_url = None
                        if hasattr(item.user, 'photo') and item.user.photo:
                            if hasattr(item.user.photo, 'url') and item.user.photo.url:
                                user_photo_url = item.user.photo.url
                            elif hasattr(item.user.photo, 'full_size_url') and item.user.photo.full_size_url:
                                user_photo_url = item.user.photo.full_size_url
                            
                        # Podstawowe dane z API
                        user_id = getattr(item.user, 'id', '0')
                        user_login = getattr(item.user, 'login', 'Unknown')
                        user_profile_url = getattr(item.user, 'profile_url', None)
                        
                        # Pobierz dodatkowe informacje o sprzedawcy
                        logger.info(f"Pobieranie dodatkowych informacji o użytkowniku {user_login} (ID: {user_id})")
                        enhanced_user_info = self.enhanced.get_user_details(user_id, user_profile_url)
                        
                        # Stwórz obiekt użytkownika z połączonymi danymi
                        user = User(
                            login=user_login,
                            id=user_id,
                            rating=enhanced_user_info.get('rating', None),
                            country=enhanced_user_info.get('country', 'Polska'),
                            country_code=enhanced_user_info.get('country_code', 'PL'),
                            city=enhanced_user_info.get('city', None),
                            profile_url=user_profile_url,
                            photo_url=enhanced_user_info.get('photo_url', user_photo_url),
                            positive_feedback_count=enhanced_user_info.get('positive_feedback_count', 0),
                            negative_feedback_count=enhanced_user_info.get('negative_feedback_count', 0),
                            neutral_feedback_count=enhanced_user_info.get('neutral_feedback_count', 0),
                            total_items_count=enhanced_user_info.get('items_count', 0)
                        )
                    
                    # Extract image URLs
                    image_url = None
                    photos_list = []
                    if hasattr(item, 'photos') and item.photos:
                        # Ten kod obsługuje różne formaty zwracane przez API Vinted
                        if isinstance(item.photos, list):
                            if len(item.photos) > 0:
                                first_photo = item.photos[0]
                                if isinstance(first_photo, str):
                                    # Lista bezpośrednich URLi
                                    image_url = first_photo
                                    photos_list = item.photos
                                elif hasattr(first_photo, 'url'):
                                    # Lista obiektów ze zdjęciami
                                    image_url = first_photo.url
                                    photos_list = [p.url if hasattr(p, 'url') else None for p in item.photos]
                        elif hasattr(item.photos, 'url'):
                            # Pojedynczy obiekt zdjęcia
                            image_url = item.photos.url
                            photos_list = [image_url]
                    
                    # Pobierz szczegółowe informacje o przedmiocie, w tym wszystkie zdjęcia
                    item_id = str(item.id)
                    item_url = item.url
                    logger.info(f"Pobieranie dodatkowych informacji o przedmiocie {item_id}")
                    
                    # Pobierz dodatkowe dane
                    enhanced_item_info = self.enhanced.get_item_details(item_id, item_url)
                    
                    # Zastosuj dodatkowe zdjęcia, jeśli są dostępne
                    if enhanced_item_info.get('all_photos') and len(enhanced_item_info['all_photos']) > 0:
                        logger.info(f"Dodatkowych zdjęć: {len(enhanced_item_info['all_photos'])}")
                        photos_list = enhanced_item_info['all_photos']
                        if not image_url and photos_list:
                            image_url = photos_list[0]
                    
                    # Create the marketplace item
                    marketplace_item = MarketplaceItem(
                        id=item_id,
                        title=item.title,
                        price=item.price,
                        currency="PLN",  # Vinted Poland uses PLN
                        url=item_url,
                        condition=getattr(item, 'status', 'Used'),
                        seller=getattr(item.user, 'login', None) if hasattr(item, 'user') and item.user else None,
                        location=getattr(item, 'city', None),
                        shipping=getattr(item, 'shipping_fee', None),
                        image_url=image_url,
                        brand_title=getattr(item, 'brand_title', None),
                        user=user,
                        photos=photos_list,
                        country_code=enhanced_item_info.get('country_code', getattr(item, 'country_code', 'PL')),
                        country_title=enhanced_item_info.get('country', getattr(item, 'country_title', 'Polska')),
                        size_title=getattr(item, 'size_title', None),
                        created_at_ts=getattr(item, 'created_at_ts', None)
                    )
                    
                    result_items.append(marketplace_item)
                except Exception as e:
                    logger.error(f"Błąd podczas przetwarzania przedmiotu: {e}")
            
            return result_items
            
        except Exception as e:
            logger.error(f"Błąd podczas wyszukiwania na Vinted: {e}")
            return []