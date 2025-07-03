#!/usr/bin/env python3
"""
Main entry point for the Streamlit application.
This file serves as the bridge between the Docker container and the actual app.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path to enable absolute imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now import and run the main app
from app.app import *