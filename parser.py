import io
import os
import sys
import yaml
import json
import argparse
# from abm import *

class MenuItem:
    def __init__(self, name, help=None, handler=None):
        self.name = name
        self.help = help
        self.handler = handler

help_args = ['help', '-h', '--help']

def bold(text:str):
    """
    Wraps the text in ANSI control sequences to generate bold text in the terminal.

    :param text: the text to be made bold
    :return: the original string wrapped in ANSI control sequences
    """
    return f"\033[1m{text}\033[0m"

def head(text):
    print(bold(text))

def print_main_help(menu_data):
    head("SYNOPSIS")
    print("    Workflow and data management for remote Galaxy instances")
    print()
    head("USAGE")
    print(f"    {sys.argv[0]} COMMAND [SUBCOMMAND] [OPTIONS]")
    print()
    head("COMMANDS")
    for menu_item in menu_data:
        print(f"    {'|'.join(bold(x) for x in menu_item['name'])}")
        print(f"        {menu_item['help']}")
    print(f"    {bold('help')}")
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
        print_main_help(menu_data)

    head("SYNOPSIS")
    print(f"    {menu_item['help']}\n")
    head("SUBCOMMANDS")
    for menu_item in submenu['menu']:
        print(f"    {'|'.join(bold(x) for x in menu_item['name'])} {menu_item['params'] if 'params' in menu_item else ''}")
        print(f"        {menu_item['help']}")
    print(f"    {bold('help')}")
    print("        print this help screen and exit")
    print()
    print("    Copyright 2021 The Galaxy Project")

def main(args = sys.argv):
    with open('menu.yml') as f:
        menu_data = yaml.safe_load(f)

    main_menu = dict()
    for main_menu_item in menu_data:
        submenu = dict()
        for name in main_menu_item['name']:
            main_menu[name] = submenu
        for submenu_item in main_menu_item['menu']:
            # handler = globals()[submenu_item['handler']]
            handler = submenu_item['handler']
            for item_name in submenu_item['name']:
                submenu[item_name] = handler

    command = args[0]
    subcommand = args[1]
    if command == 'help':
        print_main_help(menu_data)
        return

    if subcommand in help_args:
        print_help(menu_data, command)
        return

    submenu = main_menu[command]
    handler = submenu[subcommand]
    print(f"Calling {handler}")


    # print("COMMANDS\n")
    # for menu in menu_data:
    #     print(f"{' | '.join(menu['name'])}")
    #     if 'help' in menu:
    #         print(f"\t{menu['help']}")

def register_handlers():
    with open('menu.yml') as f:
        main_menu = yaml.safe_load(f)

    for menu in main_menu:
        for item in menu['menu']:
            print(f"register_handler(\"{menu['name'][0]}\", {item['name']}, {item['handler']})")

def as_json():
    with open('menu.yml') as f:
        main_menu = yaml.safe_load(f)

    print(json.dumps(main_menu, indent=4))


def _main(argv=sys.argv):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='commands', dest='command')

    wf = subparsers.add_parser("workflow")
    wfparsers = wf.add_subparsers(help='manager workflows', dest='action')

    ds = subparsers.add_parser("dataset")
    lib = subparsers.add_parser("library")

    # wfp = wf.add_subparsers()
    # wfp_list = wfp.add_parser("list")
    # wfp_list.add_argument("id", action='store')
    # wfp_download = wfp.add_parser("download")
    # wfp_download.add_argument("id", action='store')
    #
    # dsp = ds.add_subparsers()
    # dps_list = dsp.add_parser("list")

    options, args = parser.parse_known_args(argv)
    print(options, args)


if __name__ == '__main__':
    # register_handlers()
    main('hist help'.split())

