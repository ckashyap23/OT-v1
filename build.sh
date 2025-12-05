#!/bin/bash
# Build script for Azure App Service
# This script installs Python dependencies

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "Dependencies installed successfully!"

