#!/usr/bin/env python3

"""
This script is loosely based on https://github.com/galaxyproject/bioblend/blob/main/docs/examples/run_imported_workflow.py

usage: workflows.py [-h] [-s SERVER] [-a API_KEY] [-w WORKFLOW] [-d DATASET]
"""

import bioblend.galaxy
import argparse
import yaml
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

# The directory where the workflow invocation data will be saved.
INVOCATIONS_DIR = 'invocations'

def workflows():
	"""
	List all the workflows available on the server.

	:return:
	"""
	global API_KEY, GALAXY_SERVER

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


def run(args):
	global API_KEY, GALAXY_SERVER

	if args.workflow is None:
		print('ERROR: No workflow configuration was specified')
		sys.exit(1)

	if not os.path.isfile(args.workflow):
		print(f'ERROR: Could not find {args.workflow}')
		sys.exit(1)

	if os.path.exists(INVOCATIONS_DIR):
		if not os.path.isdir(INVOCATIONS_DIR):
			print('ERROR: Can not save invocation status, directory name in use.')
			sys.exit(1)
	else:
		os.mkdir(INVOCATIONS_DIR)

	with open(args.workflow, 'r') as stream:
		try:
			config = yaml.safe_load(stream)
		except yaml.YAMLError as exc:
			print(exc)

	gi = bioblend.galaxy.GalaxyInstance(url=GALAXY_SERVER, key=API_KEY)
	print(f"Connected to {GALAXY_SERVER}")

	workflow = config['workflow']
	inputs = {}
	for spec in config['inputs']:
		input = gi.workflows.get_workflow_inputs(workflow, spec['name'])
		if input is None or len(input) == 0:
			print('ERROR: Invalid input specification')
			sys.exit(1)
		inputs[input[0]] = { 'id': spec['id'], 'src': 'hda'}

	if 'history' in config:
		print(f"Saving output to a history named {config['history']}")
		invocation = gi.workflows.invoke_workflow(workflow, inputs=inputs, history_name=config['history'])
	else:
		invocation = gi.workflows.invoke_workflow(workflow, inputs=inputs)

	pprint(invocation)

	output_path = os.path.join(INVOCATIONS_DIR, invocation['id'] + '.json')
	with open(output_path, 'w') as f:
		json.dump(invocation, f, indent=4)
		print(f"Wrote {output_path}")


def rna_seq():
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
	# parser = argparse.ArgumentParser(description='Run Galaxy workflows')
	# parser.add_argument('-s', '--server', required=False, help='the Galaxy server URL.')
	# parser.add_argument('-a', '--api-key', required=False, help='your Galaxy API key')
	# args = parser.parse_args(argv)
	# if args.server is not None:
	# 	GALAXY_SERVER = args.server
	# if args.api_key is not None:
	# 	API_KEY = args.api_key
	#
	# if API_KEY is None:
	# 	print("ERROR: You have not specified a Galaxy API key")
	# 	sys.exit(1)

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


def histories():
	global API_KEY, GALAXY_SERVER
	gi = bioblend.galaxy.GalaxyInstance(url=GALAXY_SERVER, key=API_KEY)
	print(f"Connected to {GALAXY_SERVER}")
	if 'history' in args:
		history_list = gi.histories.get_histories(name=args.history)
	else:
		history_list = gi.histories.get_published_histories()

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

def status(args):
	global API_KEY, GALAXY_SERVER
	gi = bioblend.galaxy.GalaxyInstance(url=GALAXY_SERVER, key=API_KEY)
	print(f"Connected to {GALAXY_SERVER}")
	invocations = gi.invocations.get_invocations()
	print('ID\t\t\tWORKFLOW\t\tHISTORY\t\t\tSTATE')
	for invocation in invocations:
		print(f"{invocation['id']}\t{invocation['workflow_id']}\t{invocation['history_id']}\t{invocation['state']}")



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
	parser.add_argument('-w', '--workflow',help='the name of the workflow configuration to run')
	parser.add_argument('-H', '--history', help='the history ID to view')
	parser.add_argument('command', help='the command to be executed')

	args = parser.parse_args()
	if args.server is not None:
		GALAXY_SERVER = args.server
	if args.api_key is not None:
		API_KEY = args.api_key

	if API_KEY is None:
		print("ERROR: You have not specified a Galaxy API key")
		sys.exit(1)
	if GALAXY_SERVER is None:
		print('ERROR: You have not specified the Galaxy URL')
		sys.exit(1)

	if args.command in ['wf', 'flows', 'workflows']:
		workflows()
	elif args.command == 'run':
		run(args)
	elif args.command in ['h', 'hist','histories']:
		histories()
	elif args.command in ['st', 'status']:
		status(args)
	elif args.command == 'rna':
		rna_seq()
	else:
		print(f"Unknown command {args.command}")

	sys.exit(0)