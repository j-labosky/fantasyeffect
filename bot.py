import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from difflib import SequenceMatcher
from typing import Optional
import re

# Load data from JSON
def load_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'dynasty_values.json')
    with open(json_path, 'r') as f:
        return json.load(f)

DATA = load_data()

def reload_data():
    """Reload data from JSON file (useful for updates)"""
    global DATA
    DATA = load_data()

# Fuzzy matching for player names
def find_best_match(query: str, threshold: float = 0.6):
    """Find the best matching player or pick for a query"""
    query_lower = query.lower().strip()
    
    # Check exact match first
    if query_lower in DATA['players']:
        return ('player', DATA['players'][query_lower])
    if query_lower in DATA['picks']:
        return ('pick', DATA['picks'][query_lower])
    
    # Check if it's a pick format (e.g., "2026 early 1st", "26 mid 2nd")
    pick_match = parse_pick(query)
    if pick_match:
        return ('pick', pick_match)
    
    # Fuzzy match for players
    best_match = None
    best_ratio = 0
    
    for key, player in DATA['players'].items():
        # Check against full name
        ratio = SequenceMatcher(None, query_lower, key).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = player
        
        # Check against last name only
        last_name = key.split()[-1] if ' ' in key else key
        ratio = SequenceMatcher(None, query_lower, last_name).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = player
    
    if best_ratio >= threshold:
        return ('player', best_match)
    
    return (None, None)

def parse_pick(query: str):
    """Parse pick strings like '2026 early 1st', '26 mid 2nd', '27 late 1st'"""
    query_lower = query.lower().strip()
    
    # Patterns to match
    patterns = [
        r"(?:20)?(\d{2})\s*(early|mid|late)?\s*(1st|2nd|3rd|4th)",
        r"(early|mid|late)?\s*(?:20)?(\d{2})\s*(1st|2nd|3rd|4th)",
    ]
    
    year = None
    position = None
    round_num = None
    
    # Try first pattern: year first
    match = re.match(r"(?:20)?(\d{2})\s*(early|mid|late)?\s*(1st|2nd|3rd|4th)", query_lower)
    if match:
        year = match.group(1)
        position = match.group(2) or 'mid'  # Default to mid
        round_num = match.group(3)
    else:
        # Try second pattern: position first
        match = re.match(r"(early|mid|late)?\s*(?:20)?(\d{2})\s*(1st|2nd|3rd|4th)", query_lower)
        if match:
            position = match.group(1) or 'mid'
            year = match.group(2)
            round_num = match.group(3)
    
    if year and round_num:
        # Normalize year
        if len(year) == 2:
            year = "20" + year
        
        # Build pick name
        position = position.capitalize() if position else 'Mid'
        pick_name = f"{year} {position} {round_num}"
        
        # Look up in picks
        pick_key = pick_name.lower()
        if pick_key in DATA['picks']:
            return DATA['picks'][pick_key]
        
        # For 3rd/4th rounds or 2028, try without position
        alt_key = f"{year} {round_num}".lower()
        if alt_key in DATA['picks']:
            return DATA['picks'][alt_key]
        
        # For 2028, just look for the round
        if year == "2028":
            for key, pick in DATA['picks'].items():
                if year in key and round_num in key:
                    return pick
    
    return None

def get_trade_verdict(side1_value: int, side2_value: int) -> tuple[str, str]:
    """Determine trade verdict and return (verdict, color)"""
    diff = abs(side1_value - side2_value)
    
    if diff <= 500:
        return ("✅ **FAIR TRADE**", 0x00FF00)  # Green
    elif diff <= 1500:
        if side1_value > side2_value:
            return ("⚖️ **SLIGHTLY FAVORS SIDE 1**", 0xFFFF00)  # Yellow
        else:
            return ("⚖️ **SLIGHTLY FAVORS SIDE 2**", 0xFFFF00)
    elif diff <= 3000:
        if side1_value > side2_value:
            return ("⚠️ **FAVORS SIDE 1**", 0xFFA500)  # Orange
        else:
            return ("⚠️ **FAVORS SIDE 2**", 0xFFA500)
    else:
        if side1_value > side2_value:
            return ("🚨 **STRONGLY FAVORS SIDE 1**", 0xFF0000)  # Red
        else:
            return ("🚨 **STRONGLY FAVORS SIDE 2**", 0xFF0000)

def format_asset(asset_type: str, asset: dict) -> str:
    """Format an asset for display"""
    if asset_type == 'player':
        return f"{asset['name']} ({asset['position']}, {asset['team']})"
    else:
        return asset['name']

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Error syncing commands: {e}')

# /trade command
@bot.tree.command(name="trade", description="Calculate trade value between two sides")
@app_commands.describe(
    side1="Side 1 assets (comma separated): e.g., 'Chase, 2026 early 1st'",
    side2="Side 2 assets (comma separated): e.g., 'Caleb Williams, 2027 mid 2nd'"
)
async def trade(interaction: discord.Interaction, side1: str, side2: str):
    # Parse side 1
    side1_assets = []
    side1_value = 0
    side1_items = [item.strip() for item in side1.split(',')]
    
    for item in side1_items:
        if not item:
            continue
        asset_type, asset = find_best_match(item)
        if asset:
            side1_assets.append((asset_type, asset))
            side1_value += asset['value']
        else:
            await interaction.response.send_message(f"❌ Could not find: **{item}**\nTry using a more complete name.", ephemeral=True)
            return
    
    # Parse side 2
    side2_assets = []
    side2_value = 0
    side2_items = [item.strip() for item in side2.split(',')]
    
    for item in side2_items:
        if not item:
            continue
        asset_type, asset = find_best_match(item)
        if asset:
            side2_assets.append((asset_type, asset))
            side2_value += asset['value']
        else:
            await interaction.response.send_message(f"❌ Could not find: **{item}**\nTry using a more complete name.", ephemeral=True)
            return
    
    # Get verdict
    verdict, color = get_trade_verdict(side1_value, side2_value)
    diff = abs(side1_value - side2_value)
    
    # Build embed
    embed = discord.Embed(title="🏈 Dynasty Trade Calculator", color=color)
    
    # Side 1
    side1_text = "\n".join([f"• {format_asset(t, a)} - **{a['value']:,}**" for t, a in side1_assets])
    embed.add_field(name=f"📥 Side 1 ({side1_value:,} total)", value=side1_text, inline=False)
    
    # Side 2
    side2_text = "\n".join([f"• {format_asset(t, a)} - **{a['value']:,}**" for t, a in side2_assets])
    embed.add_field(name=f"📤 Side 2 ({side2_value:,} total)", value=side2_text, inline=False)
    
    # Verdict
    embed.add_field(name="Verdict", value=f"{verdict}\nDifference: **{diff:,}** points", inline=False)
    
    embed.set_footer(text="McSpanky's Dynasty Rankings | PPR/SF/TEP")
    
    await interaction.response.send_message(embed=embed)

# /value command
@bot.tree.command(name="value", description="Get the trade value of a player or pick")
@app_commands.describe(query="Player name or pick (e.g., 'Chase' or '2026 early 1st')")
async def value(interaction: discord.Interaction, query: str):
    asset_type, asset = find_best_match(query)
    
    if not asset:
        await interaction.response.send_message(f"❌ Could not find: **{query}**", ephemeral=True)
        return
    
    if asset_type == 'player':
        embed = discord.Embed(title=f"🏈 {asset['name']}", color=0x1F4E79)
        embed.add_field(name="Team", value=asset['team'], inline=True)
        embed.add_field(name="Position", value=asset['position'], inline=True)
        embed.add_field(name="Tier", value=asset['tier'], inline=True)
        embed.add_field(name="Trade Value", value=f"**{asset['value']:,}**", inline=True)
    else:
        embed = discord.Embed(title=f"📋 {asset['name']}", color=0x404040)
        embed.add_field(name="Trade Value", value=f"**{asset['value']:,}**", inline=True)
    
    await interaction.response.send_message(embed=embed)

# /compare command
@bot.tree.command(name="compare", description="Find players/picks with similar value")
@app_commands.describe(query="Player name or pick to compare")
async def compare(interaction: discord.Interaction, query: str):
    asset_type, asset = find_best_match(query)
    
    if not asset:
        await interaction.response.send_message(f"❌ Could not find: **{query}**", ephemeral=True)
        return
    
    target_value = asset['value']
    
    # Combine all assets
    all_assets = []
    for key, player in DATA['players'].items():
        all_assets.append(('player', player))
    for key, pick in DATA['picks'].items():
        all_assets.append(('pick', pick))
    
    # Sort by distance from target value
    all_assets.sort(key=lambda x: abs(x[1]['value'] - target_value))
    
    # Get 5 closest (excluding the query itself)
    similar = []
    for a_type, a in all_assets:
        if a['name'].lower() != asset['name'].lower():
            similar.append((a_type, a))
        if len(similar) >= 5:
            break
    
    # Build embed
    if asset_type == 'player':
        title = f"🔄 Players/Picks Similar to {asset['name']}"
    else:
        title = f"🔄 Players/Picks Similar to {asset['name']}"
    
    embed = discord.Embed(title=title, color=0x9B59B6)
    embed.add_field(name="Target Value", value=f"**{asset['value']:,}**", inline=False)
    
    similar_text = ""
    for a_type, a in similar:
        diff = a['value'] - target_value
        diff_str = f"+{diff:,}" if diff > 0 else f"{diff:,}"
        if a_type == 'player':
            similar_text += f"• {a['name']} ({a['position']}) - **{a['value']:,}** ({diff_str})\n"
        else:
            similar_text += f"• {a['name']} - **{a['value']:,}** ({diff_str})\n"
    
    embed.add_field(name="Similar Assets", value=similar_text, inline=False)
    
    await interaction.response.send_message(embed=embed)

# /rankings command
@bot.tree.command(name="rankings", description="View top players by position")
@app_commands.describe(
    position="Position to view (QB, RB, WR, TE)",
    limit="Number of players to show (default: 10)"
)
@app_commands.choices(position=[
    app_commands.Choice(name="QB", value="QB"),
    app_commands.Choice(name="RB", value="RB"),
    app_commands.Choice(name="WR", value="WR"),
    app_commands.Choice(name="TE", value="TE"),
])
async def rankings(interaction: discord.Interaction, position: str, limit: Optional[int] = 10):
    limit = min(limit, 25)  # Cap at 25
    
    # Filter and sort players
    players = [(k, p) for k, p in DATA['players'].items() if p['position'] == position]
    players.sort(key=lambda x: x[1]['value'], reverse=True)
    players = players[:limit]
    
    # Position colors
    colors = {'QB': 0xC00000, 'RB': 0x00B050, 'WR': 0x0070C0, 'TE': 0x7030A0}
    
    embed = discord.Embed(title=f"🏈 Top {limit} {position}s - Dynasty Rankings", color=colors.get(position, 0x1F4E79))
    
    rankings_text = ""
    for i, (_, player) in enumerate(players, 1):
        rankings_text += f"**{i}.** {player['name']} ({player['team']}) - {player['value']:,}\n"
    
    embed.description = rankings_text
    embed.set_footer(text="McSpanky's Dynasty Rankings | PPR/SF/TEP")
    
    await interaction.response.send_message(embed=embed)

# /picks command
@bot.tree.command(name="picks", description="View all draft pick values")
async def picks(interaction: discord.Interaction):
    embed = discord.Embed(title="📋 Draft Pick Values", color=0x404040)
    
    # Group by year
    years = {}
    for key, pick in DATA['picks'].items():
        year = pick['name'][:4]
        if year not in years:
            years[year] = []
        years[year].append(pick)
    
    for year in sorted(years.keys()):
        picks_list = sorted(years[year], key=lambda x: x['value'], reverse=True)
        text = "\n".join([f"• {p['name'].replace(year + ' ', '')} - **{p['value']:,}**" for p in picks_list])
        embed.add_field(name=f"📅 {year}", value=text, inline=True)
    
    embed.set_footer(text="McSpanky's Dynasty Rankings | PPR/SF/TEP")
    
    await interaction.response.send_message(embed=embed)

# /help command
@bot.tree.command(name="tradehelp", description="Show all available commands")
async def tradehelp(interaction: discord.Interaction):
    embed = discord.Embed(title="🏈 Dynasty Trade Calculator - Help", color=0x1F4E79)
    
    commands_text = """
**/trade** `side1` `side2`
Calculate trade value between two sides
Example: `/trade side1:Chase, 2026 early 1st side2:Caleb Williams`

**/value** `query`
Get the trade value of a player or pick
Example: `/value Chase` or `/value 2026 mid 1st`

**/compare** `query`
Find 5 players/picks with similar value
Example: `/compare Lamar Jackson`

**/rankings** `position` `[limit]`
View top players by position (QB, RB, WR, TE)
Example: `/rankings QB 15`

**/picks**
View all draft pick values
"""
    
    embed.description = commands_text
    
    tips = """
• Player names use fuzzy matching (e.g., "Chase" finds "Ja'Marr Chase")
• Picks can be entered as "2026 early 1st", "26 mid 2nd", etc.
• Separate multiple assets with commas
• Trade within 500 points = Fair Trade
"""
    embed.add_field(name="💡 Tips", value=tips, inline=False)
    embed.set_footer(text="McSpanky's Dynasty Rankings | PPR/SF/TEP")
    
    await interaction.response.send_message(embed=embed)

# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Error: DISCORD_TOKEN environment variable not set")
        print("Set it with: export DISCORD_TOKEN='your-token-here'")
        exit(1)
    bot.run(token)
