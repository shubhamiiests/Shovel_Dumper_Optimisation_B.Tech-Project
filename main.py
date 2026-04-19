#!/usr/bin/env python3
"""
main.py — Entry point for Fleet Optimisation System
Run: python main.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import main

if __name__ == "__main__":
    main()
