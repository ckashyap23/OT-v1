# gunicorn_config.py
# Gunicorn configuration file for Azure App Service
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now import the app
from src.api import app

# Gunicorn will use this as the application
application = app

