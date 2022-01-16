import os
import sys

this_dir = os.path.dirname(os.path.realpath(__file__))
lib_dir = os.path.join(this_dir, '..', 'lib')
sys.path.append(lib_dir)