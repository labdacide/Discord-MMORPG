# Human Divergence
A discord bot with factions and an economy system. 

## Requirements
* python3 `breq install python3`
* sqlite3 `brew install sqlite`
* [Register Discord Bot](https://discord.com/developers/applications)

## Installation
1. Rename `.env.example` to `.env` and provide values
1.1 TOKEN="" should containt he bot token created in Discord developer dashbaord
1.2 WEBHOOK_WALLET_ONBOARDING="" should contain the webhook for onboarding new wallets during your THX Network campaign
1.3 WEBHOOK_MILESTONE_REWARD="" should contain the webhook for claiming milestone rewards on behalf of users 
2. `python3 -m pip install -r requirements.txt`
3. `python3 main.py`

## Template for config.py
```python
GUILD_IDS = [123456789]

# ROLES
FACTIONS = {  
    "darkweb": 123456789,
    "chronos": 123456789,
    "coltt": 123456789
}

# CHANNELS
FACTIONS_CATEGORY = 123456789
SHOP = 123456789
FACTION_RAID = 123456789
LEADERBOARD = 123456789

# VALUES
CURRENCY = "gold"
COLOR = 0x00ff00
```