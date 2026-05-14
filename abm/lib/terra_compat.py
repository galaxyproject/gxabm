"""
Temporary compatibility fixes for Terra/AnVIL dependencies with Python 3.12.

This module provides monkey-patches for Python 3.12 compatibility issues
in Terra ecosystem packages until upstream fixes are available.
"""

import configparser
import sys


def patch_firecloud_python312():
    """
    Monkey-patch firecloud to work with Python 3.12.

    Issue: firecloud.fccore uses configparser.SafeConfigParser which was
    removed in Python 3.12 (deprecated since Python 3.2).

    Fix: Replace SafeConfigParser with ConfigParser in the configparser module
    before firecloud imports it.
    """
    if sys.version_info >= (3, 12):
        # Add SafeConfigParser as an alias to ConfigParser for backward compatibility
        if not hasattr(configparser, 'SafeConfigParser'):
            configparser.SafeConfigParser = configparser.ConfigParser
            print("🔧 Applied Python 3.12 compatibility patch for firecloud")


def patch_terra_dependencies():
    """Apply all necessary compatibility patches for Terra dependencies."""
    patch_firecloud_python312()


# Apply patches immediately when this module is imported
patch_terra_dependencies()