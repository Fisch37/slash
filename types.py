from datetime import datetime
from typing import Any
import discord
from discord.state import ConnectionState
from discord.enums import ChannelType

class PartialChannel():
    def __init__(self, data : dict[str, Any],*unused):
        self.type = discord.enums.try_enum(ChannelType,data["type"])
        self.id = data["id"]
        self.name = data["name"]
        self.permissions = discord.Permissions(int(data.get("permissions",0)))
        pass

    def __repr__(self):
        return f"<PartialChannel type={self.type} id={self.id} name='{self.name}' permissions={self.permissions}>"
        pass
    pass

# Private
class PartialDMChannel(PartialChannel, discord.PartialMessageable):
    def __init__(self, state : ConnectionState, data : dict[str,Any],*unused):
        channelType = discord.enums.try_enum(ChannelType,data["type"])
        discord.PartialMessageable.__init__(self,state,int(data["id"]),channelType)
        PartialChannel.__init__(self,data)
        pass

    def __repr__(self):
        return f"<PartialDMChannel id={self.id} name='{self.name}' permissions={self.permissions}>"
        pass
    pass

class PartialGroupChannel(PartialChannel, discord.PartialMessageable):
    def __init__(self, state : ConnectionState, data : dict[str,Any],*unused):
        channelType = discord.enums.try_enum(ChannelType,data["type"])
        discord.PartialMessageable.__init__(self,state,int(data["id"]),channelType)
        PartialChannel.__init__(self,data)
        pass

    def __repr__(self):
        return f"<PartialGroupChannel id={self.id} name='{self.name}' permissions={self.permissions}>"
        pass
    pass

# Guild
class PartialGuildChannel(PartialChannel):
    def __init__(self, state : ConnectionState,data : dict[str,Any],guild : discord.Guild,*unused):
        super().__init__(data)
        self.category_id = int(data["parent_id"]) if "parent_id" in data.keys() else None

        self.guild = guild
        self._state = state
        pass

    def __repr__(self):
        return f"<PartialGuildChannel guild={self.guild} type={self.type} id={self.id} name='{self.name}' permissions={self.permissions} category_id={self.category_id}"
        pass
    pass

class PartialCategoryChannel(PartialGuildChannel):
    def __init__(self, state : ConnectionState, data : dict[str,Any], guild : discord.Guild, *unused):
        super().__init__(state,data,guild)
        pass

    def __repr__(self):
        return f"<PartialCategoryChannel id={self.id} name='{self.name}' permissions={self.permissions}>"
        pass
    pass

class PartialTextChannel(PartialGuildChannel, discord.PartialMessageable):
    def __init__(self, state : ConnectionState, data : dict[str,Any], guild : discord.Guild, *unused):
        channelType = discord.enums.try_enum(ChannelType,data["type"])
        discord.PartialMessageable.__init__(self,state,int(data["id"]),channelType)
        PartialGuildChannel.__init__(self,state,data,guild)
        pass

    def __repr__(self):
        return f"<PartialTextChannel id={self.id} name='{self.name}' permissions={self.permissions} category_id={self.category_id}>"
        pass

    def is_news(self):
        return self.type == ChannelType.news
        pass
    pass

class PartialStoreChannel(PartialGuildChannel, discord.PartialMessageable):
    def __init__(self, state : ConnectionState, data : dict[str,Any], guild : discord.Guild, *unused):
        discord.PartialMessageable.__init__(self,state,int(data["id"]),ChannelType.store)
        PartialGuildChannel.__init__(self,state,data,guild)
        pass

    def __repr__(self):
        return super().__repr__().replace("PartialGuildChannel","PartialStoreChannel")
        pass
    pass

## Threads

class PartialThread(discord.PartialMessageable):
    def __init__(self, state : ConnectionState, data : dict[str,Any], guild : discord.Guild, *unused):
        channelType = discord.enums.try_enum(ChannelType,data["type"])
        discord.PartialMessageable.__init__(self,state,int(data["id"]),channelType)

        self.id = int(data["id"])
        self.name = data["name"]
        self.permissions = discord.Permissions(int(data.get("permissions",0)))
        self.guild = guild
        self.parent_id = int(data["parent_id"]) if "parent_id" in data.keys() else None

        
        # Metadata (Yay!)
        meta = data["thread_metadata"]
        self.locked = meta["locked"]
        self.auto_archive_minutes = meta["auto_archive_duration"]
        
        self.archived = meta["archived"]
        pyTimestamp = "".join((meta["archive_timestamp"][:meta["archive_timestamp"].find(".")],meta["archive_timestamp"][meta["archive_timestamp"].find(".")+7:])) # Remove microseconds because strptime can't interpret those and they are basically unneccessary. Weird fix, I know
        self.archived_at = datetime.strptime(pyTimestamp,"%Y-%m-%dT%H:%M:%S%z")

        pass

    def is_archived(self):
        return self.archived

    def __repr__(self):
        return f"<PartialThread id={self.id} name={self.name} permissions={self.permissions}>"
        pass
    pass

## Voice variants

class PartialVoiceChannel(PartialGuildChannel):
    def __init__(self, state : ConnectionState, data : dict[str,Any], guild : discord.Guild, *unused):
        super().__init__(state,data,guild)
        pass

    def __repr__(self):
        return super().__repr__().replace("PartialGuildChannel","PartialVoiceChannel",1)
    pass

class PartialStageChannel(PartialGuildChannel):
    def __init__(self, state : ConnectionState, data : dict[str,Any], guild : discord.Guild, *unused):
        super().__init__(state,data,guild)
    
    def __repr__(self):
        return super().__repr__().replace("PartialGuildChannel","PartialStageChannel")
        pass
    pass


# Factories
## Only includes guild_channels (meaning category, text, voice, stage)
def _partial_guild_channel_factory(channel_type : int):
    value = discord.enums.try_enum(ChannelType,channel_type)
    if value is ChannelType.category:
        return PartialCategoryChannel, value
    elif value is ChannelType.text:
        return PartialTextChannel, value
    elif value is ChannelType.voice:
        return PartialVoiceChannel, value
    elif value is ChannelType.news:
        return PartialTextChannel, value
    elif value is ChannelType.store:
        return PartialStoreChannel, value
    elif value is ChannelType.stage_voice:
        return PartialStageChannel, value
    else:
        return None, value
    pass

## Does not include threads but everything else
def _partial_channel_factory(channel_type : int):
    cls, value = _partial_guild_channel_factory(channel_type)
    if value is ChannelType.private:
        return PartialDMChannel, value
    elif value is ChannelType.group:
        return PartialGroupChannel, value
    else:
        return cls, value
    pass

## This one if only guild channels are expected (does not include DMChannels or GroupChannels)
def _partial_threaded_guild_channel_factory(channel_type : int):
    cls, value = _partial_guild_channel_factory(channel_type)
    if value in (ChannelType.private_thread,ChannelType.public_thread,ChannelType.news_thread):
        return PartialThread, value
    else:
        return cls, value
    pass

## This one for max support (includes DMChannels & GroupChannels as well)
def _partial_threaded_channel_factory(channel_type : int):
    cls, value = _partial_channel_factory(channel_type)
    if value in (ChannelType.private_thread,ChannelType.public_thread,ChannelType.news_thread):
        return PartialThread, value
    else:
        return cls, value