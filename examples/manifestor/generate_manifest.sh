#!/bin/bash
# Manifest Generator Launcher for Linux/Mac

echo ""
echo "===================================================================="
echo "  Control Tower Manifest Generator"
echo "===================================================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.7+ and try again"
    exit 1
fi

# Check if colorama is installed (optional but recommended)
if ! python3 -c "import colorama" &> /dev/null; then
    echo ""
    echo "NOTE: colorama is not installed. The tool will work but without colors."
    echo "To install: pip install colorama"
    echo ""
    sleep 2
fi

# Run the manifest generator
python3 manifest_generator.py

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Manifest generator encountered an error"
    exit 1
fi

exit 0
