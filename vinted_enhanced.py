import requests
import logging
import json
import re
import time
from bs4 import BeautifulSoup
from typing import Dict, Optional, Tuple, Any

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('vinted_enhanced')

def get_country_codes() -> Dict[str, str]:
    """
    Zwraca słownik mapowania nazw krajów na kody krajów używane na Vinted
    """
    return {
        'Polska': 'PL',
        'Niemcy': 'DE',
        'Francja': 'FR',
        'Wielka Brytania': 'GB',
        'Hiszpania': 'ES',
        'Włochy': 'IT',
        'Czechy': 'CZ',
        'Słowacja': 'SK',
        'Węgry': 'HU',
        'Austria': 'AT',
        'Holandia': 'NL',
        'Belgia': 'BE',
        'Dania': 'DK',
        'Szwecja': 'SE',
        'Norwegia': 'NO',
        'Finlandia': 'FI',
        'Grecja': 'GR',
        'Rumunia': 'RO',
        'Litwa': 'LT',
        'Łotwa': 'LV',
        'Estonia': 'EE',
        'Bułgaria': 'BG',
        'Portugalia': 'PT',
        'Irlandia': 'IE',
        'Chorwacja': 'HR',
        'Słowenia': 'SI',
        'Szwajcaria': 'CH'
    }

class VintedEnhanced:
    """
    Rozszerzenie do pobierania dodatkowych informacji z Vinted, 
    których nie dostarcza standardowa biblioteka vinted-scraper.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.vinted.pl/',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        })
        
        # Cache dla informacji o użytkowniku, aby uniknąć powtarzających się zapytań
        self.user_cache = {}
    
    def _get_with_retry(self, url: str, max_retries: int = 3) -> Optional[str]:
        """
        Pobiera zawartość URL z obsługą ponownych prób i opóźnień.
        
        Args:
            url: URL do pobrania
            max_retries: Maksymalna liczba prób
            
        Returns:
            Zawartość strony jako tekst lub None w przypadku błędu
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 429:  # Too Many Requests
                    wait_time = 2 ** attempt  # Wykładniczo rosnący czas oczekiwania
                    logger.warning(f"Otrzymano kod 429 (Too Many Requests). Oczekiwanie {wait_time} sekund.")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Błąd HTTP {response.status_code} dla {url}")
                    return None
            except requests.RequestException as e:
                logger.error(f"Błąd pobierania {url}: {e}")
                time.sleep(1)
        
        return None
    
    def get_user_details(self, user_id: str, profile_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Pobiera szczegółowe informacje o użytkowniku.
        
        Args:
            user_id: ID użytkownika Vinted
            profile_url: Opcjonalny URL profilu użytkownika
            
        Returns:
            Słownik z informacjami o użytkowniku
        """
        # Sprawdź czy mamy już dane tego użytkownika w cache
        if user_id in self.user_cache:
            logger.info(f"Używam danych z cache dla użytkownika {user_id}")
            return self.user_cache[user_id]
        
        # Domyślne/puste dane użytkownika
        user_data = {
            "login": "Nieznany",
            "country": "Polska",
            "country_code": "PL", 
            "city": None,
            "positive_feedback_count": 0,
            "negative_feedback_count": 0,
            "neutral_feedback_count": 0,
            "rating": None,
            "items_count": 0,
            "photo_url": None
        }
        
        # Jeśli nie podano URL profilu, zbuduj go na podstawie ID
        if not profile_url:
            profile_url = f"https://www.vinted.pl/member/{user_id}"
        
        logger.info(f"Pobieranie szczegółów użytkownika z {profile_url}")
        
        # Pobierz stronę profilu
        html_content = self._get_with_retry(profile_url)
        if not html_content:
            logger.error(f"Nie udało się pobrać profilu użytkownika: {profile_url}")
            return user_data
        
        try:
            # Parsuj HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Pobierz dane z meta tagów
            meta_data = {}
            for meta in soup.find_all('meta'):
                property_name = meta.get('property', '')
                if property_name.startswith('og:'):
                    key = property_name.replace('og:', '')
                    meta_data[key] = meta.get('content', '')
            
            # Pobierz dane z JSON-LD
            json_ld = None
            for script in soup.find_all('script', {'type': 'application/ld+json'}):
                try:
                    data = json.loads(script.string)
                    if '@type' in data and data['@type'] == 'Person':
                        json_ld = data
                        break
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # Wyszukaj nazwę użytkownika - bardziej ogólny selektor
            username_elem = soup.select_one('h2[class*="text"]') or soup.select_one('h1') or soup.select_one('h2')
            if username_elem:
                user_data['login'] = username_elem.text.strip()
                logger.info(f"Znaleziono nazwę użytkownika: {user_data['login']}")
            
            # Lokalizacja - kilka metod pobierania
            # Metoda 1: Standardowy selektor
            location_elem = soup.select_one('div.details-list__item:contains("Lokalizacja")') or soup.select_one('div:contains("Lokalizacja")')
            
            # Metoda 2: Szukanie konkretnych klas lokalizacji
            if not location_elem:
                location_elem = soup.select_one('.user-location') or soup.select_one('[data-testid="user-location"]')
                
            # Metoda 3: Sprawdź sekcję "O mnie", która często zawiera informacje o kraju
            if not location_elem:
                about_me_elem = soup.select_one('div:contains("O mnie:")') or soup.select_one('p:contains("O mnie:")')
                if about_me_elem:
                    location_elem = about_me_elem
                    logger.info("Znaleziono element 'O mnie', próba wyodrębnienia lokalizacji")
            
            # Metoda 4: Szukanie informacji o lokalizacji po wzorcu "Miasto, Kraj"
            if not location_elem:
                for elem in soup.select('div, span, p'):
                    if re.search(r'[A-Z][a-ząćęłńóśźż]+,\s+[A-Z][a-ząćęłńóśźż]+', elem.text):
                        location_elem = elem
                        break
                        
            # Metoda 5: Szukanie samej nazwy kraju w elemencie "O mnie"
            if not location_elem:
                for elem in soup.select('div, span, p'):
                    for country_name in get_country_codes().keys():
                        if country_name in elem.text:
                            user_data['country'] = country_name
                            user_data['country_code'] = get_country_codes()[country_name]
                            logger.info(f"Znaleziono kraj na podstawie nazwy: {country_name} ({user_data['country_code']})")
                            return user_data
                        
            if location_elem:
                logger.info(f"Znaleziono element z lokalizacją: {location_elem.text.strip()}")
                # Spróbuj znaleźć konkretną wartość
                location_text = location_elem.select_one('.details-list__item-value')
                
                # Jeśli nie znaleziono konkretnej wartości, użyj całego tekstu
                if not location_text:
                    # Szukaj wzorca "Miasto, Kraj" w tekście
                    location_match = re.search(r'([A-Z][a-ząćęłńóśźż]+),\s+([A-Z][a-ząćęłńóśźż]+)', location_elem.text)
                    if location_match:
                        location_parts = [location_match.group(1), location_match.group(2)]
                        logger.info(f"Znaleziono lokalizację (wzorzec): {location_parts}")
                    else:
                        # Ostateczna próba - szukaj przecinka w tekście
                        if ',' in location_elem.text:
                            location_parts = location_elem.text.strip().split(',')
                            location_parts = [part.strip() for part in location_parts]
                            logger.info(f"Znaleziono lokalizację (split): {location_parts}")
                        else:
                            # Jeśli nie znaleziono przecinka, ustaw domyślną wartość
                            user_data['country'] = "Polska"
                            user_data['country_code'] = "PL"
                            return user_data
                else:
                    # Jeśli znaleziono konkretną wartość, podziel ją po przecinku
                    location_parts = location_text.text.strip().split(',')
                    location_parts = [part.strip() for part in location_parts]
                    logger.info(f"Znaleziono lokalizację (standardowa): {location_parts}")
                
                # Jeśli znaleziono przynajmniej miasto i kraj
                if len(location_parts) > 1:
                    user_data['city'] = location_parts[0]
                    user_data['country'] = location_parts[-1]
                    
                    # Przypisz kod kraju na podstawie nazwy
                    country_codes = get_country_codes()
                    user_data['country_code'] = country_codes.get(location_parts[-1], 'PL')
                    
                    # Dodajmy jawnie kraj
                    if location_parts[-1] not in country_codes and location_parts[-1] != 'Polska':
                        logger.info(f"Nieznany kraj: {location_parts[-1]}, dodaję do listy")
                        user_data['country_code'] = location_parts[-1][:2].upper()
                    logger.info(f"Przypisano kod kraju: {user_data['country_code']}")
                # Jeśli znaleziono tylko jeden element, to domyślnie jest to kraj
                elif len(location_parts) == 1:
                    user_data['country'] = location_parts[0]
                    country_codes = get_country_codes()
                    user_data['country_code'] = country_codes.get(location_parts[0], 'PL')
                    
                    # Dodajmy jawnie kraj
                    if location_parts[0] not in country_codes and location_parts[0] != 'Polska':
                        logger.info(f"Nieznany kraj (tylko kraj): {location_parts[0]}, dodaję do listy")
                        user_data['country_code'] = location_parts[0][:2].upper()
                    logger.info(f"Przypisano kod kraju (tylko kraj): {user_data['country_code']}")
            else:
                # Jeśli nie znaleziono informacji o lokalizacji, ustaw domyślne wartości
                user_data['country'] = "Polska"
                user_data['country_code'] = "PL"
                logger.info("Nie znaleziono informacji o lokalizacji, użyto domyślnych")
            
            # Oceny i opinie - nowa strategie wyszukiwania
            # Metoda 1: Bezpośrednie wyszukiwanie pola oceny
            ratings_elem = soup.select_one('div.details-list__item:contains("ocena")') or soup.select_one('div:contains("ocena")')
            
            # Metoda 2: Szukanie konkretnych klas ocen
            if not ratings_elem:
                ratings_elem = soup.select_one('.user-rating') or soup.select_one('[data-testid="user-rating"]')
                
            # Metoda 3: Szukanie sekcji opinii (może zawierać "5.0", itp)
            if not ratings_elem:
                for elem in soup.select('div, span, p'):
                    if ('opini' in elem.text.lower() or 'ocen' in elem.text.lower()) and re.search(r'[\d,.]+', elem.text):
                        ratings_elem = elem
                        break
            
            # Metoda 4: Szukanie bloku z opinią
            if not ratings_elem:
                opinion_elem = soup.select_one('div:contains("opinii")') or soup.select_one('span:contains("opinii")')
                if opinion_elem:
                    ratings_elem = opinion_elem
                
            # Metoda 5: Szukanie elementu z określoną liczbą opinii
            if not ratings_elem:
                opinion_count_elem = soup.select_one('span, div') 
                if opinion_count_elem and re.search(r'(\d+)\s*opinii', opinion_count_elem.text):
                    ratings_elem = opinion_count_elem
                    
            # Parsowanie znalezionego elementu oceny
            found_rating = False
            
            # Najpierw spróbujmy znaleźć ocenę bezpośrednio w HTML
            # Jeśli znaleźliśmy jakikolwiek element z oceną
            if ratings_elem:
                logger.info(f"Znaleziono potencjalny element z ocenami: {ratings_elem.text.strip()}")
                
                # Metoda 1: Szukamy tekstu w formacie "x,xx (xxx opinii)" lub podobnym
                rating_match = re.search(r'([\d,\.]+)\s*\((\d+)', ratings_elem.text.strip())
                
                if rating_match:
                    user_data['rating'] = rating_match.group(1).replace(',', '.')
                    total_opinions = int(rating_match.group(2))
                    
                    # Dodaj dodatkowe informacje do logów
                    logger.info(f"Znaleziono ocenę w formacie standardowym: {user_data['rating']} ({total_opinions} opinii)")
                    found_rating = True
                    
                    # Szacowanie pozytywnych/negatywnych/neutralnych ocen na podstawie ogólnej oceny
                    try:
                        rating = float(user_data['rating'])
                        if rating > 0:
                            # Prosta heurystyka dla podziału ocen
                            positive_ratio = min(1.0, rating / 5.0)
                            negative_ratio = max(0, (1.0 - positive_ratio) * 0.7)
                            neutral_ratio = max(0, (1.0 - positive_ratio) * 0.3)
                            
                            user_data['positive_feedback_count'] = int(total_opinions * positive_ratio)
                            user_data['negative_feedback_count'] = int(total_opinions * negative_ratio)
                            user_data['neutral_feedback_count'] = total_opinions - user_data['positive_feedback_count'] - user_data['negative_feedback_count']
                    except (ValueError, TypeError):
                        logger.info(f"Nie udało się przetworzyć oceny jako liczby: {user_data['rating']}")
                
                # Metoda 2: Szukanie liczby opinii z osobną oceną
                if not found_rating:
                    # Próbujemy znaleźć liczbę opinii
                    opinions_match = re.search(r'(\d+)\s*opini', ratings_elem.text)
                    if opinions_match:
                        total_opinions = int(opinions_match.group(1))
                        logger.info(f"Znaleziono {total_opinions} opinii")
                        
                        # Teraz szukamy oceny (typu 4.5, 5.0 itp.)
                        rating_number = re.search(r'(\d+[,.]\d+)|\b(\d)[,.]\b', ratings_elem.text)
                        if rating_number:
                            rating_str = rating_number.group(1) or rating_number.group(2)
                            user_data['rating'] = rating_str.replace(',', '.')
                            logger.info(f"Znaleziono ocenę: {user_data['rating']}")
                            found_rating = True
                            
                            # Obliczmy pozytywne/negatywne na podstawie oceny
                            try:
                                rating = float(user_data['rating'])
                                positive_ratio = min(1.0, rating / 5.0)
                                user_data['positive_feedback_count'] = int(total_opinions * positive_ratio)
                                user_data['negative_feedback_count'] = int(total_opinions * (1-positive_ratio))
                            except (ValueError, TypeError):
                                user_data['positive_feedback_count'] = total_opinions
                                user_data['negative_feedback_count'] = 0
                
                # Metoda 3: Jeśli nadal nie mamy oceny, spróbujmy znaleźć jakiekolwiek liczby
                if not found_rating:
                    # Znajdź wszystkie liczby z przecinkami lub kropkami
                    numbers = re.findall(r'(\d+[.,]\d+)|\b(\d)[.,]\b', ratings_elem.text)
                    if numbers:
                        for number in numbers:
                            number_str = number[0] or number[1]
                            if number_str:
                                user_data['rating'] = number_str.replace(',', '.')
                                logger.info(f"Znaleziono potencjalną ocenę: {user_data['rating']}")
                                found_rating = True
                                break
            
            # Jeśli wciąż nie mamy oceny, sprawdźmy bezpośrednio na stronie
            if not found_rating:
                # Szukamy elementu, który wygląda na ocenę
                for elem in soup.select('span, div, p'):
                    if re.search(r'(\d+[,.]\d+)[^\d]*$', elem.text.strip()):
                        user_data['rating'] = re.search(r'(\d+[,.]\d+)', elem.text.strip()).group(1).replace(',', '.')
                        logger.info(f"Znaleziono samodzielną ocenę: {user_data['rating']}")
                        found_rating = True
                        break
            
            # Jeśli mamy ocenę, ale nie mamy informacji o opiniach, dodajmy domyślne wartości
            if found_rating and not user_data.get('positive_feedback_count'):
                user_data['positive_feedback_count'] = 1
                user_data['negative_feedback_count'] = 0
                user_data['neutral_feedback_count'] = 0
            
            # Liczba przedmiotów
            items_elem = soup.select_one('span.Text_text__wF6fh:contains("przedmiot")')
            if items_elem:
                items_text = items_elem.text.strip()
                items_match = re.search(r'(\d+)', items_text)
                if items_match:
                    user_data['items_count'] = int(items_match.group(1))
            
            # Zdjęcie profilowe
            profile_img = soup.select_one('img.Avatar_image__6Wax4')
            if profile_img:
                user_data['photo_url'] = profile_img.get('src')
            
            # Zapisz dane w cache
            self.user_cache[user_id] = user_data
            
            logger.info(f"Pobrano dane użytkownika {user_data['login']}: {user_data['country']}, ocena: {user_data['rating']}")
            return user_data
            
        except Exception as e:
            logger.error(f"Błąd podczas parsowania danych użytkownika: {e}")
            return user_data

    def get_item_details(self, item_id: str, item_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Pobiera szczegółowe informacje o przedmiocie.
        
        Args:
            item_id: ID przedmiotu
            item_url: Opcjonalny URL przedmiotu
            
        Returns:
            Słownik z dodatkowymi informacjami o przedmiocie
        """
        # Domyślne/puste dane przedmiotu
        item_data = {
            "country": "Polska",
            "country_code": "PL",
            "all_photos": []
        }
        
        # Jeśli nie podano URL przedmiotu, zbuduj go na podstawie ID
        if not item_url:
            item_url = f"https://www.vinted.pl/item/{item_id}"
        
        logger.info(f"Pobieranie szczegółów przedmiotu z {item_url}")
        
        # Pobierz stronę przedmiotu
        html_content = self._get_with_retry(item_url)
        if not html_content:
            logger.error(f"Nie udało się pobrać strony przedmiotu: {item_url}")
            return item_data
        
        try:
            # Parsuj HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Pobierz dane z JSON-LD
            for script in soup.find_all('script', {'type': 'application/ld+json'}):
                try:
                    data = json.loads(script.string)
                    if '@type' in data and data['@type'] == 'Product':
                        if 'image' in data:
                            # Może być pojedynczy URL lub lista URLi
                            if isinstance(data['image'], list):
                                item_data['all_photos'] = data['image']
                            else:
                                item_data['all_photos'] = [data['image']]
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # Jeśli nie znaleziono zdjęć w JSON-LD, poszukaj w HTML
            if not item_data['all_photos']:
                for img in soup.select('.item-photos img'):
                    src = img.get('src') or img.get('data-src')
                    if src and src.startswith('http'):
                        item_data['all_photos'].append(src)
            
            # Lokalizacja i kraj - kilka metod pobierania
            # Metoda 1: Standardowy selektor
            location_elem = soup.select_one('.details-list__item-details:contains("Lokalizacja")') or soup.select_one('div:contains("Lokalizacja")')
            
            # Metoda 2: Szukanie konkretnych klas lokalizacji
            if not location_elem:
                location_elem = soup.select_one('.item-location') or soup.select_one('[data-testid="item-location"]')
                
            # Metoda 3: Szukanie elementu z danymi sprzedawcy
            if not location_elem:
                seller_elem = soup.select_one('.details-list__item-details:contains("Sprzedawca")') or soup.select_one('div:contains("Sprzedawca")')
                if seller_elem:
                    # Spróbuj znaleźć link do profilu sprzedawcy
                    seller_link = seller_elem.select_one('a')
                    if seller_link and seller_link.get('href'):
                        seller_url = seller_link.get('href')
                        if seller_url.startswith('/'):
                            seller_url = 'https://www.vinted.pl' + seller_url
                        
                        seller_id = seller_url.split('/')[-1].split('-')[0]
                        if seller_id.isdigit():
                            # Pobierz dane sprzedawcy
                            logger.info(f"Pobieranie danych sprzedawcy z profilu: {seller_url}")
                            seller_data = self.get_user_details(seller_id, seller_url)
                            if seller_data.get('country'):
                                item_data['country'] = seller_data['country']
                                item_data['country_code'] = seller_data.get('country_code', 'PL')
                                logger.info(f"Ustawiono kraj na podstawie profilu sprzedawcy: {item_data['country']}")
                                return item_data
            
            # Jeśli znaleziono element z lokalizacją
            if location_elem:
                logger.info(f"Znaleziono element z lokalizacją przedmiotu: {location_elem.text.strip()}")
                location_text = location_elem.text.strip()
                # Szukaj wzorca "Miasto, Kraj" w tekście
                location_match = re.search(r'([A-Z][a-ząćęłńóśźż]+),\s+([A-Z][a-ząćęłńóśźż]+)', location_text)
                if location_match:
                    location_parts = [location_match.group(1), location_match.group(2)]
                    logger.info(f"Znaleziono lokalizację przedmiotu (wzorzec): {location_parts}")
                elif ',' in location_text:
                    location_parts = location_text.split(',')
                    location_parts = [part.strip() for part in location_parts]
                    logger.info(f"Znaleziono lokalizację przedmiotu (split): {location_parts}")
                else:
                    # Jeśli nie znaleziono przecinka, ustaw domyślną wartość
                    logger.info(f"Brak przecinka w lokalizacji, używam domyślnych wartości")
                    item_data['country'] = "Polska"
                    item_data['country_code'] = "PL"
                    return item_data
                    
                # Jeśli znaleziono informacje o lokalizacji
                if len(location_parts) > 1:
                    country = location_parts[-1].strip()
                    item_data['country'] = country
                    
                    # Przypisz kod kraju na podstawie nazwy
                    country_codes = get_country_codes()
                    item_data['country_code'] = country_codes.get(country, 'PL')
                    logger.info(f"Ustawiono kraj przedmiotu: {item_data['country']} ({item_data['country_code']})")
                elif len(location_parts) == 1:
                    # Jeśli znaleziono tylko jeden element (sam kraj)
                    country = location_parts[0].strip()
                    item_data['country'] = country
                    country_codes = get_country_codes()
                    item_data['country_code'] = country_codes.get(country, 'PL')
                    
                    # Obsługa niezdefiniowanych krajów
                    if country not in country_codes and country != 'Polska':
                        logger.info(f"Nieznany kraj przedmiotu: {country}, dodaję do listy")
                        item_data['country_code'] = country[:2].upper() if len(country) >= 2 else 'XX'
                    logger.info(f"Ustawiono kraj przedmiotu (tylko kraj): {item_data['country']} ({item_data['country_code']})")
            else:
                # Jeśli nie znaleziono informacji o lokalizacji, ustaw domyślne wartości
                logger.info("Nie znaleziono informacji o lokalizacji przedmiotu, użyto domyślnych wartości")
            
            return item_data
            
        except Exception as e:
            logger.error(f"Błąd podczas parsowania danych przedmiotu: {e}")
            return item_data


# Przykład użycia
if __name__ == "__main__":
    vinted = VintedEnhanced()
    # Przykładowe ID użytkownika i przedmiotu
    user_details = vinted.get_user_details("12345678")
    item_details = vinted.get_item_details("987654321")
    print(f"Użytkownik: {user_details}")
    print(f"Przedmiot: {item_details}")