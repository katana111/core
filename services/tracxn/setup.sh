#!/bin/bash
# Setup script for Tracxn Scraper
# Run this script to install all dependencies

echo "========================================"
echo "Tracxn Scraper - Setup Script"
echo "========================================"
echo ""

# Check Python
echo "Checking Python installation..."
if command -v python3 &> /dev/null; then
    echo "✅ Python3 found: $(python3 --version)"
else
    echo "❌ Python3 not found. Please install Python 3.7+"
    exit 1
fi

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install playwright requests

# Install Playwright browsers
echo ""
echo "Installing Playwright browsers (Chromium)..."
playwright install chromium

echo ""
echo "========================================"
echo "✅ Setup Complete!"
echo "========================================"
echo ""
echo "You can now run:"
echo "  python3 example_usage.py     # Run examples"
echo "  python3 test_scraper.py      # Test with SEON company"
echo ""
