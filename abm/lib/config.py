from common import load_profiles, save_profiles, get_yaml_parser, Context

import sys
import json
import lib

from common import print_json, print_yaml

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
    profile = { 'url': "", 'key': '', 'kube': args[1]}
    profiles[profile_name] = profile
    save_profiles(profiles)
    print_json(profile)


def remove(context: Context, args: list):
    if len(args) != 1:
        print("USAGE: abm config remove <cloud>")
        return
    profile_name = args[0]
    profiles = load_profiles()
    if not profile_name in profiles:
        print("ERROR: now cloud configuration with that name.")
        return
    del profiles[profile_name]
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
        print(f"USAGE: abm config key <cloud> <url>")
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
