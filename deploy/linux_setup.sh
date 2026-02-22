#!/bin/bash
# Linux Deployment Script for Pinecone Assistant MCP

set -e  # Exit on error

echo "=== Pinecone Assistant MCP - Linux Setup ==="
echo ""

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_info() { echo -e "${CYAN}[INFO]${NC} $1"; }

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DOCUMENTS_DIR="$SCRIPT_DIR/combined_documents"
LOG_FILE="$SCRIPT_DIR/setup.log"
UPLOAD_SCRIPT="$SCRIPT_DIR/upload_files.py"

# Source validation helpers (hidden input, key validation, secure file permissions)
source "$SCRIPT_DIR/validation_helpers.sh"

# Logging function
log_message() {
    local level="${2:-INFO}"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $1" >> "$LOG_FILE" 2>/dev/null || true
    
    case "$level" in
        "ERROR") log_error "$1" ;;
        "WARNING") log_warning "$1" ;;
        "SUCCESS") log_success "$1" ;;
        *) log_info "$1" ;;
    esac
}

# Initialize log file
echo "=== Pinecone Assistant MCP Setup Log - $(date) ===" > "$LOG_FILE"

log_message "Starting Linux setup for Pinecone Assistant MCP"

# Step 1: Check Python
if ! command -v python3 &> /dev/null; then
    log_message "Python 3 not found. Please install Python 3.11+ first." "ERROR"
    echo -e "${YELLOW}Install with: sudo apt-get install python3 python3-pip${NC}"
    echo -e "${YELLOW}Or on Fedora: sudo dnf install python3 python3-pip${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
log_message "Python found: $PYTHON_VERSION"

# Step 2: Check/Install uv
if ! command -v uv &> /dev/null; then
    log_message "uv not found. Installing uv package manager..."
    
    # Install uv using the official installer
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        # Add uv to PATH for current session
        export PATH="$HOME/.cargo/bin:$PATH"
        
        # Verify installation
        if command -v uv &> /dev/null; then
            log_message "uv installed successfully" "SUCCESS"
        else
            log_message "Failed to install uv. Please install manually:" "ERROR"
            echo -e "${YELLOW}   curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
            exit 1
        fi
    else
        log_message "Failed to install uv automatically" "ERROR"
        exit 1
    fi
else
    UV_VERSION=$(uv --version)
    log_message "uv found: $UV_VERSION"
fi

# Step 3: Install dependencies
log_message "Installing project dependencies with uv..."
cd "$PROJECT_DIR"

if uv sync; then
    log_message "Dependencies installed successfully" "SUCCESS"
else
    log_message "Failed to install dependencies" "ERROR"
    exit 1
fi

# Step 4: Install package in editable mode  
log_message "Installing Pinecone Assistant MCP package..."
if uv pip install -e .; then
    log_message "Package installed successfully" "SUCCESS"
else
    log_message "Failed to install package" "ERROR"
    exit 1
fi

# Step 5: Verify installation
log_message "Verifying installation..."
if command -v pinecone-assistant-mcp &> /dev/null; then
    log_message "Command available: $(which pinecone-assistant-mcp)" "SUCCESS"
elif uv run python -c "import src.server; print('Import successful')" &> /dev/null; then
    log_message "Package import successful - can run with: uv run python src/server.py" "SUCCESS"
else
    log_message "Installation verification failed" "WARNING"
    log_info "You can run the server with: uv run python src/server.py"
fi

# Step 6: API Key Configuration
echo ""
log_info "API Key Configuration"
echo ""

PINECONE_API_KEY=""
if ! prompt_and_validate_pinecone_key; then
    log_message "Failed to obtain valid Pinecone API key" "ERROR"
    exit 1
fi
# PINECONE_API_KEY is now set as a global variable by prompt_and_validate_pinecone_key

log_message "API key format validated" "SUCCESS"

# Step 6b: Store API key in secure storage (~/.pinecone_api_key, chmod 600)
log_info "Storing API key in secure storage..."
export SETUP_PINECONE_KEY="$PINECONE_API_KEY"

cd "$PROJECT_DIR"
STORE_RESULT=$(uv run python -c "
import sys, os, logging
logging.disable(logging.CRITICAL)  # suppress logger output from being captured
from pathlib import Path
sys.path.insert(0, str(Path('$PROJECT_DIR') / 'src'))
try:
    from config.secure_storage import SecureStorage
    key = os.environ.get('SETUP_PINECONE_KEY', '')
    storage = SecureStorage()
    if storage.store_api_key(key):
        print('SUCCESS')
    else:
        print('ERROR')
except Exception as e:
    print(f'ERROR:{e}')
" 2>&1)

unset SETUP_PINECONE_KEY

if [[ "$STORE_RESULT" == *"SUCCESS"* ]]; then
    log_message "API key stored in ~/.pinecone_api_key (permissions: 600)" "SUCCESS"
else
    log_warning "Could not write to secure key file — API key will be placed in Claude config env instead"
    log_warning "Store result: $STORE_RESULT"
fi

# Step 7: Assistant Configuration
echo ""
log_info "Assistant Configuration"
echo ""

echo "Do you need to create a new Pinecone Assistant, or do you already have one?"
echo "  [1] Create a new assistant (via API)"
echo "  [2] I already have an assistant"
echo "  [3] Skip assistant setup (configure MCP only)"
echo ""

read -p "Enter choice (1, 2, or 3): " ASSISTANT_CHOICE

case "$ASSISTANT_CHOICE" in
    1)
        read -p "Enter a name for your new assistant (e.g., my-assistant): " ASSISTANT_NAME
        while [ -z "$ASSISTANT_NAME" ]; do
            log_error "Assistant name cannot be empty"
            read -p "Enter assistant name: " ASSISTANT_NAME
        done
        
        log_message "Creating assistant: $ASSISTANT_NAME"
        
        # Try to create assistant via Python script
        cd "$PROJECT_DIR"
        export SETUP_PINECONE_KEY="$PINECONE_API_KEY"
        CREATE_RESULT=$(uv run python -c "
import sys, os
sys.path.insert(0, 'src')
try:
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.environ['SETUP_PINECONE_KEY'])
    response = pc.assistant.create_assistant(assistant_name='$ASSISTANT_NAME')
    host = response.assistant.host.rstrip('/')
    if host.endswith('/assistant'):
        host = host[:-len('/assistant')]
    print(f'SUCCESS:{host}')
except Exception as e:
    print(f'ERROR:{str(e)}')
" 2>&1)
        unset SETUP_PINECONE_KEY

        if [[ "$CREATE_RESULT" == SUCCESS:* ]]; then
            ASSISTANT_HOST="${CREATE_RESULT#SUCCESS:}"
            log_message "Assistant created successfully!" "SUCCESS"
            log_info "Assistant name: $ASSISTANT_NAME"
            log_info "Assistant host: $ASSISTANT_HOST"
        else
            ERROR_MSG="${CREATE_RESULT#ERROR:}"
            log_message "Failed to create assistant: $ERROR_MSG" "ERROR"
            
            if [[ "$ERROR_MSG" == *"403"* || "$ERROR_MSG" == *"Forbidden"* ]]; then
                log_warning "Assistant creation via API requires a paid Pinecone plan."
                echo ""
                echo "Please create assistant manually:"
                echo "1. Go to https://app.pinecone.io/"
                echo "2. Create assistant via web UI"
                echo "3. Re-run this script and choose option [2]"
                echo ""
                read -p "Press Enter to continue with manual assistant name entry..."
                read -p "Enter your existing assistant name: " ASSISTANT_NAME
            else
                exit 1
            fi
        fi
        ;;
    2)
        read -p "Enter your existing assistant name: " ASSISTANT_NAME
        while [ -z "$ASSISTANT_NAME" ]; do
            log_error "Assistant name cannot be empty"
            read -p "Enter assistant name: " ASSISTANT_NAME
        done
        
        log_message "Using existing assistant: $ASSISTANT_NAME"
        
        # Try to get assistant info to validate and get host
        cd "$PROJECT_DIR"
        export SETUP_PINECONE_KEY="$PINECONE_API_KEY"
        INFO_RESULT=$(uv run python -c "
import sys, os
sys.path.insert(0, 'src')
try:
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.environ['SETUP_PINECONE_KEY'])
    assistant_info = pc.assistant.describe_assistant(assistant_name='$ASSISTANT_NAME')
    host = assistant_info.assistant.host.rstrip('/')
    if host.endswith('/assistant'):
        host = host[:-len('/assistant')]
    print(f'SUCCESS:{host}')
except Exception as e:
    print(f'ERROR:{str(e)}')
" 2>&1)
        unset SETUP_PINECONE_KEY

        if [[ "$INFO_RESULT" == SUCCESS:* ]]; then
            ASSISTANT_HOST="${INFO_RESULT#SUCCESS:}"
            log_message "Assistant found and validated" "SUCCESS"
            log_info "Assistant host: $ASSISTANT_HOST"
        else
            log_warning "Could not validate assistant (may still work)"
            ASSISTANT_HOST="https://prod-1-data.ke.pinecone.io"
            log_info "Using default host: $ASSISTANT_HOST"
        fi
        ;;
    3)
        log_info "Skipping assistant setup"
        read -p "Enter assistant name for MCP configuration: " ASSISTANT_NAME
        ASSISTANT_HOST="https://prod-1-data.ke.pinecone.io"
        ;;
    *)
        log_error "Invalid choice"
        exit 1
        ;;
esac

# Step 8: Document Upload (if documents exist and assistant was configured)
if [[ "$ASSISTANT_CHOICE" != "3" && (-d "$DOCUMENTS_DIR" || -f "$SCRIPT_DIR/combined_documents.zip") ]]; then
    echo ""
    log_info "Document Upload Configuration"
    echo ""
    
    if [ -f "$SCRIPT_DIR/combined_documents.zip" ]; then
        log_info "Found combined_documents.zip file"
    elif [ -d "$DOCUMENTS_DIR" ]; then
        log_info "Found combined_documents directory"
    fi
    
    read -p "Upload documents to assistant '$ASSISTANT_NAME'? (Y/n): " UPLOAD_CHOICE
    UPLOAD_CHOICE=${UPLOAD_CHOICE:-Y}
    
    if [[ "$UPLOAD_CHOICE" =~ ^[Yy]$ ]]; then
        echo ""
        echo "Are you uploading the DEFAULT USPTO MPEP documents included in this repository,"
        echo "or have you replaced them with your own custom documents?"
        echo "  [1] Default USPTO MPEP documents (included in repo)"
        echo "  [2] Custom documents (I replaced the default ones)"
        echo ""
        
        read -p "Enter choice (1 or 2): " DOCUMENT_TYPE
        
        if [ "$DOCUMENT_TYPE" = "1" ]; then
            echo ""
            log_info "Since you're using USPTO MPEP documents, we'll also configure"
            log_info "the assistant with a specialized system prompt for patent law analysis."
            log_info "(System prompt will be set automatically after upload completes.)"
            echo ""

            UPLOAD_ARGS="--use-uspto-metadata"
        else
            UPLOAD_ARGS=""
        fi
        
        log_message "Starting document upload..."
        
        cd "$SCRIPT_DIR"
        # SECURITY: pipe API key via stdin to avoid --api-key appearing in process list (ps aux)
        if echo "$PINECONE_API_KEY" | uv run python upload_files.py \
                --assistant-name "$ASSISTANT_NAME" $UPLOAD_ARGS; then
            log_message "Document upload and configuration completed successfully" "SUCCESS"
        else
            log_message "Document upload failed" "ERROR"
            log_warning "You can retry upload later with:"
            echo "cd $SCRIPT_DIR && echo \"\$PINECONE_API_KEY\" | uv run python upload_files.py --assistant-name \"$ASSISTANT_NAME\""
        fi
    else
        log_info "Skipping document upload"
    fi
fi

# Step 9: Claude Code Configuration
echo ""
log_info "Claude Code Configuration"
echo ""

read -p "Would you like to configure Claude Code integration? (Y/n): " CONFIGURE_CLAUDE
CONFIGURE_CLAUDE=${CONFIGURE_CLAUDE:-Y}

if [[ "$CONFIGURE_CLAUDE" =~ ^[Yy]$ ]]; then
    # Claude Code uses ~/.claude.json; fall back to Claude Desktop path if not found
    if [ -f "$HOME/.claude.json" ]; then
        CLAUDE_CONFIG_FILE="$HOME/.claude.json"
        CLAUDE_CONFIG_DIR="$(dirname "$CLAUDE_CONFIG_FILE")"
        log_info "Detected existing Claude Code config: $CLAUDE_CONFIG_FILE"
    else
        CLAUDE_CONFIG_DIR="$HOME/.config/Claude"
        CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
        log_info "Claude Code config location: $CLAUDE_CONFIG_FILE"
    fi

    # Create config directory if needed (skip if config is directly in $HOME)
    if [ ! -d "$CLAUDE_CONFIG_DIR" ]; then
        mkdir -p "$CLAUDE_CONFIG_DIR"
        log_info "Created config directory: $CLAUDE_CONFIG_DIR"
    fi

    if [ "$CLAUDE_CONFIG_DIR" != "$HOME" ]; then
        set_secure_directory_permissions "$CLAUDE_CONFIG_DIR"
    fi

    if [ -f "$CLAUDE_CONFIG_FILE" ]; then
        log_info "Existing Claude Code config found"
        log_info "Merging Pinecone Assistant configuration with existing config..."

        # Backup the original file
        BACKUP_FILE="${CLAUDE_CONFIG_FILE}.backup_$(date +%Y%m%d_%H%M%S)"
        cp "$CLAUDE_CONFIG_FILE" "$BACKUP_FILE"
        log_info "Backup created: $BACKUP_FILE"

        # Use Python to merge JSON — preserves all existing sections unchanged
        MERGE_SCRIPT="
import json
import sys

try:
    with open('$CLAUDE_CONFIG_FILE', 'r') as f:
        config = json.load(f)

    if 'mcpServers' not in config:
        config['mcpServers'] = {}

    # NOTE: API key is NOT in config — loaded from ~/.pinecone_api_key (chmod 600)
    config['mcpServers']['pinecone_assistant'] = {
        'command': 'uv',
        'args': [
            '--directory',
            '$PROJECT_DIR',
            'run',
            'python',
            'src/server.py'
        ],
        'env': {
            'PINECONE_ASSISTANT_HOST': '$ASSISTANT_HOST',
            'PINECONE_ASSISTANT_NAME': '$ASSISTANT_NAME',
            'PINECONE_ASSISTANT_MODEL': 'gpt-4o'
        }
    }

    with open('$CLAUDE_CONFIG_FILE', 'w') as f:
        json.dump(config, f, indent=2)

    print('SUCCESS')
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
"

        if echo "$MERGE_SCRIPT" | python3; then
            log_message "Successfully merged Pinecone Assistant configuration!" "SUCCESS"
            log_message "Your existing MCP servers have been preserved" "SUCCESS"
        else
            log_message "Failed to merge config" "ERROR"
            log_info "Please manually add the configuration to $CLAUDE_CONFIG_FILE"
            exit 1
        fi

    else
        # Create new config file using Python for safe JSON generation
        log_info "Creating new Claude Code config..."

        CREATE_CONFIG_SCRIPT="
import json
import sys

try:
    # NOTE: API key is NOT in config — loaded from ~/.pinecone_api_key (chmod 600)
    config = {
        'mcpServers': {
            'pinecone_assistant': {
                'command': 'uv',
                'args': [
                    '--directory',
                    '$PROJECT_DIR',
                    'run',
                    'python',
                    'src/server.py'
                ],
                'env': {
                    'PINECONE_ASSISTANT_HOST': '$ASSISTANT_HOST',
                    'PINECONE_ASSISTANT_NAME': '$ASSISTANT_NAME',
                    'PINECONE_ASSISTANT_MODEL': 'gpt-4o'
                }
            }
        }
    }

    with open('$CLAUDE_CONFIG_FILE', 'w') as f:
        json.dump(config, f, indent=2)

    print('SUCCESS')
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
"

        if echo "$CREATE_CONFIG_SCRIPT" | python3; then
            log_message "Created new Claude Code config" "SUCCESS"
        else
            log_error "Failed to create config file"
            exit 1
        fi
    fi

    # Set restrictive permissions on config file
    if [ -f "$CLAUDE_CONFIG_FILE" ]; then
        set_secure_file_permissions "$CLAUDE_CONFIG_FILE"
    fi

    log_message "Claude Code configuration complete!" "SUCCESS"
fi

# Step 10: Final Summary
echo ""
log_message "Linux setup complete!" "SUCCESS"
log_warning "Please restart Claude Code to load the MCP server (claude mcp list to verify)"
echo ""

log_info "Configuration Summary:"
if [ -f "$HOME/.pinecone_api_key" ]; then
    log_success "API Key: Stored in secure storage (~/.pinecone_api_key, permissions: 600)"
    log_success "Security: API key NOT written to Claude Desktop config file"
else
    log_warning "API Key: Secure file storage unavailable — check Claude config for env var fallback"
fi
log_success "Assistant Name: $ASSISTANT_NAME"
if [ -n "$ASSISTANT_HOST" ]; then
    log_success "Assistant Host: $ASSISTANT_HOST"
fi
log_success "Installation Directory: $PROJECT_DIR"
echo ""

log_info "Available MCP Tools:"
echo "  - assistant_context (raw document retrieval - START HERE)"
echo "  - assistant_strategic_multi_search_context (strategic raw documents)"
echo "  - assistant_strategic_multi_search (AI-powered strategic search)"
echo "  - assistant_chat (direct AI conversation)"
echo "  - update_configuration (switch assistants mid-conversation)"
echo ""

log_info "Test the server:"
echo "  uv run python src/server.py"
echo ""

log_info "Test with Claude Code:"
echo "  Ask Claude: 'Use assistant_context to search for [your topic]'"
echo ""
log_info "Verify MCP is running:"
echo "  claude mcp list"
echo ""

if [ -f "$LOG_FILE" ]; then
    log_info "Setup log saved to: $LOG_FILE"
fi

log_message "Setup completed successfully" "SUCCESS"