# Pinecone Assistant Management Script
# Standalone tool for managing Pinecone Assistants without full MCP setup

# Import validation helpers for secure API key input
$ValidationModule = Join-Path $PSScriptRoot "Validation-Helpers.psm1"
if (Test-Path $ValidationModule) {
    Import-Module $ValidationModule -Force
    Write-Host "[OK] Validation helpers loaded" -ForegroundColor Green
} else {
    Write-Host "[WARN] Validation helpers not found - API keys will be displayed in plain text" -ForegroundColor Yellow
}

Write-Host "=== Pinecone Assistant Management Tool ===" -ForegroundColor Green
Write-Host ""

# Set error action preference
$ErrorActionPreference = "Stop"

# Script configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$DocumentsDir = Join-Path $ScriptDir "combined_documents"
$LogFile = Join-Path $ScriptDir "manage_assistant.log"

# Color functions for output
function Write-Success { param($Message) Write-Host $Message -ForegroundColor Green }
function Write-Warning { param($Message) Write-Host $Message -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host $Message -ForegroundColor Red }
function Write-Info { param($Message) Write-Host $Message -ForegroundColor Cyan }

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

# Helper function to get list of assistants
function Get-AssistantList {
    param($ApiKey, $ProjectDir)

    # SECURITY FIX (L-2): Pass API key via stdin, not script embedding
    $listScript = @"
import sys
from pinecone import Pinecone

try:
    # SECURITY: Read API key from stdin instead of hardcoded string
    api_key = sys.stdin.read().strip()
    pc = Pinecone(api_key=api_key)

    assistants = pc.assistant.list_assistants()

    if hasattr(assistants, 'assistants'):
        assistant_list = assistants.assistants
    elif isinstance(assistants, dict):
        assistant_list = assistants.get('assistants', [])
    else:
        assistant_list = assistants if isinstance(assistants, list) else []

    if not assistant_list:
        print('NO_ASSISTANTS')
        sys.exit(0)

    for assistant in assistant_list:
        if hasattr(assistant, 'name'):
            name = assistant.name
            status = getattr(assistant, 'status', 'unknown')
            created = getattr(assistant, 'created_on', 'unknown')
        else:
            name = assistant.get('name', 'unknown')
            status = assistant.get('status', 'unknown')
            created = assistant.get('created_on', 'unknown')

        print(f'ASSISTANT|{name}|{status}|{created}')

    sys.exit(0)

except Exception as e:
    print(f'ERROR|{str(e)}')
    sys.exit(1)
"@

    $tempScript = Join-Path $env:TEMP "list_assistants_temp.py"
    $listScript | Out-File -FilePath $tempScript -Encoding UTF8

    try {
        Set-Location $ProjectDir
        # SECURITY FIX (L-2): Pass API key via stdin
        $result = $ApiKey | uv run python $tempScript 2>&1 | Out-String

        $assistants = @()

        if ($result -match "NO_ASSISTANTS") {
            return $null
        } elseif ($result -match "ASSISTANT") {
            $lines = $result -split "`n"
            foreach ($line in $lines) {
                if ($line -match "ASSISTANT\|([^\|]+)\|([^\|]+)\|(.+)") {
                    $assistants += [PSCustomObject]@{
                        Name = $matches[1].Trim()
                        Status = $matches[2].Trim()
                        Created = $matches[3].Trim()
                    }
                }
            }
        }

        if ($assistants.Count -eq 0) {
            return $null
        }

        # Force return as array even if single item
        return @($assistants)

    } catch {
        Write-Log "Error retrieving assistants: $($_.Exception.Message)" "ERROR"
        return $null
    } finally {
        if (Test-Path $tempScript) {
            Remove-Item $tempScript -Force
        }
    }
}

# Helper function to select assistant from list
function Select-Assistant {
    param($ApiKey, $ProjectDir, $Purpose)

    Write-Info ""
    Write-Info "=== Select Assistant for $Purpose ==="
    Write-Info ""

    $assistantsList = Get-AssistantList -ApiKey $ApiKey -ProjectDir $ProjectDir

    if ($null -eq $assistantsList) {
        Write-Warning "No assistants found in your account."
        return $null
    }

    # Ensure it's an array (PowerShell sometimes returns single object instead of array)
    if ($assistantsList -isnot [Array]) {
        $assistants = @($assistantsList)
    } else {
        $assistants = $assistantsList
    }

    if ($assistants.Count -eq 0) {
        Write-Warning "No assistants found in your account."
        return $null
    }

    Write-Info "Available assistants:"
    foreach ($assistant in $assistants) {
        $idx = $assistants.IndexOf($assistant) + 1
        Write-Info "  [$idx] $($assistant.Name) (Status: $($assistant.Status))"
    }
    Write-Info "  [0] Cancel"
    Write-Info ""

    $selection = Read-Host "Enter choice (0-$($assistants.Count))"

    if ($selection -eq "0" -or [string]::IsNullOrWhiteSpace($selection)) {
        Write-Info "Cancelled"
        return $null
    }

    try {
        $index = [int]$selection - 1
        if ($index -ge 0 -and $index -lt $assistants.Count) {
            return $assistants[$index].Name
        } else {
            Write-Warning "Invalid selection"
            return $null
        }
    } catch {
        Write-Warning "Invalid input"
        return $null
    }
}

# Initialize log file
"Assistant management session started at $(Get-Date)" | Out-File -FilePath $LogFile -Encoding UTF8
Write-Log "Pinecone Assistant Management Tool"

# ===============================
# GET API KEY
# ===============================

Write-Info "Enter your Pinecone Assistant API key"
Write-Info "(Get it from: https://app.pinecone.io/)"
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
        $ApiKey = Read-ApiKeySecure -Prompt "Enter your Pinecone Assistant API key (input hidden)"
    } else {
        $ApiKey = Read-Host "Pinecone API key (starts with pcsk_)"
    }

    # Check if empty
    if ([string]::IsNullOrWhiteSpace($ApiKey)) {
        Write-Error "API key is required!"
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
            Write-Error "Invalid Pinecone API key format"
            Write-Info "Expected: pcsk_ followed by 70 alphanumeric/underscore characters (75 total)"
            if ($attemptCount -lt $maxAttempts) {
                Write-Info "Attempt $attemptCount of $maxAttempts - please try again"
            }
        }
    } else {
        # Fallback to basic validation if no validator
        if ($ApiKey.StartsWith("pcsk_")) {
            $validKey = $true
        } else {
            Write-Error "API key must start with 'pcsk_'"
            if ($attemptCount -lt $maxAttempts) {
                Write-Info "Attempt $attemptCount of $maxAttempts - please try again"
            }
        }
    }
}

if (-not $validKey) {
    Write-Error "Maximum attempts reached. Exiting."
    exit 1
}

# ===============================
# MAIN MENU LOOP
# ===============================

$continue = $true

while ($continue) {
    Write-Info ""
    Write-Info "=== Assistant Management Menu ==="
    Write-Info ""
    Write-Info "  [1] Create new assistant"
    Write-Info "  [2] List all assistants"
    Write-Info "  [3] Get assistant details"
    Write-Info "  [4] Upload documents to assistant"
    Write-Info "  [5] Update system prompt"
    Write-Info "  [6] Delete assistant"
    Write-Info "  [7] Exit"
    Write-Info ""

    $choice = Read-Host "Enter choice (1-7)"

    switch ($choice) {
        "1" {
            # Create new assistant
            Write-Info ""
            Write-Info "=== Create New Assistant ==="
            Write-Info ""
            Write-Host "Assistant name requirements:" -ForegroundColor Yellow
            Write-Host "  - Lowercase letters, numbers, hyphens only" -ForegroundColor Yellow
            Write-Host "  - Must start with a letter" -ForegroundColor Yellow
            Write-Host "  - No spaces or special characters" -ForegroundColor Yellow
            Write-Host "  - Example: my-assistant, uspto-docs, patent-search" -ForegroundColor Yellow
            Write-Info ""

            $AssistantName = Read-Host "Enter name for new assistant"

            # Validate assistant name format
            while ($true) {
                if ([string]::IsNullOrWhiteSpace($AssistantName)) {
                    Write-Error "Assistant name is required!"
                    $AssistantName = Read-Host "Enter name for new assistant"
                    continue
                }

                # Check for valid format: lowercase letters, numbers, hyphens, must start with letter
                if ($AssistantName -notmatch '^[a-z][a-z0-9-]*$') {
                    Write-Error "Invalid assistant name format!"

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
                    $AssistantName = Read-Host "Enter name for new assistant"
                    continue
                }

                # Valid name
                break
            }

            # Create Python script to create assistant
            # SECURITY FIX (L-2): Pass API key via stdin
            $createScript = @"
import sys
import json
from pinecone import Pinecone

try:
    # SECURITY: Read API key from stdin instead of hardcoded string
    api_key = sys.stdin.read().strip()
    pc = Pinecone(api_key=api_key)

    print('Creating assistant: $AssistantName')
    response = pc.assistant.create_assistant(assistant_name='$AssistantName')

    assistant_info = pc.assistant.describe_assistant(assistant_name='$AssistantName')

    if hasattr(assistant_info, 'host'):
        host = assistant_info.host
        status = getattr(assistant_info, 'status', 'unknown')
    else:
        host = assistant_info.get('host', 'unknown')
        status = assistant_info.get('status', 'unknown')

    print(f'SUCCESS|{host}|{status}')
    sys.exit(0)

except Exception as e:
    # Handle all errors (API and other)
    error_msg = str(e)

    # Try to get status code from the exception
    status_code = None
    if hasattr(e, 'status'):
        status_code = e.status
    elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
        status_code = e.response.status_code

    # Parse the error for specific issues
    if 'Invalid assistant name' in error_msg or status_code == 400:
        print('ERROR|INVALID_NAME|Assistant name does not meet requirements (lowercase letters, numbers, hyphens only, must start with letter)')
    elif 'already exists' in error_msg or status_code == 409:
        print('ERROR|EXISTS|An assistant with this name already exists')
    elif status_code == 401 or 'authentication' in error_msg.lower() or 'api key' in error_msg.lower():
        print('ERROR|AUTH|Invalid API key or authentication failed')
    elif status_code == 429 or 'rate limit' in error_msg.lower():
        print('ERROR|RATE_LIMIT|Rate limit exceeded - please wait and try again')
    else:
        # Return the actual error message for debugging
        print(f'ERROR|API_ERROR|{error_msg}')
    sys.exit(1)
"@

            $tempScript = Join-Path $env:TEMP "create_assistant_temp.py"
            $createScript | Out-File -FilePath $tempScript -Encoding UTF8

            try {
                Set-Location $ProjectDir
                # SECURITY FIX (L-2): Pass API key via stdin
                $result = $ApiKey | uv run python $tempScript 2>&1 | Out-String

                if ($result -match "SUCCESS\|([^\|]+)\|(.+)") {
                    $assistantHost = $matches[1]
                    $assistantStatus = $matches[2]
                    Write-Log "Assistant created successfully!" "SUCCESS"
                    Write-Info ""
                    Write-Info "Assistant Name: $AssistantName"
                    Write-Info "Host: $assistantHost"
                    Write-Info "Status: $assistantStatus"
                } elseif ($result -match "ERROR\|([^\|]+)\|(.+)") {
                    # Structured error from Python
                    $errorType = $matches[1]
                    $errorMsg = $matches[2]

                    Write-Host ""
                    Write-Host "[ERROR] Failed to create assistant" -ForegroundColor Red
                    Write-Host ""

                    switch ($errorType) {
                        "INVALID_NAME" {
                            Write-Host "Invalid Assistant Name" -ForegroundColor Yellow
                            Write-Host $errorMsg -ForegroundColor Red
                            Write-Host ""
                            Write-Host "TIP: This shouldn't happen - please report this issue!" -ForegroundColor Yellow
                        }
                        "EXISTS" {
                            Write-Host "Assistant Already Exists" -ForegroundColor Yellow
                            Write-Host "An assistant named '$AssistantName' already exists." -ForegroundColor Red
                            Write-Host ""
                            Write-Host "TIP: Try a different name or use option 3 to view existing assistant" -ForegroundColor Yellow
                        }
                        "AUTH" {
                            Write-Host "Authentication Error" -ForegroundColor Yellow
                            Write-Host "Invalid API key or authentication failed" -ForegroundColor Red
                            Write-Host ""
                            Write-Host "TIP: Check your API key starts with 'pcsk_' and is valid" -ForegroundColor Yellow
                        }
                        "RATE_LIMIT" {
                            Write-Host "Rate Limit Exceeded" -ForegroundColor Yellow
                            Write-Host "Too many requests - please wait a moment and try again" -ForegroundColor Red
                        }
                        default {
                            Write-Host "API Error" -ForegroundColor Yellow
                            Write-Host $errorMsg -ForegroundColor Red
                        }
                    }
                    Write-Host ""
                } else {
                    Write-Log "Failed to create assistant" "ERROR"
                    Write-Host ""
                    Write-Host "[ERROR] Unexpected error:" -ForegroundColor Red
                    Write-Info $result
                }

            } catch {
                Write-Log "Error: $($_.Exception.Message)" "ERROR"
            } finally {
                if (Test-Path $tempScript) {
                    Remove-Item $tempScript -Force
                }
            }
        }

        "2" {
            # List all assistants
            Write-Info ""
            Write-Info "=== List All Assistants ==="
            Write-Info ""

            # SECURITY FIX (L-2): Pass API key via stdin
            $listScript = @"
import sys
from pinecone import Pinecone

try:
    # SECURITY: Read API key from stdin instead of hardcoded string
    api_key = sys.stdin.read().strip()
    pc = Pinecone(api_key=api_key)

    assistants = pc.assistant.list_assistants()

    if hasattr(assistants, 'assistants'):
        assistant_list = assistants.assistants
    elif isinstance(assistants, dict):
        assistant_list = assistants.get('assistants', [])
    else:
        assistant_list = assistants if isinstance(assistants, list) else []

    if not assistant_list:
        print('NO_ASSISTANTS')
        sys.exit(0)

    for assistant in assistant_list:
        if hasattr(assistant, 'name'):
            name = assistant.name
            status = getattr(assistant, 'status', 'unknown')
            created = getattr(assistant, 'created_on', 'unknown')
        else:
            name = assistant.get('name', 'unknown')
            status = assistant.get('status', 'unknown')
            created = assistant.get('created_on', 'unknown')

        print(f'ASSISTANT|{name}|{status}|{created}')

    sys.exit(0)

except Exception as e:
    print(f'ERROR|{str(e)}')
    sys.exit(1)
"@

            $tempScript = Join-Path $env:TEMP "list_assistants_temp.py"
            $listScript | Out-File -FilePath $tempScript -Encoding UTF8

            try {
                Set-Location $ProjectDir
                # SECURITY FIX (L-2): Pass API key via stdin
                $result = $ApiKey | uv run python $tempScript 2>&1 | Out-String

                if ($result -match "NO_ASSISTANTS") {
                    Write-Info "No assistants found in your account."
                } elseif ($result -match "ASSISTANT") {
                    $lines = $result -split "`n"
                    $count = 0
                    foreach ($line in $lines) {
                        if ($line -match "ASSISTANT\|([^\|]+)\|([^\|]+)\|(.+)") {
                            $count++
                            Write-Info "[$count] Name: $($matches[1])"
                            Write-Info "    Status: $($matches[2])"
                            Write-Info "    Created: $($matches[3])"
                            Write-Info ""
                        }
                    }
                    Write-Success "Found $count assistant(s)"
                } else {
                    Write-Error "Unexpected response"
                    Write-Info $result
                }

            } catch {
                Write-Log "Error: $($_.Exception.Message)" "ERROR"
            } finally {
                if (Test-Path $tempScript) {
                    Remove-Item $tempScript -Force
                }
            }
        }

        "3" {
            # Get assistant details
            $AssistantName = Select-Assistant -ApiKey $ApiKey -ProjectDir $ProjectDir -Purpose "Details"

            if ($null -eq $AssistantName) {
                continue
            }

            # SECURITY FIX (L-2): Pass API key via stdin
            $detailsScript = @"
import sys
from pinecone import Pinecone

try:
    # SECURITY: Read API key from stdin instead of hardcoded string
    api_key = sys.stdin.read().strip()
    pc = Pinecone(api_key=api_key)

    assistant_info = pc.assistant.describe_assistant(assistant_name='$AssistantName')

    if hasattr(assistant_info, 'name'):
        name = assistant_info.name
        host = getattr(assistant_info, 'host', 'unknown')
        status = getattr(assistant_info, 'status', 'unknown')
        created = getattr(assistant_info, 'created_on', 'unknown')
        updated = getattr(assistant_info, 'updated_on', 'unknown')
        metadata = getattr(assistant_info, 'metadata', {})
        instructions = getattr(assistant_info, 'instructions', '')
    else:
        name = assistant_info.get('name', 'unknown')
        host = assistant_info.get('host', 'unknown')
        status = assistant_info.get('status', 'unknown')
        created = assistant_info.get('created_on', 'unknown')
        updated = assistant_info.get('updated_on', 'unknown')
        metadata = assistant_info.get('metadata', {})
        instructions = assistant_info.get('instructions', '')

    # Encode instructions for safe transmission (escape newlines)
    import base64
    instructions_encoded = base64.b64encode(instructions.encode('utf-8')).decode('utf-8') if instructions else ''

    print(f'SUCCESS|{name}|{host}|{status}|{created}|{updated}|{metadata}|{instructions_encoded}')
    sys.exit(0)

except Exception as e:
    print(f'ERROR|{str(e)}')
    sys.exit(1)
"@

            $tempScript = Join-Path $env:TEMP "details_assistant_temp.py"
            $detailsScript | Out-File -FilePath $tempScript -Encoding UTF8

            try {
                Set-Location $ProjectDir
                # SECURITY FIX (L-2): Pass API key via stdin
                $result = $ApiKey | uv run python $tempScript 2>&1 | Out-String

                if ($result -match "SUCCESS\|([^\|]+)\|([^\|]+)\|([^\|]+)\|([^\|]+)\|([^\|]+)\|([^\|]*)\|(.*)") {
                    Write-Info ""
                    Write-Success "=== Assistant Details ==="
                    Write-Info ""
                    Write-Info "  Name: $($matches[1])"
                    Write-Info "  Host: $($matches[2])"
                    Write-Info "  Status: $($matches[3])"
                    Write-Info "  Created: $($matches[4])"
                    Write-Info "  Updated: $($matches[5])"
                    if ($matches[6] -ne "{}") {
                        Write-Info "  Metadata: $($matches[6])"
                    }

                    # Decode and display system prompt (instructions)
                    if ($matches[7] -ne "") {
                        try {
                            $instructionsBytes = [System.Convert]::FromBase64String($matches[7])
                            $instructions = [System.Text.Encoding]::UTF8.GetString($instructionsBytes)

                            Write-Info ""
                            Write-Info "  System Prompt (Instructions):"
                            Write-Info "  $("-" * 60)"
                            # Display first 500 characters, or full if shorter
                            if ($instructions.Length -gt 500) {
                                Write-Info "  $($instructions.Substring(0, 500))..."
                                Write-Info "  $("[Truncated - Total length: $($instructions.Length) characters]")"
                            } else {
                                Write-Info "  $instructions"
                            }
                            Write-Info "  $("-" * 60)"
                        } catch {
                            Write-Warning "  Could not decode system prompt"
                        }
                    } else {
                        Write-Info ""
                        Write-Info "  System Prompt: (not configured)"
                    }

                    # Get and display file list
                    Write-Info ""
                    Write-Info "  Retrieving document list..."

                    # SECURITY FIX (L-2): Pass API key via stdin
                    $filesScript = @"
import sys
from pinecone import Pinecone

try:
    # SECURITY: Read API key from stdin instead of hardcoded string
    api_key = sys.stdin.read().strip()
    pc = Pinecone(api_key=api_key)

    # Get the assistant object (CORRECT API usage per Pinecone docs)
    assistant = pc.assistant.Assistant(assistant_name='$AssistantName')

    # List files on the assistant object
    # The API returns a list of File objects directly
    files_list = assistant.list_files()

    # Check if we got any files
    if not files_list or len(files_list) == 0:
        print('NO_FILES')
        sys.exit(0)

    # Process each file object
    for file_obj in files_list:
        # File objects have these attributes: id, name, size, status, created_on, updated_on
        # We need to safely extract them
        try:
            # Get name - required field
            if hasattr(file_obj, 'name'):
                name = file_obj.name
            elif isinstance(file_obj, dict):
                name = file_obj.get('name', 'unknown')
            else:
                continue

            # Get size - may be missing
            if hasattr(file_obj, 'size'):
                size = file_obj.size if file_obj.size is not None else 0
            elif isinstance(file_obj, dict):
                size = file_obj.get('size', 0)
            else:
                size = 0

            # Get status - may be missing
            if hasattr(file_obj, 'status'):
                status = file_obj.status if file_obj.status is not None else 'unknown'
            elif isinstance(file_obj, dict):
                status = file_obj.get('status', 'unknown')
            else:
                status = 'unknown'

            # Get created_on - may be missing
            if hasattr(file_obj, 'created_on'):
                created = str(file_obj.created_on) if file_obj.created_on is not None else 'unknown'
            elif isinstance(file_obj, dict):
                created = str(file_obj.get('created_on', 'unknown'))
            else:
                created = 'unknown'

            # Convert size to MB
            size_mb = size / (1024 * 1024) if size > 0 else 0

            # Output the file info
            print(f'FILE|{name}|{size_mb:.2f}|{status}|{created}')

        except Exception as e:
            # Skip files we can't process
            continue

    sys.exit(0)

except Exception as e:
    import traceback
    print(f'ERROR|{str(e)}', file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"@

                    $tempFilesScript = Join-Path $env:TEMP "list_files_temp.py"
                    $filesScript | Out-File -FilePath $tempFilesScript -Encoding UTF8

                    try {
                        # SECURITY FIX (L-2): Pass API key via stdin
                        # Capture only stdout (not stderr) to avoid treating Python errors as results
                        $filesResult = $ApiKey | uv run python $tempFilesScript 2>$null | Out-String

                        if ($filesResult -match "NO_FILES") {
                            Write-Info "  Documents: (none uploaded)"
                        } elseif ($filesResult -match "FILE") {
                            Write-Info ""
                            Write-Info "  Documents:"
                            Write-Info "  $("-" * 60)"

                            $fileLines = $filesResult -split "`n"
                            $fileCount = 0
                            foreach ($fileLine in $fileLines) {
                                if ($fileLine -match "FILE\|([^\|]+)\|([^\|]+)\|([^\|]+)\|(.+)") {
                                    $fileCount++
                                    $fileName = $matches[1]
                                    $fileSizeMB = $matches[2]
                                    $fileStatus = $matches[3]
                                    $fileCreated = $matches[4]

                                    Write-Info "    [$fileCount] $fileName"
                                    Write-Info "        Size: $fileSizeMB MB"
                                    Write-Info "        Status: $fileStatus"
                                    Write-Info "        Created: $fileCreated"
                                    Write-Info ""
                                }
                            }
                            Write-Info "  $("-" * 60)"
                            Write-Info "  Total: $fileCount file(s)"
                        } else {
                            Write-Warning "  Could not retrieve file list"
                        }
                    } catch {
                        Write-Warning "  Error retrieving files: $($_.Exception.Message)"
                    } finally {
                        if (Test-Path $tempFilesScript) {
                            Remove-Item $tempFilesScript -Force
                        }
                    }

                } else {
                    Write-Error "Failed to get details"
                    Write-Info $result
                }

            } catch {
                Write-Log "Error: $($_.Exception.Message)" "ERROR"
            } finally {
                if (Test-Path $tempScript) {
                    Remove-Item $tempScript -Force
                }
            }
        }

        "4" {
            # Upload documents
            $AssistantName = Select-Assistant -ApiKey $ApiKey -ProjectDir $ProjectDir -Purpose "Upload Documents"

            if ($null -eq $AssistantName) {
                continue
            }

            Write-Info ""
            Write-Info "Document source:"
            Write-Info "  [1] Upload from combined_documents.zip (extract all files)"
            Write-Info "  [2] Upload loose files only from combined_documents/ folder"
            Write-Info "  [3] Both - extract zip AND upload any additional loose files"
            Write-Info ""

            $sourceChoice = Read-Host "Enter choice (1-3)"

            Write-Info ""
            Write-Info "Document type:"
            Write-Info "  [1] USPTO MPEP documents (use USPTO metadata)"
            Write-Info "  [2] Custom documents (use generic metadata)"
            Write-Info ""

            $docType = Read-Host "Enter choice (1 or 2)"

            $uploadArgs = "--api-key `"$ApiKey`" --assistant-name `"$AssistantName`""

            if ($docType -eq "1") {
                $uploadArgs += " --use-uspto-metadata"
                Write-Info "Using USPTO-specific metadata"
            } else {
                Write-Info "Using generic metadata"
            }

            # Add document source flag
            if ($sourceChoice -eq "1") {
                $uploadArgs += " --zip-only"
                Write-Info "Source: combined_documents.zip only"
            } elseif ($sourceChoice -eq "2") {
                $uploadArgs += " --loose-only"
                Write-Info "Source: Loose files in combined_documents/ only"
            } else {
                # Default: both (no flag needed)
                Write-Info "Source: Both zip and loose files"
            }

            try {
                Set-Location $ScriptDir
                Write-Info ""
                Write-Info "Starting document upload..."
                Write-Info "This may take 5-10 minutes for the first file, 2-5 minutes for others."
                Write-Info ""

                Invoke-Expression "uv run python upload_files.py $uploadArgs"

                Write-Success "Upload command completed"

            } catch {
                Write-Log "Upload failed: $($_.Exception.Message)" "ERROR"
            }
        }

        "5" {
            # Update system prompt
            $AssistantName = Select-Assistant -ApiKey $ApiKey -ProjectDir $ProjectDir -Purpose "Update System Prompt"

            if ($null -eq $AssistantName) {
                continue
            }

            Write-Info ""
            Write-Info "System prompt source:"
            Write-Info "  [1] Load from assistant_system_prompt.txt (USPTO)"
            Write-Info "  [2] Load from assistant_system_prompt_generic.txt (Generic)"
            Write-Info "  [3] Enter custom prompt manually"
            Write-Info ""

            $promptChoice = Read-Host "Enter choice (1-3)"

            $systemPrompt = ""

            if ($promptChoice -eq "1") {
                $promptFile = Join-Path $ScriptDir "assistant_system_prompt.txt"
                if (Test-Path $promptFile) {
                    $systemPrompt = Get-Content -Path $promptFile -Raw -Encoding UTF8
                    Write-Success "Loaded USPTO system prompt from file"
                } else {
                    Write-Error "File not found: assistant_system_prompt.txt"
                    continue
                }
            } elseif ($promptChoice -eq "2") {
                $promptFile = Join-Path $ScriptDir "assistant_system_prompt_generic.txt"
                if (Test-Path $promptFile) {
                    $rawContent = Get-Content -Path $promptFile -Raw -Encoding UTF8
                    # Remove comment lines
                    $systemPrompt = ($rawContent -split "`n" | Where-Object { $_ -notmatch '^\s*#' -and $_ -notmatch '^\s*$' } | Select-Object -Skip 0) -join "`n"
                    Write-Success "Loaded generic system prompt from file"
                } else {
                    Write-Error "File not found: assistant_system_prompt_generic.txt"
                    continue
                }
            } else {
                Write-Info ""
                Write-Info "Enter your custom system prompt (press Ctrl+Z then Enter when done):"
                $systemPrompt = $host.UI.ReadLine()
            }

            if ([string]::IsNullOrWhiteSpace($systemPrompt)) {
                Write-Error "System prompt cannot be empty"
                continue
            }

            # Update assistant
            # SECURITY FIX (L-2): Pass API key via stdin
            $updatePromptScript = @"
import sys
from pinecone import Pinecone

try:
    # SECURITY: Read API key from stdin instead of hardcoded string
    api_key = sys.stdin.read().strip()
    pc = Pinecone(api_key=api_key)

    assistant_info = pc.assistant.describe_assistant(assistant_name='$AssistantName')

    if hasattr(assistant_info, 'metadata'):
        existing_metadata = assistant_info.metadata or {}
    else:
        existing_metadata = assistant_info.get('metadata', {})

    response = pc.assistant.update_assistant(
        assistant_name='$AssistantName',
        instructions='''$systemPrompt''',
        metadata=existing_metadata if existing_metadata else None
    )

    print('SUCCESS')
    sys.exit(0)

except Exception as e:
    print(f'ERROR|{str(e)}')
    sys.exit(1)
"@

            $tempScript = Join-Path $env:TEMP "update_prompt_temp.py"
            $updatePromptScript | Out-File -FilePath $tempScript -Encoding UTF8

            try {
                Set-Location $ProjectDir
                # SECURITY FIX (L-2): Pass API key via stdin
                $result = $ApiKey | uv run python $tempScript 2>&1 | Out-String

                if ($result -match "SUCCESS") {
                    Write-Success "System prompt updated successfully!"
                } else {
                    Write-Error "Failed to update system prompt"
                    Write-Info $result
                }

            } catch {
                Write-Log "Error: $($_.Exception.Message)" "ERROR"
            } finally {
                if (Test-Path $tempScript) {
                    Remove-Item $tempScript -Force
                }
            }
        }

        "6" {
            # Delete assistant
            Write-Info ""
            Write-Info "=== Delete Assistant ==="
            Write-Warning ""
            Write-Warning "WARNING: This action cannot be undone!"
            Write-Warning ""

            $AssistantName = Read-Host "Enter assistant name to delete"

            $confirm = Read-Host "Are you sure you want to delete '$AssistantName'? Type 'DELETE' to confirm"

            if ($confirm -ne "DELETE") {
                Write-Info "Deletion cancelled"
                continue
            }

            # SECURITY FIX (L-2): Pass API key via stdin
            $deleteScript = @"
import sys
from pinecone import Pinecone

try:
    # SECURITY: Read API key from stdin instead of hardcoded string
    api_key = sys.stdin.read().strip()
    pc = Pinecone(api_key=api_key)

    response = pc.assistant.delete_assistant(assistant_name='$AssistantName')

    print('SUCCESS')
    sys.exit(0)

except Exception as e:
    print(f'ERROR|{str(e)}')
    sys.exit(1)
"@

            $tempScript = Join-Path $env:TEMP "delete_assistant_temp.py"
            $deleteScript | Out-File -FilePath $tempScript -Encoding UTF8

            try {
                Set-Location $ProjectDir
                # SECURITY FIX (L-2): Pass API key via stdin
                $result = $ApiKey | uv run python $tempScript 2>&1 | Out-String

                if ($result -match "SUCCESS") {
                    Write-Success "Assistant '$AssistantName' deleted successfully"
                } else {
                    Write-Error "Failed to delete assistant"
                    Write-Info $result
                }

            } catch {
                Write-Log "Error: $($_.Exception.Message)" "ERROR"
            } finally {
                if (Test-Path $tempScript) {
                    Remove-Item $tempScript -Force
                }
            }
        }

        "7" {
            # Exit
            Write-Info ""
            Write-Success "Goodbye!"
            $continue = $false
        }

        default {
            Write-Warning "Invalid choice. Please enter 1-7."
        }
    }
}

Write-Info ""
Write-Log "Session log saved to: $LogFile" "INFO"
Write-Info ""
