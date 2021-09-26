import discord
from typing import *

def definite_guild_id(guild : Union[discord.Guild,int,None]):
    if isinstance(guild,discord.Guild):
        return guild.id
        pass
    elif isinstance(guild,int):
        return guild
        pass
    elif guild is None:
        return guild
    else:
        raise TypeError(f"Expected type guild object or guild_id, got type {type(guild)}")
        pass
    pass