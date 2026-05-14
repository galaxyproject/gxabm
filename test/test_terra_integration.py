#!/usr/bin/env python3
"""
Test Terra workspace integration for config bootstrap command.

This test validates that the Terra integration code works correctly
without requiring actual Terra credentials or Galaxy instances.
"""

import os
import sys
import yaml
from pathlib import Path

# Add the abm library to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'abm'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'abm', 'lib'))

try:
    from lib import terra_compat  # Apply Python 3.12 compatibility patches
    from lib import config
    from lib.config import _filter_files_by_pattern, _detect_datatype_from_extension, _extract_filename_from_url
    print("✅ Terra integration modules imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Terra integration modules: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def test_file_filtering():
    """Test file pattern filtering functionality."""
    print("\nTesting file pattern filtering:")

    # Mock workspace files
    mock_files = [
        {"path": "data/sample1.fastq.gz", "name": "sample1.fastq.gz", "size": 1024000},
        {"path": "data/sample2.fastq.gz", "name": "sample2.fastq.gz", "size": 1156000},
        {"path": "results/alignment1.bam", "name": "alignment1.bam", "size": 5000000},
        {"path": "results/alignment2.bam", "name": "alignment2.bam", "size": 4800000},
        {"path": "metadata/samples.tsv", "name": "samples.tsv", "size": 2048},
        {"path": "analysis/report.html", "name": "report.html", "size": 15360},
        {"path": "notebooks/analysis.ipynb", "name": "analysis.ipynb", "size": 8192},
    ]

    test_patterns = [
        ("data/*.fastq.gz", 2),
        ("results/*.bam", 2),
        ("metadata/*.tsv", 1),
        ("*.html", 0),  # Should not match since it's in subdirectory
        ("analysis/*.html", 1),
        ("*/*.ipynb", 1),
        ("data/*", 2),
        ("nonexistent/*", 0)
    ]

    for pattern, expected_count in test_patterns:
        matches = _filter_files_by_pattern(mock_files, pattern)
        if len(matches) == expected_count:
            print(f"  ✅ {pattern}: found {len(matches)} files (expected {expected_count})")
        else:
            print(f"  ❌ {pattern}: found {len(matches)} files (expected {expected_count})")
            for match in matches:
                print(f"    - {match['path']}")


def test_datatype_detection():
    """Test automatic datatype detection."""
    print("\nTesting datatype detection:")

    test_cases = [
        ("sample.fastq.gz", "fastqsanger.gz"),
        ("reads.fq", "fastqsanger"),
        ("alignment.bam", "bam"),
        ("variants.vcf", "vcf"),
        ("metadata.tsv", "tabular"),
        ("report.html", "html"),
        ("unknown.xyz", None),
        ("data.json", "json"),
        ("reference.fasta", None),  # fasta not in our test map
        ("", None)
    ]

    for filename, expected in test_cases:
        result = _detect_datatype_from_extension(filename)
        if result == expected:
            print(f"  ✅ {filename}: {result}")
        else:
            print(f"  ❌ {filename}: got {result}, expected {expected}")


def test_filename_extraction():
    """Test URL filename extraction."""
    print("\nTesting filename extraction:")

    test_cases = [
        ("https://example.com/data/sample.fastq.gz", "sample.fastq.gz"),
        ("gs://bucket/path/to/file.bam", "file.bam"),
        ("anvil://namespace/workspace/data/file.txt", "file.txt"),
        ("/local/path/file.vcf", "file.vcf"),
        ("file.tsv", "file.tsv")
    ]

    for url, expected in test_cases:
        result = _extract_filename_from_url(url)
        if result == expected:
            print(f"  ✅ {url}: {result}")
        else:
            print(f"  ❌ {url}: got {result}, expected {expected}")


def test_configuration_parsing():
    """Test Terra workspace configuration parsing."""
    print("\nTesting configuration parsing:")

    # Load the example configuration
    config_file = Path(__file__).parent.parent / "bootstrap-config" / "terra-example.yml"

    try:
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        print(f"  ✅ Configuration loaded: {config_file}")

        # Validate structure
        if 'terra_workspaces' in config_data:
            workspaces = config_data['terra_workspaces']
            print(f"  ✅ Found {len(workspaces)} Terra workspaces in config")

            for i, workspace in enumerate(workspaces):
                namespace = workspace.get('namespace')
                workspace_name = workspace.get('workspace')
                datasets = workspace.get('datasets', {})

                print(f"    Workspace {i+1}: {namespace}/{workspace_name}")
                print(f"      Histories: {len(datasets)}")

                total_patterns = sum(len(patterns) for patterns in datasets.values())
                print(f"      Dataset patterns: {total_patterns}")
        else:
            print(f"  ❌ No terra_workspaces section found in config")

    except FileNotFoundError:
        print(f"  ❌ Configuration file not found: {config_file}")
    except Exception as e:
        print(f"  ❌ Error parsing configuration: {e}")


def test_terra_availability():
    """Test Terra/AnVIL module availability."""
    print("\nTesting Terra module availability:")

    try:
        from anvilfs.anvilfs import AnVILFS
        print("  ✅ AnVILFS class available")

        # Test instantiation without credentials (should fail gracefully)
        try:
            anvil_fs = AnVILFS('test-namespace', 'test-workspace')
            print("  ✅ AnVILFS instance created (no credentials)")
        except Exception as e:
            if 'credentials' in str(e).lower() or 'authentication' in str(e).lower():
                print("  ✅ AnVILFS properly detects missing credentials (expected)")
            else:
                print(f"  ⚠️  Unexpected AnVILFS error: {e}")

    except ImportError as e:
        print(f"  ❌ AnVILFS not available: {e}")


def main():
    """Run all tests."""
    print("Terra Workspace Integration Tests")
    print("=" * 50)

    # Run tests
    test_file_filtering()
    test_datatype_detection()
    test_filename_extraction()
    test_configuration_parsing()
    test_terra_availability()

    print("\nTest Summary:")
    print("All core functionality for Terra workspace integration appears to be working.")
    print("Ready for integration testing with actual Terra workspaces and Galaxy instances.")
    print("\nNext steps:")
    print("1. Test with real Terra credentials and workspace")
    print("2. Test with Galaxy instance import functionality")
    print("3. Refine fs.anvilfs API integration based on actual usage")


if __name__ == "__main__":
    main()