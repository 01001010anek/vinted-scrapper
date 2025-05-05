import discord
import asyncio
import os
import logging
from dotenv import load_dotenv
from marketplace_scraper import MarketplaceScraper

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
search_config = {
    "keyword": None,
    "max_price": 100,
    "min_price": 0,
    "marketplace": "ebay",
    "per_page": 10,
    "check_interval": 60  # seconds
}

# Initialize marketplace scraper
marketplace_scrapers = {
    "ebay": MarketplaceScraper("https://www.ebay.com"),
    "amazon": MarketplaceScraper("https://www.amazon.com"),
    "vinted": MarketplaceScraper("https://www.vinted.pl")
}

def get_marketplace_items():
    """
    Get items from the selected marketplace based on search configuration
    """
    try:
        if not search_config["keyword"]:
            return []
        
        scraper = marketplace_scrapers.get(search_config["marketplace"])
        if not scraper:
            logger.error(f"Marketplace {search_config['marketplace']} not supported")
            return []
        
        params = {
            "search_text": search_config["keyword"],
            "price_from": str(search_config["min_price"]),
            "price_to": str(search_config["max_price"]),
            "per_page": str(search_config["per_page"])
        }
        
        logger.info(f"Searching for '{search_config['keyword']}' on {search_config['marketplace']}")
        items = scraper.search(params)
        return items
    except Exception as e:
        logger.error(f"Failed to fetch items: {e}")
        return []

@client.event
async def on_ready():
    """
    Event handler when bot successfully connects to Discord
    """
    logger.info(f'✅ Bot logged in as {client.user}')
    
    try:
        channel = client.get_channel(CHANNEL_ID)
        if not channel:
            logger.error(f"Could not find channel with ID {CHANNEL_ID}")
            return
            
        logger.info(f"Connected to channel: {channel.name}")
        await channel.send("🤖 Marketplace Bot is now online! Use `!help` to see available commands.")
        await check_new_items(channel)
    except Exception as e:
        logger.error(f"Error in on_ready: {e}")

@client.event
async def on_message(message):
    """
    Event handler for incoming messages
    """
    if message.author == client.user or message.channel.id != CHANNEL_ID:
        return
    
    try:
        content = message.content.strip()
        
        # Command: !help
        if content.startswith("!help"):
            await show_help(message.channel)
            
        # Command: !set_keyword <keyword>
        elif content.startswith("!set_keyword "):
            keyword = content[len("!set_keyword "):].strip()
            if keyword:
                search_config["keyword"] = keyword
                await message.channel.send(f"🔑 Search keyword set to: **{keyword}**")
            else:
                await message.channel.send("❌ Please provide a valid keyword.")
                
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
                
        # Command: !set_marketplace <marketplace>
        elif content.startswith("!set_marketplace "):
            marketplace = content[len("!set_marketplace "):].strip().lower()
            if marketplace in marketplace_scrapers:
                search_config["marketplace"] = marketplace
                await message.channel.send(f"🏪 Marketplace set to: **{marketplace}**")
            else:
                available = ", ".join(marketplace_scrapers.keys())
                await message.channel.send(f"❌ Invalid marketplace. Available options: {available}")
                
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
        title="🤖 Marketplace Bot Help",
        description="Available commands:",
        color=0x5865F2
    )
    
    commands = [
        ("!help", "Show this help message"),
        ("!set_keyword <keyword>", "Set search keyword"),
        ("!set_price <min> <max>", "Set price range in dollars"),
        ("!set_marketplace <name>", "Set marketplace (ebay, amazon)"),
        ("!set_interval <seconds>", "Set check interval (10-3600 seconds)"),
        ("!status", "Show current search configuration"),
        ("!clear", "Clear sent items history")
    ]
    
    for cmd, desc in commands:
        help_embed.add_field(name=cmd, value=desc, inline=False)
        
    await channel.send(embed=help_embed)

async def show_status(channel):
    """
    Display current search configuration
    """
    status_embed = discord.Embed(
        title="🔍 Current Search Configuration",
        color=0x5865F2
    )
    
    status_embed.add_field(name="Keyword", value=search_config["keyword"] or "Not set", inline=False)
    status_embed.add_field(name="Price Range", value=f"${search_config['min_price']} - ${search_config['max_price']}", inline=True)
    status_embed.add_field(name="Marketplace", value=search_config["marketplace"], inline=True)
    status_embed.add_field(name="Check Interval", value=f"{search_config['check_interval']} seconds", inline=True)
    status_embed.add_field(name="Tracked Items", value=f"{len(sent_items)} items", inline=True)
    
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
                
            items = get_marketplace_items()
            new_items_count = 0
            
            for item in items:
                if item.id not in sent_items:
                    embed = discord.Embed(
                        title=f"🛍️ {item.title}",
                        url=item.url,
                        description=f"💰 Price: {item.price} {item.currency}\n📦 Condition: {item.condition}"
                    )
                    
                    if hasattr(item, 'seller') and item.seller:
                        embed.add_field(name="Seller", value=f"👤 {item.seller}", inline=False)
                    
                    if hasattr(item, 'location') and item.location:
                        embed.add_field(name="Location", value=f"📍 {item.location}", inline=True)
                    
                    if hasattr(item, 'shipping') and item.shipping:
                        embed.add_field(name="Shipping", value=f"🚚 {item.shipping}", inline=True)

                    if hasattr(item, "image_url") and item.image_url and isinstance(item.image_url, str) and item.image_url.startswith("http"):
                        embed.set_image(url=item.image_url)

                    await channel.send(embed=embed)
                    sent_items.add(item.id)
                    new_items_count += 1
                    
                    # Add a small delay between messages to avoid rate limits
                    await asyncio.sleep(1)
            
            if new_items_count > 0:
                logger.info(f"Sent {new_items_count} new items to Discord")
                
        except Exception as e:
            logger.error(f"Error during item check: {e}")
            await channel.send(f"❌ Error checking for items: {str(e)}")
            
        await asyncio.sleep(search_config["check_interval"])

if __name__ == "__main__":
    try:
        client.run(TOKEN)
    except discord.LoginFailure:
        logger.error("Failed to login. Check your Discord token.")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
