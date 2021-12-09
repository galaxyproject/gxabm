import sys
import os
import yaml

from lib import history, workflow, common

# Args from yml config files
# use abm as a library to run commands
def main():
  # Original code
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

  # Command line parsing
  cloud = sys.argv[1]
  configFile = None
  
  with open(sys.argv[2], "r") as config:
    configFile = yaml.safe_load(config)
  
  if configFile is None:
    print(f'ERROR: Could not locate an abm profile file {configFile}')
  
  histories = configFile["histories"]
  workflows = configFile["workflows"]

  # TODO generate these once and write to a yaml file. Subsequent runs can use
  # the previous config
  exportURL = []
  
  # export histories from main
  for id in histories:
    # wait_for("main", id)
    result = history.export([id])
    exportURL.append(result)

  # download workflows from js
  for wf in workflows:
    # TODO create a random directory in /tmp and cleanup afterwards.
    output_filename = f"/tmp/{wf}.ga"
    workflow.download([wf, "./workflows"], output_filename)
    workflow.translate([wf])

  # Expect a list of cloud ID values in sys.argv[1:] to be bootstrapped.
  # For now we will assume all data/workflows will be exported/downloaded from
  # main, but that should be parameterized as well

  # for each instance:
  # for cloud in sys.argv[1:]:
    # Ensure GALAXY_SERVER and API_KEY are set appropriatedly.
  common.set_active_profile(cloud)
  # 	import histories from main
  for url in exportURL:
    # TODO we will need to wait here.  I will modify the import method to return the job ID to wait on.
    history._import([url])

  for filename in os.listdir("./workflow"):
    # Check return code from validate to see if we should upload.
    if not workflow.validate([filename]):
      workflow.upload([filename])


if __name__ == '__main__':
  main()

