#!/usr/bin/env python3

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
import json
import sys
import os

from pprint import pprint

# Default value for the Galaxy server URL.  This can be overriden with an
# environment variable or on the command line
GALAXY_SERVER = 'https://benchmarking.usegvl.org/initial/galaxy/'

# Your Galaxy API key.  This can be specified in an environment variable or
# on the command line.
API_KEY = None

def workflows(argv):
	"""
	List all the workflows available on the server.

	:return:
	"""
	global API_KEY, GALAXY_SERVER

	parser = argparse.ArgumentParser(description='Run Galaxy workflows')
	parser.add_argument('-s', '--server', required=False, help='the Galaxy server URL.')
	parser.add_argument('-a', '--api-key', required=False, help='your Galaxy API key')
	args = parser.parse_args(argv[2:])
	if args.server is not None:
		GALAXY_SERVER = args.server
	if args.api_key is not None:
		API_KEY = args.api_key

	if API_KEY is None:
		print("ERROR: You have not specified a Galaxy API key")
		sys.exit(1)

	gi = bioblend.galaxy.GalaxyInstance(url=GALAXY_SERVER, key=API_KEY)
	print(f"Connected to {GALAXY_SERVER}")
	wflows = gi.workflows.get_workflows(published=True) #name='imported: Benchmarking RNA-seq Cloud Costs')
	print(f"Found {len(wflows)} workflows")
	for wf in wflows:
		print(f"Name: {wf['name']}")
		print(f"ID: {wf['id']}")
		wf_info = gi.workflows.show_workflow(wf['id'])
		inputs = wf_info['inputs']
		for index in range(len(inputs)):
			print(f"Input {index}: {inputs[str(index)]['label']}")
		print()


def run():
	global API_KEY, GALAXY_SERVER
	parser = argparse.ArgumentParser(description='Run Galaxy workflows')
	parser.add_argument('-s', '--server', required=False, help='the Galaxy server URL.')
	parser.add_argument('-a', '--api-key', required=False, help='your Galaxy API key')
	parser.add_argument('-w', '--workflow', required=True, help='the name of the workflow to run')
	parser.add_argument('-H', '--history', required=True, help='the history (dataset) to be run through the workflow')

	args = parser.parse_args()
	if args.server is not None:
		GALAXY_SERVER = args.server
	if args.api_key is not None:
		API_KEY = args.api_key

	if API_KEY is None:
		print("ERROR: You have not specified a Galaxy API key")
		sys.exit(1)

	gi = bioblend.galaxy.GalaxyInstance(url=GALAXY_SERVER, key=API_KEY)
	print(f"Connected to {GALAXY_SERVER}")
	histories=gi.histories.get_histories()
	if histories is None or len(histories) == 0:
		print("ERROR: history not found!")
		return
	if len(histories) > 1:
		print("WARNING: found more than one history with that name; using the first one found")
	history = histories[0]['id']

	wf_info = gi.workflows.get_workflows(name=args.workflow)
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


def rna_seq(argv):
	"""
	048a970701a6dc44 - gencode.v38.annotation.gtf.gz (ok)
	ca5081d2c8f1088a - SRR14916263 (fastq-dump) uncompressed (ok)
	d65ad3947f73925d - SRR14916263 (fastq-dump) (ok)
	3947ba9ca107312f - gencode.v38.transcripts.fa.gz (ok)

	ID: eea1d48bdaa84118
	Input 0: Reference FASTA
	Input 1: GTF
	Input 2: FASTA Dataset
	"""
	print('rna_seq')
	GTF = '048a970701a6dc44'
	FASTA_DATA = 'ca5081d2c8f1088a'
	FASTA_REF = '3947ba9ca107312f'

	WORKFLOW_ID = 'eea1d48bdaa84118'

	global API_KEY, GALAXY_SERVER
	parser = argparse.ArgumentParser(description='Run Galaxy workflows')
	parser.add_argument('-s', '--server', required=False, help='the Galaxy server URL.')
	parser.add_argument('-a', '--api-key', required=False, help='your Galaxy API key')
	args = parser.parse_args(argv)
	if args.server is not None:
		GALAXY_SERVER = args.server
	if args.api_key is not None:
		API_KEY = args.api_key

	if API_KEY is None:
		print("ERROR: You have not specified a Galaxy API key")
		sys.exit(1)

	gi = bioblend.galaxy.GalaxyInstance(url=GALAXY_SERVER, key=API_KEY)

	fasta_ref = gi.workflows.get_workflow_inputs(WORKFLOW_ID, 'Reference FASTA')[0]
	fasta_data = gi.workflows.get_workflow_inputs(WORKFLOW_ID, 'FASTA Dataset')[0]
	gtf = gi.workflows.get_workflow_inputs(WORKFLOW_ID, 'GTF')[0]

	inputs = {
		fasta_data: { 'id': FASTA_DATA, 'src': 'hda' },
		fasta_ref: { 'id': FASTA_REF, 'src': 'hda' },
		gtf: { 'id': GTF, 'src': 'hda' }
	}
	result = gi.workflows.invoke_workflow(WORKFLOW_ID, inputs=inputs)
	pprint(result)


def histories(argv):
	print('histories')
	global API_KEY, GALAXY_SERVER
	parser = argparse.ArgumentParser(description='Run Galaxy workflows')
	parser.add_argument('-s', '--server', required=False, help='the Galaxy server URL.')
	parser.add_argument('-a', '--api-key', required=False, help='your Galaxy API key')
	# parser.add_argument('-w', '--workflow',help='the name of the workflow to run')
	parser.add_argument('-H', '--history', help='the history (dataset) to be run through the workflow')

	args = parser.parse_args(argv[2:])
	if args.server is not None:
		GALAXY_SERVER = args.server
	if args.api_key is not None:
		API_KEY = args.api_key

	if API_KEY is None:
		print("ERROR: You have not specified a Galaxy API key")
		sys.exit(1)

	gi = bioblend.galaxy.GalaxyInstance(url=GALAXY_SERVER, key=API_KEY)
	print(f"Connected to {GALAXY_SERVER}")
	if args.history is None:
		history_list = gi.histories.get_published_histories()
	else:
		history_list = gi.histories.get_histories(name=args.history)

	if history_list is None or len(history_list) == 0:
		print("ERROR: history not found!")
		return

	for history in history_list:
		# print(f"ID: {history['id']} Name: {history['name']}")
		print(f"{history['id']} - {history['name']}")
		for dataset in gi.histories.show_history(history['id'], contents=True, details='none'):
			if not dataset['deleted']:
				state = dataset['state'] if 'state' in dataset else 'Unknown'
				print(f"\t{dataset['id']} - {dataset['name']} ({state})")
		print()


if __name__ == '__main__':

	# Get defaults from the environment if available
	value = os.environ.get('GALAXY_SERVER')
	if value is not None:
		GALAXY_SERVER = value

	value = os.environ.get('API_KEY')
	if value is not None:
		print(f"API KEY is {value}")
		API_KEY = value


	if len(sys.argv) < 2 or sys.argv[1] == 'help':
		print("There is no help available at this time.")
		print("Please refer to the README.md in the GitHub repository")
		sys.exit(1)

	if sys.argv[1] == 'workflows':
		workflows(sys.argv)
	elif sys.argv[1] == 'run':
		rna_seq(sys.argv[2:])
	elif sys.argv[1] == 'histories':
		histories(sys.argv)
	else:
		print(f"Unknown command {sys.argv[1]}")
