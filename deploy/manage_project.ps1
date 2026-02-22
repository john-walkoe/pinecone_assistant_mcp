# Pinecone Project Management Script
# For managing Pinecone projects - useful for resetting free tier token limits

# Import validation helpers for secure API key input
$ValidationModule = Join-Path $PSScriptRoot "Validation-Helpers.psm1"
if (Test-Path $ValidationModule) {
    Import-Module $ValidationModule -Force
    Write-Host "[OK] Validation helpers loaded" -ForegroundColor Green
} else {
    Write-Host "[WARN] Validation helpers not found - API keys will be displayed in plain text" -ForegroundColor Yellow
}

Write-Host "=== Pinecone Project Management Tool ===" -ForegroundColor Green
Write-Host ""
Write-Host "⚠️  WARNING: This tool manages Pinecone PROJECTS (not just assistants)" -ForegroundColor Yellow
Write-Host "    Deleting a project will PERMANENTLY DELETE:" -ForegroundColor Yellow
Write-Host "    - ALL assistants and their documents" -ForegroundColor Yellow
Write-Host "    - ALL vector databases (indexes)" -ForegroundColor Yellow
Write-Host "    - ALL backups and collections" -ForegroundColor Yellow
Write-Host "    - ALL project resources and configuration" -ForegroundColor Yellow
Write-Host ""

# Set error action preference
$ErrorActionPreference = "Stop"

# Script configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$LogFile = Join-Path $ScriptDir "manage_project.log"

# Color functions for output
function Write-Success { param($Message) Write-Host $Message -ForegroundColor Green }
function Write-Warning { param($Message) Write-Host $Message -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host $Message -ForegroundColor Red }
function Write-Info { param($Message) Write-Host $Message -ForegroundColor Cyan }

# Logging function
function Write-Log {
    param($Message, $Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "[$Timestamp] [$Level] $Message"
    Add-Content -Path $LogFile -Value $LogEntry -ErrorAction SilentlyContinue

    switch ($Level) {
        "ERROR" { Write-Error $Message }
        "WARNING" { Write-Warning $Message }
        "SUCCESS" { Write-Success $Message }
        default { Write-Info $Message }
    }
}

# Helper function to get API key from secure storage or prompt
function Get-PineconeApiKey {
    # Try to get from secure storage first
    try {
        Set-Location $ProjectDir
        $result = uv run python -c "
import sys
sys.path.insert(0, 'src')
from config.secure_storage import get_secure_api_key
key = get_secure_api_key()
if key and key.startswith('pcsk_'):
    print(key)
else:
    print('NOT_FOUND')
" 2>$null | Out-String

        if ($result.Trim() -match '^pcsk_') {
            Write-Log "API key retrieved from secure storage" "SUCCESS"
            return $result.Trim()
        }
    } catch {
        # Secure storage not available or failed
    }

    # Prompt for API key
    Write-Info ""
    Write-Info "Enter your Pinecone API key"
    Write-Info "(This should be your organization API key, not assistant API key)"
    Write-Info "(Get it from: https://app.pinecone.io/ → API Keys)"
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
            $ApiKey = Read-ApiKeySecure -Prompt "Enter your Pinecone API key (input hidden)"
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

    return $ApiKey
}

# Helper function to list projects
function Get-ProjectList {
    param($ApiKey, $ProjectDir)

    $listScript = @"
import sys
import requests

try:
    headers = {
        'Api-Key': '$ApiKey',
        'Content-Type': 'application/json'
    }

    response = requests.get(
        'https://api.pinecone.io/projects',
        headers=headers,
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()
        projects = data.get('projects', [])

        if not projects:
            print('NO_PROJECTS')
            sys.exit(0)

        for project in projects:
            project_id = project.get('id', 'unknown')
            project_name = project.get('name', 'unknown')
            created_at = project.get('created_at', 'unknown')
            print(f'PROJECT|{project_id}|{project_name}|{created_at}')

        sys.exit(0)
    elif response.status_code == 401:
        print('ERROR|UNAUTHORIZED|Invalid API key or authentication failed')
        sys.exit(1)
    else:
        print(f'ERROR|HTTP_{response.status_code}|{response.text}')
        sys.exit(1)

except requests.exceptions.Timeout:
    print('ERROR|TIMEOUT|Request timed out - please check your network connection')
    sys.exit(1)
except requests.exceptions.ConnectionError:
    print('ERROR|CONNECTION|Could not connect to Pinecone API')
    sys.exit(1)
except Exception as e:
    print(f'ERROR|EXCEPTION|{str(e)}')
    sys.exit(1)
"@

    $tempScript = Join-Path $env:TEMP "list_projects_temp.py"
    $listScript | Out-File -FilePath $tempScript -Encoding UTF8

    try {
        Set-Location $ProjectDir
        $result = uv run python $tempScript 2>&1 | Out-String

        $projects = @()

        if ($result -match "NO_PROJECTS") {
            return $null
        } elseif ($result -match "PROJECT") {
            $lines = $result -split "`n"
            foreach ($line in $lines) {
                if ($line -match "PROJECT\|([^\|]+)\|([^\|]+)\|(.+)") {
                    $projects += [PSCustomObject]@{
                        Id = $matches[1].Trim()
                        Name = $matches[2].Trim()
                        CreatedAt = $matches[3].Trim()
                    }
                }
            }
        } elseif ($result -match "ERROR\|([^\|]+)\|(.+)") {
            $errorType = $matches[1]
            $errorMsg = $matches[2]
            Write-Log "API Error: $errorType - $errorMsg" "ERROR"
            return $null
        }

        if ($projects.Count -eq 0) {
            return $null
        }

        return @($projects)

    } catch {
        Write-Log "Error retrieving projects: $($_.Exception.Message)" "ERROR"
        return $null
    } finally {
        if (Test-Path $tempScript) {
            Remove-Item $tempScript -Force
        }
    }
}

# Helper function to delete a project
function Remove-PineconeProject {
    param($ApiKey, $ProjectId, $ProjectDir)

    $deleteScript = @"
import sys
import requests

try:
    headers = {
        'Api-Key': '$ApiKey',
        'Content-Type': 'application/json'
    }

    response = requests.delete(
        f'https://api.pinecone.io/projects/{$ProjectId}',
        headers=headers,
        timeout=30
    )

    if response.status_code == 202:
        print('SUCCESS|Project deletion request accepted')
        sys.exit(0)
    elif response.status_code == 401:
        print('ERROR|UNAUTHORIZED|Invalid API key')
        sys.exit(1)
    elif response.status_code == 403:
        print('ERROR|FORBIDDEN|Permission denied - you may not have access to delete this project')
        sys.exit(1)
    elif response.status_code == 404:
        print('ERROR|NOT_FOUND|Project not found')
        sys.exit(1)
    elif response.status_code == 400:
        # Likely has assistants or resources that need to be deleted first
        print('ERROR|HAS_RESOURCES|Project still has resources (assistants, indexes, etc). Delete them first.')
        sys.exit(1)
    else:
        print(f'ERROR|HTTP_{response.status_code}|{response.text}')
        sys.exit(1)

except requests.exceptions.Timeout:
    print('ERROR|TIMEOUT|Request timed out')
    sys.exit(1)
except Exception as e:
    print(f'ERROR|EXCEPTION|{str(e)}')
    sys.exit(1)
"@

    $tempScript = Join-Path $env:TEMP "delete_project_temp.py"
    $deleteScript | Out-File -FilePath $tempScript -Encoding UTF8

    try {
        Set-Location $ProjectDir
        $result = uv run python $tempScript 2>&1 | Out-String

        if ($result -match "SUCCESS") {
            return $true
        } elseif ($result -match "ERROR\|([^\|]+)\|(.+)") {
            $errorType = $matches[1]
            $errorMsg = $matches[2]
            Write-Log "Delete failed: $errorType - $errorMsg" "ERROR"
            return $false
        } else {
            Write-Log "Unexpected response: $result" "ERROR"
            return $false
        }

    } catch {
        Write-Log "Error deleting project: $($_.Exception.Message)" "ERROR"
        return $false
    } finally {
        if (Test-Path $tempScript) {
            Remove-Item $tempScript -Force
        }
    }
}

# Helper function to delete all assistants in current project
function Remove-AllAssistants {
    param($ApiKey, $ProjectDir)

    Write-Info ""
    Write-Info "Before deleting a project, you must delete all assistants in it."
    Write-Info "Do you want to list and delete all assistants now? (Y/n)"

    $deleteAssistants = Read-Host

    if ($deleteAssistants -eq "" -or $deleteAssistants -eq "Y" -or $deleteAssistants -eq "y") {
        # Call manage_assistant.ps1 in delete mode
        $manageAssistantScript = Join-Path $ScriptDir "manage_assistant.ps1"

        if (Test-Path $manageAssistantScript) {
            Write-Info ""
            Write-Info "Launching assistant management tool..."
            Write-Info "Please delete all assistants (option 6), then exit (option 7)"
            Write-Info ""
            Read-Host "Press Enter to continue"

            & $manageAssistantScript

            Write-Info ""
            Write-Info "Have you deleted all assistants? (Y/n)"
            $confirmed = Read-Host

            if ($confirmed -eq "" -or $confirmed -eq "Y" -or $confirmed -eq "y") {
                return $true
            } else {
                Write-Warning "Project deletion cancelled - assistants must be deleted first"
                return $false
            }
        } else {
            Write-Warning "manage_assistant.ps1 not found"
            Write-Info "Please manually delete all assistants before proceeding"
            Write-Info "Visit: https://app.pinecone.io/ → Assistants → Delete each assistant"
            Write-Info ""
            Write-Info "Have you deleted all assistants? (Y/n)"
            $confirmed = Read-Host

            return ($confirmed -eq "" -or $confirmed -eq "Y" -or $confirmed -eq "y")
        }
    } else {
        Write-Warning "You must delete all assistants before deleting the project"
        return $false
    }
}

# Initialize log file
"Project management session started at $(Get-Date)" | Out-File -FilePath $LogFile -Encoding UTF8
Write-Log "Pinecone Project Management Tool"

# Get API key
$ApiKey = Get-PineconeApiKey

# Main menu loop
$continue = $true

while ($continue) {
    Write-Info ""
    Write-Info "=== Project Management Menu ==="
    Write-Info ""
    Write-Info "  [1] List all projects in organization"
    Write-Info "  [2] Delete a project (⚠️  DESTRUCTIVE - deletes all assistants/data)"
    Write-Info "  [3] View project deletion requirements"
    Write-Info "  [4] Exit"
    Write-Info ""

    $choice = Read-Host "Enter choice (1-4)"

    switch ($choice) {
        "1" {
            # List all projects
            Write-Info ""
            Write-Info "=== List All Projects ==="
            Write-Info ""

            $projects = Get-ProjectList -ApiKey $ApiKey -ProjectDir $ProjectDir

            if ($null -eq $projects) {
                Write-Info "No projects found in your organization, or unable to retrieve projects."
            } else {
                Write-Success "Found $($projects.Count) project(s):"
                Write-Info ""

                $index = 1
                foreach ($project in $projects) {
                    Write-Info "[$index] Project: $($project.Name)"
                    Write-Info "    ID: $($project.Id)"
                    Write-Info "    Created: $($project.CreatedAt)"
                    Write-Info ""
                    $index++
                }
            }
        }

        "2" {
            # Delete a project
            Write-Info ""
            Write-Info "=== Delete Project ==="
            Write-Warning ""
            Write-Warning "⚠️  WARNING: This will PERMANENTLY DELETE:"
            Write-Warning "   - All assistants in the project"
            Write-Warning "   - All documents/files uploaded to assistants"
            Write-Warning "   - All vector databases (indexes) in the project"
            Write-Warning "   - All backups and collections"
            Write-Warning "   - All project configuration"
            Write-Warning "   - This action CANNOT be undone!"
            Write-Warning ""
            Write-Info "⚠️  IMPORTANT: If you have Pinecone vector databases in this project,"
            Write-Info "   they will be DELETED along with all their data!"
            Write-Warning ""
            Write-Info "For Starter Plan:"
            Write-Info "   - You can only have 1 project at a time"
            Write-Info "   - Deleting and recreating resets token limits"
            Write-Info "   - You will need to re-upload all documents"
            Write-Warning ""

            # List projects first
            $projects = Get-ProjectList -ApiKey $ApiKey -ProjectDir $ProjectDir

            if ($null -eq $projects -or $projects.Count -eq 0) {
                Write-Info "No projects found to delete."
                continue
            }

            Write-Info "Available projects:"
            $index = 1
            foreach ($project in $projects) {
                Write-Info "  [$index] $($project.Name) (ID: $($project.Id))"
                $index++
            }
            Write-Info "  [0] Cancel"
            Write-Info ""

            $selection = Read-Host "Select project to delete (0-$($projects.Count))"

            if ($selection -eq "0" -or [string]::IsNullOrWhiteSpace($selection)) {
                Write-Info "Deletion cancelled"
                continue
            }

            try {
                $projectIndex = [int]$selection - 1
                if ($projectIndex -ge 0 -and $projectIndex -lt $projects.Count) {
                    $selectedProject = $projects[$projectIndex]

                    Write-Warning ""
                    Write-Warning "Selected project: $($selectedProject.Name)"
                    Write-Warning "Project ID: $($selectedProject.Id)"
                    Write-Warning ""

                    # Delete assistants first
                    $assistantsDeleted = Remove-AllAssistants -ApiKey $ApiKey -ProjectDir $ProjectDir

                    if (-not $assistantsDeleted) {
                        Write-Warning "Cannot proceed with project deletion until assistants are deleted"
                        continue
                    }

                    # Final confirmation
                    Write-Warning ""
                    Write-Warning "FINAL CONFIRMATION:"
                    Write-Warning "Type the exact project name to confirm deletion: $($selectedProject.Name)"
                    Write-Warning ""

                    $confirmation = Read-Host "Project name"

                    if ($confirmation -ne $selectedProject.Name) {
                        Write-Info "Deletion cancelled - name did not match"
                        continue
                    }

                    # Perform deletion
                    Write-Info ""
                    Write-Info "Deleting project..."

                    $success = Remove-PineconeProject -ApiKey $ApiKey -ProjectId $selectedProject.Id -ProjectDir $ProjectDir

                    if ($success) {
                        Write-Success ""
                        Write-Success "✓ Project deletion request accepted!"
                        Write-Success "  Project: $($selectedProject.Name)"
                        Write-Success "  ID: $($selectedProject.Id)"
                        Write-Info ""
                        Write-Info "The project is being deleted asynchronously."
                        Write-Info "It may take a few moments to complete."
                        Write-Info ""
                        Write-Info "Next Steps:"
                        Write-Info "1. Wait 1-2 minutes for deletion to complete"
                        Write-Info "2. Create a new project in Pinecone Console: https://app.pinecone.io/"
                        Write-Info "3. Run setup script to recreate assistants:"
                        Write-Info "   .\deploy\windows_setup.ps1"
                        Write-Info "4. Re-upload your documents"
                        Write-Info ""
                    } else {
                        Write-Error "Project deletion failed - see error above"
                    }
                } else {
                    Write-Warning "Invalid selection"
                }
            } catch {
                Write-Warning "Invalid input"
            }
        }

        "3" {
            # View requirements
            Write-Info ""
            Write-Info "=== Project Deletion Requirements ==="
            Write-Info ""
            Write-Info "Before you can delete a Pinecone project, you must:"
            Write-Info ""
            Write-Info "1. Delete ALL assistants in the project"
            Write-Info "   - Use manage_assistant.ps1 or Pinecone Console"
            Write-Info "   - Each assistant must be deleted individually"
            Write-Info ""
            Write-Info "2. Delete ALL vector databases (indexes) in the project (if any)"
            Write-Info "   - ⚠️  This will delete ALL data in your vector databases!"
            Write-Info "   - Manage in Pinecone Console: Indexes → Delete"
            Write-Info "   - Make sure you have backups if you need the data"
            Write-Info ""
            Write-Info "3. Delete ALL backups and collections (if any)"
            Write-Info "   - Manage in Pinecone Console"
            Write-Info ""
            Write-Warning "⚠️  CRITICAL: If you have production vector databases in this"
            Write-Warning "   project, DO NOT delete the project! Create a new project"
            Write-Warning "   instead and migrate your assistant to the new project."
            Write-Info ""
            Write-Info "Why delete and recreate a project?"
            Write-Info ""
            Write-Info "Starter Plan token limits are LIFETIME per project:"
            Write-Info "  - Input tokens: 1.5M (for AI chat)"
            Write-Info "  - Output tokens: 200K (AI responses)"
            Write-Info "  - Context tokens: 500K (document retrieval)"
            Write-Info ""
            Write-Info "These do NOT reset monthly. Deleting and recreating the"
            Write-Info "project gives you fresh token limits for extended testing."
            Write-Info ""
            Write-Info "⚠️  IMPORTANT:"
            Write-Info "  - Starter Plan: Only 1 project allowed at a time"
            Write-Info "  - Must delete old project before creating new one"
            Write-Info "  - All documents must be re-uploaded (20-35 min for USPTO)"
            Write-Info "  - For production use, upgrade to paid plan instead"
            Write-Info ""
            Write-Info "Reference:"
            Write-Info "https://docs.pinecone.io/guides/assistant/pricing-and-limits"
            Write-Info ""
        }

        "4" {
            # Exit
            Write-Info ""
            Write-Success "Goodbye!"
            $continue = $false
        }

        default {
            Write-Warning "Invalid choice. Please enter 1-4."
        }
    }
}

Write-Info ""
Write-Log "Session log saved to: $LogFile" "INFO"
Write-Info ""
