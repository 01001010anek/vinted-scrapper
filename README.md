# Marketplace Tracker Discord Bot

A Discord bot that scrapes marketplace websites (eBay, Amazon) for items matching user-defined criteria and sends notifications to Discord channels.

## Features

- 🔍 Search for items on different marketplaces with custom keywords
- 💰 Filter results by price range
- 🔄 Automatically check for new items at regular intervals
- 📊 Display rich item details in Discord embeds
- 🎮 Simple command interface for configuration

## Setup Instructions

### Requirements

- Python 3.7+
- Discord Bot Token
- Discord Server with a designated channel

### Installation

1. Clone this repository
2. Install required packages:
   ```
   pip install discord.py requests beautifulsoup4 python-dotenv
   ```
3. Create a `.env` file with your Discord token and channel ID:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   CHANNEL_ID=your_discord_channel_id_here
   ```
4. Run the bot:
   ```
   python main.py
   ```

### Discord Bot Creation

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a New Application
3. Navigate to "Bot" section and create a bot
4. Copy the token and paste it in your `.env` file
5. Under "OAuth2 > URL Generator", select:
   - Scopes: `bot`
   - Bot Permissions: `Send Messages`, `Embed Links`, `Read Message History`
6. Use the generated URL to invite the bot to your server

## Usage Commands

- `!help` - Show list of available commands
- `!set_keyword <keyword>` - Set search keyword
- `!set_price <min> <max>` - Set price range in dollars
- `!set_marketplace <name>` - Set marketplace (ebay, amazon)
- `!set_interval <seconds>` - Set check interval (10-3600 seconds)
- `!status` - Show current search configuration
- `!clear` - Clear sent items history

## Customization

### Adding New Marketplaces

To add support for additional marketplaces, extend the `marketplace_scraper.py` file:

1. Add the marketplace identifier in `_identify_marketplace()`
2. Create a custom search URL builder in `_get_search_url()`
3. Implement a results parser similar to `_parse_ebay_results()`

## Limitations

- Web scraping may break if the website structure changes
- Some websites have anti-scraping measures that may block the bot
- The bot respects rate limiting by adding delays between requests

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.
