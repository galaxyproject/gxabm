import subprocess
import sys
import yaml
import os
import time
import json

from abm import history, workflow, common

# Args from yml config files
# use abm as a library to run commands
# take benchmarking config as an input
def main():

  # Original Code
  ###
  # configPath = sys.argv[1]
  # profile = None;
  # if os.path.exists(configPath):
  #   with open(configPath, 'r') as f:
  #     profile = yaml.safe_load(f)
  # if profile is None:
  #   print(f'ERROR: Could not locate an abm profile file in {configPath}')
  #
  # clouds = profile['cloud']

  # RNA-paired hist on main: b7a6e3abfe13a9c3
  # RNA-single hist on main: 68c184b7901bc21a
  # DNA-single hist on main: d59d7f1482fd9fd5
  # DNA-paired hist on main: df8b040f22887247

  # TODO - Load these from a YAML configuration file.
  historyID = ["b7a6e3abfe13a9c3", "68c184b7901bc21a", "d59d7f1482fd9fd5", "df8b040f22887247"]
  workflows = ["de503f2935ac5629", "39f1e01ca3950c18", "313eddf294db855d", "e7234e29592c1dfb"]
  exportURL = []


  # export histories from main
  for id in historyID:
    # NOTE: history.export blocks unless we specify "--no-wait" so there is no
    # need to wait here.  In any case we would need to wait *after* calling
    # export, and we would need to wait on the job ID not the history ID.
    # wait_for("main", id)
    result = history.export([id])
    exportURL.append(result)

  # download workflows from js
  for wf in workflows:
    workflow.export([wf, "./workflows"])
    workflow.translate([wf])
      
  profiles = common.load_profiles()
  # Assume sys.argv[1:] contains a list of cloud instance ID values that should
  # be bootstrapped
  # for each instance:
  for cloud in sys.argv[1:]:
    # 	import histories from main
    for url in exportURL:
      history._import([url])

    for filename in os.listdir("./workflow"):
      workflow.validate([filename])
      workflow.upload([filename])



if __name__ == '__main__':
    main()
