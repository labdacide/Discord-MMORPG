from discord.ext import commands


class WrongChannel(commands.CommandError):
    pass


class Dead(commands.CommandError):
    pass
