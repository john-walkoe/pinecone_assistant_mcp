# Pinecone Assistant MCP - API Key Management Script
# ==================================================
#
# Features:
# - View current API key status (shows last 5 digits only for security)
# - Update Pinecone API key
# - Remove API key from Windows Credential Manager
# - Test API key access
# - Check storage method (Credential Manager vs DPAPI vs Environment)

param(
    [switch]$Help
)

# Import validation helpers for secure API key input and display
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ValidationModule = Join-Path $ScriptDir "Validation-Helpers.psm1"
if (Test-Path $ValidationModule) {
    Import-Module $ValidationModule -Force
    Write-Host "[OK] Validation helpers loaded" -ForegroundColor Green
} else {
    Write-Host "[WARN] Validation helpers not found - using basic functions" -ForegroundColor Yellow
    # Fallback function if validation module not available
    function Hide-ApiKey {
        param([string]$ApiKey, [int]$VisibleChars = 5)
        if ([string]::IsNullOrEmpty($ApiKey)) {
            return "Not set"
        }
        if ($ApiKey.Length -le $VisibleChars) {
            return "***"
        }
        $masked = '*' * ($ApiKey.Length - $VisibleChars)
        $visible = $ApiKey.Substring($ApiKey.Length - $VisibleChars)
        return "$masked$visible"
    }
    function Read-ApiKeySecure {
        param([string]$Prompt)
        $secureString = Read-Host -Prompt $Prompt -AsSecureString
        $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureString)
        $apiKey = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        return $apiKey
    }
}

# Check if help is requested
if ($Help) {
    Write-Host "Pinecone Assistant MCP - API Key Management" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\manage_api_keys.ps1"
    Write-Host ""
    Write-Host "Features:"
    Write-Host "  - View current API key (secure - last 5 digits only)"
    Write-Host "  - Update Pinecone API key"
    Write-Host "  - Remove API key from storage"
    Write-Host "  - Test API key functionality"
    Write-Host "  - Check storage location"
    Write-Host ""
    Write-Host "Storage Priority:"
    Write-Host "  1. Windows Credential Manager (cmdkey)"
    Write-Host "  2. DPAPI encrypted file (legacy)"
    Write-Host "  3. Environment variable (fallback)"
    Write-Host ""
    Write-Host "Security: API keys are stored in Windows Credential Manager"
    Write-Host "Target: pinecone_API_KEY"
    exit 0
}

$ProjectDir = Split-Path -Parent $PSScriptRoot

# Function to format key display (last 5 digits only for security)
function Format-KeyDisplay {
    param([string]$ApiKey)

    if ([string]::IsNullOrEmpty($ApiKey)) {
        return "Not set"
    }

    $lastDigits = $ApiKey.Substring([Math]::Max(0, $ApiKey.Length - 5))
    return "...$lastDigits ($($ApiKey.Length) chars)"
}

# Function to test if uv is available
function Test-Requirements {
    try {
        $uvVersion = uv --version 2>$null
        if (-not $uvVersion) {
            Write-Host "[ERROR] uv package manager is required but not found" -ForegroundColor Red
            Write-Host "        Please install uv: https://github.com/astral-sh/uv" -ForegroundColor Yellow
            return $false
        }
        return $true
    } catch {
        Write-Host "[ERROR] uv package manager is required but not found" -ForegroundColor Red
        Write-Host "        Please install uv: https://github.com/astral-sh/uv" -ForegroundColor Yellow
        return $false
    }
}

# Function to check Windows Credential Manager
function Get-CredentialManagerKey {
    try {
        $targetName = "pinecone_API_KEY"
        $result = cmdkey /list:$targetName 2>&1 | Out-String

        if ($result -match "Target: $targetName") {
            return "CREDENTIAL_MANAGER"
        }
        return $null
    } catch {
        return $null
    }
}

# Function to get current API key status
function Get-ApiKeyStatus {
    try {
        Set-Location $ProjectDir
        $result = uv run python -c "
import sys
import os
sys.path.insert(0, 'src')

from config.secure_storage import get_secure_api_key, get_api_key_from_credential_manager

# Check storage locations
storage_location = 'NONE'
api_key = None

# Try Credential Manager first
cred_key = get_api_key_from_credential_manager()
if cred_key:
    api_key = cred_key
    storage_location = 'CREDENTIAL_MANAGER'
else:
    # Try DPAPI file storage
    from config.secure_storage import SecureStorage
    storage = SecureStorage()
    if storage.storage_file.exists():
        dpapi_key = storage.get_api_key()
        if dpapi_key and not dpapi_key.startswith('PINECONE'):
            api_key = dpapi_key
            storage_location = 'DPAPI_FILE'
        else:
            # Check environment
            env_key = os.environ.get('PINECONE_ASSISTANT_API_KEY', '')
            if env_key:
                api_key = env_key
                storage_location = 'ENVIRONMENT'
    else:
        # Check environment as fallback
        env_key = os.environ.get('PINECONE_ASSISTANT_API_KEY', '')
        if env_key:
            api_key = env_key
            storage_location = 'ENVIRONMENT'

print('KEY:' + (api_key if api_key else ''))
print('STORAGE:' + storage_location)
" 2>&1 | Out-String

        if ($LASTEXITCODE -eq 0) {
            $lines = $result -split "`n"
            $apiKey = ""
            $storageLocation = "NONE"

            foreach ($line in $lines) {
                $line = $line.Trim()
                if ($line.StartsWith("KEY:")) {
                    $apiKey = $line.Substring(4)
                } elseif ($line.StartsWith("STORAGE:")) {
                    $storageLocation = $line.Substring(8)
                }
            }

            return @{
                "ApiKey" = $apiKey
                "Storage" = $storageLocation
            }
        } else {
            Write-Host "[ERROR] Failed to check API key status" -ForegroundColor Red
            Write-Host $result -ForegroundColor Red
            return $null
        }
    } catch {
        Write-Host "[ERROR] Failed to check API key status: $_" -ForegroundColor Red
        return $null
    }
}

# Function to store API key using cmdkey
function Set-ApiKey {
    param([string]$ApiKey)

    # Validate key format
    if (-not $ApiKey.StartsWith("pcsk_")) {
        Write-Host "[ERROR] Invalid API key format. Must start with 'pcsk_'" -ForegroundColor Red
        return $false
    }

    if ($ApiKey.Length -lt 33) {
        Write-Host "[ERROR] API key too short (minimum 33 characters)" -ForegroundColor Red
        return $false
    }

    try {
        $targetName = "pinecone_API_KEY"

        # Remove existing credential if present
        cmdkey /delete:$targetName 2>&1 | Out-Null

        # Store new credential
        $result = cmdkey /generic:$targetName /user:"pinecone_API_KEY" /pass:$ApiKey 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] API key stored in Windows Credential Manager" -ForegroundColor Green
            Write-Host "     Target: $targetName" -ForegroundColor Gray

            # SECURITY: Remove any legacy plaintext cache file (H-4 fix)
            $legacyCacheFile = Join-Path $env:USERPROFILE ".pinecone_assistant_cred_cache"
            if (Test-Path $legacyCacheFile) {
                Remove-Item $legacyCacheFile -Force -ErrorAction SilentlyContinue
                Write-Host "     Removed legacy plaintext cache file" -ForegroundColor Gray
            }

            # Also store in DPAPI so Python can retrieve it without a plaintext file
            $storeScript = @"
import sys
sys.path.insert(0, 'src')
from config.secure_storage import SecureStorage
storage = SecureStorage()
success = storage.store_api_key(sys.stdin.read().strip())
print('DPAPI' if success else 'FAIL')
"@
            $tempStoreScript = Join-Path $env:TEMP "store_key_temp.py"
            $storeScript | Out-File -FilePath $tempStoreScript -Encoding UTF8
            try {
                Set-Location $ProjectDir
                $storeResult = $ApiKey | uv run python $tempStoreScript 2>&1
                if ($storeResult -match "DPAPI") {
                    Write-Host "     Also stored in DPAPI encryption" -ForegroundColor Gray
                }
            } catch { } finally {
                Remove-Item $tempStoreScript -ErrorAction SilentlyContinue
            }

            return $true
        } else {
            Write-Host "[ERROR] Failed to store credential: $result" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "[ERROR] Failed to store API key: $_" -ForegroundColor Red
        return $false
    }
}

# Function to remove API key
function Remove-ApiKey {
    param([switch]$All)

    $removed = @()

    try {
        # Remove from Credential Manager
        $targetName = "pinecone_API_KEY"
        $checkResult = cmdkey /list:$targetName 2>&1 | Out-String

        if ($checkResult -match "Target: $targetName") {
            cmdkey /delete:$targetName 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                $removed += "Credential Manager"
            }
        }

        # Remove cache file (always remove when removing from Credential Manager)
        $cacheFile = Join-Path $env:USERPROFILE ".pinecone_assistant_cred_cache"
        if (Test-Path $cacheFile) {
            Remove-Item $cacheFile -Force
            $removed += "Cache File"
        }

        if ($All) {
            # Also remove DPAPI files
            Set-Location $ProjectDir
            $result = uv run python -c "
import sys
sys.path.insert(0, 'src')
from config.secure_storage import SecureStorage

storage = SecureStorage()
removed = []

if storage.storage_file.exists():
    storage.storage_file.unlink()
    removed.append('DPAPI_KEY')

print(','.join(removed) if removed else 'NONE')
" 2>&1 | Out-String

            if ($result.Trim() -ne "NONE" -and $result.Trim() -ne "") {
                $removed += "DPAPI Files"
            }
        }

        if ($removed.Count -gt 0) {
            Write-Host "[OK] Removed API key from: $($removed -join ', ')" -ForegroundColor Green
        } else {
            Write-Host "[INFO] No API keys found to remove" -ForegroundColor Yellow
        }

        return $true
    } catch {
        Write-Host "[ERROR] Failed to remove API key: $_" -ForegroundColor Red
        return $false
    }
}

# Function to test API key functionality
function Test-ApiKey {
    Write-Host ""
    Write-Host "Testing API Key Functionality" -ForegroundColor Cyan
    Write-Host "==============================" -ForegroundColor Cyan

    try {
        Set-Location $ProjectDir
        $result = uv run python -c "
import sys
sys.path.insert(0, 'src')

from config.secure_storage import get_secure_api_key
from config.config import get_settings

print('1. Checking API key retrieval...')
api_key = get_secure_api_key()

if not api_key:
    print('   [FAIL] No API key found')
    sys.exit(1)

if not api_key.startswith('pcsk_'):
    print('   [FAIL] Invalid API key format')
    sys.exit(1)

print(f'   [OK] API key retrieved ({len(api_key)} chars)')

print('2. Testing settings integration...')
try:
    # Temporarily set env var for settings test
    import os
    os.environ['PINECONE_ASSISTANT_API_KEY'] = api_key

    settings = get_settings()

    if settings.pinecone_assistant_api_key:
        print('   [OK] Settings loaded with API key')
    else:
        print('   [WARN] Settings loaded but API key not found')
except Exception as e:
    print(f'   [FAIL] Settings error: {e}')
    sys.exit(1)

print('')
print('All tests passed!')
" 2>&1 | Out-String

        Write-Host $result
    } catch {
        Write-Host "[ERROR] Failed to run API key tests: $_" -ForegroundColor Red
    }
}

# Function to show storage information
function Show-StorageInfo {
    Write-Host ""
    Write-Host "API Key Storage Information" -ForegroundColor Cyan
    Write-Host "============================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Storage Priority:" -ForegroundColor White
    Write-Host "  1. Windows Credential Manager (cmdkey)" -ForegroundColor Green
    Write-Host "     Target: pinecone_API_KEY"
    Write-Host "     Most secure, native Windows integration"
    Write-Host ""
    Write-Host "  2. DPAPI Encrypted File" -ForegroundColor Yellow
    Write-Host "     Location: ~/.pinecone_api_key"
    Write-Host "     Entropy:  ~/.uspto_internal_auth_secret (bytes 0-31)"
    Write-Host "     Shared across all 3 Pinecone MCPs"
    Write-Host ""
    Write-Host "  3. Environment Variable (fallback)" -ForegroundColor Red
    Write-Host "     Variable: PINECONE_API_KEY"
    Write-Host "     Fallback: PINECONE_ASSISTANT_API_KEY"
    Write-Host "     Not encrypted, visible in process list"
    Write-Host ""
    Write-Host "Recommendation: Use Windows Credential Manager (option 1)" -ForegroundColor Cyan
}

# Main menu
function Main {
    # Check requirements
    if (-not (Test-Requirements)) {
        exit 1
    }

    while ($true) {
        # Clear screen and show header
        Clear-Host
        Write-Host "Pinecone Assistant MCP - API Key Management" -ForegroundColor Cyan
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host ""

        # Get current API key status
        $keyInfo = Get-ApiKeyStatus

        if ($keyInfo) {
            Write-Host "Current Status:" -ForegroundColor White

            # Use Hide-ApiKey if available, otherwise fallback to Format-KeyDisplay
            if (Get-Command "Hide-ApiKey" -ErrorAction SilentlyContinue) {
                $keyDisplay = Hide-ApiKey -ApiKey $keyInfo.ApiKey
            } else {
                $keyDisplay = Format-KeyDisplay $keyInfo.ApiKey
            }
            $storageColor = switch ($keyInfo.Storage) {
                "CREDENTIAL_MANAGER" { "Green" }
                "DPAPI_FILE" { "Yellow" }
                "ENVIRONMENT" { "Red" }
                default { "Gray" }
            }

            $storageText = switch ($keyInfo.Storage) {
                "CREDENTIAL_MANAGER" { "Windows Credential Manager" }
                "DPAPI_FILE" { "DPAPI Encrypted File (legacy)" }
                "ENVIRONMENT" { "Environment Variable (insecure)" }
                "NONE" { "Not configured" }
                default { $keyInfo.Storage }
            }

            Write-Host "  API Key: $keyDisplay" -ForegroundColor $(if ($keyInfo.ApiKey) { "Green" } else { "Red" })
            Write-Host "  Storage: $storageText" -ForegroundColor $storageColor
        } else {
            Write-Host "Unable to check current API key status" -ForegroundColor Red
        }

        Write-Host ""
        Write-Host "Actions:" -ForegroundColor White
        Write-Host "  [1] Update Pinecone API key"
        Write-Host "  [2] Remove API key"
        Write-Host "  [3] Test API key functionality"
        Write-Host "  [4] Show storage information"
        Write-Host "  [5] Refresh status"
        Write-Host "  [6] Exit"
        Write-Host ""

        $choice = Read-Host "Enter choice (1-6)"

        switch ($choice) {
            "1" {
                Write-Host ""
                Write-Host "Update Pinecone API Key" -ForegroundColor Cyan
                Write-Host "========================" -ForegroundColor Cyan
                Write-Host ""
                Write-Host "Get your API key from: https://app.pinecone.io/" -ForegroundColor Yellow
                Write-Host "Key format: pcsk_ followed by 70 characters (75 total)" -ForegroundColor Yellow
                Write-Host ""

                $attemptCount = 0
                $maxAttempts = 3
                $validKey = $false
                $newKey = ""

                while (-not $validKey -and $attemptCount -lt $maxAttempts) {
                    $attemptCount++

                    # Use masked input if available
                    if (Get-Command "Read-ApiKeySecure" -ErrorAction SilentlyContinue) {
                        $newKey = Read-ApiKeySecure -Prompt "Enter new Pinecone API key (input hidden)"
                    } else {
                        $newKey = Read-Host "Enter new Pinecone API key"
                    }

                    if ([string]::IsNullOrWhiteSpace($newKey)) {
                        Write-Host "[INFO] No key provided - operation cancelled" -ForegroundColor Yellow
                        break
                    }

                    # Validate format if validator available
                    if (Get-Command "Test-PineconeApiKey" -ErrorAction SilentlyContinue) {
                        if (Test-PineconeApiKey -ApiKey $newKey) {
                            $validKey = $true
                            Write-Host "[OK] Pinecone API key format validated" -ForegroundColor Green
                        } else {
                            Write-Host "[ERROR] Invalid Pinecone API key format" -ForegroundColor Red
                            Write-Host "[INFO] Expected: pcsk_ followed by 70 alphanumeric/underscore characters (75 total)" -ForegroundColor Yellow
                            if ($attemptCount -lt $maxAttempts) {
                                Write-Host "[INFO] Attempt $attemptCount of $maxAttempts - please try again" -ForegroundColor Yellow
                            }
                        }
                    } else {
                        # No validator available - accept non-empty key
                        $validKey = $true
                    }
                }

                if ($validKey) {
                    Set-ApiKey -ApiKey $newKey.Trim()
                } elseif (-not [string]::IsNullOrWhiteSpace($newKey)) {
                    Write-Host "[ERROR] Maximum attempts reached - key not updated" -ForegroundColor Red
                }

                Write-Host ""
                Read-Host "Press Enter to continue"
            }

            "2" {
                Write-Host ""
                Write-Host "Remove API Key" -ForegroundColor Cyan
                Write-Host "===============" -ForegroundColor Cyan
                Write-Host "  [1] Remove from Credential Manager only"
                Write-Host "  [2] Remove ALL stored keys (Credential Manager + DPAPI files)"
                Write-Host "  [3] Cancel"
                Write-Host ""

                $removeChoice = Read-Host "Enter choice (1-3)"

                switch ($removeChoice) {
                    "1" { Remove-ApiKey }
                    "2" {
                        $confirm = Read-Host "Are you sure you want to remove ALL stored API keys? (y/N)"
                        if ($confirm -eq "y" -or $confirm -eq "Y") {
                            Remove-ApiKey -All
                        } else {
                            Write-Host "[INFO] Operation cancelled" -ForegroundColor Yellow
                        }
                    }
                    "3" { Write-Host "[INFO] Operation cancelled" -ForegroundColor Yellow }
                    default { Write-Host "[ERROR] Invalid choice" -ForegroundColor Red }
                }

                Write-Host ""
                Read-Host "Press Enter to continue"
            }

            "3" {
                Test-ApiKey
                Write-Host ""
                Read-Host "Press Enter to continue"
            }

            "4" {
                Show-StorageInfo
                Write-Host ""
                Read-Host "Press Enter to continue"
            }

            "5" {
                # Just refresh - loop will redraw
                continue
            }

            "6" {
                Write-Host ""
                Write-Host "Goodbye!" -ForegroundColor Green
                exit 0
            }

            default {
                Write-Host ""
                Write-Host "[ERROR] Invalid choice. Please enter 1-6." -ForegroundColor Red
                Start-Sleep -Seconds 2
            }
        }
    }
}

# Run the main function
Main
