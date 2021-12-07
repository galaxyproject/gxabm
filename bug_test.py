import bioblend.galaxy
from pprint import pprint
import os
import sys


def findall(text, lines):
    result = []
    for line in lines:
        if text in line:
            result.append(line)
    return result


def waitfor(pod: str):
    pass


def main():
    with open(os.path.expanduser("/tmp/data.txt")) as f:
        data = f.read()
    lines = data.split('\n')
    print(len(lines))
    jobs = findall('galaxy-job', lines)
    print(len(jobs))
    for job in jobs:
        tokens = job.split()
        print(len(tokens))
        print(tokens)


if __name__ == '__main__':
    main()