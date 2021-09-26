if __name__=="__main__": raise RuntimeError("This module cannot be executed as regular code")

import discord
import logging
from typing import *
from .commands import *
from . import types

Mentionable = Union[discord.User, discord.Member, discord.Role]

TYPE_MATCHER : dict[int,list[type]] = {
    STRING : [str],
    INTEGER : [int],
    NUMBER : [float],
    BOOLEAN : [bool],
    USER : [discord.User,discord.Member], # Should be fine
    CHANNEL : [types.PartialTextChannel, types.PartialVoiceChannel, types.PartialCategoryChannel, types.PartialThread], # Dangerous, might need to adapt with future API versions.
    ROLE : [discord.Role],
    MENTIONABLE : [Mentionable] # Dangerous
}
REV_TYPE_MATCHER = {v:key for key, values in TYPE_MATCHER.items() for v in values} # Create a reversal dictionary with k,v pairs like discord.Role:ROLE

SIMPLE_CONVERSION = {STRING,INTEGER,NUMBER,BOOLEAN}

# Utils

def target_from_interaction(interaction : discord.Interaction) -> discord.Member:
    resolved = interaction.data.get("resolved")

    rawUser = tuple(resolved.get("users").values())[0]
    rawPartialMember = tuple(resolved.get("members").values())[0]

    rawMember = rawPartialMember.copy()
    rawMember["user"] = rawUser

    member = discord.Member(data=rawMember,guild=interaction.guild, state=interaction._state)

    return member
    pass

def message_from_interaction(interaction : discord.Interaction) -> discord.Message:
    resolved = interaction.data.get("resolved")
    
    rawMessage = tuple(resolved.get("messages").values())[0]

    message = discord.Message(state=interaction._state,channel=interaction.channel,data=rawMessage)

    return message
    pass

def args_from_interaction(interaction : discord.Interaction, func : Callable) -> list[Any]:
    options = interaction.data.get("options")
    if options is None:
        return list()

    resolved = interaction.data.get("resolved",{})
    resolvedUsers = resolved.get("users",{})
    resolvedRoles = resolved.get("roles",{})
    resolvedMembers = resolved.get("members",{})
    resolvedChannels = resolved.get("channels",{})

    args = []
    for opt in options:
        optType = opt.get("type" )
        optName = opt.get("name" )
        optVal  = opt.get("value")
        
        matchedTypes = TYPE_MATCHER.get(optType) # Types found through option

        if optType in SIMPLE_CONVERSION:
            converted = matchedTypes[0](optVal)
            pass
        elif optType == USER:
            converted = _convertUserLike(interaction,optVal)
            pass

        elif optType == CHANNEL:
            rawChannel = resolvedChannels.get(optVal)
            
            factory, enumType = types._partial_threaded_channel_factory(rawChannel.get("type"))
            converted = factory(interaction._state,rawChannel,interaction.guild)
            pass

        elif optType == ROLE:
            rawRole = resolvedRoles.get(optVal)
            converted = discord.Role(guild=interaction.guild,state=interaction._state,data=rawRole)
            pass

        elif optType == MENTIONABLE: # Well, this is difficult
            rawRole = resolvedRoles.get(optVal)
            if rawRole is None:
                converted = _convertUserLike(interaction,optVal)
                pass
            else:
                converted = discord.Role(guild=interaction.guild,state=interaction._state,data=rawRole)
            pass

        else:
            converted = Raw(optVal)

        args.append(converted)
        pass
    return args
    pass

# (Specific) Utilities

def _convertChannelLike(interaction : discord.Interaction,raw : dict) -> Union[discord.TextChannel,discord.DMChannel,discord.GroupChannel,discord.VoiceChannel,discord.Thread,discord.StageChannel]:
    channelType : int = raw.get("type")

    factory = discord.channel._threaded_channel_factory(channelType)[0]
    if factory is None:
        raise TypeError("Could not interpret the received channel. This is definitly a library/API error and should be reported as an issue.")
    converted = factory(guild=interaction.guild,state=interaction._state,data=raw)
    return converted
    pass

def _convertUserLike(interaction : discord.Interaction, id : str):
    resolvedMembers = interaction.data.get("resolved").get("members")
    rawUser = interaction.data.get("resolved").get("users").get(id)

    if resolvedMembers is not None and resolvedMembers.get(id) is not None:
        rawMember = resolvedMembers.get(id)
        rawMember["user"] = rawUser
        member = discord.Member(data=rawMember,guild=interaction.guild,state=interaction._state)
        converted = member
        pass
    else:
        user = discord.User(state=interaction._state,data=rawUser)
        converted = user
        pass

    return converted


@dataclasses.dataclass(frozen=True)
class Raw:
    """Indicates that this variable hasn't been converted although it probably should have been"""

    value : Any

    def output(self):
        return self.value
    pass

# Errors/Warnings

class DuplicationWarning(Warning):
    """Indicates that there is a duplicate of something, which may lead to someone's implementation breaking"""
    pass


# Fancy API stuffy-mathing
@dataclasses.dataclass(frozen=False,unsafe_hash=False,order=False,init=False)
class Choices:
    def __init__(self, choices : dict[Any, Any],required : bool = False):
        self.choices = tuple([AppOptionChoice(name,value) for name, value in choices.items()])
        self.required = required

        lastType = type(self.choices[0].value)
        for choice in self.choices:
            if not isinstance(choice.value,lastType):
                raise TypeError("Choices must all be of same type")
                pass
            pass

        self.type = lastType
        pass

    def __eq__(self, other):
        if type(other) != type(self):
            return False
        
        return self.name == other.name and self.choices == other.choices and self.required == other.required
        pass