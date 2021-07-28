"""
This script is loosely based on https://github.com/galaxyproject/bioblend/blob/main/docs/examples/run_imported_workflow.py

TO-DO
1. Allow the user to specify an output history.
2. Maybe allow the user to specify a URL to data that should be uploaded to
   the server to be used as input to the workflow.
3. Don't assume the name of the input parameter is 'input'

usage: workflows.py [-h] [-s SERVER] [-a API_KEY] -w WORKFLOW -d DATASET
"""

import bioblend.galaxy
import argparse
import sys
import os

from pprint import pprint

# Default value for the Galaxy server URL.  This can be overriden with an
# environment variable or on the command line
GALAXY_SERVER = 'https://benchmarking.usegvl.org/initial/galaxy/'

# Your Galaxy API key.  This can be specified in an environment variable or
# on the command line.
API_KEY = None

def run(workflow_name, history_name):
	gi = bioblend.galaxy.GalaxyInstance(url=GALAXY_SERVER, key=API_KEY)
	print(f"Connected to {GALAXY_SERVER}")
	histories=gi.histories.get_histories(name=history_name)
	if histories is None or len(histories) == 0:
		print("ERROR: history not found!")
		return
	if len(histories) > 1:
		print("WARNING: found more than one history with that name; using the first one found")
	history = histories[0]['id']

	wf_info = gi.workflows.get_workflows(name=workflow_name)
	if wf_info is None or len(wf_info) == 0:
		print("ERROR: no workflow with that name found.")
		return
	if len(wf_info) > 1:
		print("WARNING: found more than one workflow with that name; using the first one found.")
	workflow = wf_info[0]['id']
	datasets = gi.histories.show_history(history, contents=True, details='none')
	for dataset in datasets:
		inputs = {0: {'id':dataset['id'], 'src':'hda'}}
		result = gi.workflows.invoke_workflow(workflow, inputs=inputs)
		pprint(result)
		print()


if __name__ == '__main__':
	# Get defaults from the environment if available
	value = os.environ.get('GALAXY_SERVER')
	if value is not None:
		GALAXY_SERVER = value

	value = os.environ.get('API_KEY')
	if value is not None:
		API_KEY = value

	parser = argparse.ArgumentParser(description='Run Galaxy workflows')
	parser.add_argument('-s', '--server', required=False, help='the Galaxy server URL.')
	parser.add_argument('-a', '--api-key', required=False, help='your Galaxy API key')
	parser.add_argument('-w', '--workflow', required=True, help='the name of the workflow to run')
	parser.add_argument('-d', '--dataset', required=True, help='the history (dataset) to be run through the workflow')

	args = parser.parse_args()

	if args.server is not None:
		GALAXY_SERVER = args.server
	if args.api_key is not None:
		API_KEY = args.api_key

	if API_KEY is None:
		print("ERROR: You have not specified a Galaxy API key")
		sys.exit(1)

	run(args.workflow, args.dataset)