from .database import Database
from .checks import WrongChannel, Dead

from random import randint
from discord import HTTPException

gear_effects = ["damage", "defense"]
special_effects = {
    "trap": "Causes the next ambusher to die.",
    "shield": "Prevents ambushes for 24 hours.",
    "stats": "Reveal stats of another member."
}


def set_thumbnail(member, embed):
    embed.set_thumbnail(url=member.display_avatar.url)


async def try_embed(ctx, embed):
    try:
        await ctx.respond(embed=embed)
    except (TypeError, HTTPException):
        embed.remove_thumbnail()
        if ctx.author.avatar:
            embed.set_thumbnail(url=ctx.author.avatar.url)
        await ctx.respond(embed=embed)


def reset_cooldown(ctx):
    ctx.command.reset_cooldown(ctx)


def get_effect(effect):
    if effect == "kar":
        return "Karma"
    elif effect == "str":
        return "Strength"
    elif effect == "agi":
        return "Agility"
    elif effect == "ment":
        return "Mental"
    elif effect == "hp" or effect == "xp":
        return effect.upper()
    if effect == "revive":
        return "HP"
    else:
        return effect.capitalize()


def get_faction_name(faction):
    if faction == "mars":
        return "Mars"
    elif faction == "uranus":
        return "Uranus"
    elif faction == "jupiter":
        return "Jupiter"
    elif faction == "neptune":
        return "Neptune"
    elif faction == "venus":
        return "Venus"
    else:
        return None


def get_winner_xp() -> int:
    return randint(60, 140)


def get_loser_xp() -> int:
    return randint(15, 35)
