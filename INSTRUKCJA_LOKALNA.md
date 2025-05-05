# Instrukcja uruchomienia bota Vinted lokalnie

## Wymagania wstępne

1. **Python 3.8 lub nowszy**
   - Sprawdź swoją wersję Pythona: `python --version`
   - Jeśli nie masz Pythona, pobierz go z [oficjalnej strony](https://www.python.org/downloads/)

2. **Git** (opcjonalnie, do sklonowania repozytorium)
   - Pobierz z [git-scm.com](https://git-scm.com/downloads)

3. **Edytor tekstu** (np. VS Code, Notepad++, itd.)

## Krok 1: Pobranie kodu

### Opcja A: Przez Git
```bash
git clone <adres_repozytorium>
cd <nazwa_folderu>
```

### Opcja B: Pobranie bezpośrednio
1. Pobierz kod jako plik ZIP
2. Rozpakuj w wybranym folderze
3. Otwórz terminal/wiersz poleceń w tym folderze

## Krok 2: Ustawienie wirtualnego środowiska (opcjonalne, ale zalecane)

### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

### macOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

## Krok 3: Instalacja zależności

```bash
pip install discord.py requests beautifulsoup4 python-dotenv vinted-scraper
```

## Krok 4: Konfiguracja bota Discord

1. Przejdź do [Discord Developer Portal](https://discord.com/developers/applications)
2. Kliknij "New Application" i nadaj nazwę
3. W menu po lewej wybierz "Bot"
4. Kliknij "Add Bot" i potwierdź
5. Pod sekcją "TOKEN" kliknij "Copy" (lub "Reset Token" jeśli potrzebujesz nowy)
6. W menu po lewej wybierz "OAuth2" > "URL Generator"
7. Zaznacz następujące uprawnienia:
   - Scopes: `bot`
   - Bot Permissions:
     - Send Messages
     - Embed Links
     - Read Message History
     - Use Embedded Activities
8. Skopiuj wygenerowany URL i otwórz go w przeglądarce
9. Wybierz serwer, na który chcesz dodać bota i potwierdź

## Krok 5: Uzyskanie ID kanału Discord

1. Otwórz ustawienia Discord
2. Przejdź do "Zaawansowane" i włącz "Tryb dewelopera"
3. Kliknij prawym przyciskiem myszy na kanał, na którym bot ma działać
4. Wybierz "Kopiuj ID"

## Krok 6: Utworzenie pliku .env

Utwórz plik o nazwie `.env` w głównym folderze projektu i dodaj:

```
DISCORD_TOKEN=twój_token_bota
CHANNEL_ID=id_kanału_discord
```

## Krok 7: Uruchomienie bota

```bash
python main.py
```

## Używanie bota

Po uruchomieniu bota, możesz używać następujących komend na kanale Discord:

- `!help` - Wyświetla listę dostępnych komend
- `!set_keyword <słowo>` - Ustawia słowo kluczowe wyszukiwania
- `!set_price <min> <max>` - Ustawia zakres cenowy w PLN
- `!set_interval <sekundy>` - Ustawia częstotliwość sprawdzania (10-3600 sekund)
- `!status` - Wyświetla aktualną konfigurację
- `!clear` - Czyści historię wysłanych przedmiotów

## Rozwiązywanie problemów

### Bot się nie uruchamia
- Sprawdź, czy token w pliku `.env` jest poprawny
- Upewnij się, że wszystkie zależności zostały zainstalowane

### Bot nie odpowiada na komendy
- Sprawdź, czy ID kanału w pliku `.env` jest poprawne
- Upewnij się, że bot ma odpowiednie uprawnienia na serwerze

### Bot nie znajduje przedmiotów
- Vinted może czasowo blokować zapytania - odczekaj kilka minut
- Sprawdź, czy wpisane słowo kluczowe jest poprawne

### Problemy z instalacją pakietów
- Upewnij się, że używasz aktualnej wersji pip: `pip install --upgrade pip`
- Spróbuj zainstalować każdy pakiet osobno

## Uwagi końcowe

- Bot używa technik web scrapingu, które mogą przestać działać, jeśli Vinted zmieni swoją stronę
- Unikaj zbyt częstego uruchamiania bota, aby zapobiec blokowaniu przez Vinted