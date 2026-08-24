#!/bin/bash
# SysWatch v2.1 - Linux/macOS Installer
# Installs Python dependencies, initializes database, starts the application

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
PYTHON=${PYTHON:-python3}
PIP=${PIP:-pip3}

echo "================================"
echo "  SysWatch v2.1 Installer"
echo "================================"

# Check Python version
if ! command -v $PYTHON &> /dev/null; then
    echo "ERROR: Python 3 is not installed."
    echo "Install with: sudo apt install python3 python3-pip (Ubuntu/Debian)"
    echo "Or: brew install python (macOS)"
    exit 1
fi

PY_VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python version: $PY_VERSION"

# Create virtual environment
VENV_DIR="$SCRIPT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    $PYTHON -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r "$BACKEND_DIR/requirements.txt"

# Copy .env if it doesn't exist
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "Creating .env from .env.example..."
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    
    # Generate a random JWT secret
    JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
    ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
    
    # Update .env with generated secrets
    sed -i.bak "s/JWT_SECRET=.*/JWT_SECRET=$JWT_SECRET/" "$SCRIPT_DIR/.env"
    sed -i.bak "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=$ENCRYPTION_KEY/" "$SCRIPT_DIR/.env"
    rm -f "$SCRIPT_DIR/.env.bak"
    
    echo "Generated JWT_SECRET and ENCRYPTION_KEY"
fi

echo ""
echo "================================"
echo "  Installation Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env to configure database, CORS, and other settings"
echo "  2. Ensure MySQL/MariaDB is running and DATABASE_URL is correct"
echo "  3. Start the application:"
echo "     cd backend && python app.py"
echo "  4. Or with Gunicorn:"
echo "     cd backend && gunicorn -w 4 -b 0.0.0.0:5000 'app:app'"
echo "  5. Access the web UI at http://localhost:5000"
echo ""
echo "Default login: admin@syswatch.local / admin123"
echo "CHANGE THE PASSWORD IMMEDIATELY after first login!"
echo ""
echo "To install the monitoring agent on a host:"
echo "  python agents/syswatch_agent.py --install"
echo ""