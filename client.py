if __name__=="__main__": raise RuntimeError("This module cannot be executed as regular code")
from slash_extension.commands import *
from slash_extension.interactions import *
from typing import *
import functools, inspect, time

EMPTY = object()

class KeywordWarning(Warning):
    """Raised if @SlashClient.slash_command finds a keyword only argument"""
    pass

class SlashClient(discord.Client):
    
    # Properties autocommit, slash_commands, user_commands, message_commands
    def __init__(self,*, autocommit : bool = True,**options : Any):
        super().__init__(**options)

        self.autocommit = autocommit

        self.slash_commands   : set[SlashCommand  ] = set()
        self.user_commands    : set[UserCommand   ] = set()
        self.message_commands : set[MessageCommand] = set()

        self.__raw_commands__ : list[dict] = [] # Contains information like this: ("name":str,["description":str],["options":str],"guild_id":int,"default_permission":bool,"func":Callable)

        self.__retrieved_commands__ = False

        self.__on_interaction_listener__ : Callable = None
        self.__on_ready_listener__ : Callable = None

        async def on_interaction(interaction : discord.Interaction):
            # Regular event call
            if self.__on_interaction_listener__ is not None:
                await self.__on_interaction_listener__(interaction)
                pass
            stampStart = time.time()
            # Application Command detection
            for command in self.slash_commands.union(self.user_commands,self.message_commands):
                if command.id == int(interaction.data.get("id")):
                    logging.debug("Found matching command for interaction")
                    if command.__func__ is None:
                        logging.warn("Received interaction that doesn't have a function associated. This shouldn't happen!")
                        break # That still only counts as one!
                        pass

                    interactArg : list[Union[discord.Member,discord.Message]] = []
                    if command.__type__ == USER_COMMAND:
                        interactArg.append(target_from_interaction(interaction))
                        pass
                    elif command.__type__ == MESSAGE_COMMAND:
                        interactArg.append(message_from_interaction(interaction))
                        pass
                    elif command.__type__ == SLASH_COMMAND:
                        interactArg = args_from_interaction(interaction,command.__func__)
                        pass
                    else:
                        interactArg = interaction
                        pass
                    await command.__func__(interaction, *interactArg)
                    break # There can only be one!
                    pass
                pass
            stampEnd = time.time()
            logging.debug(f"Took {stampEnd-stampStart} seconds")
            pass

        async def on_ready():
            if not self.__retrieved_commands__:
                logging.info("Loading application commands. This may take a while")
                slash_commands, user_commands, message_commands = await self.get_application_commands()

                for guild in self.guilds:
                    new_slash, new_user, new_message = await self.get_application_commands(guild)
                    slash_commands  .update(new_slash  )
                    user_commands   .update(new_user   )
                    message_commands.update(new_message)
                    pass

                self.slash_commands  .update(slash_commands  )
                self.user_commands   .update(user_commands   )
                self.message_commands.update(message_commands)
                logging.info(f"Loaded {len(slash_commands)+len(user_commands)+len(message_commands)} application commands")

                logging.info("Applying decorators")
                
                lookup = {(command.__type__,command.name,command.guild_id):command for command in self.slash_commands.union(self.user_commands).union(self.message_commands)} # Create dictionary for finding commands by type, name, and guild
                for raw in self.__raw_commands__: 
                    # Raw is a dictionary with following values: ("type":int,"name":str,["description":str],["options":CommandOptions],"guild_id":int,"default_permission":bool,"func":Callable)
                    cmd_type           = raw["type"]
                    name               = raw["name"]
                    description        = raw["description"]
                    options            = raw.get("options")
                    guild_id           = raw.get("guild_id")
                    default_permission = raw.get("default_permission",False)
                    func               = raw.get("func")

                    command : Union[Command,None] = lookup.get((cmd_type,name,guild_id))
                    if command is None: # Create new command if not already exists
                        if cmd_type == SLASH_COMMAND:
                            self.slash_commands.add(SlashCommand(name,description,options=options,guild_id=guild_id,default_permission=default_permission,__func__=func))
                            pass
                        elif cmd_type == USER_COMMAND:
                            self.user_commands.add(UserCommand(name,guild_id=guild_id,default_permission=default_permission,__func__=func))
                            pass
                        elif cmd_type == MESSAGE_COMMAND:
                            self.message_commands.add(MessageCommand(name,guild_id=guild_id,default_permission=default_permission,__func__=func))
                            pass
                        pass
                    else: # Update existing command object 
                        command.description = description
                        if cmd_type == SLASH_COMMAND: command.options = options
                        command.guild_id = guild_id
                        command.default_permission = default_permission
                        command.__func__ = func
                        pass
                    pass

                if self.autocommit:
                    await self.update_commands()
                self.__retrieved_commands__ = True
                pass

            # Call regular event (if set)
            if self.__on_ready_listener__ is not None:
                await self.__on_ready_listener__()
                pass
            pass

        super().event(on_interaction)
        super().event(on_ready)
        pass

    async def login(self, token : str):
        self.token = token

        return await super().login(token)
        pass

    async def connect(self,*,reconnect : bool = True):
        return await super().connect(reconnect=reconnect)
        pass
    
    # New Functions

    async def command_garbage_collector(self):
        """Deletes all commands from the API that don't have a function associated to it"""
        for command in self.slash_commands.union(self.user_commands,self.message_commands):
            if command.__func__ is None and command.is_identified():
                await self.delete_command(command)
                pass
            pass
        pass

    async def update_commands(self):
        """Commit all changes in commands to the API"""
        if self.application_id is None:
            raise RuntimeError("No Application ID found. Is the client logged in yet?")
            pass

        tasks = []
        for command in self.slash_commands.union(self.user_commands,self.message_commands):
            if len(command._differences.keys()) == 0 and command.is_identified():
                continue
            
            if not command.is_identified():
                tasks.append(asyncio.create_task(command.register(self.application_id,self.token)))
                pass
            else:
                tasks.append(asyncio.create_task(command.update(self.application_id,self.token)))
                pass
            pass

        results = await asyncio.gather(*tasks,return_exceptions=False)
        pass

    async def register_command(self,command : Command) -> BaseCommand:
        """Register a command. Simpler version of `BaseCommand.register`"""
        if self.application_id is None:
            raise RuntimeError("Could not find application_id. Is the client not logged in?")
        return await command.register(self.application_id,self.token)
        pass

    async def delete_command(self,command : Command):
        """Delete a command. Simpler version of `BaseCommand.delete`"""
        if self.application_id is None:
            raise RuntimeError("Could not find application_id. Is the client logged in?")
        
        return await command.delete(self.application_id,self.token)
        pass

    def command_by_name(self,name : str, type : int = "any") -> Command:
        if type == SLASH_COMMAND:     commandSet = self.slash_commands  .copy()
        elif type == USER_COMMAND:    commandSet = self.user_commands   .copy()
        elif type == MESSAGE_COMMAND: commandSet = self.message_commands.copy()
        elif type == "any": commandSet = self.slash_commands.union(self.user_commands,self.message_commands)
        else:
            raise ValueError(f"Could not interpret type {type} (only accepts SLASH_COMMAND, USER_COMMAND, MESSAGE_COMMAND or 'any')")
            pass

        countable = [command.name for command in commandSet]
        lookup = {command.name : command for command in commandSet}
        
        if countable.count(name) > 1:
            raise DuplicationWarning(f"{name} has a duplicate. There are more than 1 of these. Narrow down your type to protect against this.")
            pass

        return lookup.get(name)
        pass


    # Application Command Decorators
    def slash_command(
        self, 
        name : str, 
        *, 
        description : str,
        descriptions : Union[Iterable[str],None] = None, 
        options : Union[CommandOptions,None] = None, 
        guild : Union[discord.Guild,int] = None, 
        availableByDefault : bool = True, 
        __suppress_kw_warning__ : bool = False
        ):

        guild_id = definite_guild_id(guild)
        oldOptions = options

        def outer(func):
            if oldOptions is None: # Get options from args
                argspec = inspect.getfullargspec(func)
                argspec.args.pop(0)
                typeHints = argspec.annotations
                

                if len(argspec.kwonlyargs) > 0 and not __suppress_kw_warning__:
                    raise KeywordWarning("Keyword-only argument found. These arguments will not be interpreted by the decorator. If this is intentional, set __supress_kw_warning__ to True")
                    pass
                
                defaults = argspec.defaults if argspec.defaults is not None else tuple()
                defaultStartingIndex = len(argspec.args) - len(defaults) # Can't have non-default after default ELSE SyntaxError
                defaultsDict = {arg:default for arg, default in zip(argspec.args[defaultStartingIndex:], defaults)}

                raw_options = []
                if (len(descriptions) if descriptions is not None else 0) != len(argspec.args):
                    raise ValueError("You need to give each option a description. Pass `descriptions` an Iterable of strings with the same length as the amount of arguments. Your version was either unset or of a different length.")
                    pass
                for i in range(len(argspec.args)):
                    arg = argspec.args[i]
                    default = defaultsDict.get(arg)
                    typeHint = typeHints.get(arg)
                    optDescription = descriptions[i] if descriptions is not EMPTY else ""
                    if typeHint is None:
                        raise SyntaxError("Invalid type hint. Slash Command options always require a type hint to match. If you do not want to use automated type hints, use the options parameter instead")
                        pass
                    
                    if not isinstance(typeHint,Choices):
                        apiType = REV_TYPE_MATCHER.get(typeHint)
                        if apiType is None:
                            raise TypeError("Unsupported type hint. Check the docs for a list of allowed type hints.")
                            pass

                        option = AppCommandOption(apiType,arg,descriptions[i],default is None)
                        pass
                    else:
                        choices : Choices = typeHint

                        apiType = REV_TYPE_MATCHER.get(choices.type)
                        if apiType is None:
                            raise TypeError("Unsupported type. Check the docs for a list of allowed types.")
                        
                        option = AppCommandOption(apiType,arg,descriptions[i],choices.required,choices.choices)
                        pass
                    raw_options.append(option)
                    pass
                options = CommandOptions(raw_options)
                pass
            else: # Fix some stupid UnboundLocalError in Python 3.9.6 where options is not defined.
                options = oldOptions
                pass

            async def wrapper(*args, **kwargs):
                functools.wraps(func)

                return await func(*args,**kwargs)
                pass
            raw_command = {"type":SLASH_COMMAND,"name":name,"description":description,"options":options,"guild_id":guild_id, "func" : wrapper, "default_permission" : availableByDefault}
            self.__raw_commands__.append(raw_command)
            return wrapper
            pass

        return outer
        pass

    def user_command(self, name : str, *, guild : Union[discord.Guild,int] = None, availableByDefault : bool = True):
        guild_id = definite_guild_id(guild)

        def outer(func):
            async def wrapper(*args,**kwargs):
                functools.wraps(func)

                return await func(*args,**kwargs)
                pass
            raw_command = {"type":USER_COMMAND,"description":"","name":name,"guild_id":guild_id, "func":wrapper, "default_permission":availableByDefault}
            self.__raw_commands__.append(raw_command)

            return wrapper
            pass
        return outer
        pass

    def message_command(self, name : str, *, guild : Union[discord.Guild,int] = None, availableByDefault : bool = True):
        """NOTE: The discord.Message.author is always of type User, not Member"""

        guild_id = definite_guild_id(guild)

        def outer(func):
            async def wrapper(*args,**kwargs):
                functools.wraps(func)

                return await func(*args,**kwargs)
                pass

            raw_command = {"type":MESSAGE_COMMAND,"description":"", "name": name, "guild_id" : guild_id, "func" : wrapper, "default_permission" : availableByDefault}
            self.__raw_commands__.append(raw_command)

            return wrapper
            pass

        return outer
        pass

    # GET Interaction with the Discord API
    async def get_application_commands(self, guild : Union[discord.Guild,int] = None) -> tuple[set[SlashCommand],set[UserCommand],set[MessageCommand]]:
        """Retrieves all application commands.\n
        By default this accesses the global commands, but can be set to only gather guild commands, by passing in the `guild` parameter.\n
        It also will update the internal registers of commands

        Parameters
        ----------
        guild (optional): Set to gather guild only commands. Can be a `discord.Guild` object or a guild_id.

        Returns
        -------
        Three sets containing the following: Slash Commands, User Commands, Message Commands

        Raises
        ------
        (exc)TypeError:     The guild attribute was not set properly.

        (exc)NotFound:      Resource could not be located.
        (exc)Forbidden:     Discord has denied this request.
        (exc)HTTPException: Any other error not mentioned here.
        """
        if guild is None:
            guild_id = None
            pass
        elif isinstance(guild, discord.Guild):
            guild_id = guild.id
            pass
        elif isinstance(guild,int):
            guild_id = guild
            pass
        else:
            raise TypeError("Attribute guild is neither discord.Guild nor a guild_id.")

        if self.user is None: raise discord.errors.ClientException("This client is not logged in. Id could not be retrieved")

        raw_commands = await self.get_raw_app_commands(guild_id)

        slash_commands = set()
        user_commands  = set()
        msg_commands   = set()

        for raw in raw_commands:
            raw : dict
            raw.setdefault("type",SLASH_COMMAND)
            
            type = raw.get("type")

            cmd_id = int(raw.get("id")) if "id" in raw.keys() else None
            app_id = raw.get("application_id")
            cmd_guild_id = int(raw.get("guild_id")) if "guild_id" in raw.keys() else None
            name = raw.get("name")
            description = raw.get("description")
            options = raw.get("options") # Only exists on CHAT_INPUT
            raw.setdefault("default_permission",True); default_perm = raw.get("default_permission")

            if type == SLASH_COMMAND:
                slash_commands.add(
                    SlashCommand(name,description,options=CommandOptions.from_raw(options),guild_id=cmd_guild_id,default_permission=default_perm, _id=cmd_id)
                )
                pass

            elif type == USER_COMMAND:
                user_commands.add(
                    UserCommand(name,guild_id=cmd_guild_id, default_permission=default_perm, _id=cmd_id)
                )
                pass

            elif type == MESSAGE_COMMAND:
                msg_commands.add(
                    MessageCommand(name,guild_id=cmd_guild_id,default_permission=default_perm,_id=cmd_id)
                )
                pass
            else:
                logging.warn("API returned unexpected type, skipping that command")
                continue
            pass

        return slash_commands, user_commands, msg_commands
        pass

    async def get_raw_app_commands(self,guild_id : int = None) -> list[dict]:
        """Should not be called manually"""
        if guild_id is not None:
            url = GUILD_CMD_BASE.format(app_id=self.user.id, guild_id=guild_id)
        else:
            url = GLOBAL_CMD_BASE.format(app_id=self.user.id)
        async with aiohttp.ClientSession() as conn:
            while True:
                async with conn.get(url,headers={"Authorization":f"Bot {self.token}"}) as resp:
                    if resp.status == 429: # Check if being rate limited
                        await asyncio.sleep((await resp.json()).get("retry_after")) # Wait returned amount of time before continuing
                        pass

                    elif resp.status == 404:
                        raise discord.errors.NotFound(resp,f"The API endpoint with for application commands of guild {guild_id} could not be found")
                        pass
                    elif resp.status == 403:
                        raise discord.errors.Forbidden(resp,"This request was forbidden. Is your token invalid?")
                        pass

                    elif resp.status in range(200,300):
                        return await resp.json() # If no rate limit: Return the response json
                        pass

                    else:
                        raise discord.errors.HTTPException(resp,"Unknown error")
                    pass
                pass
            pass
        pass
    
    def event(self,coro : Callable):
        if coro.__name__ == "on_interaction":
            self.__on_interaction_listener__ = coro
            logging.debug(f"Set {coro.__name__} to be called at an on_interaction event")
            pass
        elif coro.__name__ == "on_ready":
            self.__on_ready_listener__ = coro
            logging.debug(f"Set {coro.__name__} to be called at an on_ready event")
            pass
        else:
            super().event(coro)
            pass
        pass
    pass
