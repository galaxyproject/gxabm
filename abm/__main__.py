#!/usr/bin/env python3

"""
The Automated Benchmarking Tool

Copyright 2021 The Galaxy Project. All rights reserved.

"""

import common
from common import connect
import job
import dataset
import workflow
import history
import library
import folder
import yaml
import json
import sys
import os

from pprint import pprint

VERSION = '1.1.0'

BOLD = '\033[1m'
CLEAR = '\033[0m'

PROFILE_SEARCH_PATH = ['~/.abm/profile.yml', '.abm-profile.yml']

def bold(text: str):
    """
    Wraps the text in ANSI control sequences to generate bold text in the terminal.

    :param text: the text to be made bold
    :return: the original string wrapped in ANSI control sequences
    """
    return f"{BOLD}{text}{CLEAR}"


help_args = ['help', '-h', '--help']

def head(text):
    print(bold(text))

def command_list(commands:list):
    return '|'.join(bold(c) for c in commands)

def print_main_help(menu_data):
    print()
    head("SYNOPSIS")
    print("    Workflow and data management for remote Galaxy instances")
    print()
    head("USAGE")
    print(f"    {sys.argv[0]} COMMAND [SUBCOMMAND] [OPTIONS]")
    print()
    head("COMMANDS")
    for menu_item in menu_data:
        print(f"    {command_list(menu_item['name'])}")
        print(f"        {menu_item['help']}")
    print(f"    {command_list(['version', '-v', '--version'])}")
    print("        print the program version and exit")
    print(f"    {command_list(help_args)}")
    print("        print this help screen and exit")
    print()
    head("NOTES")
    print(f"    Available SUBCOMMANDS and OPTIONS depend on the command. Use the {bold('help')} subcommand")
    print(f"    to learn more about each of the commands\n")
    print("    Copyright 2021 The Galaxy Project\n")

def print_help(menu_data, command):
    submenu = None
    for menu_item in menu_data:
        if command in menu_item['name']:
            submenu = menu_item
            break
    if submenu is None:
        #print_main_help(menu_data)
        print(f"No help for {command} is available")
        return

    print()
    head("SYNOPSIS")
    print(f"    {submenu['help']}\n")
    head("SUBCOMMANDS")
    for menu_item in submenu['menu']:
        print(f"    {'|'.join(bold(x) for x in menu_item['name'])} {menu_item['params'] if 'params' in menu_item else ''}")
        print(f"        {menu_item['help']}")
    print(f"    {bold('help')}")
    print("        print this help screen and exit")
    print()
    print("    Copyright 2021 The Galaxy Project\n")



# def create_rev_index(gi):
#     wfindex = dict()
#     for workflow in gi.workflows.get_workflows(published=True):
#         # pprint(workflow)
#         # wfindex[workflow[Keys.NAME]] = workflow['id']
#         wfindex[workflow['id']] = workflow[Keys.NAME]
#         print(f"Index workflow {workflow['id']} ")
#     # index['workflow'] = wfindex
#     dsindex = dict()
#     for dataset in gi.datasets.get_datasets(limit=1000, deleted=True, purged=False, ):
#         # dsindex[dataset[Keys.NAME]] = dataset['id']
#         dsindex[dataset['id']] = dataset[Keys.NAME]
#         print(f"index dataset {dataset['id']}")
#     # index['dataset'] = dsindex
#     return wfindex, dsindex
#
#
# def create_index(gi):
#     wfindex = dict()
#     for workflow in gi.workflows.get_workflows(published=True):
#         # pprint(workflow)
#         wfindex[workflow[Keys.NAME]] = workflow['id']
#         print(f"Index {workflow[Keys.NAME]} = {workflow['id']}")
#     # index['workflow'] = wfindex
#     dsindex = dict()
#     for dataset in gi.datasets.get_datasets(limit=1000, deleted=False, purged=False):
#         dsindex[dataset[Keys.NAME]] = dataset['id']
#     # index['dataset'] = dsindex
#     return wfindex, dsindex



all_commands = {}


def parse_profile(profile_name: str):
    profiles = None
    for profile_path in PROFILE_SEARCH_PATH:
        profile_path = os.path.expanduser(profile_path)
        if os.path.exists(profile_path):
            with open(profile_path, 'r') as f:
                # print(f'Loading profile from {profile_path}')
                profiles = yaml.safe_load(f)
            break
    if profiles is None:
        print(f'ERROR: Could not locate an abm profile file in {PROFILE_SEARCH_PATH}')
        return None, None
    if profile_name not in profiles:
        print(f'ERROR: {profile_name} is not the name of a valid profile.')
        print(f'The defined profile names are {profiles.keys()}')
        return None, None
    profile = profiles[profile_name]
    return (profile['url'], profile['key'])


def get_menu(name: str):
    if name in all_commands:
        return all_commands[name]
    menu = dict()
    all_commands[name] = menu
    return menu


def register_handler(name: str, commands: list, handler):
    menu = get_menu(name)
    for command in commands:
        menu[command] = handler


def alias(shortcut, fullname):
    all_commands[shortcut] = all_commands[fullname]


def parse_menu():
    menu_config = f'{os.path.dirname(__file__)}/menu.yml'
    if not os.path.exists(menu_config):
        print(f"ERROR: Unable to load the menu configuration from {menu_config}")
        sys.exit(1)
    with open(menu_config) as f:
        menu_data = yaml.safe_load(f)
    for main_menu_item in menu_data:
        # Use the first name in the list as the main name for the item. The
        # others will be aliased below.
        name = main_menu_item['name'][0]
        for submenu_item in main_menu_item['menu']:
            handler = globals()
            handler_name = submenu_item['handler']
            for part in handler_name.split('.'):
                if type(handler) is not dict:
                    handler = handler.__dict__
                handler = handler[part]
            if type(handler) == 'dict':
                print(f"Handler not found {handler_name}")
                sys.exit(1)
            register_handler(name, submenu_item['name'], handler)
        for command_alias in main_menu_item['name'][1:]:
            alias(command_alias, name)
    return menu_data

def version():
    print()
    print(f"    Galaxy Automated Benchmarking v{VERSION}")
    print(f"    Copyright 2021 The Galaxy Project. All Rights Reserved.\n")


def main():
    menu_data = parse_menu()

    if len(sys.argv) < 2 or sys.argv[1] in help_args:
        print_main_help(menu_data)
        return

    version_args = ['-v', '--version', 'version']
    program = sys.argv[0]
    profile = sys.argv[1]
    if profile in version_args:
        version()
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


    common.GALAXY_SERVER, common.API_KEY = parse_profile(profile)
    if common.GALAXY_SERVER is None:
        return
    if command in all_commands:
        subcommands = all_commands[command]
        if subcommand not in subcommands:
            print(f'ERROR: unrecognized subcommand "{subcommand}"')
            print(f'Type "{program} {command} help" for more help.')
            return
        # print(f'Dispatching "{command} {subcommand}"')
        handler = subcommands[subcommand]
        handler(params)
    else:
        print(f'\n{bold("ERROR:")} Unknown command {bold("{command}")}')
        print_main_help(menu_data)


if __name__ == '__main__':
    main()
