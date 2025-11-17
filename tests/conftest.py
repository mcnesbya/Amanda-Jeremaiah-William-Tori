"""
conftest.py - Pytest configuration file.
This file is automatically loaded by pytest and can be used to:
- Add paths to sys.path
- Define fixtures shared across tests
- Configure pytest settings
"""
import sys
import os

# Add parent directory to Python path so we can import modules from the root
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

