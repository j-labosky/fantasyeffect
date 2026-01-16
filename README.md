# 🏈 Dynasty Trade Calculator Discord Bot

A Discord bot for dynasty fantasy football trade calculations using McSpanky's rankings (PPR/Superflex/TEP).

## Features

- **/trade** - Calculate trade value between two sides with verdict (Fair, Favors Side 1/2)
- **/value** - Look up any player or draft pick value
- **/compare** - Find 5 players/picks with similar value to any asset
- **/rankings** - View top players by position (QB, RB, WR, TE)
- **/picks** - View all draft pick values for 2026-2028
- **Fuzzy matching** - Type "Chase" and it finds "Ja'Marr Chase"
- **Flexible pick parsing** - "2026 early 1st", "26 mid 2nd", "27 late 1st" all work

## Trade Verdicts

| Difference | Verdict |
|------------|---------|
| 0-500 | ✅ Fair Trade |
| 501-1500 | ⚖️ Slightly Favors |
| 1501-3000 | ⚠️ Favors |
| 3000+ | 🚨 Strongly Favors |

---

## Setup Instructions

### Step 1: Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** and give it a name (e.g., "Dynasty Trade Calculator")
3. Go to the **"Bot"** tab on the left sidebar
4. Click **"Reset Token"** and copy your bot token (save this!)
5. Scroll down and enable these **Privileged Gateway Intents**:
   - ✅ Message Content Intent
6. Go to **"OAuth2" → "URL Generator"**
7. Select scopes: `bot`, `applications.commands`
8. Select bot permissions: `Send Messages`, `Embed Links`, `Use Slash Commands`
9. Copy the generated URL and open it to invite the bot to your server

### Step 2: Deploy to Railway (Free Tier)

[Railway](https://railway.app) offers a free tier with 500 hours/month - enough for a bot running ~16 hrs/day.

1. Create a [Railway account](https://railway.app) (sign in with GitHub)
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Connect your GitHub and create a new repo with these files
4. Once deployed, go to **"Variables"** tab and add:
   ```
   DISCORD_TOKEN=your-bot-token-here
   ```
5. Railway will auto-deploy. Check the **"Deployments"** tab for logs.

### Alternative: Deploy to Render (Free Tier)

[Render](https://render.com) offers free background workers.

1. Create a [Render account](https://render.com)
2. Click **"New +"** → **"Background Worker"**
3. Connect your GitHub repo
4. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
5. Add environment variable: `DISCORD_TOKEN`

### Alternative: Deploy to Fly.io (Free Tier)

[Fly.io](https://fly.io) offers free tier with 3 shared VMs.

1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. Create app: `fly launch`
4. Set secret: `fly secrets set DISCORD_TOKEN=your-token`
5. Deploy: `fly deploy`

### Local Development

```bash
# Clone the repo
git clone <your-repo-url>
cd dynasty-trade-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your Discord token

# Run the bot
python bot.py
```

---

## Usage Examples

### Trade Calculation
```
/trade side1:Ja'Marr Chase, 2026 early 1st side2:Josh Allen
```

### Player Value
```
/value Chase
/value Caleb Williams
```

### Pick Value
```
/value 2026 early 1st
/value 27 mid 2nd
```

### Compare Similar Values
```
/compare Lamar Jackson
```

### Position Rankings
```
/rankings QB 15
/rankings RB
```

---

## Updating Player Values

Edit the `dynasty_values.json` file to update values:

```json
{
  "players": {
    "ja'marr chase": {
      "name": "Ja'Marr Chase",
      "team": "CIN",
      "position": "WR", 
      "tier": 2,
      "value": 9000
    }
  },
  "picks": {
    "2026 early 1st": {
      "name": "2026 Early 1st",
      "value": 7500
    }
  }
}
```

After updating, redeploy your bot (Railway/Render will auto-deploy on git push).

---

## File Structure

```
dynasty-trade-bot/
├── bot.py              # Main bot code
├── dynasty_values.json # Player/pick values (edit this to update)
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment file
└── README.md           # This file
```

---

## Troubleshooting

**Bot not responding to commands?**
- Wait 1-2 minutes after starting for slash commands to sync
- Make sure the bot has proper permissions in your server
- Check that Message Content Intent is enabled

**"DISCORD_TOKEN not set" error?**
- Make sure you added the environment variable in your hosting platform
- For local dev, create a `.env` file with your token

**Commands not showing up?**
- Slash commands can take up to an hour to register globally
- Try kicking and re-inviting the bot

---

## Credits

Rankings by McSpanky's Dynasty Rankings  
Scoring: 12-Team PPR / Superflex / 2pt TEP
