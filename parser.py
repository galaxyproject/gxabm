import os
import sys
import yaml
import json


def main():
    with open('menu.yml') as f:
        main_menu = yaml.safe_load(f)

    for menu in main_menu:
        print(f"{menu['name'][0]}_menu = " + '{')
        for item in menu['menu']:
            for name in item['name']:
                print(f"    \"{name}\": {item['handler']},")
        print("}")

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



if __name__ == '__main__':
    register_handlers()


