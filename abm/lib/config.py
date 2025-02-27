import os
from pathlib import Path

import yaml
from common import (Context, find_config, get_yaml_parser, load_profiles,
                    print_json, print_yaml, save_config, save_profiles)


def do_list(context: Context, args: list):
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
    profile = {"url": "", "key": "", "kube": args[1]}
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
    profile["key"] = key
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
    profile["url"] = url
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
    # userfile = os.path.join(Path.home(), ".abm", "workflows.yml")
    userfile = find_config("workflows.yml")
    if userfile is None:
        print("ERROR: this instance has not been configured to import workflows.")
        return
    workflows = _load_config(userfile)
    if workflows is None:
        return
    save = False
    if len(args) == 0 or args[0] in ["list", "ls"]:
        print(f"Workflows defined in {userfile}")
        for key, url in workflows.items():
            print(f"{key:10} {url}")
    elif args[0] in ["delete", "del", "rm"]:
        if len(args) != 2:
            print("USAGE: abm config workflows delete <workflow>")
            return
        id = args[1]
        if id not in workflows:
            print(f"ERROR: No such workflow {id}")
            return
        url = workflows[id]
        del workflows[id]
        print(f"Removed workflow {id} -> {url}.")
        save = True
    elif args[0] in ["add", "new"]:
        if len(args) != 3:
            print("USAGE: abm config workflows add <workflow> <url>")
            return
        id = args[1]
        if id in workflows:
            print(f"ERROR: Workflow {id} already exists.")
            return
        url = args[2]
        workflows[id] = url
        print(f"Added workflow {id} -> {url}.")
        save = True
    else:
        print(f"ERROR: Unrecognized command {args[0]}")
    if save:
        save_config(userfile, workflows)


def datasets(context: Context, args: list):
    # userfile = os.path.join(Path.home(), ".abm", "datasets.yml")
    userfile = find_config("datasets.yml")
    if userfile is None:
        print("ERROR: this instance has not been configured to import datasets.")
        return
    datasets = _load_config(userfile)
    if datasets is None:
        return
    save = False
    if len(args) == 0 or args[0] in ["list", "ls"]:
        print(f"Datasets defined in {userfile}")
        for key, url in datasets.items():
            print(f"{key:10} {url}")
    elif args[0] in ["delete", "del", "rm"]:
        id = args[1]
        if id not in datasets:
            print(f"ERROR: No such dataset {id}")
            return
        url = datasets[id]
        del datasets[id]
        print(f"Removed dataset {id} -> {url}.")
        save = True
    elif args[0] in ["add", "new"]:
        if len(args) != 3:
            print("USAGE: abm config datasets add <dataset> <url>")
            return
        id = args[1]
        if id in datasets:
            print(f"ERROR: Dataset {id} already exists.")
            return
        url = args[2]
        datasets[id] = url
        print(f"Added dataset {id} -> {url}.")
        save = True
    else:
        print(f"ERROR: Unrecognized command {args[0]}")
    if save:
        save_config(userfile, datasets)


def histories(context: Context, args: list):
    userfile = find_config("histories.yml")
    if userfile is None:
        print("ERROR: this instance has not been configured to import histories.")
        return
    histories = _load_config(userfile)
    if histories is None:
        return
    save = False
    if len(args) == 0 or args[0] in ["list", "ls"]:
        print(f"Datasets defined in {userfile}")
        for key, url in histories.items():
            print(f"{key:10} {url}")
    elif args[0] in ["delete", "del", "rm"]:
        if len(args) != 2:
            print("USAGE: abm config histories delete <history>")
            return
        id = args[1]
        if id not in histories:
            print(f"ERROR: No such history {id}")
            return
        url = histories[id]
        del histories[id]
        save = True
        print(f"Removed history {id} -> {url}.")
    elif args[0] in ["add", "new"]:
        if len(args) != 3:
            print("USAGE: abm config histories add <history> <url>")
            return
        id = args[1]
        if id in histories:
            print(f"ERROR: History {id} already exists.")
            return
        url = args[2]
        histories[id] = url
        print(f"Added history {id} -> {url}.")
        save = True
    else:
        print(f"ERROR: Unrecognized command {args[0]}")
    if save:
        save_config(userfile, histories)


def _load_config(filepath):
    if not os.path.exists(filepath):
        print(f"ERROR: configuration file not found: {filepath}")
        return None
    with open(filepath, "r") as f:
        return yaml.safe_load(f)
