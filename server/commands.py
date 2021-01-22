from __future__ import annotations

import logging
import random
from typing import List, Optional, Callable
from typing import TYPE_CHECKING

import constants

if TYPE_CHECKING:
    from server.handler import Client

logger = logging.getLogger('commands')
logger.setLevel(logging.DEBUG)


class CommandHandler:
    """
    The CommandHandler class does exactly what it says: it handles commands.

    This class integrates with the Client class
    """

    def __init__(self, client: Client) -> None:
        self.client = client
        self.aliases = {}
        self.commands = {}
        self.__install_command(self.reroll, 'Reroll', 'reroll', 'Change your color to a random color.',
                               aliases=['newcolor'])
        self.__install_command(self.help, 'Help', 'help', 'Get info on a given commands functionality and more.',
                               aliases=['about', 'doc'])

    def __install_command(self, func: Callable, name: str = None, command_name: str = None, description: str = '',
                          aliases: List[str] = None):
        if aliases is None:
            aliases = []

        name = name or func.__name__.capitalize()
        command_name = (command_name or func.__name__).lower()

        for alias in aliases:
            self.aliases[alias] = command_name

        self.commands[command_name] = {
            'func': func,
            'command': command_name,
            'name': name or func.__name__,
            'description': description,
            'aliases': aliases
        }

    def process(self, arguments: List[str]) -> Optional[str]:
        """
        Processes a single command issued by the given client.

        :param arguments: A full list of arguments with at least one element, beginning with the name of the command.
        :return: A optional simple return message. The command can also issue messages itself, but this is the quicker method.
        """
        if len(arguments) == 0:
            logger.error('CommandHandler.process() was called with zero arguments (no command given)')
            return 'Error while processing command.'
        else:
            try:
                if arguments[0] in self.commands.keys():
                    command_func = self.commands[arguments[0]].get('func')
                    return command_func(*arguments[1:])
                elif arguments[0] in self.aliases.keys():
                    command = self.aliases[arguments[0]]
                    command_func = self.commands[command].get('func')
                    return command_func(*arguments[1:])
                else:
                    return f'Command "{arguments[0]}" does not exist.'
            except Exception as e:
                logger.error(f'Could not process client {self.client.nickname}\'s command request.', exc_info=e)
                return 'A fatal error occurred while trying to process this command.'

    def reroll(self, minimum_contrast: float = constants.MINIMUM_CONTRAST) -> str:
        """
        Randomly change the client's color to a different color.
        """
        i = 0
        new_color = self.client.color
        choices = constants.Colors.has_contrast(float(minimum_contrast))

        while i < 50 and new_color == self.client.color:
            new_color = random.choice(choices)

        self.client.color = new_color
        contrast = round(constants.Colors.WHITE.contrast_ratio(new_color), 1)
        return f'Changed your color to {new_color.name} ({new_color.hex}/{contrast})'

    def help(self, command: str = None) -> Optional[str]:
        """
        Print information about a given command
        :return:
        """
        if command is None:
            return f"'help' requires 1 argument (command: str)."

        if command in self.aliases.keys():
            command = self.aliases[command]

        if command in self.commands.keys():
            info: dict = self.commands[command]

            if 'description' in info.keys() or 'aliases' in info.keys():
                self.client.broadcast_message(f"<b>{info['name']}</b> (/{info['command']})")
                if info.get('description'):
                    self.client.broadcast_message(f"Description: {info['description']}")
                if info.get('aliases'):
                    alias_formatting = ', '.join(f'<i>{alias}</i>' for alias in info["aliases"])
                    self.client.broadcast_message(f"Aliases: {alias_formatting}")

            return None
        else:
            return f'Command "{command}" does not exist.'
