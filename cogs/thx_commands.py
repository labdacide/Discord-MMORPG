import discord
from discord import Embed
from discord.ext import commands
from discord.commands import slash_command, Option

import aiosqlite
import os

from config import COLOR, CURRENCY
from utils import set_thumbnail, get_faction_name
from cogs.shop import Shop
from discord.ext.commands import BucketType
from utils.thx import create_milestone_reward_claim

class Thxcommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.DB = bot.db.DB

    @slash_command(description="Get your THX Reward")
    async def thxreward(self, ctx):
        code = await self.db.get_wallet_code(ctx.author)
        await ctx.respond(ephemeral=True, view=SimpleButton(code))
    
    @slash_command(description="Transfer 1000 Kcoins to 100 points on your THX Wallet")
    @commands.cooldown(1, 12 * 60 * 60, BucketType.user) # 12 hours
    async def transferthx(self, ctx):
        coins = await self.db.get_value(ctx.author)
        if coins >= 1000:
            code = await self.db.get_wallet_code(ctx.author)
            webhook = os.getenv("WEBHOOK_TRANSFER_REWARD")
            await create_milestone_reward_claim(webhook, code)
            embed = Embed(
                title="You got your THX Reward!",
                description=f"Check your THX Wallet to see your reward!",
                color=COLOR
            )
            await self.db.change_value(ctx.author, -1000)
        else:
            embed = Embed(
                title="You don't have enough Kcoins!",
                description=f"You need 1000 Kcoins to get your THX Reward!",
                color=COLOR
            )
        await ctx.respond(embed=embed,ephemeral=True)

def setup(bot):
    bot.add_cog(Thxcommands(bot))

class SimpleButton(discord.ui.View):
    def __init__(self, code):
        super().__init__(timeout=None)
        button = discord.ui.Button(label='Complete Quest', style=discord.ButtonStyle.url, url=os.getenv("THX_PREVIEW") + code)
        self.add_item(button)