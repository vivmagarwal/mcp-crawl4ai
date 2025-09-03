#!/bin/bash

echo "========================================="
echo "MCP Crawl4AI Server Installation"
echo "========================================="

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo "❌ Error: Python 3.10 or higher is required. Found: Python $python_version"
    exit 1
fi
echo "✅ Python $python_version found"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists. Skipping..."
else
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -e . --quiet
echo "✅ Dependencies installed"

# Install Playwright browsers
echo ""
echo "Installing Playwright browsers..."
playwright install chromium
echo "✅ Playwright browsers installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created (please configure your API keys)"
fi

# Test installation
echo ""
echo "Testing installation..."
python3 -c "import server; print('✅ Server module imported successfully')"

echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Configure your .env file with API keys (if needed)"
echo "2. Add the server to your Claude Code configuration"
echo "3. Run the test suite: python test_server.py"
echo ""
echo "To add to Claude Code, use this configuration:"
echo ""
echo '{'
echo '  "mcp-crawl4ai": {'
echo '    "command": "python",'
echo "    \"args\": [\"$(pwd)/server.py\"],"
echo '    "env": {'
echo '      "OPENAI_API_KEY": "your-api-key"  // Optional'
echo '    }'
echo '  }'
echo '}'
echo ""