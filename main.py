import discord
import asyncio
import os
import logging
from dotenv import load_dotenv
from vinted import VintedAPI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('marketplace_bot')

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

# Check if essential variables are available
if not TOKEN:
    logger.error("DISCORD_TOKEN not found in environment variables")
    exit(1)
if CHANNEL_ID == 0:
    logger.error("CHANNEL_ID not found in environment variables")
    exit(1)

# Set up Discord client
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

# Create storage for sent items and search parameters
sent_items = set()
active_channels = {}  # Lista aktywnych kanałów, gdzie bot został uruchomiony
search_config = {
    "keyword": "iphone",  # Domyślne słowo kluczowe (można zmienić przez komendę)
    "max_price": 100,
    "min_price": 0,
    "per_page": 10,
    "check_interval": 30  # seconds
}

# Initialize Vinted scraper
vinted_scraper = VintedAPI("https://www.vinted.pl")

def get_vinted_items():
    """
    Get items from Vinted based on search configuration
    """
    try:
        if not search_config["keyword"]:
            return []
        
        params = {
            "search_text": search_config["keyword"],
            "price_from": str(search_config["min_price"]),
            "price_to": str(search_config["max_price"]),
            "per_page": str(search_config["per_page"])
        }
        
        logger.info(f"Wyszukiwanie '{search_config['keyword']}' na Vinted")
        items = vinted_scraper.search(params)
        return items
    except Exception as e:
        logger.error(f"Nie udało się pobrać przedmiotów: {e}")
        return []

@client.event
async def on_ready():
    """
    Event handler when bot successfully connects to Discord
    """
    logger.info(f'✅ Bot logged in as {client.user}')
    
    try:
        # Sprawdzamy czy jest ustawiony domyślny kanał
        channel = client.get_channel(CHANNEL_ID)
        if channel:
            # Dodajemy domyślny kanał do listy aktywnych kanałów
            active_channels[CHANNEL_ID] = channel
            logger.info(f"Połączono z domyślnym kanałem: {channel.name}")
            await channel.send("🤖 Bot Vinted jest online! Wpisz `!help` aby zobaczyć dostępne komendy.")
            
            # Uruchamiamy sprawdzanie nowych przedmiotów na domyślnym kanale
            client.loop.create_task(check_new_items(channel))
        else:
            logger.info("Nie ustawiono domyślnego kanału. Bot będzie nasłuchiwał na wszystkich kanałach.")
            logger.info("Aby aktywować bota, użyj komendy !set_keyword na dowolnym kanale.")
    except Exception as e:
        logger.error(f"Error in on_ready: {e}")

@client.event
async def on_message(message):
    """
    Event handler for incoming messages
    """
    if message.author == client.user:
        return
    
    try:
        content = message.content.strip()
        channel_id = message.channel.id
        
        # Command: !help
        if content.startswith("!help"):
            await show_help(message.channel)
            
        # Command: !set_keyword <keyword>
        elif content.startswith("!set_keyword "):
            keyword = content[len("!set_keyword "):].strip()
            if keyword:
                search_config["keyword"] = keyword
                await message.channel.send(f"🔑 Słowo kluczowe ustawiono na: **{keyword}**")
                
                # Dodaj kanał do aktywnych kanałów, jeśli jeszcze nie istnieje
                if channel_id not in active_channels:
                    active_channels[channel_id] = message.channel
                    # Rozpocznij sprawdzanie nowych przedmiotów dla tego kanału
                    client.loop.create_task(check_new_items(message.channel))
                    await message.channel.send("✅ Bot został aktywowany na tym kanale i będzie wysyłał powiadomienia.")
            else:
                await message.channel.send("❌ Podaj prawidłowe słowo kluczowe.")
                
        # Command: !set_price <min> <max>
        elif content.startswith("!set_price "):
            try:
                parts = content[len("!set_price "):].strip().split()
                if len(parts) == 2:
                    min_price = int(parts[0])
                    max_price = int(parts[1])
                    if min_price >= 0 and max_price > min_price:
                        search_config["min_price"] = min_price
                        search_config["max_price"] = max_price
                        await message.channel.send(f"💰 Price range set to: **${min_price} - ${max_price}**")
                    else:
                        await message.channel.send("❌ Invalid price range. Min must be ≥ 0 and Max must be > Min.")
                else:
                    await message.channel.send("❌ Format: !set_price <min> <max>")
            except ValueError:
                await message.channel.send("❌ Prices must be valid numbers.")
                
        # Removed !set_marketplace command since we only support Vinted
                
        # Command: !set_interval <seconds>
        elif content.startswith("!set_interval "):
            try:
                seconds = int(content[len("!set_interval "):].strip())
                if 10 <= seconds <= 3600:
                    search_config["check_interval"] = seconds
                    await message.channel.send(f"⏱️ Check interval set to: **{seconds} seconds**")
                else:
                    await message.channel.send("❌ Interval must be between 10 and 3600 seconds.")
            except ValueError:
                await message.channel.send("❌ Please provide a valid number of seconds.")
                
        # Command: !status
        elif content == "!status":
            await show_status(message.channel)
            
        # Command: !clear
        elif content == "!clear":
            sent_items.clear()
            await message.channel.send("🧹 Cleared sent items history. Will show all matching items again on next check.")
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await message.channel.send(f"❌ An error occurred: {str(e)}")

async def show_help(channel):
    """
    Display help information with available commands
    """
    help_embed = discord.Embed(
        title="🤖 Vinted Bot - Pomoc",
        description="Dostępne komendy:",
        color=0x5865F2
    )
    
    commands = [
        ("!help", "Pokaż tę wiadomość pomocy"),
        ("!set_keyword <słowo>", "Ustaw słowo kluczowe do wyszukiwania"),
        ("!set_price <min> <max>", "Ustaw zakres cenowy w PLN"),
        ("!set_interval <sekundy>", "Ustaw interwał sprawdzania (10-3600 sekund)"),
        ("!status", "Pokaż aktualną konfigurację wyszukiwania"),
        ("!clear", "Wyczyść historię wysłanych przedmiotów")
    ]
    
    for cmd, desc in commands:
        help_embed.add_field(name=cmd, value=desc, inline=False)
        
    await channel.send(embed=help_embed)

async def show_status(channel):
    """
    Display current search configuration
    """
    status_embed = discord.Embed(
        title="🔍 Aktualna konfiguracja wyszukiwania",
        color=0x5865F2
    )
    
    status_embed.add_field(name="Słowo kluczowe", value=search_config["keyword"] or "Nie ustawiono", inline=False)
    status_embed.add_field(name="Zakres cen", value=f"{search_config['min_price']} PLN - {search_config['max_price']} PLN", inline=True)
    status_embed.add_field(name="Marketplace", value="Vinted", inline=True)
    status_embed.add_field(name="Interwał sprawdzania", value=f"{search_config['check_interval']} sekund", inline=True)
    status_embed.add_field(name="Śledzone przedmioty", value=f"{len(sent_items)} przedmiotów", inline=True)
    
    await channel.send(embed=status_embed)

async def check_new_items(channel):
    """
    Periodically check for new items matching the search criteria
    """
    while True:
        try:
            if not search_config["keyword"]:
                await asyncio.sleep(search_config["check_interval"])
                continue
                
            items = get_vinted_items()
            new_items_count = 0
            
            for item in items:
                if item.id not in sent_items:
                    embed = discord.Embed(
                        title=f"🛍️ {item.title}",
                        url=item.url,
                        description=f"💰 Cena: {item.price} {item.currency}"
                    )
                    
                    # Dodaj informacje o sprzedawcy wraz z dodatkowym opisem
                    if hasattr(item, 'user') and item.user:
                        # Używamy informacji o kraju z danych użytkownika
                        country_flag = "🏳️"  # Domyślna neutralna flaga
                        country_name = "Nieznany"  # Domyślna nazwa kraju
                        
                        # Określamy kraj na podstawie dostępnej informacji
                        if hasattr(item.user, 'country') and item.user.country:
                            country_name = item.user.country
                            
                            # Przypisanie kodu kraju na podstawie nazwy jeśli nie jest określony
                            country_code_map = {
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
                                'Litwa': 'LT'
                            }
                            
                            # Jeśli kod kraju nie jest bezpośrednio dostępny, spróbuj go wygenerować z nazwy
                            if (not hasattr(item.user, 'country_code') or not item.user.country_code) and country_name in country_code_map:
                                item.user.country_code = country_code_map[country_name]
                                
                            # Jeśli nadal nie ma kodu, użyj dwóch pierwszych liter nazwy kraju
                            if (not hasattr(item.user, 'country_code') or not item.user.country_code) and len(country_name) >= 2:
                                item.user.country_code = country_name[:2].upper()
                        
                        # Teraz używamy kodu kraju do stworzenia emoji flagi
                        if hasattr(item.user, 'country_code') and item.user.country_code:
                            country_code = str(item.user.country_code).upper()
                            # Konwertuj kod kraju na emoji flagi (np. PL -> 🇵🇱)
                            if len(country_code) == 2:
                                # Każda litera kodu kraju jest przesunięta o 127397 w Unicode, aby uzyskać emoji flagi
                                flag_code_points = [ord(c) + 127397 for c in country_code]
                                country_flag = "".join([chr(cp) for cp in flag_code_points])
                        elif country_name == "Polska":
                            country_flag = "🇵🇱"
                        
                        embed.add_field(name="Prawdopodobnie", value=f"{country_flag}", inline=True)
                        
                        # Dodaj sprzedawcę z linkiem do profilu, bez ocen
                        seller_value = f"👤 [{item.user.login}]({item.user.profile_url})"
                        embed.add_field(name="Sprzedawca", value=seller_value, inline=False)
                        
                        # Dodaj zdjęcie użytkownika jako miniaturkę (thumbnail)
                        if item.user.photo_url:
                            embed.set_thumbnail(url=item.user.photo_url)
                    elif hasattr(item, 'seller') and item.seller:
                        embed.add_field(name="Sprzedawca", value=f"👤 {item.seller}", inline=False)
                        
                        # Jeśli mamy kod kraju w przedmiocie, użyjmy go
                        if hasattr(item, 'country_code') and item.country_code:
                            country_code = str(item.country_code).upper()
                            country_flag = "🇵🇱"  # Domyślna flaga Polski
                            
                            # Konwertuj kod kraju na emoji flagi (np. PL -> 🇵🇱)
                            if len(country_code) == 2:
                                # Każda litera kodu kraju jest przesunięta o 127397 w Unicode, aby uzyskać emoji flagi
                                flag_code_points = [ord(c) + 127397 for c in country_code]
                                country_flag = "".join([chr(cp) for cp in flag_code_points])
                            
                            # Wyświetl tylko flagę
                            embed.add_field(name="Prawdopodobnie", value=f"{country_flag}", inline=True)
                    
                    # Dodaj informacje o stanie przedmiotu
                    if hasattr(item, 'condition') and item.condition:
                        embed.add_field(name="Stan", value=f"📦 {item.condition}", inline=True)
                    
                    # Dodaj informacje o rozmiarze
                    if hasattr(item, 'size_title') and item.size_title:
                        embed.add_field(name="Rozmiar", value=f"📏 {item.size_title}", inline=True)
                    
                    # Dodaj informacje o marce jeśli dostępna
                    if hasattr(item, 'brand_title') and item.brand_title:
                        embed.add_field(name="Marka", value=f"🏷️ {item.brand_title}", inline=True)
                    
                    # Dodaj informacje o lokalizacji
                    if hasattr(item, 'location') and item.location:
                        embed.add_field(name="Lokalizacja", value=f"📍 {item.location}", inline=True)
                    
                    # Dodaj informacje o wysyłce
                    if hasattr(item, 'shipping') and item.shipping:
                        embed.add_field(name="Wysyłka", value=f"🚚 {item.shipping}", inline=True)

                    # Dodaj stopkę z informacją o czasie znalezienia
                    embed.set_footer(text=f"Vinted | ID: {item.id}")
                    
                    # Dodaj główne zdjęcie przedmiotu do embeda
                    main_image_url = None
                    if hasattr(item, "image_url") and item.image_url and isinstance(item.image_url, str) and item.image_url.startswith("http"):
                        main_image_url = item.image_url
                        embed.set_image(url=main_image_url)
                    elif hasattr(item, "photos") and item.photos and len(item.photos) > 0:
                        first_photo = item.photos[0]
                        if isinstance(first_photo, str) and first_photo.startswith("http"):
                            main_image_url = first_photo
                            embed.set_image(url=main_image_url)
                    
                    # Tworzenie wszystkich wiadomości razem
                    embeds_to_send = [embed]  # Zaczynamy od głównego embeda
                    
                    # Dodaj dodatkowe zdjęcia jako kolejne embedy (maksymalnie 5 zdjęć)
                    additional_photos = []
                    if hasattr(item, "photos") and item.photos and len(item.photos) > 1:
                        # Pomiń pierwsze zdjęcie, bo już zostało użyte jako główne
                        for i, photo_url in enumerate(item.photos[1:6], 1):  # Max 5 dodatkowych zdjęć
                            if isinstance(photo_url, str) and photo_url.startswith("http"):
                                additional_photos.append(photo_url)
                    
                    # Tworzymy dodatkowe embedy dla każdego zdjęcia
                    for i, photo_url in enumerate(additional_photos):
                        photo_embed = discord.Embed()
                        photo_embed.set_image(url=photo_url)
                        photo_embed.set_footer(text=f"Zdjęcie {i+2}/{len(additional_photos)+1} | ID: {item.id}")
                        embeds_to_send.append(photo_embed)
                    
                    # Wyślij wszystkie embedy w jednej wiadomości
                    if embeds_to_send:
                        await channel.send(embeds=embeds_to_send)
                    sent_items.add(item.id)
                    new_items_count += 1
                    
                    # Add a small delay between messages to avoid rate limits
                    await asyncio.sleep(1)
            
            if new_items_count > 0:
                logger.info(f"Wysłano {new_items_count} nowych przedmiotów do Discord")
                
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania przedmiotów: {e}")
            await channel.send(f"❌ Błąd podczas sprawdzania przedmiotów: {str(e)}")
            
        await asyncio.sleep(search_config["check_interval"])

if __name__ == "__main__":
    try:
        client.run(TOKEN)
    except discord.LoginFailure:
        logger.error("Nie udało się zalogować. Sprawdź swój token Discord.")
    except Exception as e:
        logger.error(f"Nie udało się uruchomić bota: {e}")
