import subprocess
import sys
import yaml
import os
import time
import json

from pathlib import Path
path = str(Path(Path(__file__).parent.absolute()).parent.absolute())
sys.path.insert(0, path)
from abm import history, workflow

# Args from yml config files
# use abm as a library to run commands
# take benchmarking config as an input
def main():
  configPath = sys.argv[1]
  profile = None;
  if os.path.exists(configPath):
    with open(configPath, 'r') as f:
      profile = yaml.safe_load(f)
  if profile is None:
    print(f'ERROR: Could not locate an abm profile file in {configPath}')

  clouds = profile['cloud']

  # RNA-paired hist on main: b7a6e3abfe13a9c3
  # RNA-single hist on main: 68c184b7901bc21a
  # DNA-single hist on main: d59d7f1482fd9fd5
  # DNA-paired hist on main: df8b040f22887247

  historyID = ["b7a6e3abfe13a9c3", "68c184b7901bc21a", "d59d7f1482fd9fd5", "df8b040f22887247"]
  workflows = ["de503f2935ac5629", "39f1e01ca3950c18", "313eddf294db855d", "e7234e29592c1dfb"]
  exportURL = []
  
  # export histories from main
  for id in historyID:
    wait_for("main", id)
    result = history.export([id])
    exportURL.append(result)

  # download workflows from js
  for wf in workflows:
    workflow.export([wf, "./workflows"])
    workflow.translate([wf])
  
  # for each instance:
  for cloud in clouds:
    # 	import histories from main
    for url in exportURL:
      history._import([url])

    for filename in os.listdir("./workflow"):
      workflow.validate([filename])
      workflow.upload([filename])


def wait_for(cloud: str, id: str):
  subprocess.run(["python3", "abm", "main", "history", "export", id, "--no-wait"])
  print(f"Waiting for export")
  waiting = True
  while waiting:
    result = run(f"python3 abm {cloud} job show {id}")
    if result is None:
      waiting = False
      break
    print(result)
    # lines = result.split('\n')
    # job = filter(lines, id)
    waiting = json.loads(result)['state'] != 'ok'
    if waiting:
        # print(f'{len(pods)} zzz...')
        time.sleep(30)
        
  print(f"Export is done")


def run(command):
  result = subprocess.run(command.split(), capture_output=True, env=os.environ)
  if result.returncode == 0:
      return result.stdout.decode('utf-8').strip()

  print(f"ERROR: {result.stderr.decode('utf-8')}")
  return None

def find_executable(name):
    return run(f"which {name}")

if __name__ == '__main__':
    main()
