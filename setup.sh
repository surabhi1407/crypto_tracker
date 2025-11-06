#!/bin/bash
# Setup script for Crypto Market Intelligence Dashboard

echo "=================================================="
echo "🚀 Crypto Market Intelligence Dashboard - Setup"
echo "=================================================="
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"
echo ""

# Check if we're in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  No virtual environment detected."
    echo "Creating a virtual environment is recommended..."
    echo ""
    
    read -p "Create a virtual environment? (y/n) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        
        echo "Activating virtual environment..."
        source venv/bin/activate
        
        echo "✅ Virtual environment created and activated"
        echo ""
    else
        echo "Continuing without virtual environment..."
        echo "Note: You may need to use --user flag or --break-system-packages"
        echo ""
    fi
else
    echo "✅ Virtual environment detected: $VIRTUAL_ENV"
    echo ""
fi

# Install dependencies
echo "Installing dependencies..."
echo ""

if [[ -n "$VIRTUAL_ENV" ]]; then
    pip install -r requirements.txt
else
    # Try with --user flag first
    pip3 install --user -r requirements.txt 2>/dev/null || \
    pip3 install --break-system-packages -r requirements.txt
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Dependencies installed successfully"
else
    echo ""
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p data/backups logs

echo "✅ Directories created"
echo ""

# Copy .env.example if .env doesn't exist
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "Creating .env file from template..."
        cp .env.example .env
        echo "✅ .env file created (you can customize it later)"
    fi
fi

echo ""
echo "=================================================="
echo "✅ Setup Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo ""
echo "1. (Optional) Edit .env file to customize configuration"
echo "2. Run the test script:"
echo "   python3 test_pipeline.py"
echo ""
echo "3. Run the ingestion pipeline:"
echo "   python3 main.py"
echo ""
echo "4. Check the dashboard:"
echo "   streamlit run app.py"
echo ""
echo "=================================================="

