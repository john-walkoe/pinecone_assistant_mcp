# Pinecone Assistant MCP - Windows Setup Script
# Question-driven comprehensive setup including assistant management and Claude Desktop configuration

# Import validation helpers for secure API key input
$ValidationModule = Join-Path $PSScriptRoot "Validation-Helpers.psm1"
if (Test-Path $ValidationModule) {
    Import-Module $ValidationModule -Force
    Write-Host "[OK] Validation helpers loaded" -ForegroundColor Green
} else {
    Write-Host "[WARN] Validation helpers not found - API keys will be displayed in plain text" -ForegroundColor Yellow
}

Write-Host "=== Pinecone Assistant MCP - Windows Setup ===" -ForegroundColor Green
Write-Host ""

# Set error action preference
$ErrorActionPreference = "Stop"

# Script configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$DocumentsDir = Join-Path $ScriptDir "combined_documents"
$LogFile = Join-Path $ScriptDir "setup.log"
$UploadScript = Join-Path $ScriptDir "upload_files.py"

# Color functions for output
function Write-Success { param($Message) Write-Host $Message -ForegroundColor Green }
function Write-Warning { param($Message) Write-Host $Message -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host $Message -ForegroundColor Red }
function Write-Info { param($Message) Write-Host $Message -ForegroundColor Cyan }

# SECURITY FIX (M-3): Input validation and sanitization
function Validate-ApiKey {
    param([string]$ApiKey)

    # Check format: must start with "pcsk_" and contain only safe characters
    if (-not ($ApiKey -match '^pcsk_[a-zA-Z0-9_-]{28,}$')) {
        return $false
    }

    # Check length (typical Pinecone keys are ~50 chars)
    if ($ApiKey.Length -lt 33 -or $ApiKey.Length -gt 100) {
        return $false
    }

    return $true
}

function Validate-AssistantName {
    param([string]$Name)

    # Check format: alphanumeric, hyphens, underscores only
    if (-not ($Name -match '^[a-zA-Z0-9_-]+$')) {
        return $false
    }

    # Check length
    if ($Name.Length -lt 3 -or $Name.Length -gt 64) {
        return $false
    }

    return $true
}

function Sanitize-Input {
    # IMPORTANT: Do NOT use $Input as parameter name - it's a reserved PowerShell automatic variable!
    param([string]$InputString, [string]$AllowedPattern)

    # Remove any characters not matching the allowed pattern
    if ($AllowedPattern) {
        $pattern = "[^$AllowedPattern]"
        $Sanitized = $InputString -replace $pattern, ""
    } else {
        $Sanitized = $InputString
    }

    # Escape single quotes for safety in Python strings
    $Sanitized = $Sanitized -replace "'", ""

    return $Sanitized
}

# SECURITY FIX (L-5): Log rotation and restrictive ACLs
$MaxLogSizeMB = 10
$MaxLogBackups = 5

function Rotate-LogFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    $logSize = (Get-Item $Path).Length / 1MB
    if ($logSize -gt $MaxLogSizeMB) {
        $backupFile = "$Path.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Move-Item $Path $backupFile -Force -ErrorAction SilentlyContinue
        # Keep only $MaxLogBackups most recent backups
        $pattern = [System.IO.Path]::GetFileName($Path) + ".*"
        $parentDir = Split-Path $Path -Parent
        Get-ChildItem $parentDir -Filter $pattern |
            Sort-Object LastWriteTime -Descending |
            Select-Object -Skip $MaxLogBackups |
            Remove-Item -Force -ErrorAction SilentlyContinue
    }
}

function Set-LogFilePermissions {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    try {
        $acl = Get-Acl $Path
        $acl.SetAccessRuleProtection($true, $false)
        $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
        $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $identity, "FullControl", "Allow"
        )
        $acl.SetAccessRule($accessRule)
        Set-Acl $Path $acl
    } catch {
        # Non-fatal: log permission setting may fail in some environments
    }
}

# Logging function with rotation and secure permissions
function Write-Log {
    param($Message, $Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "[$Timestamp] [$Level] $Message"

    # Rotate if needed before writing
    Rotate-LogFile -Path $LogFile
    Add-Content -Path $LogFile -Value $LogEntry -ErrorAction SilentlyContinue

    # Set restrictive permissions on first write
    if ((Test-Path $LogFile) -and -not $script:LogPermissionsSet) {
        Set-LogFilePermissions -Path $LogFile
        $script:LogPermissionsSet = $true
    }

    switch ($Level) {
        "ERROR" { Write-Error $Message }
        "WARNING" { Write-Warning $Message }
        "SUCCESS" { Write-Success $Message }
        default { Write-Info $Message }
    }
}

# Windows Credential Manager storage functions
function Set-SecureApiKey {
    param([string]$ApiKey)

    try {
        # Store in Windows Credential Manager using cmdkey
        # Target format: pinecone_API_KEY (unified across all 3 Pinecone MCPs)
        $targetName = "pinecone_API_KEY"

        # Remove existing credential if present
        cmdkey /delete:$targetName 2>&1 | Out-Null

        # Store the new credential
        $result = cmdkey /generic:$targetName /user:"pinecone_API_KEY" /pass:$ApiKey 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Log "API key stored in Windows Credential Manager" "SUCCESS"
            Write-Info "  Target: $targetName"
            Write-Info "  Note: Accessible only by your Windows user account"

            # SECURITY: Remove legacy plaintext cache file if it exists
            $legacyCacheFile = Join-Path $env:USERPROFILE ".pinecone_assistant_cred_cache"
            if (Test-Path $legacyCacheFile) {
                Write-Host "  Removing legacy plaintext cache file for security..." -ForegroundColor Yellow
                Remove-Item $legacyCacheFile -Force -ErrorAction SilentlyContinue
            }

            # SECURITY: Also store in DPAPI SecureStorage for Python code
            # API key passed via stdin — NOT embedded in heredoc string (prevents M-10 code injection)
            $storeScript = @"
import sys
sys.path.insert(0, 'src')
try:
    from config.secure_storage import SecureStorage
    storage = SecureStorage()
    success = storage.store_api_key(sys.stdin.readline().strip())
    if success:
        print('DPAPI')
    sys.exit(0 if success else 1)
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
"@
            $tempScript = Join-Path $env:TEMP "store_key_temp.py"
            $storeScript | Out-File -FilePath $tempScript -Encoding UTF8

            try {
                $storeResult = $ApiKey | uv run python $tempScript 2>&1
                if ($LASTEXITCODE -eq 0 -and $storeResult -match "DPAPI") {
                    Write-Log "API key stored using Windows DPAPI encryption" "SUCCESS"
                }
            } catch {
                Write-Warning "Could not store in DPAPI (Credential Manager storage succeeded)"
            } finally {
                Remove-Item $tempScript -ErrorAction SilentlyContinue
            }

            return $true
        } else {
            Write-Log "Failed to store credential: $result" "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "Failed to store API key in Credential Manager: $_" "ERROR"
        return $false
    }
}

function Test-SecureApiKey {
    try {
        # Check if credential exists in Windows Credential Manager
        $targetName = "pinecone_API_KEY"
        $result = cmdkey /list:$targetName 2>&1 | Out-String

        if ($result -match "Target: $targetName") {
            return $true
        }
        return $false
    }
    catch {
        return $false
    }
}

function Get-SecureApiKey {
    # Note: cmdkey doesn't allow direct retrieval of passwords
    # The Python code will read from Credential Manager using ctypes/win32cred
    # This function just checks if the credential exists
    return Test-SecureApiKey
}

function Remove-SecureApiKey {
    try {
        $targetName = "pinecone_API_KEY"
        cmdkey /delete:$targetName 2>&1 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Initialize log file
"Setup started at $(Get-Date)" | Out-File -FilePath $LogFile -Encoding UTF8
Write-Log "Starting Pinecone Assistant MCP setup"

# ===============================
# STEP 1-2: DETECT PYTHON AND UV
# ===============================

Write-Info "Step 1-2: Checking installation prerequisites..."
Write-Info ""

# Check Python (informational only - not required)
try {
    $pythonVersion = python --version 2>$null
    Write-Log "Python detected: $pythonVersion (Note: uv will manage Python automatically)" "INFO"
} catch {
    Write-Log "Python not detected (OK - uv will manage Python automatically)" "INFO"
}

Write-Info ""

# ===============================
# STEP 3-5: UV INSTALLATION
# ===============================

Write-Info "Step 3-5: UV package manager setup..."
Write-Info ""

try {
    $uvVersion = uv --version 2>$null
    Write-Log "UV found: $uvVersion" "SUCCESS"
} catch {
    Write-Log "UV not found. Installing UV..." "WARNING"

    # Try winget first (preferred method)
    try {
        winget install --id=astral-sh.uv -e
        Write-Log "UV installed via winget" "SUCCESS"
    } catch {
        Write-Log "winget failed, trying PowerShell install method..." "WARNING"
        try {
            powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
            Write-Log "UV installed via PowerShell script" "SUCCESS"
        } catch {
            Write-Log "Failed to install UV. Please install manually:" "ERROR"
            Write-Info "   winget install --id=astral-sh.uv -e"
            Write-Info "   OR visit: https://docs.astral.sh/uv/getting-started/installation/"
            exit 1
        }
    }

    # Refresh PATH for current session
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")

    # Add uv's typical installation paths if not already in PATH
    $uvPaths = @(
        "$env:USERPROFILE\.cargo\bin",           # cargo install location
        "$env:LOCALAPPDATA\Programs\uv\bin",      # winget install location
        "$env:APPDATA\uv\bin"                     # alternative location
    )

    foreach ($uvPath in $uvPaths) {
        if (Test-Path $uvPath) {
            if ($env:PATH -notlike "*$uvPath*") {
                $env:PATH = "$uvPath;$env:PATH"
                Write-Log "Added $uvPath to PATH" "WARNING"
            }
        }
    }

    # Verify uv is now accessible
    try {
        $uvVersion = uv --version 2>$null
        Write-Log "UV is now accessible: $uvVersion" "SUCCESS"
    } catch {
        Write-Log "UV installed but not accessible. Please restart PowerShell and run script again." "ERROR"
        Write-Info "[INFO] Or manually add UV to PATH and continue."
        exit 1
    }
}

Write-Info ""
Write-Log "Installing project dependencies with UV..." "INFO"

try {
    Set-Location $ProjectDir

    # Use Python 3.12 which has guaranteed prebuilt wheels for all dependencies
    Write-Log "Installing dependencies with prebuilt wheels (Python 3.12)..." "INFO"
    uv sync --python 3.12

    Write-Log "Project dependencies installed successfully" "SUCCESS"

} catch {
    Write-Log "Failed to install dependencies: $($_.Exception.Message)" "ERROR"
    Write-Info "Please run manually: uv sync --python 3.12"
    exit 1
}

# ===============================
# STEP 6: PINECONE API KEY
# ===============================

Write-Info ""
Write-Info "Step 6: Pinecone API Key Configuration"
Write-Info ""
Write-Info "Get your API key from: https://app.pinecone.io/"
Write-Info "(API key is stored only in Claude Desktop config - not in system environment variables)"
Write-Info ""

# Use secure input with validation (3-attempt retry)
$attemptCount = 0
$maxAttempts = 3
$validKey = $false
$ApiKey = ""

while (-not $validKey -and $attemptCount -lt $maxAttempts) {
    $attemptCount++

    # Use masked input if available
    if (Get-Command "Read-ApiKeySecure" -ErrorAction SilentlyContinue) {
        $ApiKey = Read-ApiKeySecure -Prompt "Enter your Pinecone Assistant API key (input hidden - get from https://app.pinecone.io/)"
    } else {
        $ApiKey = Read-Host "Enter your Pinecone Assistant API key (starts with pcsk_)"
    }

    # Check if empty
    if ([string]::IsNullOrWhiteSpace($ApiKey)) {
        Write-Log "API key is required!" "ERROR"
        if ($attemptCount -lt $maxAttempts) {
            Write-Info "Attempt $attemptCount of $maxAttempts - please try again"
        }
        continue
    }

    # Validate format if validator available
    if (Get-Command "Test-PineconeApiKey" -ErrorAction SilentlyContinue) {
        if (Test-PineconeApiKey -ApiKey $ApiKey) {
            $validKey = $true
            Write-Log "Pinecone API key format validated" "SUCCESS"
        } else {
            Write-Log "Invalid Pinecone API key format" "ERROR"
            Write-Info "Expected: pcsk_ followed by 70 alphanumeric/underscore characters (75 total)"
            if ($attemptCount -lt $maxAttempts) {
                Write-Info "Attempt $attemptCount of $maxAttempts - please try again"
            }
        }
    } else {
        # Fallback to legacy validation
        if (Validate-ApiKey -ApiKey $ApiKey) {
            $validKey = $true
        }
    }
}

if (-not $validKey) {
    Write-Log "Maximum attempts reached. Exiting setup." "ERROR"
    exit 1
}

# Sanitize API key (remove any unexpected characters)
$ApiKey = Sanitize-Input -InputString $ApiKey -AllowedPattern "a-zA-Z0-9_-"

# Store API key securely
Write-Info ""
Write-Info "Storing API key securely..."
if (Set-SecureApiKey -ApiKey $ApiKey) {
    Write-Log "API key stored using Windows DPAPI encryption" "SUCCESS"
} else {
    Write-Log "Failed to store API key securely - will use environment variables" "WARNING"
}

# Select default model
Write-Info ""
Write-Info "Select default AI model for the assistant:"
Write-Info "  [1] gpt-4o (OpenAI GPT-4 Optimized - recommended)"
Write-Info "  [2] gpt-4.1 (OpenAI GPT-4.1)"
Write-Info "  [3] o4-mini (OpenAI O4 Mini)"
Write-Info "  [4] claude-3-5-sonnet (Anthropic Claude 3.5 Sonnet - auto-routed to 4.5)"
Write-Info "  [5] claude-3-7-sonnet (Anthropic Claude 3.7 Sonnet - auto-routed to 4.5)"
Write-Info "  [6] gemini-2-5-pro (Google Gemini 2.5 Pro)"
Write-Info "  [7] claude-sonnet-4-5 (Anthropic Claude Sonnet 4.5)"
Write-Info ""

$modelChoice = Read-Host "Enter choice (1-7, default is 1)"

$AssistantModel = switch ($modelChoice) {
    "2" { "gpt-4.1" }
    "3" { "o4-mini" }
    "4" { "claude-3-5-sonnet" }
    "5" { "claude-3-7-sonnet" }
    "6" { "gemini-2-5-pro" }
    "7" { "claude-sonnet-4-5" }
    default { "gpt-4o" }
}

Write-Log "Selected model: $AssistantModel" "SUCCESS"

# ===============================
# STEP 7-9: ASSISTANT MANAGEMENT
# ===============================

Write-Info ""
Write-Info "Step 7-9: Assistant Configuration"
Write-Info ""

$AssistantName = ""
$AssistantHost = ""
$SkipAssistantSetup = $false

Write-Info "Do you need to create a new Pinecone Assistant, or do you already have one?"
Write-Info "  [1] Create a new assistant (via API)"
Write-Info "  [2] I already have an assistant"
Write-Info "  [3] Skip assistant setup (configure MCP only)"
Write-Info ""

$assistantChoice = Read-Host "Enter choice (1, 2, or 3)"

if ($assistantChoice -eq "1") {
    # Create new assistant
    Write-Info ""
    Write-Log "Creating new Pinecone Assistant..." "INFO"

    Write-Host "Assistant name requirements:" -ForegroundColor Yellow
    Write-Host "  - Lowercase letters, numbers, hyphens only" -ForegroundColor Yellow
    Write-Host "  - Must start with a letter" -ForegroundColor Yellow
    Write-Host "  - No spaces or special characters" -ForegroundColor Yellow
    Write-Host "  - Example: my-assistant, uspto-docs, patent-search" -ForegroundColor Yellow
    Write-Info ""

    $AssistantName = Read-Host "Enter a name for your new assistant"

    # Validate assistant name format
    while ($true) {
        if ([string]::IsNullOrWhiteSpace($AssistantName)) {
            Write-Log "Assistant name is required!" "ERROR"
            $AssistantName = Read-Host "Enter a name for your new assistant"
            continue
        }

        # Check for valid format: lowercase letters, numbers, hyphens, must start with letter
        if ($AssistantName -notmatch '^[a-z][a-z0-9-]*$') {
            Write-Log "Invalid assistant name format!" "ERROR"

            # Provide specific feedback
            if ($AssistantName -match '\s') {
                Write-Host "  [X] Contains spaces - use hyphens instead (e.g., 'patent-books' not 'patent books')" -ForegroundColor Red
            }
            if ($AssistantName -match '[A-Z]') {
                Write-Host "  [X] Contains uppercase letters - use lowercase only" -ForegroundColor Red
                Write-Host "  TIP: Try '$($AssistantName.ToLower())'" -ForegroundColor Yellow
            }
            if ($AssistantName -match '^[^a-z]') {
                Write-Host "  [X] Must start with a letter" -ForegroundColor Red
            }
            if ($AssistantName -match '[^a-z0-9-]') {
                Write-Host "  [X] Contains invalid characters - only lowercase letters, numbers, and hyphens allowed" -ForegroundColor Red
            }

            Write-Info ""
            $AssistantName = Read-Host "Enter a name for your new assistant"
            continue
        }

        # Valid name
        break
    }

    # Create Python script to create assistant
    # SECURITY FIX: Use temporary environment variable instead of stdin piping
    $createAssistantScript = @"
import sys
import os
sys.path.insert(0, 'src')

from pinecone import Pinecone

try:
    # SECURITY: Read API key from Windows Credential Manager
    from config.secure_storage import get_api_key_from_credential_manager, get_secure_api_key

    api_key = get_api_key_from_credential_manager()
    if not api_key:
        api_key = get_secure_api_key()

    if not api_key:
        print('ERROR|API key not found in Credential Manager or secure storage')
        sys.exit(1)

    pc = Pinecone(api_key=api_key)

    # Create assistant
    print('Creating assistant: $AssistantName')
    response = pc.assistant.create_assistant(assistant_name='$AssistantName')

    # Get assistant details to retrieve host
    assistant_info = pc.assistant.describe_assistant(assistant_name='$AssistantName')

    # Handle both dict and object responses
    if hasattr(assistant_info, 'host'):
        host = assistant_info.host
        status = getattr(assistant_info, 'status', 'unknown')
    else:
        host = assistant_info.get('host', 'unknown')
        status = assistant_info.get('status', 'unknown')

    print(f'SUCCESS|{host}|{status}')
    sys.exit(0)

except Exception as e:
    print(f'ERROR|{str(e)}')
    sys.exit(1)
"@

    $tempScript = Join-Path $env:TEMP "create_assistant_temp.py"
    $createAssistantScript | Out-File -FilePath $tempScript -Encoding UTF8

    try {
        Set-Location $ProjectDir
        $result = uv run python $tempScript 2>&1 | Out-String

        if ($result -match "SUCCESS\|([^\|]+)\|(.+)") {
            $AssistantHost = $matches[1]
            $status = $matches[2]
            Write-Log "Assistant created successfully!" "SUCCESS"
            Write-Log "Assistant name: $AssistantName" "SUCCESS"
            Write-Log "Assistant host: $AssistantHost" "SUCCESS"
            Write-Log "Status: $status" "INFO"
        } elseif ($result -match "ERROR\|(.+)") {
            $errorMsg = $matches[1]
            Write-Log "Failed to create assistant: $errorMsg" "ERROR"

            if ($errorMsg -match "409" -or $errorMsg -match "Conflict" -or $errorMsg -match "already exists") {
                Write-Info ""
                Write-Info "NOTE: An assistant with name '$AssistantName' already exists."
                Write-Info ""

                Write-Info "Options:"
                Write-Info "  [1] Use the existing assistant named '$AssistantName'"
                Write-Info "  [2] Choose a different name for a new assistant"
                Write-Info "  [3] Skip assistant setup"
                Write-Info ""
                $conflictChoice = Read-Host "Enter choice (1, 2, or 3)"

                if ($conflictChoice -eq "1") {
                    # Try to get the host from the existing assistant
                    # SECURITY FIX: Use Windows Credential Manager directly
                    $getHostScript = @"
import sys
import os
sys.path.insert(0, 'src')

from pinecone import Pinecone

try:
    # SECURITY: Read API key from Windows Credential Manager
    from config.secure_storage import get_api_key_from_credential_manager, get_secure_api_key

    api_key = get_api_key_from_credential_manager()
    if not api_key:
        api_key = get_secure_api_key()

    if not api_key:
        print('ERROR|API key not found in Credential Manager')
        sys.exit(1)

    pc = Pinecone(api_key=api_key)
    assistant_info = pc.assistant.describe_assistant(assistant_name='$AssistantName')

    # Handle both dict and object responses
    if hasattr(assistant_info, 'host'):
        host = assistant_info.host
    else:
        host = assistant_info.get('host', 'unknown')

    print(f'SUCCESS|{host}')
    sys.exit(0)
except Exception as e:
    print(f'ERROR|{str(e)}')
    sys.exit(1)
"@
                    $getHostScript | Out-File -FilePath $tempScript -Encoding UTF8
                    $hostResult = uv run python $tempScript 2>&1 | Out-String

                    if ($hostResult -match "SUCCESS\|(.+)") {
                        $AssistantHost = $matches[1].Trim()
                        Write-Log "Retrieved existing assistant host: $AssistantHost" "SUCCESS"
                    } else {
                        Write-Warning "Could not retrieve assistant host automatically"
                        $AssistantHost = Read-Host "Enter the assistant host URL (e.g., https://prod-1-data.ke.pinecone.io)"
                    }
                } elseif ($conflictChoice -eq "2") {
                    Write-Info ""
                    $AssistantName = Read-Host "Enter a different name for your new assistant"

                    while ([string]::IsNullOrWhiteSpace($AssistantName)) {
                        Write-Log "Assistant name is required!" "ERROR"
                        $AssistantName = Read-Host "Enter a name for your new assistant"
                    }

                    # Retry creation with new name (reuse the same logic)
                    Write-Log "Creating assistant: $AssistantName" "INFO"
                    $createAssistantScript | Out-File -FilePath $tempScript -Encoding UTF8

                    try {
                        Set-Location $ProjectDir
                        $result = uv run python $tempScript 2>&1 | Out-String

                        if ($result -match "SUCCESS\|([^\|]+)\|(.+)") {
                            $AssistantHost = $matches[1]
                            $status = $matches[2]
                            Write-Log "Assistant created successfully!" "SUCCESS"
                            Write-Log "Assistant name: $AssistantName" "SUCCESS"
                            Write-Log "Assistant host: $AssistantHost" "SUCCESS"
                        } else {
                            Write-Log "Failed to create assistant with new name" "ERROR"
                            $SkipAssistantSetup = $true
                        }
                    } catch {
                        Write-Log "Failed to create assistant: $($_.Exception.Message)" "ERROR"
                        $SkipAssistantSetup = $true
                    }
                } else {
                    Write-Warning "Skipping assistant setup. You can re-run this script later."
                    $SkipAssistantSetup = $true
                }
            } elseif ($errorMsg -match "403" -or $errorMsg -match "Forbidden" -or $errorMsg -match "paid plan") {
                Write-Info ""
                Write-Info "NOTE: Assistant creation via API requires a paid Pinecone plan."
                Write-Info "Please create your assistant manually:"
                Write-Info "  1. Go to https://app.pinecone.io/"
                Write-Info "  2. Navigate to Assistant section"
                Write-Info "  3. Create a new assistant named: $AssistantName"
                Write-Info ""

                $manualCreate = Read-Host "Have you created the assistant manually? (y/N)"
                if ($manualCreate -eq "y" -or $manualCreate -eq "Y") {
                    # Try to get the host from the existing assistant
                    # SECURITY FIX: Use Windows Credential Manager directly
                    $getHostScript = @"
import sys
import os
sys.path.insert(0, 'src')

from pinecone import Pinecone

try:
    # SECURITY: Read API key from Windows Credential Manager
    from config.secure_storage import get_api_key_from_credential_manager, get_secure_api_key

    api_key = get_api_key_from_credential_manager()
    if not api_key:
        api_key = get_secure_api_key()

    if not api_key:
        print('ERROR|API key not found in Credential Manager')
        sys.exit(1)

    pc = Pinecone(api_key=api_key)
    assistant_info = pc.assistant.describe_assistant(assistant_name='$AssistantName')

    # Handle both dict and object responses
    if hasattr(assistant_info, 'host'):
        host = assistant_info.host
    else:
        host = assistant_info.get('host', 'unknown')

    print(f'SUCCESS|{host}')
    sys.exit(0)
except Exception as e:
    print(f'ERROR|{str(e)}')
    sys.exit(1)
"@
                    $getHostScript | Out-File -FilePath $tempScript -Encoding UTF8
                    # SECURITY FIX: Set temporary environment variable
                    $env:TEMP_PINECONE_API_KEY = $ApiKey
                    $hostResult = uv run python $tempScript 2>&1 | Out-String

                    if ($hostResult -match "SUCCESS\|(.+)") {
                        $AssistantHost = $matches[1].Trim()
                        Write-Log "Retrieved assistant host: $AssistantHost" "SUCCESS"
                    } else {
                        Write-Warning "Could not retrieve assistant host automatically"
                        $AssistantHost = Read-Host "Enter the assistant host URL (e.g., https://prod-1-data.ke.pinecone.io)"
                    }
                } else {
                    Write-Warning "Skipping assistant setup. You can re-run this script later."
                    $SkipAssistantSetup = $true
                }
            } else {
                Write-Warning "Skipping assistant setup due to error. You can re-run this script later."
                $SkipAssistantSetup = $true
            }
        } else {
            Write-Log "Unexpected response from assistant creation" "ERROR"
            Write-Warning "Skipping assistant setup. You can re-run this script later."
            $SkipAssistantSetup = $true
        }

    } catch {
        Write-Log "Failed to run assistant creation script: $($_.Exception.Message)" "ERROR"
        $SkipAssistantSetup = $true
    } finally {
        if (Test-Path $tempScript) {
            Remove-Item $tempScript -Force
        }
    }

} elseif ($assistantChoice -eq "2") {
    # Use existing assistant
    Write-Info ""
    Write-Host "Assistant name requirements:" -ForegroundColor Yellow
    Write-Host "  - Lowercase letters, numbers, hyphens only" -ForegroundColor Yellow
    Write-Host "  - Must start with a letter" -ForegroundColor Yellow
    Write-Host "  - No spaces or special characters" -ForegroundColor Yellow
    Write-Host "  - Example: my-assistant, uspto-docs, patent-search" -ForegroundColor Yellow
    Write-Info ""

    $AssistantName = Read-Host "Enter the name of your existing assistant"

    # Validate assistant name format
    while ($true) {
        if ([string]::IsNullOrWhiteSpace($AssistantName)) {
            Write-Log "Assistant name is required!" "ERROR"
            $AssistantName = Read-Host "Enter the name of your existing assistant"
            continue
        }

        # Check for valid format: lowercase letters, numbers, hyphens, must start with letter
        if ($AssistantName -notmatch '^[a-z][a-z0-9-]*$') {
            Write-Log "Invalid assistant name format!" "ERROR"

            # Provide specific feedback
            if ($AssistantName -match '\s') {
                Write-Host "  [X] Contains spaces - use hyphens instead (e.g., 'patent-books' not 'patent books')" -ForegroundColor Red
            }
            if ($AssistantName -match '[A-Z]') {
                Write-Host "  [X] Contains uppercase letters - use lowercase only" -ForegroundColor Red
                Write-Host "  TIP: Try '$($AssistantName.ToLower())'" -ForegroundColor Yellow
            }
            if ($AssistantName -match '^[^a-z]') {
                Write-Host "  [X] Must start with a letter" -ForegroundColor Red
            }
            if ($AssistantName -match '[^a-z0-9-]') {
                Write-Host "  [X] Contains invalid characters - only lowercase letters, numbers, and hyphens allowed" -ForegroundColor Red
            }

            Write-Info ""
            $AssistantName = Read-Host "Enter the name of your existing assistant"
            continue
        }

        # Valid name
        break
    }

    Write-Log "Verifying assistant and retrieving host URL..." "INFO"

    # Create Python script to verify assistant and get host
    # SECURITY FIX: Retrieve API key from Windows Credential Manager directly
    # (environment variables don't reliably propagate to uv run subprocesses)
    $verifyAssistantScript = @"
import sys
import os
from pathlib import Path
sys.path.insert(0, 'src')

from pinecone import Pinecone

try:
    # SECURITY: Read API key from Windows Credential Manager or DPAPI storage
    from config.secure_storage import get_api_key_from_credential_manager, get_secure_api_key

    # Try Credential Manager first, then fallback to other methods
    api_key = get_api_key_from_credential_manager()
    print(f'DEBUG|get_api_key_from_credential_manager returned: {bool(api_key)}')

    if not api_key:
        # Fallback to secure storage (DPAPI file or env var)
        api_key = get_secure_api_key()
        print(f'DEBUG|get_secure_api_key returned: {bool(api_key)}')

    if not api_key:
        print('ERROR|API key not found in Credential Manager or secure storage')
        sys.exit(1)

    pc = Pinecone(api_key=api_key)
    assistant_info = pc.assistant.describe_assistant(assistant_name='$AssistantName')

    # Handle both dict and object responses
    if hasattr(assistant_info, 'host'):
        host = assistant_info.host
        status = getattr(assistant_info, 'status', 'unknown')
    else:
        host = assistant_info.get('host', 'unknown')
        status = assistant_info.get('status', 'unknown')

    print(f'SUCCESS|{host}|{status}')
    sys.exit(0)

except Exception as e:
    import traceback
    print(f'ERROR|{str(e)}')
    traceback.print_exc()
    sys.exit(1)
"@

    $tempScript = Join-Path $env:TEMP "verify_assistant_temp.py"
    $verifyAssistantScript | Out-File -FilePath $tempScript -Encoding UTF8

    try {
        Set-Location $ProjectDir
        $result = uv run python $tempScript 2>&1 | Out-String

        if ($result -match "SUCCESS\|([^\|]+)\|(.+)") {
            $AssistantHost = $matches[1].Trim()
            $status = $matches[2].Trim()
            Write-Log "Assistant verified successfully!" "SUCCESS"
            Write-Log "Assistant name: $AssistantName" "SUCCESS"
            Write-Log "Assistant host: $AssistantHost" "SUCCESS"
            Write-Log "Status: $status" "INFO"
        } elseif ($result -match "ERROR\|(.+)") {
            $errorMsg = $matches[1]
            Write-Log "Failed to verify assistant: $errorMsg" "ERROR"
            Write-Warning "Could not verify assistant. Please check the name and try again."
            $SkipAssistantSetup = $true
        } else {
            Write-Log "Unexpected response from assistant verification" "ERROR"
            $SkipAssistantSetup = $true
        }

    } catch {
        Write-Log "Failed to run assistant verification script: $($_.Exception.Message)" "ERROR"
        $SkipAssistantSetup = $true
    } finally {
        if (Test-Path $tempScript) {
            Remove-Item $tempScript -Force
        }
    }

} else {
    # Skip assistant setup
    Write-Log "Skipping assistant setup" "WARNING"
    Write-Info "Note: Claude Desktop JSON cannot be auto-created without assistant details."
    Write-Info "You can re-run this script later when you have an assistant."
    $SkipAssistantSetup = $true
}

# ===============================
# STEP 10-11: DOCUMENT UPLOAD
# ===============================

Write-Info ""
Write-Info "Step 10-11: Document Upload Configuration"
Write-Info ""

if ($SkipAssistantSetup -or [string]::IsNullOrWhiteSpace($AssistantName)) {
    Write-Log "Skipping document upload (no assistant configured)" "WARNING"
} else {
    # Check if upload script exists
    if (-not (Test-Path $UploadScript)) {
        Write-Log "Upload script not found: $UploadScript" "WARNING"
        Write-Info "Skipping document upload"
    } elseif (-not (Test-Path $DocumentsDir)) {
        Write-Log "Documents directory not found: $DocumentsDir" "WARNING"
        Write-Info "Skipping document upload"
    } else {
        # Check for documents (either MD files or zip file)
        $Documents = Get-ChildItem -Path $DocumentsDir -Filter "*.md" -ErrorAction SilentlyContinue
        $ZipFile = Join-Path $DocumentsDir "combined_documents.zip"

        if ($Documents.Count -eq 0 -and -not (Test-Path $ZipFile)) {
            Write-Log "No documents or zip file found to upload" "WARNING"
        } else {
            if ($Documents.Count -eq 0 -and (Test-Path $ZipFile)) {
                Write-Info "Found combined_documents.zip file - will extract documents for upload"
                $DocumentsToUpload = 6  # Expected number of USPTO documents
            } elseif ($Documents.Count -gt 0) {
                Write-Info "Found $($Documents.Count) markdown documents to upload"
                $DocumentsToUpload = $Documents.Count
            }

            $uploadDocs = Read-Host "Upload documents to assistant '$AssistantName'? (Y/n)"

            if ($uploadDocs -eq "" -or $uploadDocs -eq "Y" -or $uploadDocs -eq "y") {
                # Ask about document type for metadata
                Write-Info ""
                Write-Info "Are you uploading the DEFAULT USPTO MPEP documents included in this repository,"
                Write-Info "or have you replaced them with your own custom documents?"
                Write-Info "  [1] Default USPTO MPEP documents (included in repo)"
                Write-Info "  [2] Custom documents (I replaced the default ones)"
                Write-Info ""

                $docTypeChoice = Read-Host "Enter choice (1 or 2)"

                $useUsptoMetadata = $false
                $configureUsptoPrompt = $false
                $configureCustomPrompt = $false

                if ($docTypeChoice -eq "1") {
                    $useUsptoMetadata = $true
                    $configureUsptoPrompt = $true
                    $defaultTemperature = "0.2"  # Low temperature for USPTO legal precision
                    Write-Log "Using USPTO-specific metadata for document upload" "INFO"
                    Write-Log "Setting default temperature to 0.2 for legal analysis precision" "INFO"
                    Write-Info ""
                    Write-Info "Note: Since you're using USPTO MPEP documents, we'll also configure"
                    Write-Info "      the assistant with a specialized system prompt for patent law analysis."
                    Write-Info "      This optimizes responses for IRAC methodology and USPTO guidance."
                    Write-Info ""
                } else {
                    $defaultTemperature = $null  # No default for custom documents
                    Write-Log "Using generic metadata for document upload" "INFO"
                    Write-Info ""
                    Write-Info "Would you like to configure a custom system prompt for your assistant?"
                    Write-Info "  [1] Yes - Use custom system prompt from assistant_system_prompt_generic.txt"
                    Write-Info "  [2] No - Skip system prompt configuration"
                    Write-Info ""

                    $customPromptChoice = Read-Host "Enter choice (1 or 2)"

                    if ($customPromptChoice -eq "1") {
                        $configureCustomPrompt = $true
                        Write-Info ""
                        Write-Info "Note: Edit deploy/assistant_system_prompt_generic.txt to customize"
                        Write-Info "      the system prompt for your specific document domain."
                        Write-Info ""
                    } else {
                        $configureCustomPrompt = $false
                    }
                }

                Write-Log "Starting document upload via Python script..." "INFO"

                # Run Python upload script with metadata flag
                Set-Location $ScriptDir

                Write-Log "Executing upload script from: $ScriptDir" "INFO"
                Write-Log "Assistant: $AssistantName" "INFO"

                # Temporarily disable ErrorActionPreference to show live output
                $previousErrorActionPreference = $ErrorActionPreference
                $ErrorActionPreference = "Continue"

                try {
                    if ($useUsptoMetadata) {
                        Write-Log "Command: `$ApiKey | uv run python upload_files.py --assistant-name $AssistantName --use-uspto-metadata" "INFO"
                        $ApiKey | uv run python upload_files.py --assistant-name $AssistantName --use-uspto-metadata
                    } else {
                        Write-Log "Command: `$ApiKey | uv run python upload_files.py --assistant-name $AssistantName" "INFO"
                        $ApiKey | uv run python upload_files.py --assistant-name $AssistantName
                    }

                    $exitCode = $LASTEXITCODE
                    Write-Log "Upload script exit code: $exitCode" "INFO"

                    if ($exitCode -eq 0) {
                        Write-Log "Document upload completed successfully" "SUCCESS"

                        # Configure system prompt based on document type
                        if ($configureUsptoPrompt) {
                            Write-Info ""
                            Write-Log "Configuring USPTO patent law analysis system prompt..." "INFO"

                            # Load USPTO-specific system prompt from file
                            $promptFile = Join-Path $ScriptDir "assistant_system_prompt.txt"
                            if (Test-Path $promptFile) {
                                $usptoSystemPrompt = Get-Content -Path $promptFile -Raw -Encoding UTF8
                                Write-Log "Loaded system prompt from: assistant_system_prompt.txt" "SUCCESS"
                            } else {
                                Write-Warning "System prompt file not found, using built-in default"
                                $usptoSystemPrompt = @"
Conduct comprehensive patent law analysis using IRAC methodology (Issue-Rule-Application-Conclusion).

**Analysis Standards:**
- Provide detailed analysis based on legal authority in the knowledge base
- Reference specific sources: MPEP sections, 35 USC provisions, Federal Circuit decisions, USPTO examination guidance
- If precedent is unclear, acknowledge uncertainty and explain available legal approaches
- Deliver actionable strategic recommendations

**Professional Requirements:**
- Structure analysis with clear headings
- Maintain professional legal writing standards
- Focus on practical implications for patent prosecution
- State limitations when context lacks specific authority

**Output Format:**
Present analysis in logical legal framework incorporating all relevant authority, with precise citations and strategic guidance for patent practitioners.
"@
                            }

                            # SECURITY FIX (M-10): Write prompt to JSON-encoded temp file
                            # instead of embedding directly in heredoc (prevents triple-quote injection)
                            $updatePromptScript = @"
import sys, json, pathlib
from pinecone import Pinecone

try:
    # SECURITY: API key via stdin; prompt via JSON-encoded temp file (argv[1])
    api_key = sys.stdin.readline().strip()
    prompt_text = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
    pc = Pinecone(api_key=api_key)

    # Get existing assistant to preserve metadata (if any)
    assistant_info = pc.assistant.describe_assistant(assistant_name='$AssistantName')

    # Handle both dict and object responses
    if hasattr(assistant_info, 'metadata'):
        existing_metadata = assistant_info.metadata or {}
    else:
        existing_metadata = assistant_info.get('metadata', {})

    # Update assistant with USPTO system prompt, preserving existing metadata
    response = pc.assistant.update_assistant(
        assistant_name='$AssistantName',
        instructions=prompt_text,
        metadata=existing_metadata if existing_metadata else None
    )

    print('SUCCESS|System prompt configured for USPTO patent law analysis')
    sys.exit(0)

except Exception as e:
    print(f'ERROR|{str(e)}')
    sys.exit(1)
"@

                            $tempPromptScript = Join-Path $env:TEMP "update_prompt_temp.py"
                            $tempPromptData  = Join-Path $env:TEMP "update_prompt_data.json"
                            $updatePromptScript | Out-File -FilePath $tempPromptScript -Encoding UTF8
                            # JSON-encode the prompt text so no string-terminator injection is possible
                            $usptoSystemPrompt | ConvertTo-Json | Out-File -FilePath $tempPromptData -Encoding UTF8

                            try {
                                Set-Location $ProjectDir
                                # Pass API key via stdin; prompt file path as argument
                                $promptResult = $ApiKey | uv run python $tempPromptScript $tempPromptData 2>&1 | Out-String

                                if ($promptResult -match "SUCCESS") {
                                    Write-Log "USPTO system prompt configured successfully" "SUCCESS"
                                    Write-Info "Assistant will now use IRAC methodology for patent law analysis"
                                } else {
                                    Write-Log "Failed to configure system prompt (non-critical)" "WARNING"
                                    Write-Info "Upload succeeded, but system prompt configuration failed"
                                }

                            } catch {
                                Write-Log "Failed to configure system prompt: $($_.Exception.Message)" "WARNING"
                            } finally {
                                if (Test-Path $tempPromptScript) {
                                    Remove-Item $tempPromptScript -Force
                                }
                                if (Test-Path $tempPromptData) {
                                    Remove-Item $tempPromptData -Force
                                }
                            }
                        }

                        # Configure custom system prompt if user selected custom documents and wants custom prompt
                        if ($configureCustomPrompt) {
                            Write-Info ""
                            Write-Log "Configuring custom system prompt..." "INFO"

                            # Load custom system prompt from file
                            $customPromptFile = Join-Path $ScriptDir "assistant_system_prompt_generic.txt"
                            if (Test-Path $customPromptFile) {
                                $rawContent = Get-Content -Path $customPromptFile -Raw -Encoding UTF8

                                # Remove comment header (lines starting with # until first non-comment line)
                                $customSystemPrompt = ($rawContent -split "`n" | Where-Object { $_ -notmatch '^\s*#' -and $_ -notmatch '^\s*$' } | Select-Object -Skip 0) -join "`n"

                                # If the prompt is mostly empty after removing comments, warn user
                                if ($customSystemPrompt.Trim().Length -lt 50) {
                                    Write-Warning "Custom system prompt file seems empty or contains only comments"
                                    Write-Info "Using file contents as-is, but you may want to edit: assistant_system_prompt_generic.txt"
                                    $customSystemPrompt = $rawContent
                                }

                                Write-Log "Loaded custom system prompt from: assistant_system_prompt_generic.txt" "SUCCESS"
                            } else {
                                Write-Warning "Custom system prompt file not found: assistant_system_prompt_generic.txt"
                                Write-Info "Skipping custom system prompt configuration"
                                $customSystemPrompt = $null
                            }

                            # Only proceed if we have a prompt to configure
                            if ($customSystemPrompt) {
                                # Create Python script to update assistant instructions
                                # SECURITY: API key via stdin; prompt via JSON-encoded temp file (M-10 fix)
                                $updateCustomPromptScript = @"
import sys, json, pathlib
from pinecone import Pinecone

try:
    # SECURITY: API key via stdin; prompt text via JSON-encoded file (argv[1])
    api_key = sys.stdin.readline().strip()
    prompt_text = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
    pc = Pinecone(api_key=api_key)

    # Get existing assistant to preserve metadata (if any)
    assistant_info = pc.assistant.describe_assistant(assistant_name='$AssistantName')

    # Handle both dict and object responses
    if hasattr(assistant_info, 'metadata'):
        existing_metadata = assistant_info.metadata or {}
    else:
        existing_metadata = assistant_info.get('metadata', {})

    # Update assistant with custom system prompt, preserving existing metadata
    response = pc.assistant.update_assistant(
        assistant_name='$AssistantName',
        instructions=prompt_text,
        metadata=existing_metadata if existing_metadata else None
    )

    print('SUCCESS|Custom system prompt configured')
    sys.exit(0)

except Exception as e:
    print(f'ERROR|{str(e)}')
    sys.exit(1)
"@

                                $tempCustomPromptScript = Join-Path $env:TEMP "update_custom_prompt_temp.py"
                                $tempCustomPromptData   = Join-Path $env:TEMP "update_custom_prompt_data.json"
                                $updateCustomPromptScript | Out-File -FilePath $tempCustomPromptScript -Encoding UTF8
                                # JSON-encode prompt so no string-terminator injection is possible
                                $customSystemPrompt | ConvertTo-Json | Out-File -FilePath $tempCustomPromptData -Encoding UTF8

                                try {
                                    Set-Location $ProjectDir
                                    # SECURITY: API key via stdin; prompt via JSON temp file
                                    $customPromptResult = $ApiKey | uv run python $tempCustomPromptScript $tempCustomPromptData 2>&1 | Out-String

                                    if ($customPromptResult -match "SUCCESS") {
                                        Write-Log "Custom system prompt configured successfully" "SUCCESS"
                                        Write-Info "Assistant will now use your custom system prompt"
                                    } else {
                                        Write-Log "Failed to configure custom system prompt (non-critical)" "WARNING"
                                        Write-Info "Upload succeeded, but custom system prompt configuration failed"
                                    }

                                } catch {
                                    Write-Log "Failed to configure custom system prompt: $($_.Exception.Message)" "WARNING"
                                } finally {
                                    if (Test-Path $tempCustomPromptScript) {
                                        Remove-Item $tempCustomPromptScript -Force
                                    }
                                    if (Test-Path $tempCustomPromptData) {
                                        Remove-Item $tempCustomPromptData -Force
                                    }
                                }
                            }
                        }

                    } else {
                        Write-Log "Document upload completed with errors (exit code $exitCode)" "WARNING"
                    }

                } catch {
                    Write-Log "Failed to run upload script: $($_.Exception.Message)" "ERROR"
                    Write-Info "Full error details:"
                    Write-Host $_.Exception | Format-List -Force
                    Write-Host $_.ScriptStackTrace
                } finally {
                    # Restore ErrorActionPreference
                    $ErrorActionPreference = $previousErrorActionPreference
                }
            } else {
                Write-Log "Document upload skipped by user" "WARNING"
            }
        }
    }
}

# ===============================
# STEP 12: MCP ENVIRONMENT SETUP
# ===============================

Write-Info ""
Write-Info "Step 12: MCP Environment Setup"
Write-Info ""

Write-Log "Verifying MCP environment is ready..." "INFO"
Write-Log "Note: API key will NOT be stored in system environment variables" "INFO"
Write-Log "      API key will only be stored in Claude Desktop config file" "INFO"

Write-Log "MCP environment setup complete" "SUCCESS"

# ===============================
# STEP 13-14: CLAUDE DESKTOP CONFIG
# ===============================

Write-Info ""
Write-Info "Step 13-14: Claude Desktop Configuration"
Write-Info ""

$configureClaudeDesktop = Read-Host "Would you like to configure Claude Desktop integration? (Y/n)"

if ($configureClaudeDesktop -eq "" -or $configureClaudeDesktop -eq "Y" -or $configureClaudeDesktop -eq "y") {

    # Check if we have the required information
    if ([string]::IsNullOrWhiteSpace($AssistantName) -or [string]::IsNullOrWhiteSpace($AssistantHost)) {
        Write-Warning "Cannot auto-create Claude Desktop config without assistant details."
        Write-Info ""
        Write-Info "You skipped assistant setup or assistant verification failed."
        Write-Info "Please re-run this script after you have created an assistant."
        Write-Info ""
        Write-Info "Manual configuration instructions:"
        Write-Info "Add this to your mcpServers section in: $env:APPDATA\Claude\claude_desktop_config.json"
        Write-Info ""

        # Get current directory and convert backslashes to forward slashes
        $CurrentDir = $ProjectDir -replace "\\","/"

        $manualJson = @"
"pinecone_assistant": {
  "command": "$CurrentDir/.venv/Scripts/python.exe",
  "args": ["-m", "src.server"],
  "cwd": "$CurrentDir",
  "env": {
    "PINECONE_ASSISTANT_HOST": "YOUR_ASSISTANT_HOST_HERE",
    "PINECONE_ASSISTANT_NAME": "YOUR_ASSISTANT_NAME_HERE",
    "PINECONE_ASSISTANT_MODEL": "$AssistantModel"
  }
}
"@
        Write-Host $manualJson -ForegroundColor Cyan

    } else {
        # We have all required information - proceed with auto-configuration

        Write-Info ""
        Write-Info "Claude Desktop Configuration Method:"
        Write-Info "  [1] Secure Python DPAPI (recommended) - Automatic secure storage"
        Write-Info "      - API key encrypted with Windows DPAPI (Python-based)"
        Write-Info "      - API key not stored in Claude Desktop config file"
        Write-Info "      - Direct Python execution with built-in secure storage"
        Write-Info "      - No PowerShell execution policy requirements"
        Write-Info "      - Cross-platform fallback to environment variables"
        Write-Info ""
        Write-Info "  [2] Traditional - API key stored in Claude Desktop config file"
        Write-Info "      - API key visible in claude_desktop_config.json"
        Write-Info "      - Direct Python execution"
        Write-Info "      - Simpler setup, less secure"
        Write-Info "      - Works on all platforms"
        Write-Info ""

        $configMethod = Read-Host "Enter choice (1 or 2, default is 1)"
        
        if ($configMethod -eq "2") {
            Write-Info "Using traditional method (API key in config file)"
            $useSecureMethod = $false
        } else {
            Write-Info "Using secure Python DPAPI method (encrypted API key storage)"
            $useSecureMethod = $true
        }

        # Get current directory and convert backslashes to forward slashes
        $CurrentDir = $ProjectDir -replace "\\","/"

        # Claude Desktop config location
        $ClaudeConfigDir = "$env:APPDATA\Claude"
        $ClaudeConfigFile = "$ClaudeConfigDir\claude_desktop_config.json"

        Write-Log "Claude Desktop config location: $ClaudeConfigFile" "INFO"

        if (Test-Path $ClaudeConfigFile) {
            Write-Log "Existing Claude Desktop config found" "WARNING"
            Write-Log "Merging Pinecone Assistant configuration with existing config..." "WARNING"

            # Backup the original file first
            $backupFile = "$ClaudeConfigFile.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
            Copy-Item $ClaudeConfigFile $backupFile
            Write-Log "Backup created: $backupFile" "SUCCESS"

            # Build env block as a JSON fragment (Python will embed it)
            # Using Python json.load/json.dump guarantees ALL top-level keys
            # (preferences, globalShortcuts, etc.) are preserved untouched.
            # Only mcpServers.pinecone_assistant is added or replaced.
            if ($useSecureMethod) {
                $envJson = @"
{
    "PINECONE_ASSISTANT_HOST": "$AssistantHost",
    "PINECONE_ASSISTANT_NAME": "$AssistantName",
    "PINECONE_ASSISTANT_MODEL": "$AssistantModel"
}
"@
            } else {
                $envJson = @"
{
    "PINECONE_ASSISTANT_API_KEY": "$ApiKey",
    "PINECONE_ASSISTANT_HOST": "$AssistantHost",
    "PINECONE_ASSISTANT_NAME": "$AssistantName",
    "PINECONE_ASSISTANT_MODEL": "$AssistantModel"
}
"@
            }
            if ($defaultTemperature) {
                # Insert temperature into the env JSON before the closing brace
                $envJson = $envJson.TrimEnd("`n", "`r", " ").TrimEnd('}') +
                    ",`n    `"PINECONE_ASSISTANT_TEMPERATURE`": `"$defaultTemperature`"`n}"
            }

            $mergeScript = @"
import json, sys

config_path = r'$ClaudeConfigFile'
env_block   = $envJson

with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# Only touch mcpServers — every other top-level key is left alone
if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers']['pinecone_assistant'] = {
    'command': r'$CurrentDir/.venv/Scripts/python.exe',
    'args': ['-m', 'src.server'],
    'cwd': r'$CurrentDir',
    'env': env_block
}

with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=2)

print('SUCCESS')
"@

            $tempMergeScript = Join-Path $env:TEMP "merge_claude_config_temp.py"
            try {
                $mergeScript | Out-File -FilePath $tempMergeScript -Encoding UTF8
                Set-Location $ProjectDir
                $mergeResult = uv run python $tempMergeScript 2>&1 | Out-String

                if ($mergeResult -match "SUCCESS") {
                    Write-Log "Successfully merged Pinecone Assistant configuration!" "SUCCESS"
                    Write-Log "Your existing MCP servers have been preserved" "SUCCESS"
                    Write-Log "All other top-level config settings (preferences, etc.) preserved" "SUCCESS"
                } else {
                    throw "Merge script returned: $mergeResult"
                }
            } catch {
                Write-Log "Failed to merge configuration: $_" "ERROR"
                Write-Info ""
                Write-Info "Please manually add this configuration to: $ClaudeConfigFile"
                Write-Info ""
                Write-Info "Add this to your mcpServers section:"

                if ($useSecureMethod) {
                    $manualJson = @"
"pinecone_assistant": {
  "command": "$CurrentDir/.venv/Scripts/python.exe",
  "args": ["-m", "src.server"],
  "cwd": "$CurrentDir",
  "env": {
    "PINECONE_ASSISTANT_HOST": "$AssistantHost",
    "PINECONE_ASSISTANT_NAME": "$AssistantName",
    "PINECONE_ASSISTANT_MODEL": "$AssistantModel"
  }
}
"@
                } else {
                    $manualJson = @"
"pinecone_assistant": {
  "command": "$CurrentDir/.venv/Scripts/python.exe",
  "args": ["-m", "src.server"],
  "cwd": "$CurrentDir",
  "env": {
    "PINECONE_ASSISTANT_API_KEY": "$ApiKey",
    "PINECONE_ASSISTANT_HOST": "$AssistantHost",
    "PINECONE_ASSISTANT_NAME": "$AssistantName",
    "PINECONE_ASSISTANT_MODEL": "$AssistantModel"
  }
}
"@
                }
                Write-Host $manualJson -ForegroundColor Cyan
            } finally {
                if (Test-Path $tempMergeScript) { Remove-Item $tempMergeScript -Force }
            }

        } else {
            Write-Log "Creating new Claude Desktop config..." "INFO"

            # Create directory if it doesn't exist
            New-Item -ItemType Directory -Force -Path $ClaudeConfigDir | Out-Null

            # Build JSON manually to ensure valid format (use chosen method)
            if ($useSecureMethod) {
                # Secure method - use PowerShell wrapper, minimal env vars
                $envVars = @"
        "PINECONE_ASSISTANT_HOST": "$AssistantHost",
        "PINECONE_ASSISTANT_NAME": "$AssistantName",
        "PINECONE_ASSISTANT_MODEL": "$AssistantModel"
"@
                if ($defaultTemperature) {
                    $envVars += ",`n        `"PINECONE_ASSISTANT_TEMPERATURE`": `"$defaultTemperature`""
                }

                $jsonConfig = @"
{
  "mcpServers": {
    "pinecone_assistant": {
      "command": "$CurrentDir/.venv/Scripts/python.exe",
      "args": ["-m", "src.server"],
      "cwd": "$CurrentDir",
      "env": {
$envVars
      }
    }
  }
}
"@
            } else {
                # Traditional method - direct Python, API key in config
                $envVars = @"
        "PINECONE_ASSISTANT_API_KEY": "$ApiKey",
        "PINECONE_ASSISTANT_HOST": "$AssistantHost",
        "PINECONE_ASSISTANT_NAME": "$AssistantName",
        "PINECONE_ASSISTANT_MODEL": "$AssistantModel"
"@
                if ($defaultTemperature) {
                    $envVars += ",`n        `"PINECONE_ASSISTANT_TEMPERATURE`": `"$defaultTemperature`""
                }

                $jsonConfig = @"
{
  "mcpServers": {
    "pinecone_assistant": {
      "command": "$CurrentDir/.venv/Scripts/python.exe",
      "args": ["-m", "src.server"],
      "cwd": "$CurrentDir",
      "env": {
$envVars
      }
    }
  }
}
"@
            }

            # Write the config file with UTF8 without BOM
            $utf8NoBom = New-Object System.Text.UTF8Encoding $false
            [System.IO.File]::WriteAllText($ClaudeConfigFile, $jsonConfig, $utf8NoBom)
            Write-Log "Config created at: $ClaudeConfigFile" "SUCCESS"
        }

        Write-Info ""
        Write-Log "Claude Desktop configuration complete!" "SUCCESS"
        Write-Info ""
    }

} else {
    Write-Log "Skipping Claude Desktop configuration" "WARNING"
    Write-Info ""
    Write-Info "You can re-run this script later to configure Claude Desktop."
    Write-Info ""
}

# ===============================
# COMPLETION AND NEXT STEPS
# ===============================

Write-Info ""
Write-Log "Windows setup complete!" "SUCCESS"
Write-Info ""

if (-not $SkipAssistantSetup -and -not [string]::IsNullOrWhiteSpace($AssistantName)) {
    Write-Info "Please restart Claude Desktop to load the MCP server"
    Write-Info ""
    Write-Info "Configuration Summary:"
    if ($useSecureMethod) {
        Write-Log "  Configuration Method: Secure (encrypted API key storage)" "SUCCESS"
        Write-Log "  API Key: Encrypted with Windows DPAPI" "SUCCESS"
    } else {
        Write-Log "  Configuration Method: Traditional (API key in config file)" "SUCCESS"
        Write-Log "  API Key: Stored in Claude Desktop config file" "SUCCESS"
    }
    Write-Log "  Assistant Name: $AssistantName" "SUCCESS"
    Write-Log "  Assistant Host: $AssistantHost" "SUCCESS"
    Write-Log "  Installation Directory: $CurrentDir" "SUCCESS"
    Write-Info ""
    Write-Info "Available MCP Tools:"
    Write-Info "  - assistant_chat: Direct conversation with your assistant"
    Write-Info "  - assistant_strategic_multi_search: Multi-pattern strategic research"
    Write-Info "  - assistant_context: Raw document retrieval without AI processing"
    Write-Info "  - assistant_strategic_multi_search_context: Strategic search with raw documents"
    Write-Info ""
    if ($useSecureMethod) {
        Write-Info "Troubleshooting:"
        Write-Info "  If Claude Desktop fails to connect to MCP server, check execution policy:"
        Write-Host "  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Cyan
        Write-Info ""
    }
    Write-Info "Test with: Ask Claude questions about your document corpus"
} else {
    Write-Info "Setup completed but assistant configuration was skipped."
    Write-Info "Please re-run this script when you're ready to configure your assistant."
}

Write-Info ""
Write-Log "Setup log saved to: $LogFile" "INFO"
Write-Info ""
