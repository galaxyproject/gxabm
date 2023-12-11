import os
from pathlib import Path

import yaml
from common import (Context, get_yaml_parser, load_profiles, print_json,
                    print_yaml, save_profiles)


def list(context: Context, args: list):
    profiles = load_profiles()
    print(f"Loaded {len(profiles)} profiles")
    for profile in profiles:
        print(f"{profile}\t{profiles[profile]['url']}")


def create(context: Context, args: list):
    if len(args) != 2:
        print("USAGE: abm config create <cloud> /path/to/kube.config")
        return
    profile_name = args[0]
    profiles = load_profiles()
    if profile_name in profiles:
        print("ERROR: a cloud configuration with that name already exists.")
        return
    profile = {'url': "", 'key': '', 'kube': args[1]}
    profiles[profile_name] = profile
    save_profiles(profiles)
    print_json(profile)


def remove(context: Context, args: list):
    if len(args) == 0:
        print("USAGE: abm config remove <cloud> [<cloud>...]")
        return
    profiles = load_profiles()
    for profile_name in args:
        if profile_name in profiles:
            del profiles[profile_name]
        else:
            print("ERROR: now cloud configuration with that name.")
    save_profiles(profiles)
    print_yaml(profiles)


def key(context: Context, args: list):
    if len(args) != 2:
        print(f"USAGE: abm config key <cloud> <key>")
        return
    profile_name = args[0]
    key = args[1]
    profiles = load_profiles()
    if not profile_name in profiles:
        print(f"ERROR: Unknown cloud {profile_name}")
        return
    profile = profiles[profile_name]
    profile['key'] = key
    save_profiles(profiles)
    print_json(profile)


def url(context: Context, args: list):
    if len(args) != 2:
        print(f"USAGE: abm config url <cloud> <url>")
        return
    profile_name = args[0]
    url = args[1]
    profiles = load_profiles()
    if not profile_name in profiles:
        print(f"ERROR: Unknown cloud {profile_name}")
        return
    profile = profiles[profile_name]
    profile['url'] = url
    save_profiles(profiles)
    print_json(profile)


def show(context: Context, args: list):
    if len(args) != 1:
        print("USAGE: abm config show <cloud>")
        return
    profiles = load_profiles()
    if args[0] not in profiles:
        print(f"ERROR: No such cloud {args[0]}")
        return
    print_json(profiles[args[0]])


def workflows(context: Context, args: list):
    userfile = os.path.join(Path.home(), ".abm", "workflows.yml")
    if len(args) == 0 or args[0] in ['list', 'ls']:
        workflows = _load_config(userfile)
        if workflows is None:
            return
        print(f"Workflows defined in {userfile}")
        for key, url in workflows.items():
            print(f"{key:10} {url}")
    elif args[0] in ['delete', 'del', 'rm']:
        print(
            f"Deleting workflows is not supported at this time. Please edit {userfile} directly."
        )
    elif args[0] in ['add', 'new']:
        print(
            f"Adding workflows is not supported at this time. Please edit {userfile} directly."
        )
    else:
        print(f"ERROR: Unrecognized command {args[0]}")


def datasets(context: Context, args: list):
    userfile = os.path.join(Path.home(), ".abm", "datasets.yml")
    if len(args) == 0 or args[0] in ['list', 'ls']:
        datasets = _load_config(userfile)
        if datasets is None:
            return
        print(f"Datasets defined in {userfile}")
        for key, url in datasets.items():
            print(f"{key:10} {url}")
    elif args[0] in ['delete', 'del', 'rm']:
        print(
            f"Deleting datasets is not supported at this time. Please edit {userfile} directly."
        )
    elif args[0] in ['add', 'new']:
        print(
            f"Adding datasets is not supported at this time. Please edit {userfile} directly."
        )
    else:
        print(f"ERROR: Unrecognized command {args[0]}")


def histories(context: Context, args: list):
    userfile = os.path.join(Path.home(), ".abm", "histories.yml")
    if len(args) == 0 or args[0] in ['list', 'ls']:
        histories = _load_config(userfile)
        if histories is None:
            return
        print(f"Datasets defined in {userfile}")
        for key, url in histories.items():
            print(f"{key:10} {url}")
    elif args[0] in ['delete', 'del', 'rm']:
        print(
            f"Deleting history entries is not supported at this time. Please edit {userfile} directly."
        )
    elif args[0] in ['add', 'new']:
        print(
            f"Adding dataset entries is not supported at this time. Please edit {userfile} directly."
        )
    else:
        print(f"ERROR: Unrecognized command {args[0]}")


# def _load_dataset_config(configfile):
#     if not os.path.exists(configfile):
#         print("ERROR: this instance has not been configured to import datasets.")
#         print(f"Please configure {configfile} to enable dataset imports.")
#         return None
#     return _load_config(configfile)


# def _load_workflow_config(userfile):
#     if not os.path.exists(userfile):
#         print("ERROR: this instance has not been configured to import workflows.")
#         print(f"Please configure {userfile} to enable workflow imports.")
#         return None
#     return _load_config(userfile)


def _load_config(filepath):
    if not os.path.exists(filepath):
        print(f"ERROR: configuration file not found: {filepath}")
        return None
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)
