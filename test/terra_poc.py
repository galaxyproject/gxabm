#!/usr/bin/env python3
"""
Proof-of-concept for fs.anvilfs Terra workspace integration.

This script demonstrates how fs.anvilfs could be used to:
1. Connect to Terra workspaces via PyFilesystem2 interface
2. Browse workspace files with pattern matching
3. Extract file metadata for Galaxy import
4. Generate signed URLs for dataset import

Run with:
  python test/terra_poc.py

For actual workspace access, set environment variables:
  export GOOGLE_APPLICATION_CREDENTIALS="path/to/credentials.json"
  export TERRA_NOTEBOOK_GOOGLE_ACCESS_TOKEN="$(gcloud auth print-access-token)"
"""

import os
import re
from typing import List, Dict, Any, Optional
from pathlib import Path


def simulate_fs_anvilfs_interface():
    """
    Simulate fs.anvilfs interface for proof-of-concept.
    In real usage, this would be:

    from fs.anvilfs import AnVILFS
    anvil_fs = AnVILFS(namespace="my-namespace", workspace="my-workspace")
    """

    # Mock workspace structure
    mock_files = [
        {"name": "data/sample1.fastq.gz", "size": 1024000, "type": "file"},
        {"name": "data/sample2.fastq.gz", "size": 1156000, "type": "file"},
        {"name": "results/alignment1.bam", "size": 5000000, "type": "file"},
        {"name": "results/alignment2.bam", "size": 4800000, "type": "file"},
        {"name": "metadata/samples.tsv", "size": 2048, "type": "file"},
        {"name": "analysis/report.html", "size": 15360, "type": "file"},
    ]

    class MockFileSystem:
        def __init__(self, namespace: str, workspace: str):
            self.namespace = namespace
            self.workspace = workspace
            self._files = mock_files

        def scandir(self, path: str = "/") -> List[Dict[str, Any]]:
            """Simulate scanning directory for files"""
            filtered_files = []
            for file_info in self._files:
                file_path = file_info["name"]
                if path == "/" or file_path.startswith(path.lstrip("/")):
                    filtered_files.append({
                        "name": Path(file_path).name,
                        "path": file_path,
                        "size": file_info["size"],
                        "type": file_info["type"],
                        "is_file": file_info["type"] == "file"
                    })
            return filtered_files

        def listdir(self, path: str = "/") -> List[str]:
            """List directory contents"""
            return [f["name"] for f in self.scandir(path)]

        def get_signed_url(self, file_path: str) -> str:
            """Simulate generating signed URL for Terra file"""
            return f"https://storage.googleapis.com/mock-workspace-bucket/{file_path}?signed=true"

    return MockFileSystem


def filter_files_by_pattern(files: List[Dict[str, Any]], pattern: str) -> List[Dict[str, Any]]:
    """Filter files by glob-style pattern"""
    # Convert glob pattern to regex
    regex_pattern = pattern.replace("*", ".*").replace("?", ".")
    regex = re.compile(f"^{regex_pattern}$")

    return [f for f in files if regex.match(f["path"])]


def extract_filename_from_path(path: str) -> str:
    """Extract filename from path for dataset naming"""
    return Path(path).name


def detect_datatype_from_extension(filename: str) -> Optional[str]:
    """Detect Galaxy datatype from file extension"""
    extension_map = {
        '.fastq.gz': 'fastqsanger.gz',
        '.fastq': 'fastqsanger',
        '.bam': 'bam',
        '.sam': 'sam',
        '.tsv': 'tabular',
        '.csv': 'csv',
        '.html': 'html',
        '.txt': 'txt',
        '.bed': 'bed',
        '.gtf': 'gtf',
        '.gff': 'gff',
        '.vcf': 'vcf'
    }

    for ext, datatype in extension_map.items():
        if filename.lower().endswith(ext):
            return datatype
    return None


def process_terra_workspace_config(workspace_config: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Process Terra workspace configuration and return dataset import plan.

    This simulates what would happen in the actual bootstrap integration.
    """
    namespace = workspace_config["namespace"]
    workspace_name = workspace_config["workspace"]

    print(f"Connecting to Terra workspace: {namespace}/{workspace_name}")

    # Initialize fs.anvilfs connection (simulated)
    MockFS = simulate_fs_anvilfs_interface()
    anvil_fs = MockFS(namespace=namespace, workspace=workspace_name)

    import_plan = {}

    # Process dataset import patterns
    for history_name, dataset_configs in workspace_config.get("datasets", {}).items():
        datasets_to_import = []

        print(f"\nProcessing history: {history_name}")

        for dataset_config in dataset_configs:
            if isinstance(dataset_config, str):
                # Simple pattern string
                pattern = dataset_config
                custom_datatype = None
            else:
                # Dictionary with pattern and optional datatype
                pattern = dataset_config["pattern"]
                custom_datatype = dataset_config.get("datatype")

            print(f"  Looking for files matching: {pattern}")

            # Get all files from workspace
            all_files = anvil_fs.scandir("/")

            # Filter by pattern
            matching_files = filter_files_by_pattern(all_files, pattern)

            print(f"  Found {len(matching_files)} matching files:")

            for file_info in matching_files:
                file_path = file_info["path"]
                file_name = extract_filename_from_path(file_path)
                file_size = file_info["size"]

                # Detect datatype
                datatype = custom_datatype or detect_datatype_from_extension(file_name)

                # Generate signed URL for Galaxy import
                signed_url = anvil_fs.get_signed_url(file_path)

                dataset_entry = {
                    "url": signed_url,
                    "name": file_name,
                    "datatype": datatype,
                    "size": file_size,
                    "original_path": file_path
                }

                datasets_to_import.append(dataset_entry)
                print(f"    - {file_name} ({file_size} bytes, type: {datatype})")

        import_plan[history_name] = datasets_to_import

    return import_plan


def demo_bootstrap_integration():
    """Demonstrate Terra workspace integration with bootstrap configuration"""

    print("Terra Workspace fs.anvilfs Proof-of-Concept")
    print("=" * 50)

    # Example bootstrap configuration with Terra workspaces
    bootstrap_config = {
        "version": 1,
        "terra_workspaces": [
            {
                "namespace": "broad-dsde-dev",
                "workspace": "my-analysis-workspace",
                "datasets": {
                    "Raw Sequencing Data": [
                        "data/*.fastq.gz"
                    ],
                    "Alignment Results": [
                        {"pattern": "results/*.bam", "datatype": "bam"}
                    ],
                    "Metadata": [
                        {"pattern": "metadata/*.tsv", "datatype": "tabular"}
                    ]
                }
            }
        ]
    }

    # Process each Terra workspace
    for workspace_config in bootstrap_config["terra_workspaces"]:
        import_plan = process_terra_workspace_config(workspace_config)

        print(f"\nImport Plan Summary:")
        print("-" * 30)

        total_files = 0
        total_size = 0

        for history_name, datasets in import_plan.items():
            print(f"{history_name}: {len(datasets)} files")
            for dataset in datasets:
                total_files += 1
                total_size += dataset["size"]

        print(f"\nTotal: {total_files} files, {total_size:,} bytes")

        # Show how this would integrate with existing bootstrap infrastructure
        print("\nIntegration with existing bootstrap code:")
        print("This data would be passed to _process_datasets_v1() from Issue #339")
        print("Each dataset dict contains: url, name, datatype (compatible with enhanced format)")


if __name__ == "__main__":
    print("Checking environment...")

    # Check for Terra authentication
    has_credentials = "GOOGLE_APPLICATION_CREDENTIALS" in os.environ
    has_token = "TERRA_NOTEBOOK_GOOGLE_ACCESS_TOKEN" in os.environ

    if has_credentials and has_token:
        print("✓ Terra credentials detected - could connect to real workspaces")
    else:
        print("ℹ  No Terra credentials - running simulation mode")
        print("  Set GOOGLE_APPLICATION_CREDENTIALS and TERRA_NOTEBOOK_GOOGLE_ACCESS_TOKEN for real access")

    print()

    demo_bootstrap_integration()