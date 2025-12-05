#!/bin/bash
# Azure App Service startup script
# Install dependencies if not already installed
if [ ! -f /home/site/wwwroot/.dependencies_installed ]; then
    echo "Installing Python dependencies..."
    cd /home/site/wwwroot
    pip install --upgrade pip
    pip install -r requirements.txt
    touch /home/site/wwwroot/.dependencies_installed
    echo "Dependencies installed successfully!"
fi

# Set PYTHONPATH to include project root
export PYTHONPATH="${PYTHONPATH}:/home/site/wwwroot"
cd /home/site/wwwroot
gunicorn --bind 0.0.0.0:8000 --timeout 600 --workers 2 --pythonpath /home/site/wwwroot gunicorn_config:application

