# Benchmarking Scripts
Python Bioblend scripts for automating tasks in Galaxy

## Prerequisites

The only Python requirement (so far) is the Bioblend library.

Create a Python virtual environment and install the bioblend library:

```
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install bioblend
```

**NOTE:** On Linux and MacOS system you can set the executable bit on the `workflow.py`
file so you do not need to explicitly run the script with Python.

```
chmod +x workflow.py
./workflow.py help
```

## Credentials

To use these scripts you will need an [API key](https://training.galaxyproject.org/training-material/faqs/galaxy/preferences_admin_api_key.html) for the Galaxy server. While the Galaxy URL and API key can be specified on the command line, it is easier to define them as environment variables, preferably in a file you can `source` to make them available.

```
export GALAXY_SERVER=https://benchmarking.usegvl.org/initial/galaxy/
export API_KEY=<your api key>
```

## Usage

```
python3 workflow.py <COMMAND> [options]
```



## Commands

***This is a work in progress***

**histories**<br/>
Prints all public histories from all users on the server.  Don't do this on Main or EU!

**workflows**<br/>
Prints all published workflows and their expected inputs.

**run**<br/>
Run a workflow.  Currently this is hard coded to simply run the `RNA Workflow Test`.

## Runtime Configuration

In progress. See [#1](../../issues/1)

## Obtaining Results

TBD. 

Scrape the results of a workflow invocation will be scraped from the server and
output in a format suitable for importing into a spreadsheet or database.

### Contributing

Fork this repository and then create a working branch for yourself base off the `dev` branch. All pull requests should target  `dev` and not the `master` branch.

```bash
git clone https://github.com/ksuderman/bioblend-scripts.git
cd bioblend-scripts
git checkout -b my-branch
```

If you decide to work on one of the [issues](bioblend-scripts/issues) be sure to assign yourself to that issue to let others know the issue is taken.

