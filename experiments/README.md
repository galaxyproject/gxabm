## Experiment YAML Format Guide

`name:` label for experiment - does not manifest

`runs:` number of times each benchmark repeats

`benchmark_confs:` list of benchmarks (yaml files) to be conducted

`cloud:` list of clouds that benchmarks will run on

`job_configs:` list of CPU and memory settings for all listed benchmarks to be run with (e.g. 4x8 means 4 CPUs and 8 GB memory)
