"""
FloodGuard AI — conftest.py
Pytest configuration and shared fixtures.
"""
import sys
import os

# Ensure root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
