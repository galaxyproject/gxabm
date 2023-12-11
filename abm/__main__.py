#!/usr/bin/env python3

"""
The Automated Benchmarking Tool

Copyright 2023 The Galaxy Project. All rights reserved.

"""

import logging
import os
import sys
from pprint import pprint

import yaml
# These imports are required because we need Python to be load them to the
# symbol table so the parse_menu method can find them in globals()
from lib import (benchmark, cloudlaunch, config, dataset, experiment, folder,
                 helm, history, invocation, job, kubectl, library, users,
                 workflow)
from lib.common import Context

from abm import getVersion

log = logging.getLogger('abm')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

log.setLevel(logging.ERROR)
handler.setLevel(logging.ERROR)
handler.setFormatter(formatter)
log.addHandler(handler)


# VERSION = '2.0.0-dev'

BOLD = '\033[1m'
CLEAR = '\033[0m'


def bold(text: str):
    """
    Wraps the text in ANSI control sequences to generate bold text in the terminal.

    :param text: the text to be made bold
    :return: the original string wrapped in ANSI control sequences
    """
    return f"{BOLD}{text}{CLEAR}"


help_args = ['help', '-h', '--help']
version_args = ['-v', '--version', 'version']

# Commands that do not depend on a cloud instance
stand_alone_commands = []


def head(text):
    print(bold(text))


def command_list(commands: list):
    return '|'.join(bold(c) for c in commands)


def copyright():
    print(f"    Copyright 2023 The Galaxy Project. All Rights Reserved.\n")


def print_main_help(menu_data):
    print()
    head("    DESCRIPTION")
    print("        Workflow and data management for remote Galaxy instances")
    print()
    head("    SYNOPSIS")
    print(f"        abm COMMAND [SUBCOMMAND] [OPTIONS]")
    print()
    head("    COMMANDS")
    for menu_item in menu_data:
        print(f"        {command_list(menu_item['name'])}")
        print(f"            {menu_item['help']}")
    print(f"        {command_list(['version', '-v', '--version'])}")
    print("            print the program version and exit")
    print(f"        {command_list(help_args)}")
    print("            print this help screen and exit")
    print()
    head("    NOTES")
    print(
        f"        Available SUBCOMMANDS and OPTIONS depend on the command. Use the {bold('help')} subcommand"
    )
    print(f"        to learn more about each of the commands. For example:\n")
    print(f"        $> abm workflow help\n")
    copyright()


def print_help(menu_data, command):
    submenu = None
    for menu_item in menu_data:
        if command in menu_item['name']:
            submenu = menu_item
            break
    if submenu is None:
        # print_main_help(menu_data)
        print(f"No help for {command} is available")
        return

    print()
    head("    SYNOPSIS")
    if submenu['name'][0] in stand_alone_commands:
        print(f"        abm {command} SUBCOMMAND <ARGS>\n")
    else:
        print(f"        abm [cloud] {command} SUBCOMMAND <ARGS>\n")
    head("    DESCRIPTION")
    print(f"        {submenu['help']}\n")
    head("    SUBCOMMANDS")
    for menu_item in submenu['menu']:
        print(
            f"        {'|'.join(bold(x) for x in menu_item['name'])} {menu_item['params'] if 'params' in menu_item else ''}"
        )
        print(f"            {menu_item['help']}")
    print(f"        {bold('help')}")
    print("            print this help screen and exit")
    print()
    copyright()


all_commands = {}


def get_menu(name: str):
    if name in all_commands:
        return all_commands[name]
    menu = dict()
    all_commands[name] = menu
    return menu


def register_handler(name: str, commands: list, handler):
    log.debug("Registering handler for menu: %s", name)
    menu = get_menu(name)
    for command in commands:
        menu[command] = handler


def alias(shortcut, fullname):
    all_commands[shortcut] = all_commands[fullname]


def parse_menu():
    log.debug('parse_menu')
    menu_config = f'{os.path.dirname(os.path.abspath(__file__))}/lib/menu.yml'
    if not os.path.exists(menu_config):
        log.error(f"ERROR: Unable to load the menu configuration from {menu_config}")
        # TODO Throw an exception that can be caught at the appropriate level
        sys.exit(1)
    with open(menu_config) as f:
        menu_data = yaml.safe_load(f)
    for main_menu_item in menu_data:
        # Use the first name in the list as the main name for the item. The
        # others will be aliased below.
        name = main_menu_item['name'][0]
        if main_menu_item.get('standalone', False):
            for item_name in main_menu_item['name']:
                stand_alone_commands.append(item_name)
        log.debug('Menu name: %s', name)
        for submenu_item in main_menu_item['menu']:
            handler = globals()
            handler_name = submenu_item['handler']
            log.debug('Submenu item: %s', handler_name)
            for part in handler_name.split('.'):
                # log.debug("Part: %s", part)
                if type(handler) is not dict:
                    handler = handler.__dict__
                if not part in handler:
                    print(f"ERROR: {part} not found")
                else:
                    handler = handler[part]
            if isinstance(handler, dict):
                log.error(f"Handler not found {handler_name}")
                # TODO Throw and excpetion that can be caught at the appropriate level.
                sys.exit(1)
            register_handler(name, submenu_item['name'], handler)
        for command_alias in main_menu_item['name'][1:]:
            alias(command_alias, name)
    return menu_data


def version():
    version = getVersion()
    print()
    print(f"    Galaxy Automated Benchmarking v{version}")
    copyright()


def _get_logopt(args: list):
    OPTS = ['-log', '--log', '-logging', '--logging']
    for i in range(len(args)):
        if args[i] in OPTS:
            return i
    return -1


def entrypoint():
    # Check if log level is being set
    logopt = _get_logopt(sys.argv)
    if logopt >= 0:
        if logopt + 1 >= len(sys.argv):
            print("ERROR: no log level provided")
            return

        level = sys.argv[logopt + 1].upper()
        if level not in [
            'DEBUG',
            'INFO',
            'WARN',
            'WARNING',
            'ERROR',
            'FATAL',
            'CRITICAL',
        ]:
            print(f"ERROR: Invalid logging level {sys.argv[logopt + 1]}")
            return
        print(f"Setting the log level to {level}")
        log.setLevel(level)
        global handler
        handler.setLevel(level)
        del sys.argv[logopt]
        del sys.argv[logopt]

    menu_data = parse_menu()

    if len(sys.argv) < 2 or sys.argv[1] in help_args:
        print_main_help(menu_data)
        return

    program = sys.argv[0]
    profile = sys.argv[1]
    if profile in version_args:
        version()
        return

    if profile in stand_alone_commands:
        command = profile
        profile = None
        if len(sys.argv) < 3:
            print_help(menu_data, command)
            return
        subcommand = sys.argv[2]
        if len(sys.argv) > 3:
            params = sys.argv[3:]
        else:
            params = []
    else:
        if len(sys.argv) < 3:
            print(f"{bold('ERROR')} Invalid command {bold(profile)}")
            return
        command = sys.argv[2]
        if command in version_args:
            version()
            return
        subcommand = None
        if len(sys.argv) > 3:
            subcommand = sys.argv[3]
        if len(sys.argv) > 4:
            params = sys.argv[4:]
        else:
            params = []

    if command in help_args:
        print_help(menu_data, profile)
        return
    if subcommand and subcommand in help_args:
        print_help(menu_data, command)
        return

    context = None
    if profile is not None:
        context = Context(profile)
    if command in all_commands:
        subcommands = all_commands[command]
        if subcommand not in subcommands:
            print(f'ERROR: unrecognized subcommand "{subcommand}"')
            print(f'Type "{program} {command} help" for more help.')
            return
        handler = subcommands[subcommand]
        handler(context, params)
    else:
        print(f'\n{bold("ERROR:")} Unknown command {bold({command})}')
        print_main_help(menu_data)


if __name__ == '__main__':
    entrypoint()
