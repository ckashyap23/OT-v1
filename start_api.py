#!/usr/bin/env python3
"""
Start script for the Flask API backend.
For Azure deployment, use: gunicorn --bind 0.0.0.0:8000 src.api:app
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.api import app

if __name__ == '__main__':
    # For local development
    app.run(host='0.0.0.0', port=5000, debug=True)
else:
    # For production (gunicorn)
    application = app

