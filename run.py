#!/usr/bin/env python3
"""
Development run script for yt-dlp GUI.

Usage:
    python run.py
"""

import sys
from pathlib import Path

# Add src to path for development
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path.parent))

from src.main import main

if __name__ == '__main__':
    sys.exit(main())
