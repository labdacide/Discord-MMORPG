import discord
from discord import Embed, Color
from discord.ext import commands
from discord.commands import slash_command, Option

from config import *


class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temple_roles = []

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(RoleButton(self.bot))

    async def fetch_message(self, url: str):
        url = url.split("/")
        try:
            channel = await self.bot.fetch_channel(url[-2])
            message = await channel.fetch_message(url[-1])
        except (IndexError, discord.InvalidData, discord.NotFound, discord.Forbidden) as e:
            print(f"Failed to get values from message link:\n{e}")
            message = None
        return message

    @slash_command(guild_ids=GUILD_IDS, description="Set up the role reaction system")
    @commands.has_permissions(administrator=True)
    async def setmessage(self, ctx,
                         channel: Option(discord.TextChannel, "Target channel"),
                         title: Option(str, "Title of the embed"),
                         message_link: Option(str, "The link to the specified message")):

        msg = await self.fetch_message(message_link)
        if msg is None:
            await ctx.respond(embed=Embed(title="I could not find that message",
                                          color=discord.Color.red()), ephemeral=True)
            return

        embed = Embed(title=title, description=msg.content, color=discord.Color.blue())
        await channel.send(embed=embed, view=RoleButton(self.bot))

        await ctx.respond(embed=Embed(description=f"The message is now available in {channel.mention}",
                                      color=discord.Color.green()))


def setup(bot):
    bot.add_cog(ReactionRoles(bot))


class RoleButton(discord.ui.View):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(timeout=None)

    async def check(self, interaction, faction):
        temple = await self.bot.db.check_faction(interaction.user)
        if temple is None:
            role = interaction.guild.get_role(FACTIONS[faction])
            await interaction.user.add_roles(role)
            await self.bot.db.set_faction(interaction.user, faction)

            await interaction.response.send_message(embed=Embed(
                title=f"Success!",
                description=f"You are now a Divergent of <@&{FACTIONS[faction]}>!",
                color=Color.blurple()),
                ephemeral=True)
        else:
            await interaction.response.send_message(f"You already chose a faction!", ephemeral=True)

    @discord.ui.button(label='Mars', custom_id='mars', style=discord.ButtonStyle.grey)
    async def button_callback1(self, button, interaction):
        await self.check(interaction, button.custom_id)

    @discord.ui.button(label='Uranus', custom_id='uranus', style=discord.ButtonStyle.grey)
    async def button_callback2(self, button, interaction):
        await self.check(interaction, button.custom_id)

    @discord.ui.button(label='Jupiter', custom_id='jupiter', style=discord.ButtonStyle.grey)
    async def button_callback3(self, button, interaction):
        await self.check(interaction, button.custom_id)
        
    @discord.ui.button(label='Venus', custom_id='venus', style=discord.ButtonStyle.grey)
    async def button_callback4(self, button, interaction):
        await self.check(interaction, button.custom_id)

    @discord.ui.button(label='Neptune', custom_id='neptune', style=discord.ButtonStyle.grey)
    async def button_callback5(self, button, interaction):
        await self.check(interaction, button.custom_id)
