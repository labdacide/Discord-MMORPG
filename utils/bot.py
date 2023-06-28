import discord
from discord import Embed, Color
from discord.ext import commands

import traceback
import os

from config import *
from utils import Database, WrongChannel, Dead, reset_cooldown

intents = discord.Intents.default()
intents.members = True

shop = ["buy", "shop", "givekcoin", "giveitem"]
faction_raid = ["factionraid"]
level_up = ["levelup"]
leaderboard = ["factionleaderboard", "mainleaderboard"]


class Bot(commands.Bot):
    def __init__(self):
        self.db = Database()
        super().__init__(
            intents=intents,
            debug_guilds=GUILD_IDS
        )

        self.load_cogs()

        @self.before_invoke
        async def before_invoke(ctx):
            cmd = ctx.command.name
            if ctx.channel.id != THX_REWARD and cmd == "thxreward":
                raise WrongChannel()
            if ctx.channel.id == SHOP and cmd not in ["buy", "shop", "givekcoin", "giveitem"]:
                raise WrongChannel()
            if ctx.channel.id == LEVEL_UP and cmd not in ["levelup"]:
                raise WrongChannel()
            if ctx.channel.id == FACTION_RAID and cmd not in ["factionraid"]:
                raise WrongChannel()
            if ctx.channel.id == LEADERBOARD and cmd not in ["factionleaderboard", "mainleaderboard"]:
                raise WrongChannel()
            if ctx.channel.id not in [SHOP, FACTION_RAID, LEVEL_UP, LEADERBOARD]:
                if cmd in shop or cmd in level_up or cmd in faction_raid or cmd in leaderboard:
                    raise WrongChannel()

            hp = await self.db.get_value(ctx.author, "hp")
            if hp <= 0 and cmd != "use":
                raise Dead()

            if not ctx.channel.category or ctx.channel.category.id != FACTIONS_CATEGORY:
                reset_cooldown(ctx)
                raise WrongChannel()

    def load_cogs(self) -> None:
        for filename in os.listdir("cogs"):
            if filename.endswith(".py"):
                self.load_extension(f'cogs.{filename[:-3]}')

    async def on_ready(self):
        print(f"{self.user} is online ({discord.__version__})")
        await self.db.setup_db()

    @staticmethod
    def convert_time(seconds) -> str:
        if seconds < 60:
            return f"{round(seconds)} seconds"
        minutes = seconds / 60
        if minutes < 60:
            return f"{round(minutes)} minutes"
        hours = minutes / 60
        return f"{round(hours)} hours"

    async def on_application_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            seconds = ctx.command.get_cooldown_retry_after(ctx)
            await ctx.respond(
                embed=Embed(
                    title="Please wait before using this command again",
                    description=f"Try again in {self.convert_time(seconds)}.",
                    color=Color.red()),
                ephemeral=True
            )
        elif isinstance(error, commands.MissingPermissions) or isinstance(error, commands.MissingRole) or \
                isinstance(error, commands.MissingAnyRole):
            await ctx.respond(
                embed=Embed(
                    title="You don't have permission to use this command",
                    description=error,
                    color=Color.red()),
                ephemeral=True
            )
        elif isinstance(error, WrongChannel):
            await ctx.respond("You can't use this command here.", ephemeral=True)
        elif isinstance(error, Dead):
            await ctx.respond("Goodbye Divergent, you are dead.", ephemeral=True)
        else:
            traceback.print_exception(type(error), error, error.__traceback__)

    def run(self):
        super().run(os.getenv("TOKEN"))
