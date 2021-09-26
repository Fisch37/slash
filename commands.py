if __name__=="__main__": raise RuntimeError("This module cannot be executed as regular code")
from .util import definite_guild_id
from typing import *
import discord, json, dataclasses, re, inspect
import discord.http


SLASH_COMMAND = 1
USER_COMMAND = 2 # Command available via the apps section in a user menu
MESSAGE_COMMAND = 3 # Command available via the apps section in a message menu

SUB_COMMAND = 1
SUB_COMMAND_GROUP = 2

STRING = 3
INTEGER = 4
BOOLEAN = 5
USER = 6
CHANNEL = 7
ROLE = 8
MENTIONABLE = 9
NUMBER = 10

TYPES =                (SUB_COMMAND,SUB_COMMAND_GROUP,STRING,INTEGER,BOOLEAN,USER,CHANNEL,ROLE,MENTIONABLE,NUMBER)
AppOptionType = Literal[SUB_COMMAND,SUB_COMMAND_GROUP,STRING,INTEGER,BOOLEAN,USER,CHANNEL,ROLE,MENTIONABLE,NUMBER]
OPTION_REGEX = r"^[\w-]{1,32}$"
OPTION_TYPE_STRING = {
    SUB_COMMAND : "SUB_COMMAND",
    SUB_COMMAND_GROUP : "SUB_COMMAND_GROUP",
    STRING : "STRING",
    INTEGER : "INTEGER",
    BOOLEAN : "BOOLEAN",
    USER : "USER",
    CHANNEL : "CHANNEL",
    ROLE : "ROLE",
    MENTIONABLE : "MENTIONABLE",
    NUMBER : "NUMBER"
}

GUILD_CMD_BASE = "/applications/{app_id}/guilds/{guild_id}/commands"
GLOBAL_CMD_BASE= "/applications/{app_id}/commands"

GUILD_CMD_EDIT = "/applications/{app_id}/guilds/{guild_id}/commands/{command_id}"
GLOBAL_CMD_EDIT= "/applications/{app_id}/commands/{command_id}"

SPECIFIC_PERM = "/applications/{app_id}/guilds/{guild_id}/commands/{command_id}/permissions"
ALL_PERM = "/applications/{app_id}/guilds/{guild_id}/commands/permissions"


# Command Option Stuff
@dataclasses.dataclass(frozen=True,unsafe_hash=False,eq=True)
class AppOptionChoice:
    name : str
    value : Union[str,int,float]
    def __post_init__(self):
        if not len(self.name) in range(1,100):
            raise ValueError("property name must be a string within the length range of (1,100)")
            pass
        if not isinstance(self.value,(str,int,float)):
            raise ValueError(f"property value can only be of type str, int, or float (was {type(self.value)})")
            pass
        pass

    def as_dict(self) -> dict[str,Union[str,int,float]]:
        return {"name":self.name,"value":self.value}
        pass
    def __repr__(self) -> str:
        return f"<AppOptionChoice name:{self.name};value:{self.value}>"
        pass
    def __str__(self) -> str:
        return json.dumps(self.as_dict())
        pass
    pass

@dataclasses.dataclass(frozen=True,unsafe_hash=False,eq=True)
class AppCommandOption:
    type : AppOptionType
    name : str
    description : str
    required : bool = False
    choices : Iterable[AppOptionChoice] = None

    def __post_init__(self):
        if not self.type in TYPES:
            raise ValueError("type property has to be one of AppOptionType")
            pass
        if not isinstance(self.name,str) or re.search(OPTION_REGEX,self.name) is None and self.name.lower() != self.name:
            raise ValueError("option name must be all lowercase with no special characters, between 1 and 32 characters long, and of type str (one of those is wrong)")
            pass
        if not len(self.description) in range(1,100):
            raise ValueError("option description must be within 1 and 100 characters")
        if not isinstance(self.required,bool):
            raise ValueError("required must be a boolean True or False (default is False)")
            pass
        if self.choices is not None:
            if not all([isinstance(choice,AppOptionChoice) for choice in self.choices]):
                raise ValueError("OptionChoices must be of type AppOptionChoice")
                pass
            pass
        pass

    def __eq__(self, o: object) -> bool:
        if type(self) is not type(o): raise NotImplementedError(f"Can only compare two instances of AppCommandOption, other was {type(o)}")
        return self.type == o.type and self.name == o.name and self.description == o.description and self.required is o.required and self.choices == o.choices
        pass

    def as_dict(self) -> dict[str,Union[AppOptionType,str,bool,Iterable[dict[str,Union[str,int,float]]]]]:
        dictionary = {"type":self.type,"name":self.name,"description":self.description,"required":self.required}
        if self.choices is not None: dictionary["choices"] = [choice.as_dict() for choice in self.choices]
        return dictionary
        pass
    def __repr__(self) -> str:
        return f"""<AppCommandOption
        type:{OPTION_TYPE_STRING[self.type]}
        name:{self.name}
        description:{self.description}
        choices:{repr(self.choices)}
        >"""
        pass
    def __str__(self) -> str:
        return json.dumps(self.as_dict())
        pass
    pass

class CommandOptions:
    def __init__(self,options : Iterable[AppCommandOption]):
        allRequired = True
        for option in options:
            if not allRequired and option.required:
                raise ValueError("Required option cannot come after optional option")
                pass
            allRequired = option.required
        self._options = options
        pass

    @classmethod
    def from_raw(cls, iterable : Iterable[dict[str,Any]]):
        if iterable is None:
            return cls(tuple())
        options = []
        for raw in iterable:
            raw.setdefault("required",False)
            rawChoices : Iterable[dict[str,Union[str,int,float]]] = raw.get("choices")
            if rawChoices is not None:
                choices = tuple([AppOptionChoice(rawchoice.get("name"),rawchoice.get("value")) for rawchoice in rawChoices])
            else:
                choices = None
            options.append(AppCommandOption(raw.get("type"),raw.get("name"),raw.get("description"),raw.get("required"),choices))
            pass
        options = tuple(options)

        return cls(options)
        pass

    def __repr__(self):
        return f"""<CommandOptions {repr(self._options)}>"""
        pass

    def comprehend(self) -> tuple[dict[str,Union[AppOptionType,str,bool,Iterable[dict[str,Union[str,int,float]]]]]]:
        return tuple([option.as_dict() for option in self._options])
        pass

    def __eq__(self, o):
        if not isinstance(o,self.__class__): return False

        if len(self._options) != len(o._options):
            return False
        return all([self._options[i] == o._options[i] for i in range(len(self._options))])
        pass
    pass

# Permissions system

RawPermissionRule = dict[Union[Literal["type"],Literal["id"],Literal["permission"]],Union[int,Union[str,int],bool]]
PermissionRule = dict[Union[Literal["type"],Literal["id"],Literal["permission"]], Union[int,int,bool]]

class CommandPermissions:
    """Unfinished, don't use """
    def __init__(self,*,rules : Optional[dict[int,PermissionRule]] = None):
        self.rules : dict[int,PermissionRule] = {} if rules is None else rules.copy()
        pass

    def set_raw_rule(self, rule : RawPermissionRule):
        ruleType = rule["type"]
        ruleTarget = int(rule["id"])
        ruleSetting = rule["permission"]

        self.rules[ruleTarget] = {"type":ruleType,"id":ruleTarget,"permission":ruleSetting}
        pass
    
    def set_rule(self, target : Union[discord.Member,discord.Role, tuple], setting : bool):
        if isinstance(target,discord.Role):
            raw_rule_type = 1
            raw_target = target.id
            pass
        elif isinstance(target,discord.Member):
            raw_rule_type = 2
            raw_target = target.id
            pass
        elif isinstance(target,tuple) and len(target) == 2:
            raw_rule_type = target[0]
            raw_target = target[1]
            pass
        else:
            raise ValueError("Did not receive a valid target. You must provide either a `discord.Role` or `discord.Member` object.")

        self.set_raw_rule({"type":raw_rule_type,"id":raw_target,"permission":setting})
        pass

    def remove_rule(self, rule : RawPermissionRule):
        ruleTarget = int(rule["id"])

        self.rules.pop(ruleTarget)
        pass

    def check_permission(self, member : discord.Member):
        memberRule = self.rules.get(member.id)
        if memberRule is not None:
            return memberRule["permission"]
            pass

        roleIds = [role.id for role in member.guild.roles]
        roleIds.reverse()
        for roleId in roleIds:
            rule = self.rules.get(roleId)
            if rule is None:
                continue
            return rule["permission"]
            pass
        pass

    def to_raw(self) -> Iterable[RawPermissionRule]:
        raw = []
        for ruleTarget, rule in self.rules.items():
            target = str(ruleTarget)
            ruleType = rule["type"]
            setting = rule["permission"]
            raw.append({"type":ruleType, "id":target,"permission":setting})
            pass

        return raw
        pass

    @classmethod
    def from_raw(cls, raw : Iterable[RawPermissionRule]):
        adapted = {}
        for rawRule in raw:
            ruleType = rawRule["type"]
            ruleTarget = int(rawRule["id"])
            ruleSetting = rawRule["permission"]
            adapted[ruleTarget] = {"type":ruleType,"id":ruleTarget,"permission":ruleSetting}
            pass

        return cls(rules=adapted)
        pass
    pass

# Commands
class BaseCommand:
    def __init__(self, name : str, description : str,*, options : CommandOptions = None, guild_id : int = None, default_permission = True, _id : int = None, __func__ : Callable = None,__type__ = SLASH_COMMAND):
        self._differences = {}

        self.id = _id
        self.name = name
        self.description = description
        self.options = options
        self.guild_id = guild_id
        self.default_permission = default_permission
        self.__func__ = __func__

        self.__type__ = __type__

        self._differences = {}
        pass

    async def register(self, application_id : int, http : discord.http.HTTPClient):
        if self.guild_id is not None:
            url = GUILD_CMD_BASE.format(app_id=application_id,guild_id=self.guild_id)
        else:
            url = GLOBAL_CMD_BASE.format(app_id=application_id)

        return await http.request(discord.http.Route("POST",url),json=self.postify())
        pass

    async def update(self, application_id : int, http : discord.http.HTTPClient):
        if not self.is_identified():
            raise RuntimeError("Command has no stored id. Maybe this command hasn't been registered yet?")
            pass
        if self.guild_id is not None:
            url = GUILD_CMD_EDIT.format(app_id = application_id, guild_id = self.guild_id, command_id = self.id)
            pass
        else:
            url = GLOBAL_CMD_EDIT.format(app_id = application_id, command_id = self.id)
            pass

        return await http.request(discord.http.Route("POST",url),json=self.postify())
        pass

    async def delete(self, application_id : int, http : discord.http.HTTPClient):
        if not self.is_identified():
            raise RuntimeError("Command has no stored id. Maybe this command hasn't been registered yet?")
            pass
        if self.guild_id is not None:
            url = GUILD_CMD_EDIT.format(app_id = application_id, guild_id = self.guild_id, command_id = self.id)
            pass
        else:
            url = GLOBAL_CMD_EDIT.format(app_id = application_id, command_id = self.id)
            pass

        return await http.request(discord.http.Route("DELETE",url))
        pass

    async def get_permissions(self, application_id : int, guild : Union[discord.Guild, int], http : discord.http.HTTPClient):
        """Not completed yet"""
        if not self.is_identified():
            raise RuntimeError("Command has no stored id. Maybe this command hasn't been registered yet?")
            pass
        guild_id = definite_guild_id(guild)
        url = SPECIFIC_PERM.format(app_id=application_id,guild_id=guild_id,command_id=self.id)
        
        respJson = await http.request(discord.http.Route("GET",url))

        permissions : Iterable[RawPermissionRule] = respJson["permissions"]

        return CommandPermissions.from_raw(permissions)
        pass

    async def set_permissions(self,application_id : int, guild : Union[discord.Guild, int], http : discord.http.HTTPClient, permissions : CommandPermissions):
        """Not completed"""
        if not self.is_identified():
            raise RuntimeError("Command has no stored id. Maybe this command hasn't been registered yet?")
            pass

        guild_id = definite_guild_id(guild)
        url = SPECIFIC_PERM.format(app_id=application_id,guild_id=guild_id,command_id=self.id)

        await http.request(discord.http.Route("PUT",url),json={"permissions":permissions.to_raw()})
        pass

    def is_identified(self):
        return self.id is not None

    def postify(self):
        dic = {}
        dic["type"] = self.__type__
        dic["name"] = self.name
        if self.description is not None: dic["description"] = self.description
        if self.options is not None: dic["options"] = self.options.comprehend()
        dic["default_permission"] = self.default_permission

        return dic
        pass

    def __setattr__(self, name: str, value: Any) -> None:
        if name not in ("_differences","__func__"):
            if hasattr(self,name) and value != self.__getattribute__(name):
                self._differences[name] = value
                pass
            pass
        super().__setattr__(name,value)
        pass

    def __repr__(self):
        return f"<BaseCommand id={self.id}; name={self.name}; guild_id={self.guild_id}; default_permission={self.default_permission}; options={repr(self.options)}>"
        pass
    pass

class SlashCommand(BaseCommand):
    def __repr__(self):
        return super().__repr__().replace("BaseCommand","SlashCommand",1)
        pass
    pass

class UserCommand(BaseCommand):
    def __init__(self, name : str,*, guild_id : Union[int,None] = None, default_permission : bool = True, _id : Union[int,None] = None, __func__ : Callable = None):
        super().__init__(name,description="",guild_id=guild_id,default_permission=default_permission,_id=_id,__func__=__func__,__type__=USER_COMMAND)
        pass

    def __repr__(self):
        return super().__repr__().replace("BaseCommand","UserCommand",1)
    pass

class MessageCommand(BaseCommand):
    def __init__(self, name : str,*, guild_id : Union[int,None] = None, default_permission : bool = True, _id : Union[int,None] = None, __func__ : Callable = None):
        super().__init__(name,"",guild_id=guild_id,default_permission=default_permission,_id=_id,__func__=__func__,__type__=MESSAGE_COMMAND)
        pass

    def __repr__(self):
        return super().__repr__().replace("BaseCommand","MessageCommand",1)
    pass

Command = Union[SlashCommand,UserCommand,MessageCommand]

# Command Groups

class CommandNest(object):
    """Useful to create nested subcommands / subcommand groups. 
    Inherit from this class to complete the neccessary setup."""

    def __init__(self):
        possible_commands = inspect.getmembers(self, lambda a: inspect.iscoroutinefunction(a) and not a.__name__.startswith("_"))
        _, self.commands = zip(*possible_commands)

        _, self.subcommand_groups = zip(*inspect.getmembers(self, lambda a: inspect.isclass(a) and not a.__name__.startswith("_")))


        pass

    # Singleton behaviour
    _instances = dict()
    def __new__(cls):
        if not cls in cls._instances.keys():
            cls._instances[cls] = object.__new__(cls)
            pass
        return cls._instances[cls]
        pass
    pass

class SubcommandGroup(object):
    """Inherit from this class to create a new Subcommand Group in a CommandNest"""

    def __init__(self):
        possible_commands = inspect.getmembers(self, lambda a: inspect.iscoroutinefunction(a) and not a.__name__.startswith("_"))
        _, self.commands = zip(*possible_commands)
        self.commands : tuple[Callable]
        pass

    # Singleton behaviour
    _instances = dict()
    def __new__(cls):
        if not cls in cls._instances.keys():
            cls._instances[cls] = object.__new__(cls)
            pass
        return cls._instances[cls]
        pass
    pass
discord.Intents.default


def interpretSubcommandSystem(nest : CommandNest):
    nest.subcommand_groups
    pass