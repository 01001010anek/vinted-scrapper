# Bot Discord do scrapowania vinteda

Bot Discord, który automatycznie monitoruje przedmioty na platformie Vinted według określonych kryteriów i wysyła powiadomienia na kanał Discord.

## Funkcje

- 🔍 Wyszukiwanie przedmiotów na Vinted według słów kluczowych
- 💰 Filtrowanie wyników według zakresu cenowego
- 🔄 Automatyczne sprawdzanie nowych przedmiotów w regularnych odstępach czasu
- 🖼️ Wyświetlanie wielu zdjęć przedmiotu
- 👤 Informacje o sprzedającym (nazwa, zdjęcie profilowe)
- 🌐 Dane o kraju pochodzenia przedmiotu (czasami działa a czasami nie)
- 📊 Prosta konfihuracja

## Instrukcja Instalacji Lokalnej

### Wymagania

- Python 3.8+ (zalecane 3.11)
- Token Bota Discord
- Serwer Discord z wyznaczonym kanałem do powiadomień

### Instalacja

1. Sklonuj to repozytorium:
   ```
   git clone [https://github.com/01001010anek/vinted-scrapper](https://github.com/01001010anek/vinted-scrapper)
   cd vinted-scrapper
   ```

2. Zainstaluj wymagane pakiety:
   ```
   pip install -r requirements.txt
   ```

   Lub zainstaluj pakiety bezpośrednio:
   ```
   pip install discord.py requests beautifulsoup4 python-dotenv vinted-scraper
   ```

3. Utwórz plik `.env` z Twoim tokenem Discord i ID kanału:
   ```
   DISCORD_TOKEN=twoj_token_bota_discord
   CHANNEL_ID=twoje_id_kanalu_discord
   ```

4. Uruchom bota:
   ```
   python main.py
   ```

### Tworzenie Bota Discord

1. Przejdź do [Discord Developer Portal](https://discord.com/developers/applications)
2. Utwórz nową aplikację
3. Przejdź do sekcji "Bot" i utwórz bota
4. Skopiuj token i wklej go do pliku `.env`
5. W sekcji "OAuth2 > URL Generator", wybierz:
   - Zakres (Scopes): `bot`
   - Uprawnienia bota: `Send Messages`, `Embed Links`, `Read Message History`, `Use Embedded Activities`
6. Użyj wygenerowanego URL, aby zaprosić bota na swój serwer
7. Znajdź ID kanału, na którym ma działać bot (Włącz tryb dewelopera w Discordzie, kliknij prawym przyciskiem myszy na kanał i wybierz "Kopiuj ID")

## Komendy

- `!help` - Pokaż listę dostępnych komend
- `!set_keyword <słowo_kluczowe>` - Ustaw słowo kluczowe do wyszukiwania
- `!set_price <min> <max>` - Ustaw zakres cenowy w PLN
- `!set_interval <sekundy>` - Ustaw interwał sprawdzania (10-3600 sekund)
- `!status` - Pokaż aktualną konfigurację wyszukiwania
- `!clear` - Wyczyść historię wysłanych przedmiotów

## Rozwiązywanie problemów

- **Problem z połączeniem do Vinted**: Bot używa zaawansowanych technik, aby obejść zabezpieczenia anti-scraping, ale jeśli Vinted zmieni swoją strukturę, może być konieczna aktualizacja kodu
- **Wolne wyszukiwanie**: Dodaliśmy opóźnienia między zapytaniami, aby uniknąć blokady przez Vinted
- **Brak niektórych informacji**

## Jak działa bot?

Bot wykorzystuje dwa podejścia do pozyskiwania danych:
1. Biblioteka `vinted-scraper` do pobierania podstawowych informacji o przedmiotach
2. Bezpośrednie pobieranie dodatkowych danych ze stron Vinted dla pozyskania informacji o:
   - Ocenach sprzedającego
   - Kraju pochodzenia przedmiotu
   - Dodatkowych zdjęciach przedmiotu

## Ograniczenia

- Web scraping może przestać działać, jeśli struktura strony Vinted się zmieni
- Vinted ma zabezpieczenia anti-scraping, które mogą blokować bota
- Bot respektuje limity zapytań, dodając opóźnienia między nimi
