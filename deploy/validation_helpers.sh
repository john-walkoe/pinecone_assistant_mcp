#!/bin/bash
# validation_helpers.sh
# API Key and Input Validation Functions for Pinecone Assistant MCP Deployment
#
# Security: Validates API key formats and uses hidden input to prevent key exposure
# Usage: source this file in deployment scripts
#
# Date: 2026-02-21
# Adapted from: USPTO PFW MCP validation_helpers.sh

# Color codes for output (guard against re-definition)
if [[ -z "$GREEN" ]]; then
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    CYAN='\033[0;36m'
    NC='\033[0m'
fi

# Logging functions (if not already defined by caller)
if ! type log_error &>/dev/null; then
    log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
fi
if ! type log_warning &>/dev/null; then
    log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fi
if ! type log_success &>/dev/null; then
    log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
fi
if ! type log_info &>/dev/null; then
    log_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
fi

# ============================================
# Secure Input Functions
# ============================================

# Read API key with hidden input (no echo)
read_api_key_secure() {
    local prompt="$1"
    local var_name="$2"
    local api_key=""

    read -r -s -p "$prompt: " api_key
    echo  # New line after hidden input

    # SECURITY: printf -v avoids eval injection if api_key contains single quotes
    printf -v "$var_name" '%s' "$api_key"
}

# ============================================
# Pinecone API Key Validation
# ============================================

# Validate Pinecone Assistant API Key
# Format: starts with 'pcsk_', min 32 chars, alphanumeric + _ + -
validate_pinecone_api_key() {
    local key="$1"
    local key_length=${#key}

    if [[ -z "$key" ]]; then
        log_error "Pinecone API key is empty"
        return 1
    fi

    if [[ ! "$key" =~ ^pcsk_ ]]; then
        log_error "Pinecone API key must start with 'pcsk_'"
        return 1
    fi

    if [[ $key_length -lt 32 ]]; then
        log_error "Pinecone API key appears too short (got ${key_length} chars, minimum 32)"
        return 1
    fi

    if ! [[ "$key" =~ ^pcsk_[A-Za-z0-9_-]+$ ]]; then
        log_error "Pinecone API key contains invalid characters (only alphanumeric, _ and - allowed after 'pcsk_')"
        return 1
    fi

    if check_placeholder_pattern "$key" "Pinecone"; then
        return 1
    fi

    log_success "Pinecone API key format validated"
    return 0
}

# Check for common placeholder patterns
check_placeholder_pattern() {
    local key="$1"
    local key_type="$2"

    local placeholder_patterns=(
        "your.*key"
        "your.*api"
        "api.*key.*here"
        "placeholder"
        "insert.*key"
        "replace.*me"
        "changeme"
        "put.*key.*here"
        "add.*key.*here"
        "enter.*key"
        "paste.*key"
        "fill.*in"
        "pcsk_xxx"
        "pcsk_your"
    )

    local key_lower
    key_lower=$(echo "$key" | tr '[:upper:]' '[:lower:]')

    for pattern in "${placeholder_patterns[@]}"; do
        if echo "$key_lower" | grep -qiE "$pattern"; then
            log_error "Detected placeholder pattern in $key_type API key"
            log_error "Please use your actual API key, not a placeholder"
            return 0  # 0 = pattern found (error condition)
        fi
    done

    return 1  # 1 = no placeholder found (success)
}

# ============================================
# Existing Key Detection
# ============================================

# Check if Pinecone API key exists in secure storage
check_existing_pinecone_key() {
    if [[ -f "$HOME/.pinecone_api_key" ]]; then
        return 0
    else
        return 1
    fi
}

# Load existing key from secure storage via Python
load_existing_pinecone_key() {
    python3 << 'EOF'
import sys
from pathlib import Path
key_file = Path.home() / ".pinecone_api_key"
try:
    if key_file.exists():
        key = key_file.read_text().strip()
        if key.startswith("pcsk_") and len(key) >= 32:
            print(key)
            sys.exit(0)
    sys.exit(1)
except Exception:
    sys.exit(1)
EOF
}

# Ask user whether to reuse an existing key
prompt_use_existing_key() {
    local masked_key="$1"
    echo ""
    log_success "Detected existing Pinecone API key in secure storage"
    log_info "Key (masked): $masked_key"
    echo ""
    read -p "Would you like to use this existing key? (Y/n): " USE_EXISTING
    USE_EXISTING=${USE_EXISTING:-Y}
    if [[ "$USE_EXISTING" =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

# ============================================
# Full Prompt + Validate Flow
# ============================================

# Prompt for Pinecone API key with hidden input and validation.
# Sets the global PINECONE_API_KEY variable on success.
# Returns 0 on success, 1 on failure.
# IMPORTANT: Do NOT capture this with $() — it sets a global variable directly
# to avoid stdout capture mixing log messages into the key value.
prompt_and_validate_pinecone_key() {
    local key=""
    local max_attempts=3
    local attempt=0

    # Check for existing key first
    if check_existing_pinecone_key; then
        log_info "Checking existing Pinecone API key in secure storage..."
        local existing_key
        existing_key=$(load_existing_pinecone_key)
        if [[ $? -eq 0 && -n "$existing_key" ]]; then
            local masked_key
            masked_key=$(mask_api_key "$existing_key")
            if prompt_use_existing_key "$masked_key"; then
                log_success "Using existing Pinecone API key from secure storage"
                PINECONE_API_KEY="$existing_key"
                return 0
            else
                log_info "You chose to enter a new Pinecone API key"
                log_warning "This will OVERWRITE the existing key in secure storage"
                read -p "Are you sure? (y/N): " CONFIRM_OVERWRITE
                if [[ ! "$CONFIRM_OVERWRITE" =~ ^[Yy]$ ]]; then
                    log_info "Keeping existing key"
                    PINECONE_API_KEY="$existing_key"
                    return 0
                fi
            fi
        else
            log_warning "Existing key file found but could not load — enter a new key"
        fi
    fi

    # Prompt for new key
    log_info "Get your API key from: https://app.pinecone.io/"
    echo ""

    while [[ $attempt -lt $max_attempts ]]; do
        ((attempt++))

        read_api_key_secure "Enter your Pinecone API key (starts with pcsk_)" key

        if [[ -z "$key" ]]; then
            log_error "API key cannot be empty"
            [[ $attempt -lt $max_attempts ]] && log_info "Attempt $attempt of $max_attempts"
            continue
        fi

        if validate_pinecone_api_key "$key"; then
            PINECONE_API_KEY="$key"
            return 0
        else
            [[ $attempt -lt $max_attempts ]] && log_warning "Attempt $attempt of $max_attempts — please try again"
        fi
    done

    log_error "Failed to provide a valid Pinecone API key after $max_attempts attempts"
    return 1
}

# ============================================
# Utility Functions
# ============================================

# Mask API key — show only last 5 characters
mask_api_key() {
    local key="$1"
    local visible_chars="${2:-5}"

    if [[ -z "$key" ]]; then
        echo "[Not set]"
    elif [[ ${#key} -le $visible_chars ]]; then
        echo "***"
    else
        local key_length=${#key}
        local masked_length=$(( key_length - visible_chars ))
        local asterisks
        asterisks=$(printf '*%.0s' $(seq 1 $masked_length))
        echo "${asterisks}${key: -$visible_chars}"
    fi
}

# Set restrictive file permissions (owner read/write only)
set_secure_file_permissions() {
    local file="$1"
    if chmod 600 "$file" 2>/dev/null; then
        log_success "Set permissions 600 on: $file"
    else
        log_warning "Could not set permissions on: $file"
    fi
}

# Set restrictive directory permissions (owner only)
set_secure_directory_permissions() {
    local dir="$1"
    if chmod 700 "$dir" 2>/dev/null; then
        log_success "Set permissions 700 on: $dir"
    else
        log_warning "Could not set directory permissions on: $dir"
    fi
}

# Public API summary (for documentation):
# - prompt_and_validate_pinecone_key  : full flow (detect existing, hidden input, validate)
# - validate_pinecone_api_key         : format validation only
# - read_api_key_secure               : hidden input only
# - mask_api_key                      : mask for display
# - set_secure_file_permissions       : chmod 600
# - set_secure_directory_permissions  : chmod 700
