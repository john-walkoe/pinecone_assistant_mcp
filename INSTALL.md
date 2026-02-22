# Installation Guide - Pinecone Assistant MCP

Complete installation guide for setting up the Pinecone Assistant MCP server with automated setup scripts.

## Prerequisites

- **Git installed** or the source files
- **uv Package Manager** - Handles Python installation automatically. If using Quick Start Windows install PowerShell script, uv will be installed automatically if not present.
- **Pinecone Assistant API Key** (required, see **[API Key Guide](PINECONE_KEY_GUIDE.md)**)
- **Claude Desktop** (Recommended for MCP client integration)

## ⚡Quick Start (Recommended)

### Windows Install

**Run PowerShell as Administrator**, then:

```powershell
# Navigate to your user profile
cd $env:USERPROFILE

# If git is installed:
git clone https://github.com/john-walkoe/pinecone_assistant_mcp.git
cd pinecone_assistant_mcp

# If git is NOT installed:
# Download and extract the repository to C:\Users\YOUR_USERNAME\pinecone_assistant_mcp
# Then navigate to the folder:
# cd C:\Users\YOUR_USERNAME\pinecone_assistant_mcp

# The script detects if uv is installed and if it is not it will install uv - https://docs.astral.sh/uv

# Run setup script (sets execution policy for this session only):
Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope Process
.\deploy\windows_setup.ps1

# Close Powershell Window.
# If choose option to "configure Claude Desktop integration" during the script then restart Claude Desktop
```

The PowerShell script will:
- ✅ Auto-install uv package manager (if not already installed)
- ✅ Install dependencies with Python 3.12
- ✅ Prompt for Pinecone Assistant API key
- ✅ Guide you through assistant creation or connection
- ✅ Upload documents with metadata (USPTO or custom)
- ✅ Configure USPTO system prompt (if using default documents)
- ✅ Set up Claude Desktop integration automatically
- ✅ Create timestamped backups before modifying configs

**Example Output:**
```
PS C:\Users\YOUR_USERNAME\pinecone_assistant_mcp> .\deploy\windows_setup.ps1
[OK] Validation helpers loaded
=== Pinecone Assistant MCP - Windows Setup ===

Starting Pinecone Assistant MCP setup
Step 1-2: Checking installation prerequisites...

Python detected: Python 3.13.7 (Note: uv will manage Python automatically)

Step 3-5: UV package manager setup...

UV not found. Installing UV...
Found uv [astral-sh.uv] Version 0.10.4
This application is licensed to you by its owner.
Microsoft is not responsible for, nor does it grant any licenses to, third-party packages.
This package requires the following dependencies:
  - Packages
      Microsoft.VCRedist.2015+.x64
Downloading https://github.com/astral-sh/uv/releases/download/0.10.4/uv-x86_64-pc-windows-msvc.zip
  ██████████████████████████████  21.0 MB / 21.0 MB
Successfully verified installer hash
Extracting archive...
Successfully extracted archive
Starting package install...
Command line alias added: "uvx"
Command line alias added: "uv"
Command line alias added: "uvw"
Path environment variable modified; restart your shell to use the new value.
Successfully installed
UV installed via winget
UV is now accessible: uv 0.10.4 (079e3fd05 2026-02-17)

Installing project dependencies with UV...
Installing dependencies with prebuilt wheels (Python 3.12)...
Resolved 53 packages in 2ms
Audited 53 packages in 8ms
Project dependencies installed successfully

Step 6: Pinecone API Key Configuration

Get your API key from: https://app.pinecone.io/
(API key is stored only in Claude Desktop config - not in system environment variables)

Enter your Pinecone Assistant API key (input hidden - get from https://app.pinecone.io/): *************************************************************************** [pcsk_YOUR_PINECONE_KEY]
[OK] Pinecone API key format validated (75 chars, pcsk_...)
Pinecone API key format validated

Storing API key securely...
API key stored in Windows Credential Manager
  Target: pinecone_API_KEY
  Note: Accessible only by your Windows user account
Could not store in DPAPI (Credential Manager storage succeeded)
API key stored using Windows DPAPI encryption

Select default AI model for the assistant:
  [1] gpt-4o (OpenAI GPT-4 Optimized - recommended)
  [2] gpt-4.1 (OpenAI GPT-4.1)
  [3] o4-mini (OpenAI O4 Mini)
  [4] claude-3-5-sonnet (Anthropic Claude 3.5 Sonnet - auto-routed to 4.5)
  [5] claude-3-7-sonnet (Anthropic Claude 3.7 Sonnet - auto-routed to 4.5)
  [6] gemini-2-5-pro (Google Gemini 2.5 Pro)
  [7] claude-sonnet-4-5 (Anthropic Claude Sonnet 4.5)

Enter choice (1-7, default is 1): 1
Selected model: gpt-4o

Step 7-9: Assistant Configuration

Do you need to create a new Pinecone Assistant, or do you already have one?
  [1] Create a new assistant (via API)
  [2] I already have an assistant
  [3] Skip assistant setup (configure MCP only)

Enter choice (1, 2, or 3): 1

Creating new Pinecone Assistant...
Assistant name requirements:
  - Lowercase letters, numbers, hyphens only
  - Must start with a letter
  - No spaces or special characters
  - Example: my-assistant, uspto-docs, patent-search

Enter a name for your new assistant: my-assistant
Assistant created successfully!
Assistant name: my-assistant
Assistant host: https://prod-1-data.ke.pinecone.io/assistant
Status: Ready

Step 10-11: Document Upload Configuration

Found combined_documents.zip file - will extract documents for upload
Upload documents to assistant 'my-assistant'? (Y/n): y

Are you uploading the DEFAULT USPTO MPEP documents included in this repository,
or have you replaced them with your own custom documents?
  [1] Default USPTO MPEP documents (included in repo)
  [2] Custom documents (I replaced the default ones)

Enter choice (1 or 2): 1
Using USPTO-specific metadata for document upload
Setting default temperature to 0.2 for legal analysis precision

Note: Since you're using USPTO MPEP documents, we'll also configure
      the assistant with a specialized system prompt for patent law analysis.
      This optimizes responses for IRAC methodology and USPTO guidance.

Starting document upload via Python script...
Executing upload script from: C:\Users\YOUR_USERNAME\pinecone_assistant_mcp\deploy
Assistant: my-assistant
Command: $ApiKey | uv run python upload_files.py --assistant-name my-assistant --use-uspto-metadata
Pinecone Assistant File Upload
========================================
✓ Connected to assistant: my-assistant
Found combined_documents.zip, extracting...
✓ Successfully extracted documents from zip file
Using USPTO-specific metadata
Found 8 files to upload

Validating files before upload...
============================================================
Total files: 8
Total size: 33.21 MB
File types: .md

✓ All files validated successfully

Starting upload of 8 files...
============================================================

⏱️  UPLOAD TIME ESTIMATE:
   First file:  5-10 minutes (depends on file size and network)
   Other files: 2-5 minutes each
   Total estimate: 26-45 minutes

💡 TIP: To track real-time upload progress, check the Pinecone Console:
   https://app.pinecone.io/ → Your Assistant → Files tab
   You'll see a progress bar for each file there!
============================================================

[1/8] (12%) ✓ Successfully uploaded Combined_Training_Materials.md (5.4MB)
  ⏱ Waiting 1 second (rate limiting)...

[2/8] (25%) ✓ Successfully uploaded Combined_MPEP_Updates.md (2.1MB)
  ⏱ Waiting 1 second (rate limiting)...

[3/8] (38%) ✓ Successfully uploaded Combined_MPEP_9th_Edition_Part1.md (7.1MB)
  ⏱ Waiting 1 second (rate limiting)...

[4/8] (50%) ✓ Successfully uploaded Combined_MPEP_9th_Edition_Part2.md (6.5MB)
  ⏱ Waiting 1 second (rate limiting)...

[5/8] (62%) ✓ Successfully uploaded Combined_MPEP_9th_Edition_Part3.md (4.9MB)
  ⏱ Waiting 1 second (rate limiting)...

[6/8] (75%) ✓ Successfully uploaded Combined_MPEP_9th_Edition_Part4.md (4.0MB)
  ⏱ Waiting 1 second (rate limiting)...

[7/8] (88%) ✓ Successfully uploaded mpep-9015-appx-l-July-2025.md (0.6MB)
  ⏱ Waiting 1 second (rate limiting)...

[8/8] (100%) ✓ Successfully uploaded mpep-9020-appx-r-July-2025.md (2.7MB)

============================================================

Upload Summary: 8 successful, 0 failed

Successful uploads:
  ✓ Combined_Training_Materials.md - 5.39MB (ID: b8c320c6-15cd-424d-a3bb-8ab193d66767)
  ✓ Combined_MPEP_Updates.md - 2.06MB (ID: 173bf102-de15-4773-9526-fcf27bc5af0b)
  ✓ Combined_MPEP_9th_Edition_Part1.md - 7.15MB (ID: 92ceaf86-b8cd-41ec-9d37-045376e43d8a)
  ✓ Combined_MPEP_9th_Edition_Part2.md - 6.45MB (ID: 7f280b37-78da-4886-986c-1554dd2d0be9)
  ✓ Combined_MPEP_9th_Edition_Part3.md - 4.9MB (ID: 7ee90069-6e89-4751-9451-78511d3dcc52)
  ✓ Combined_MPEP_9th_Edition_Part4.md - 3.98MB (ID: 903f0eaa-7f86-4ee5-98c9-c4633ded916b)
  ✓ mpep-9015-appx-l-July-2025.md - 0.61MB (ID: c3e2cb9d-87a6-4b47-a99e-490d59c8f46a)
  ✓ mpep-9020-appx-r-July-2025.md - 2.66MB (ID: 3d6d4a01-4079-42ef-8258-7b9b0c4f639f)

============================================================
UPLOAD VERIFICATION - Checking what made it to the assistant...
============================================================

✓ Assistant currently has 8 total files

Upload Results:
  Files attempted: 8
  Upload succeeded: 8
  Upload failed: 0

============================================================
DETAILED FILE-BY-FILE VERIFICATION:
============================================================

[1/8] ✅ Combined_Training_Materials.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Created: 2026-02-22T04:56:53.584805812Z

[2/8] ✅ Combined_MPEP_Updates.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Created: 2026-02-22T05:01:07.657971070Z

[3/8] ✅ Combined_MPEP_9th_Edition_Part1.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Created: 2026-02-22T05:02:25.598192954Z

[4/8] ✅ Combined_MPEP_9th_Edition_Part2.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Created: 2026-02-22T05:07:07.885352762Z

[5/8] ✅ Combined_MPEP_9th_Edition_Part3.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Created: 2026-02-22T05:11:45.234501812Z

[6/8] ✅ Combined_MPEP_9th_Edition_Part4.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Created: 2026-02-22T05:14:45.435854179Z

[7/8] ✅ mpep-9015-appx-l-July-2025.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Created: 2026-02-22T05:17:32.105469327Z

[8/8] ✅ mpep-9020-appx-r-July-2025.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Created: 2026-02-22T05:18:09.488008263Z

============================================================
FINAL VERIFICATION SUMMARY:
============================================================

What you tried to upload:  8 files
What made it to assistant: 8 files

Breakdown:
  ✅ Ready & Available:     8 files
  ⏳ Still Processing:      0 files
  ❌ Failed Processing:     0 files
  ⚠️  Missing/Not Found:     0 files

🎉 SUCCESS! All 8 files uploaded and ready to use!

============================================================
CONFIGURING USPTO SYSTEM PROMPT...
============================================================
Loaded system prompt from: assistant_system_prompt.txt
✓ USPTO system prompt configured successfully!
  Assistant will now use IRAC methodology for patent law analysis.

Cleaning up extracted files from zip...
(Note: Loose files in combined_documents/ folder are preserved)
  Deleted (extracted): Combined_Training_Materials.md
  Deleted (extracted): Combined_MPEP_Updates.md
  Deleted (extracted): Combined_MPEP_9th_Edition_Part1.md
  Deleted (extracted): Combined_MPEP_9th_Edition_Part2.md
  Deleted (extracted): Combined_MPEP_9th_Edition_Part3.md
  Deleted (extracted): Combined_MPEP_9th_Edition_Part4.md
  Deleted (extracted): mpep-9015-appx-l-July-2025.md
  Deleted (extracted): mpep-9020-appx-r-July-2025.md
✓ Cleanup completed - deleted 8 extracted file(s)

✓ Upload process completed successfully!

Next steps:
1. Wait a few minutes for document processing to complete
2. Test the assistant with a sample query
3. Configure the MCP server environment variables
Upload script exit code: 0
Document upload completed successfully

Configuring USPTO patent law analysis system prompt...
Loaded system prompt from: assistant_system_prompt.txt
USPTO system prompt configured successfully
Assistant will now use IRAC methodology for patent law analysis

Step 12: MCP Environment Setup

Verifying MCP environment is ready...
Note: API key will NOT be stored in system environment variables
      API key will only be stored in Claude Desktop config file
MCP environment setup complete

Step 13-14: Claude Desktop Configuration

Would you like to configure Claude Desktop integration? (Y/n): y

Claude Desktop Configuration Method:
  [1] Secure Python DPAPI (recommended) - Automatic secure storage
      - API key encrypted with Windows DPAPI (Python-based)
      - API key not stored in Claude Desktop config file
      - Direct Python execution with built-in secure storage
      - No PowerShell execution policy requirements
      - Cross-platform fallback to environment variables

  [2] Traditional - API key stored in Claude Desktop config file
      - API key visible in claude_desktop_config.json
      - Direct Python execution
      - Simpler setup, less secure
      - Works on all platforms

Enter choice (1 or 2, default is 1): 1
Using secure Python DPAPI method (encrypted API key storage)
Claude Desktop config location: C:\Users\YOUR_USERNAME\AppData\Roaming\Claude\claude_desktop_config.json
Existing Claude Desktop config found
Merging Pinecone Assistant configuration with existing config...
Backup created: C:\Users\YOUR_USERNAME\AppData\Roaming\Claude\claude_desktop_config.json.backup_20260221_232028
Successfully merged Pinecone Assistant configuration!
Your existing MCP servers have been preserved
All other top-level config settings (preferences, etc.) preserved

Claude Desktop configuration complete!


Windows setup complete!

Please restart Claude Desktop to load the MCP server

Configuration Summary:
  Configuration Method: Secure (encrypted API key storage)
  API Key: Encrypted with Windows DPAPI
  Assistant Name: my-assistant
  Assistant Host: https://prod-1-data.ke.pinecone.io/assistant
  Installation Directory: C:/Users/YOUR_USERNAME/pinecone_assistant_mcp

Available MCP Tools:
  - assistant_chat: Direct conversation with your assistant
  - assistant_strategic_multi_search: Multi-pattern strategic research
  - assistant_context: Raw document retrieval without AI processing
  - assistant_strategic_multi_search_context: Strategic search with raw documents

Troubleshooting:
  If Claude Desktop fails to connect to MCP server, check execution policy:
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

Test with: Ask Claude questions about your document corpus

Setup log saved to: C:\Users\YOUR_USERNAME\pinecone_assistant_mcp\deploy\setup.log
```

## 🔒 Secure Configuration Options

During the Windows setup, you'll be presented with two configuration methods:

### Method 1: Windows Secure Python DPAPI (Recommended)

- 🔒 **API key encrypted with Windows DPAPI** — stored in `~/.pinecone_api_key` (self-contained: entropy embedded in bytes 0–31)
- 🔒 **API key not stored in Claude Desktop config file**
- 🔒 **No `INTERNAL_AUTH_SECRET` needed in config** — unlike USPTO MCPs, decryption is self-contained from the key file
- ⚡ **Direct Python execution with built-in secure storage**

**Example Configuration Generated:**

```json
{
  "mcpServers": {
    "pinecone_assistant": {
      "command": "C:/Users/YOUR_USERNAME/pinecone_assistant_mcp/.venv/Scripts/python.exe",
      "args": [
        "-m",
        "src.server"
      ],
      "cwd": "C:/Users/YOUR_USERNAME/pinecone_assistant_mcp",
      "env": {
        "PINECONE_ASSISTANT_HOST": "https://prod-1-data.ke.pinecone.io/assistant",
        "PINECONE_ASSISTANT_NAME": "my-assistant",
        "PINECONE_ASSISTANT_MODEL": "gpt-4o",
        "PINECONE_ASSISTANT_TEMPERATURE": "0.2"
      }
    }
  }
}
```

> **Note:** No `PINECONE_API_KEY` or `INTERNAL_AUTH_SECRET` in the env block — the API key is loaded automatically from the encrypted `~/.pinecone_api_key` file at server startup.

### Method 2: Windows Traditional

- 📄 **API key stored in Claude Desktop config file**
- 🔓 **Less secure - key visible in config**
- ⚡ **Direct Python execution**
- ✅ **Simpler setup**

**Example Configuration Generated:**

```json
{
  "mcpServers": {
    "pinecone_assistant": {
      "command": "C:/Users/YOUR_USERNAME/pinecone_assistant_mcp/.venv/Scripts/python.exe",
      "args": ["-m", "src.server"],
      "cwd": "C:/Users/YOUR_USERNAME/pinecone_assistant_mcp",
      "env": {
        "PINECONE_API_KEY": "pcsk_YOUR_PINECONE_KEY",
        "PINECONE_ASSISTANT_HOST": "https://prod-1-data.ke.pinecone.io/assistant",
        "PINECONE_ASSISTANT_NAME": "my-assistant",
        "PINECONE_ASSISTANT_MODEL": "gpt-4o",
        "DEFAULT_TEMPERATURE": "0.2"
      }
    }
  }
}
```

**To get your exact Python path Windows:**

```powershell
# Navigate to your MCP directory
cd C:/Users/YOUR_USERNAME/pinecone_assistant_mcp

# Get the exact Python executable path
uv run python -c "import sys; print(sys.executable)"
```



## :penguin: Linux Install

```bash
git clone https://github.com/john-walkoe/pinecone_assistant_mcp.git
cd pinecone_assistant_mcp

# Make setup script executable (if needed)
chmod +x deploy/linux_setup.sh

# Run automated setup script
./deploy/linux_setup.sh
```

The Linux script will:
- ✅ Check for and auto-install uv package manager (via official installer)
- ✅ Install dependencies and create virtual environment
- ✅ Prompt for Pinecone Assistant API key (required)
- ✅ Guide you through assistant creation or connection (with API validation)
- ✅ Upload documents with metadata (USPTO or custom)
- ✅ Configure USPTO system prompt (if using default documents)  
- ✅ Ask if you want Claude Desktop integration configured
- ✅ Automatically merge with existing Claude Desktop config (preserves other MCP servers)
- ✅ Create timestamped backups before modifying existing configs
- ✅ Provide installation summary and testing instructions

**Example Output:**
```
USER@debian:~/pinecone_assistant_mcp# ./deploy/linux_setup.sh
=== Pinecone Assistant MCP - Linux Setup ===

[INFO] Starting Linux setup for Pinecone Assistant MCP
[INFO] Python found: Python 3.12.10
[INFO] uv found: uv 0.7.10
[INFO] Installing project dependencies with uv...
Using CPython 3.13.3
Creating virtual environment at: .venv
Resolved 53 packages in 0.82ms
░░░░░░░░░░░░░░░░░░░░ [0/51] Installing wheels...
warning: Failed to hardlink files; falling back to full copy. This may lead to degraded performance.
If the cache and target directories are on different filesystems, hardlinking may not be supported.
If this is intentional, set `export UV_LINK_MODE=copy` or use `--link-mode=copy` to suppress this warning.[*]
Installed 51 packages in 8.84s
 + annotated-types==0.7.0
 + anyio==4.11.0
...
 + urllib3==2.5.0
 + uvicorn==0.37.0
 + virtualenv==20.35.3
[OK] Dependencies installed successfully
[INFO] Installing Pinecone Assistant MCP package...
Resolved 37 packages in 22ms
Built pinecone-assistant-mcp @ file:///USER/pinecone_assistant_mcp
Prepared 1 package in 205ms
Uninstalled 1 package in 31ms
░░░░░░░░░░░░░░░░░░░░ [0/1] Installing wheels...
warning: Failed to hardlink files; falling back to full copy. This may lead to degraded performance.
If the cache and target directories are on different filesystems, hardlinking may not be supported.
If this is intentional, set `export UV_LINK_MODE=copy` or use `--link-mode=copy` to suppress this warning.[*]
Installed 1 package in 118ms
 ~ pinecone-assistant-mcp==1.0.0 (from file:///USER/pinecone_assistant_mcp)
[OK] Package installed successfully
[INFO] Verifying installation...
[OK] Package import successful - can run with: uv run python src/server.py

[INFO] API Key Configuration

[INFO] Get your API key from: https://app.pinecone.io/

Enter your Pinecone API key (starts with pcsk_): [your_actual_pinecone_api_key_here[**]]
[OK] Pinecone API key format validated
[OK] API key format validated
[INFO] Storing API key in secure storage...
[OK] API key stored in ~/.pinecone_api_key (permissions: 600)

[INFO] Assistant Configuration

Do you need to create a new Pinecone Assistant, or do you already have one?
  [1] Create a new assistant (via API)
  [2] I already have an assistant
  [3] Skip assistant setup (configure MCP only)

Enter choice (1, 2, or 3): 1
Enter a name for your new assistant (e.g., my-assistant): my-assistant
[INFO] Creating assistant: my-assistant
[OK] Assistant created successfully!
[INFO] Assistant name: my-assistant
[INFO] Assistant host: https://prod-1-data.ke.pinecone.io/assistant

[INFO] Document Upload Configuration

[INFO] Found combined_documents directory
Upload documents to assistant 'my-assistant'? (Y/n): y

Are you uploading the DEFAULT USPTO MPEP documents included in this repository,
or have you replaced them with your own custom documents?
  [1] Default USPTO MPEP documents (included in repo)
  [2] Custom documents (I replaced the default ones)

Enter choice (1 or 2): 1

[INFO] Since you're using USPTO MPEP documents, we'll also configure
[INFO] the assistant with a specialized system prompt for patent law analysis.

[INFO] Starting document upload...
WARNING: API key passed via command-line is visible in process listings. Consider using stdin instead.
Pinecone Assistant File Upload
========================================
✓ Connected to assistant: my-assistant
Found combined_documents.zip, extracting...
✓ Successfully extracted documents from zip file
Using USPTO-specific metadata
Found 8 files to upload

Validating files before upload...
============================================================
Total files: 8
Total size: 33.21 MB
File types: .md

✓ All files validated successfully

Starting upload of 8 files...
============================================================

⏱️  UPLOAD TIME ESTIMATE:
   First file:  5-10 minutes (depends on file size and network)
   Other files: 2-5 minutes each
   Total estimate: 26-45 minutes

💡 TIP: To track real-time upload progress, check the Pinecone Console:
   https://app.pinecone.io/ → Your Assistant → Files tab
   You'll see a progress bar for each file there!
============================================================

[1/8] (12%) ✓ Successfully uploaded Combined_Training_Materials.md (5.4MB)
  ⏱ Waiting 1 second (rate limiting)...

[2/8] (25%) ✓ Successfully uploaded Combined_MPEP_Updates.md (2.1MB)
  ⏱ Waiting 1 second (rate limiting)...

[3/8] (38%) ✓ Successfully uploaded Combined_MPEP_9th_Edition_Part1.md (7.1MB)
  ⏱ Waiting 1 second (rate limiting)...

[4/8] (50%) ✓ Successfully uploaded Combined_MPEP_9th_Edition_Part2.md (6.5MB)
  ⏱ Waiting 1 second (rate limiting)...

[5/8] (62%) ✓ Successfully uploaded Combined_MPEP_9th_Edition_Part3.md (4.9MB)
  ⏱ Waiting 1 second (rate limiting)...

[6/8] (75%) ✓ Successfully uploaded Combined_MPEP_9th_Edition_Part4.md (4.0MB)
  ⏱ Waiting 1 second (rate limiting)...

[7/8] (88%) ✓ Successfully uploaded mpep-9015-appx-l-July-2025.md (0.6MB)
  ⏱ Waiting 1 second (rate limiting)...

[8/8] (100%) ✓ Successfully uploaded mpep-9020-appx-r-July-2025.md (2.7MB)

============================================================

Upload Summary: 8 successful, 0 failed

Successful uploads:
  ✓ Combined_Training_Materials.md - 5.39MB (ID: 9911e652-6c78-4364-8e25-52012ebe11e1)
  ✓ Combined_MPEP_Updates.md - 2.06MB (ID: 8fe862ec-0101-4040-9ba6-a1ec1994d306)
  ✓ Combined_MPEP_9th_Edition_Part1.md - 7.15MB (ID: 930d3d3f-4cbc-4e51-a8de-a50f32ab8771)
  ✓ Combined_MPEP_9th_Edition_Part2.md - 6.45MB (ID: 24f6f318-19a3-4baf-8581-fa5f7d15af7d)
  ✓ Combined_MPEP_9th_Edition_Part3.md - 4.9MB (ID: ec0fcf7f-be9a-4a55-90c3-2932d1f68694)
  ✓ Combined_MPEP_9th_Edition_Part4.md - 3.98MB (ID: 385193af-eef5-4502-9306-b9f365625b8c)
  ✓ mpep-9015-appx-l-July-2025.md - 0.61MB (ID: e682d681-ad25-48c6-9c34-e443f49dc418)
  ✓ mpep-9020-appx-r-July-2025.md - 2.66MB (ID: 5f13005c-d83d-4c74-9296-676206ea3a62)

============================================================
UPLOAD VERIFICATION - Checking what made it to the assistant...
============================================================

✓ Assistant currently has 8 total files

Upload Results:
  Files attempted: 8
  Upload succeeded: 8
  Upload failed: 0

============================================================
DETAILED FILE-BY-FILE VERIFICATION:
============================================================

[1/8] ✅ Combined_Training_Materials.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Created: 2026-02-22T02:25:06.124302460Z

[2/8] ✅ Combined_MPEP_Updates.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Created: 2026-02-22T02:29:17.076633256Z

[3/8] ✅ Combined_MPEP_9th_Edition_Part1.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Created: 2026-02-22T02:30:35.346740626Z

[4/8] ✅ Combined_MPEP_9th_Edition_Part2.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Created: 2026-02-22T02:35:06.728465195Z

[5/8] ✅ Combined_MPEP_9th_Edition_Part3.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Created: 2026-02-22T02:39:48.233388002Z

[6/8] ✅ Combined_MPEP_9th_Edition_Part4.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Created: 2026-02-22T02:43:08.998074397Z

[7/8] ✅ mpep-9015-appx-l-July-2025.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Created: 2026-02-22T02:46:23.722527821Z

[8/8] ✅ mpep-9020-appx-r-July-2025.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Created: 2026-02-22T02:46:45.668778069Z

============================================================
FINAL VERIFICATION SUMMARY:
============================================================

What you tried to upload:  8 files
What made it to assistant: 8 files

Breakdown:
  ✅ Ready & Available:     8 files
  ⏳ Still Processing:      0 files
  ❌ Failed Processing:     0 files
  ⚠️  Missing/Not Found:     0 files

🎉 SUCCESS! All 8 files uploaded and ready to use!

============================================================
CONFIGURING USPTO SYSTEM PROMPT...
============================================================
Loaded system prompt from: assistant_system_prompt.txt
✓ USPTO system prompt configured successfully!
  Assistant will now use IRAC methodology for patent law analysis.

Cleaning up extracted files from zip...
(Note: Loose files in combined_documents/ folder are preserved)
  Deleted (extracted): Combined_Training_Materials.md
  Deleted (extracted): Combined_MPEP_Updates.md
  Deleted (extracted): Combined_MPEP_9th_Edition_Part1.md
  Deleted (extracted): Combined_MPEP_9th_Edition_Part2.md
  Deleted (extracted): Combined_MPEP_9th_Edition_Part3.md
  Deleted (extracted): Combined_MPEP_9th_Edition_Part4.md
  Deleted (extracted): mpep-9015-appx-l-July-2025.md
  Deleted (extracted): mpep-9020-appx-r-July-2025.md
✓ Cleanup completed - deleted 8 extracted file(s)

✓ Upload process completed successfully!

Next steps:
1. Wait a few minutes for document processing to complete
2. Test the assistant with a sample query
3. Configure the MCP server environment variables
[OK] Document upload completed successfully
[OK] USPTO system prompt configured successfully
[INFO] Assistant will now use IRAC methodology for patent law analysis

[INFO] Claude Code Configuration

Would you like to configure Claude Code integration? (Y/n): y
[INFO] Detected existing Claude Code config: /USER/.claude.json
[INFO] Existing Claude Code config found
[INFO] Merging Pinecone Assistant configuration with existing config...
[INFO] Backup created: /USER/.claude.json.backup_20260221_211905
SUCCESS
[OK] Successfully merged Pinecone Assistant configuration!
[OK] Your existing MCP servers have been preserved
[OK] Set permissions 600 on: /USER/.claude.json
[OK] Claude Code configuration complete!

[OK] Linux setup complete!
[WARN] Please restart Claude Code to load the MCP server (claude mcp list to verify)

[INFO] Configuration Summary:
[OK] API Key: Stored in secure storage (~/.pinecone_api_key, permissions: 600)
[OK] Security: API key NOT written to Claude Desktop config file
[OK] Assistant Name: my-assistant
[OK] Assistant Host: https://prod-1-data.ke.pinecone.io
[OK] Installation Directory: /USER/pinecone_assistant_mcp

[INFO] Available MCP Tools:
  - assistant_context (raw document retrieval - START HERE)
  - assistant_strategic_multi_search_context (strategic raw documents)
  - assistant_strategic_multi_search (AI-powered strategic search)
  - assistant_chat (direct AI conversation)
  - update_configuration (switch assistants mid-conversation)

[INFO] Test the server:
  uv run python src/server.py

[INFO] Test with Claude Code:
  Ask Claude: 'Use assistant_context to search for [your topic]'

[INFO] Verify MCP is running:
  claude mcp list

[INFO] Setup log saved to: /USER/pinecone_assistant_mcp/deploy/setup.log
[OK] Setup completed successfully
```

*The warnings are just uv being verbose about filesystem optimization.  This is similar to seeing compiler warnings that don't affect the final program - informational but not problematic.

** When typing in the API keys no output is displayed as a security feature.

**Test Claude Code's MCP**

```
USER@debian:~/pinecone_assistant_mcp# claude mcp list
Checking MCP server health...

pinecone_assistant: uv --directory /USER/pinecone_assistant_mcp run python src/server.py - ✓ Connected
```

**Example Quick Start Linux Configuration Generated:**

```json
{
  "mcpServers": {
    "pinecone_assistant": {
      "command": "uv",
      "args": [
        "--directory",
        "/USER/pinecone_assistant_mcp",
        "run",
        "python",
        "src/server.py"
      ],
      "env": {
        "PINECONE_ASSISTANT_HOST": "https://prod-1-data.ke.pinecone.io",
        "PINECONE_ASSISTANT_NAME": "my-assistant",
        "PINECONE_ASSISTANT_MODEL": "gpt-4o"
      }
     }
    }
  }
```

## 🔀 n8n Integration (Linux)

For workflow automation with **locally hosted n8n instances**, you can integrate the Pinecone Assistant MCP as a node using nerding-io's community MCP client connector.

**Requirements:**

- ✅ **Self-hosted n8n instance** (local or server deployment)
- ✅ **n8n version 1.0.0+** (required for community nodes)
- ✅ **nerding-io's Community MPC Client node**: [n8n-nodes-mcp](https://github.com/nerding-io/n8n-nodes-mcp)
- ❌ **Cannot be used with n8n Cloud** (requires local filesystem access to MCP executables)

**For AI Agent Integration:**

- Must set `N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true` environment variable

### Setup Steps

1. **Install n8n** (if not already installed):

   ```bash
   npm install -g n8n
   
   # Or using Docker with required environment variable
   docker run -it --rm --name n8n -p 5678:5678 \
     -e N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true \
     n8nio/n8n
   ```

2. **Install nerding-io's Community MPC Client  Node:**

   Follow the [n8n community nodes installation guide](https://docs.n8n.io/integrations/community-nodes/installation/):

   ```bash
   # Method 1: Via n8n UI
   # Go to Settings > Community Nodes > Install
   # Enter: n8n-nodes-mcp
   
   # Method 2: Via npm (for self-hosted)
   npm install n8n-nodes-mcp
   
   # Method 3: Via Docker environment
   # Add to docker-compose.yml:
   # environment:
   #   - N8N_NODES_INCLUDE=[n8n-nodes-mcp]
   ```

3. **Configure Credentials:**

   n8n MCP Configuration Example

   **Environment Variables Configuration (Installed using Linux Quick Start Script):**

   ![n8n Pinecone Assistant Environment Variables](documentation_photos\n8n_pinecone_assistant_1.jpg)

   **Complete Configuration with API Keys (When installed using traditional PIP Install):**

   ![n8n Pinecone Assistant Environment Variables Traditional](documentation_photos\n8n_pinecone_assistant_2.jpg)

   - **Connection Type**: `Command-line Based Transport (STDIO)`

   - **Command**: `/home/YOUR_USERNAME/pinecone_assistant_mcp/.venv/bin/pinecone-assistant-mcp` (see below step 4 on how to get)

   - **Arguments**: (leave empty)

   - **Environment Variables** (Entered in as Expression):

     ```
     PINECONE_API_KEY=pcsk_YOUR_PINECONE_KEY
     PINECONE_ASSISTANT_HOST=https://prod-1-data.ke.pinecone.io
     PINECONE_ASSISTANT_NAME=my-assistant
     PINECONE_ASSISTANT_MODEL=gpt-4o
     ```

4. **Find MCP Executable Path:**
   Navigate to your Pinecone Assistant directory and run:

   ```bash
   cd /path/to/pinecone_assistant_mcp
   uv run python -c "import sys; print(sys.executable)"
   ```

   This will return something like:

   ```
   /home/YOUR_USERNAME/pinecone_assistant_mcp/.venv/bin/python3
   ```

   Take the directory path and append `pinecone-assistant-mcp` to get your command:

   ```
   /home/YOUR_USERNAME/pinecone_assistant_mcp/.venv/bin/pinecone-assistant-mcp
   ```

   Use this full path as your command in the n8n MCP configuration.

5. **Add MCP Client Node:**

   - In n8n workflow editor, add "MCP Client (STDIO) API" node
   - Select your configured credentials
   - Choose operation (List Tools, Execute Tool, etc.)

6. **Test Connection:**

   ![n8n Execute Tool Operation](documentation_photos\n8n_pinecone_assistant_3.jpg)

   - Use "List Tools" operation to see available Pinecone Assistant functions
   - Use "Execute Tool" operation with `get_configuration_status`
   - Parameters example: `{}`

### Example n8n Workflow Use Cases

- **Automated Pinecone Assistant research:** Schedule searches against the Pinecone Assistant documents
- **MPEP Research Workflows:** Use the included document Corpus for automated patent research

The n8n integration enables powerful automation workflows combining Pinecone Assistant research with other business systems.

## Configuration

### Environment Variables

Required (one of):

- `PINECONE_API_KEY`: Your Pinecone API key — **canonical name, preferred**
- `PINECONE_ASSISTANT_API_KEY`: Legacy fallback (still accepted; prefer `PINECONE_API_KEY`)
- `PINECONE_ASSISTANT_HOST`: Pinecone Assistant API host URL
- `PINECONE_ASSISTANT_NAME`: Name of your Assistant instance

> **Windows DPAPI:** If the key is stored in `~/.pinecone_api_key` (via setup script), neither `PINECONE_API_KEY` nor `PINECONE_ASSISTANT_API_KEY` is needed in the config — the server reads the encrypted file automatically.

Optional with defaults:

- `PINECONE_ASSISTANT_MODEL`: Default AI model (Default: "gpt-4o")
- `DEBUG_LOGGING`: Enable debug logging (Default: "false")
- `REQUEST_TIMEOUT`: HTTP request timeout in seconds (Default: "30")
- `MAX_RETRIES`: Maximum number of request retries (Default: "3")  
- `RETRY_DELAY`: Base delay between retries in seconds (Default: "1.0")
- `MAX_STRATEGIC_SEARCHES`: Maximum strategic searches per request (Default: "10")
- `DEFAULT_TEMPERATURE`: AI response temperature (Default: "0.2" for legal/analytical precision)

### Default Temperature Configuration - used for AI models in **`assistant_chat`** & **`assistant_strategic_multi_search_chat`**

**Default: 0.2 (Low Temperature for Legal/USPTO Precision)**

The MCP is configured with a low default temperature (0.2) optimized for patent law and legal analysis:

**Why Low Temperature for USPTO/Legal Work:**

- **Accurate Citations**: Prevents AI from inventing MPEP sections or case names
- **Consistent Analysis**: Same query yields consistent legal interpretations
- **Factual Precision**: Critical for exact statute/regulation references
- **Risk Mitigation**: Reduces hallucinations in legal advice
- **IRAC Reliability**: Structured analysis requires deterministic responses

**Temperature Guide:**

| Temperature   | Behavior               | Best For                          | USPTO Suitability                     |
| ------------- | ---------------------- | --------------------------------- | ------------------------------------- |
| **0.0 - 0.3** | Deterministic, precise | Legal citations, factual analysis | ✅ **Recommended**                     |
| **0.4 - 0.7** | Balanced               | General research                  | ⚠️ Acceptable for exploratory research |
| **0.8 - 2.0** | Creative, varied       | Brainstorming, creative writing   | ❌ Not recommended for legal work      |

### Strategic Search Patterns

Search patterns are defined in `strategic-searches.yaml` and automatically adapt to your content. **No code changes needed** to add/modify domains.

**Example USPTO domains** (included by default):

- **`core_examination_framework`**: Section 101/102/103 analysis, examination procedures
- **`prosecution_support`**: Office action responses, claim drafting, amendments
- **`post_grant_proceedings`**: IPR/PGR, PTAB standards, claim construction
- **`petition_practice`**: Revival petitions, supervisory review, Director petitions
- **`software_ai_technology`**: Software patents, AI/ML, business methods (TC 2100/2400)
- **`biotechnology_life_sciences`**: Pharmaceutical, biotech, medical devices (TC 1600)
- **`mechanical_engineering`**: Mechanical, electrical, manufacturing (TC 3600/3700)
- **`specification_requirements`**: Section 112, drawing requirements, formalities
- **`appeal_practice`**: PTAB appeals, brief preparation, oral hearings
- **`ai_patent_practice`**: AI tool ethics, confidentiality, verification duties
- **`ai_inventorship`**: AI inventorship requirements, eligibility, ownership

**Customize for your domain:** Simply edit `strategic-searches.yaml` to define your own search patterns and domains.



## 🧪 Claude Code Configuration

### Claude Code MCP Configuration

**Method 1: Using Claude Code CLI**

```powershell
# Windows - uv installation (recommended)
claude mcp add pinecone_assistant -s user `
  -e PINECONE_API_KEY=your_actual_api_key_here `
  -e PINECONE_ASSISTANT_HOST=https://prod-1-data.ke.pinecone.io `
  -e PINECONE_ASSISTANT_NAME=my-assistant `
  -e PINECONE_ASSISTANT_MODEL=gpt-4o `
  -e DEFAULT_TEMPERATURE=0.2 `
  -- uv --directory C:\Users\YOUR_USERNAME\pinecone_assistant_mcp run python src/server.py

# Linux - uv installation
claude mcp add pinecone_assistant -s user \
  -e PINECONE_API_KEY=your_actual_api_key_here \
  -e PINECONE_ASSISTANT_HOST=https://prod-1-data.ke.pinecone.io \
  -e PINECONE_ASSISTANT_NAME=my-assistant \
  -e PINECONE_ASSISTANT_MODEL=gpt-4o \
  -e DEFAULT_TEMPERATURE=0.2 \
  -- uv --directory /home/YOUR_USERNAME/pinecone_assistant_mcp run python src/server.py
```

## 📋 Manual Installation (Advanced)

### Prerequisites

- **uv Package Manager** - [Install Guide](https://docs.astral.sh/uv/getting-started/installation/)
- **Pinecone Assistant API Key** - [API Key Guide](PINECONE_KEY_GUIDE.md)
- **Claude Desktop** - [Download](https://claude.ai/download)

### Step 1: Clone Repository

```bash
git clone https://github.com/john-walkoe/pinecone_assistant_mcp.git
cd pinecone_assistant_mcp
```

### Step 2: Install Dependencies

```bash
# Install with uv (recommended)
uv sync --python 3.12

# Or install with pip
pip install -e .
```

### Step 3: Create Pinecone Assistant

**Via Web UI** (Free tier compatible)

1. Go to https://app.pinecone.io/
2. Navigate to Assistant section
3. Create new assistant
4. Note the assistant name and host URLStep 4: Upload Documents

```bash
cd deploy
uv run python upload_files.py \
  --api-key "pcsk_YOUR_PINECONE_KEY" \
  --assistant-name "my-assistant" \
  --use-uspto-metadata  # or omit for generic metadata
```

### Step 5: Configure Claude Desktop

**Windows Manual Configuration**

Edit `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "pinecone_assistant": {
      "command": "uv",
      "args": [
        "--directory",
        "C:/Users/YOUR_USERNAME/pinecone_assistant_mcp",
        "run",
        "python",
        "src/server.py"
      ],
      "env": {
        "PINECONE_API_KEY": "pcsk_YOUR_PINECONE_KEY",
        "PINECONE_ASSISTANT_HOST": "https://prod-1-data.ke.pinecone.io",
        "PINECONE_ASSISTANT_NAME": "my-assistant",
        "PINECONE_ASSISTANT_MODEL": "gpt-4o",
        "DEFAULT_TEMPERATURE": "0.2"
      }
    }
  }
}
```

> **Windows DPAPI alternative:** If you have run the setup script and stored the key securely, omit `PINECONE_API_KEY` — the server loads it automatically from `~/.pinecone_api_key`. No `INTERNAL_AUTH_SECRET` is needed.

**Linux Manual Configuration**

Edit `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "pinecone_assistant": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/YOUR_USERNAME/pinecone_assistant_mcp",
        "run",
        "python",
        "src/server.py"
      ],
      "env": {
        "PINECONE_API_KEY": "pcsk_YOUR_PINECONE_KEY",
        "PINECONE_ASSISTANT_HOST": "https://prod-1-data.ke.pinecone.io",
        "PINECONE_ASSISTANT_NAME": "my-assistant",
        "PINECONE_ASSISTANT_MODEL": "gpt-4o",
        "DEFAULT_TEMPERATURE": "0.2"
      }
    }
  }
}
```

### Step 6: Restart Claude Desktop

Close and restart Claude Desktop to load the MCP server.

---

## 🎯 Assistant Management Script Usage

### Using the Interactive Assistant Management Tool

For ongoing assistant management without full setup, use the PowerShell management script:

```powershell
# Navigate to the project directory
cd C:\Users\YOUR_USERNAME\pinecone_assistant_mcp

# Run the assistant management tool
.\deploy\manage_assistant.ps1
```

**Features:**
- 🔍 List all your existing assistants
- 📊 View assistant details and configuration
- 📁 Upload documents to any assistant
- ⚙️  Configure system prompts for specialized domains
- 🔄 Switch between different assistants for Claude Desktop
- 🔐 Secure API key storage

**Example Session:**
```
=== Pinecone Assistant Management Tool ===

What would you like to do?
  [1] List my assistants
  [2] Upload documents to an assistant
  [3] Configure system prompt
  [4] Switch Claude Desktop assistant
  [5] View assistant details

Enter choice (1-5): 1

Listing your Pinecone Assistants...

[OK] Found 3 assistants:

Assistant 1: patent-analyzer
  Status: Ready
  Files: 12/12 processed
  Model: gpt-4o
  Host: https://prod-1-data.ke.pinecone.io

Assistant 2: uspto-mpep
  Status: Ready  
  Files: 6/6 processed
  Model: gpt-4o
  Host: https://prod-1-data.ke.pinecone.io

Assistant 3: legal-research
  Status: Processing
  Files: 8/10 processed (2 still uploading)
  Model: claude-3-5-sonnet
  Host: https://prod-1-data.ke.pinecone.io

Press Enter to continue...
```

**Switching Assistants Example:**
```
Enter choice (1-5): 4

Current Claude Desktop assistant: patent-analyzer

Available assistants:
  [1] patent-analyzer (current)
  [2] uspto-mpep
  [3] legal-research

Select new assistant (1-3): 2

Claude Desktop configured to use: uspto-mpep
Restart Claude Desktop to apply changes

[OK] Assistant switch complete!
```

### Project Management for Free Tier Token Limits

**For Starter Plan users who need to reset token limits:**

The Starter Plan has **lifetime token limits per project** (1.5M input, 200K output, 500K context - see Plan Limits table below). When you exhaust these limits, you can delete and recreate your project to get fresh limits.

**⚠️ Important Limitations:**
- **Starter Plan allows only 1 project at a time** - you must delete the old project before creating a new one
- Deleting a project **permanently deletes ALL resources** in that project:
  - All assistants and their documents
  - All vector databases (indexes) and their data
  - All backups and collections
  - All project configuration
- **If you have production vector databases in this project, DO NOT delete it!**
- You will need to **re-upload all documents** (can take 20-35 minutes for USPTO docs)
- This workflow is intended for **extended testing only**
- **For production use, consider paid plans** but be aware of costs:
  - Standard Plan: $50/month minimum + $0.05/hour per assistant + token/storage charges
  - See Plan Limits & Pricing Reference table above for detailed cost breakdown

**Automated Workflow (Recommended):**

```powershell
# Use the new project management tool
.\deploy\manage_project.ps1
```

This interactive script will:
- List all your projects and their details
- Guide you through deleting all assistants
- Warn you about vector databases and other resources
- Provide step-by-step deletion instructions
- Remind you about recreation steps

**Step-by-Step Manual Workflow:**

1. **Document your current setup:**
   ```powershell
   # Run the management script to view your assistants
   .\deploy\manage_assistant.ps1
   # Choose option 2 (List all assistants)
   # Note down: assistant names, system prompts, document lists
   ```

2. **Delete all assistants in your project:**
   ```powershell
   # Still in manage_assistant.ps1
   # Choose option 6 (Delete assistant)
   # Repeat for each assistant in your project
   ```

3. **Delete any vector databases (indexes) in your project:**
   - Log into [Pinecone Console](https://app.pinecone.io/)
   - Navigate to: Indexes
   - Delete each index if any exist
   - **⚠️  WARNING: This permanently deletes all vector database data!**

4. **Delete your project via Pinecone Console:**
   - Navigate to: Organization Settings → Projects
   - Click on your project → Settings → Delete Project
   - Confirm deletion (type project name)

5. **Create a new project:**
   - In Pinecone Console: Projects → Create Project
   - Note the new project name and ID

6. **Re-run the setup script:**
   ```powershell
   # This will create new assistants and upload documents
   .\deploy\windows_setup.ps1
   ```
   - Enter your API key (same as before)
   - Create new assistant(s) with the same or different names
   - Upload documents (select same documents as before)
   - Reconfigure Claude Desktop integration

7. **Verify token limits reset:**
   - Check [Pinecone Console](https://app.pinecone.io/) → Usage
   - Token counters should be back to 0

**Alternative approach to maximize free tier:**
- Use `assistant_context` and `assistant_strategic_multi_search_context` tools which consume context tokens (500K limit) instead of input/output tokens
- Reserve AI-powered tools (`assistant_chat`, `assistant_strategic_multi_search_chat`) for complex questions that truly need synthesis
- Context-only tools can handle 90% of queries while consuming far fewer tokens

---

## 📦 Document Upload Features

### Pre-Upload Validation

The script validates before uploading:
- ✅ File size limits (10MB for .md/.txt, 100MB for .pdf)
- ✅ Plan limits (Starter: 10 files, 1GB storage)
- ✅ Total size calculation
- ✅ File type checking

**Example Validation:**
```
Validating files before upload...
============================================================
Total files: 6
Total size: 45.32 MB
File types: .md

Plan Limits Check:
- File count: 6/10 (within Starter plan limit)
- Storage used: 45.32 MB / 1 GB (within Starter plan limit)
- Largest file: 12.8 MB (within .md/.txt limits)

✓ All files validated successfully
```

### Upload Process

- **Progress tracking**: `[2/6] (33%) Uploading...`
- **Rate limiting**: 1-second delays between uploads
- **Error handling**: Specific guidance for common errors
- **Auto-retry**: On rate limit errors

### Post-Upload Verification

After upload completes:
```
============================================================
UPLOAD VERIFICATION - Checking what made it to the assistant...
============================================================

✓ Assistant currently has 12 total files

Upload Results:
  Files attempted: 6
  Upload succeeded: 6
  Upload failed: 0

============================================================
DETAILED FILE-BY-FILE VERIFICATION:
============================================================

[1/6] ✅ Combined_Training_Materials.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Size: 3.5 MB
    Created: 2025-01-19T12:34:56Z

[2/6] ✅ Combined_MPEP_Part1.md
    Upload Status: Succeeded
    Assistant Status: AVAILABLE (Ready to use)
    Processing: 100% complete
    Size: 8.2 MB
    Created: 2025-01-19T12:35:12Z

============================================================
FINAL VERIFICATION SUMMARY:
============================================================

What you tried to upload:  6 files
What made it to assistant: 6 files

Breakdown:
  ✅ Ready & Available:     6 files
  ⏳ Still Processing:      0 files
  ❌ Failed Processing:     0 files
  ⚠️  Missing/Not Found:     0 files

🎉 SUCCESS! All 6 files uploaded and ready to use!
```

---

## 🎯 USPTO System Prompt Configuration

When you select "Default USPTO MPEP documents", the script automatically configures a specialized system prompt for patent law analysis:

**System Prompt:**
```
Conduct comprehensive patent law analysis using IRAC methodology
(Issue-Rule-Application-Conclusion).

**Analysis Standards:**
- Provide detailed analysis based on legal authority in the knowledge base
- Reference specific sources: MPEP sections, 35 USC provisions,
  Federal Circuit decisions, USPTO examination guidance
- If precedent is unclear, acknowledge uncertainty and explain
  available legal approaches
- Deliver actionable strategic recommendations

**Professional Requirements:**
- Structure analysis with clear headings
- Maintain professional legal writing standards
- Focus on practical implications for patent prosecution
- State limitations when context lacks specific authority

**Source Document Context:**
When analyzing content from Combined_MPEP_Updates.md or Combined_Training_Materials.md:
- Identify which specific guidance document the content comes from (look for === UPDATE markers)
- Reference the specific guidance title in your analysis (e.g., "According to the 2024-02-12 AI Inventorship Guidance...")
- When citing MPEP content, reference the MPEP section number if present (e.g., "MPEP § 2138.04")

**Citation Best Practices:**
- Always cite the most specific document identifier available in the source
- For updates: Include the date and title (e.g., "2024-02-12 AI Inventorship Guidance")
- For MPEP: Include section numbers (e.g., "MPEP § 2138.04")
- For Federal Register: Include FR citation if present (e.g., "89 FR 10043")

**Output Format:**
Present analysis in logical legal framework incorporating all relevant authority, with precise citations and strategic guidance for patent practitioners.
```

**Benefits:**
- ✅ Optimized for IRAC (Issue-Rule-Application-Conclusion) methodology
- ✅ Ensures precise MPEP/USC citations
- ✅ Professional legal writing standards
- ✅ Strategic guidance for practitioners

**Safety:**
- ✅ Preserves existing assistant metadata
- ✅ Only updates `instructions` field
- ✅ Non-critical operation (setup succeeds even if this fails)

---

## 🔐 Security & Privacy

### API Key Storage

**The setup script provides two security options:**

#### Secure Storage (Windows - Recommended)
✅ **Encrypted storage using Windows DPAPI:**
- API key encrypted using Windows DPAPI via Python ctypes calls to crypt32.dll
- Stored in: `%USERPROFILE%\.pinecone_api_key` — unified key file shared across all Pinecone MCPs
- File format: bytes 0–31 = DPAPI entropy prefix, bytes 32+ = encrypted API key (self-contained)
- Credential Manager target: `pinecone_API_KEY` (Windows Credential Manager)
- Can only be decrypted by your user account on this machine
- Claude Desktop config contains **NO plain text API key and NO `INTERNAL_AUTH_SECRET`**
- No PowerShell execution policy requirements
- Cross-platform compatible with automatic fallback to environment variables (`PINECONE_API_KEY` then `PINECONE_ASSISTANT_API_KEY`)

> **Why no `INTERNAL_AUTH_SECRET` in the JSON config?** Unlike the USPTO MCPs which pass an external entropy secret as an environment variable, the Pinecone MCP uses a self-contained design: the DPAPI entropy is embedded directly in bytes 0–31 of `~/.pinecone_api_key`. The server decrypts the key at startup by reading the file itself — no external variable is required. The shared `~/.uspto_internal_auth_secret` file is only consulted when *writing* (storing) a new key, not when reading it.

#### Traditional Storage (Fallback/Manual)
⚠️ **Plain text storage:**
- API key stored in Claude Desktop config file as environment variable
- Required for Linux/macOS or manual setup
- File permissions protect the config, but key is not encrypted

### Security Best Practices

❌ **Never stored in:**
- System environment variables
- User environment variables  
- `.env` files (not used - API keys belong in Claude Desktop config or secure storage)
- Version control (git repositories)
- Shared configuration files

✅ **Security features:**
- Temporary variables cleared after use
- Python DPAPI encryption on Windows (when using setup script)
- File-level permissions on Claude Desktop config
- API key validation during setup
- Pure Python implementation eliminates PowerShell execution policy issues

**Why Claude Desktop config (not .env files)?**
- Required for MCP server to authenticate with Pinecone
- Protected by OS-level file permissions  
- Standard practice for MCP servers
- Environment variables and .env files are not used in this implementation

---

## ✅ Verify Installation

### Test MCP Server

```bash
# Test directly
uv run python src/main.py

# Should start server and wait for MCP protocol messages
# Press Ctrl+C to stop
```

### Test in Claude Desktop

1. Open Claude Desktop
2. Look for MCP server indicator (🔌 icon)
3. Try a test query:
   ```
   Use assistant_chat to ask: "What are the Section 101 eligibility requirements?"
   ```

### Expected Response

You should see a response with:
- Detailed analysis based on MPEP content
- Citations to specific MPEP sections
- Text highlights from source documents
- Usage statistics (tokens consumed)

---

## 🔄 Updating

### Update to Latest Version

```bash
cd pinecone_assistant_mcp
git pull origin master
uv sync
```

### Re-run Setup (if needed)

```powershell
.\deploy\windows_setup.ps1
```

The script will detect existing configuration and offer to update.

---

## 🛠️ Troubleshooting

### "API key must start with 'pcsk_'"

**Solution:** Ensure you're using a Pinecone Assistant API key, not a regular Pinecone API key.

Get the correct key from: https://app.pinecone.io/ → API Keys → Assistant API

### "Failed to create assistant: 403 Forbidden"

**Solution:** Assistant creation via API requires a paid Pinecone plan.

Create assistant manually:
1. Go to https://app.pinecone.io/
2. Create assistant via web UI
3. Re-run setup script
4. Choose option [2] "I already have an assistant"

### "uv not found"

**Solution:** The script should auto-install uv, but if it fails:

```powershell
# Windows
winget install --id=astral-sh.uv -e

# Or
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### "Claude Desktop not loading server"

**Checklist:**
1. ✅ Verify JSON syntax in config file
2. ✅ Check installation path is correct and absolute
3. ✅ Ensure API key is valid
4. ✅ Restart Claude Desktop completely
5. ✅ Check Claude Desktop logs for errors

**View logs:**
- Windows: `%APPDATA%\Claude\logs\`
- Linux: `~/.config/claude/logs/`

### Upload Failures

If files fail to upload:
1. **Check file sizes**: Max 10MB for .md/.txt
2. **Check plan limits**: Starter plan has 10 file limit
3. **Verify API key**: Must be valid Assistant API key
4. **Check network**: Ensure connection to Pinecone

Run verification again:
```bash
cd deploy
uv run python upload_files.py --api-key "pcsk_YOUR_PINECONE_KEY" --assistant-name "your-assistant"
```

---

## 📚 Next Steps

After installation:

1. **Learn the tools:** See [README.md](./README.md) for MCP tool documentation
2. **Customize for your domain:** See [CUSTOMIZATION.md](./CUSTOMIZATION.md)
3. **View usage examples:** See [USAGE_EXAMPLES.md](./USAGE_EXAMPLES.md)
4. **Configure search patterns:** Edit `strategic-searches.yaml`

### Example Queries to Try

**Basic chat:**
```
Ask the assistant about Section 101 patent eligibility requirements
```

**Strategic search:**
```
Use assistant_strategic_multi_search_chat with domain "core_examination_framework"
and query "software patent eligibility after Alice"
```

**Raw document retrieval:**
```
Use assistant_context to find documents about "examiner's answer"
with snippet_size 1024 and top_k 5
```

---

## 🆘 Getting Help

- **Documentation:** See [README.md](./README.md) and [CUSTOMIZATION.md](./CUSTOMIZATION.md)
- **Pinecone Docs:** https://docs.pinecone.io/

---

## 📊 Plan Limits & Pricing Reference

| Feature | Starter | Standard | Enterprise |
|---------|---------|----------|------------|
| **Monthly minimum** | $0 | **$50** | **$500** |
| **Hourly rate per assistant** | Free | **$0.05/hour** | **$0.05/hour** |
| Assistants per project | 5 | Unlimited | Unlimited |
| Files per assistant | 10 | 10,000 | 10,000 |
| File storage per project | 1 GB (monthly)* | Unlimited | Unlimited |
| **Storage rate** | Free | **$3/GB/month** | **$3/GB/month** |
| File size (.md, .txt, .json) | 10 MB | 10 MB | 10 MB |
| File size (.pdf) | 10 MB | 100 MB | 100 MB |
| Chat input tokens per project | 1,500,000 (LIFETIME)** | Unlimited*** | Unlimited*** |
| **Input token rate** | Free | **$8/million** | **$8/million** |
| Chat output tokens per project | 200,000 (LIFETIME)** | Unlimited*** | Unlimited*** |
| **Output token rate** | Free | **$15/million** | **$15/million** |
| Context tokens per project | 500,000 (LIFETIME)** | Unlimited*** | Unlimited*** |
| **Context token rate** | Free | **$5/million** | **$5/million** |

**\*File Storage Limits:** Only storage limits (1 GB for Starter) reset monthly.

**\*\*Starter Plan Token Limits:** Token limits on Starter plan are **LIFETIME limits per project, NOT monthly**. Once exhausted, you must either:
1. **Upgrade to a paid plan** (Standard: $50/month minimum even if usage is less)
2. **Delete and recreate your project** (for extended testing only - requires re-uploading all documents)

**\*\*\*Paid Plan Costs:** "Unlimited" means no hard caps, but you pay for usage:
- **Standard Plan**: $50/month minimum (if usage < $50, you still pay $50; if usage > $50, you pay actual usage)
- **Hourly charges**: $0.05/hour per assistant (even if inactive) - 1 assistant costs ~$36/month just to keep running
- **Token charges**: $8/million input + $15/million output + $5/million context
- **Storage charges**: $3/GB per month

**Example Cost Scenarios:**

**Standard Plan - Low Usage:**
- Usage: $20 in tokens + $5 in storage = $25 total
- Bill: $50 (monthly minimum applies)

**Standard Plan - High Usage:**
- 1 assistant running 24/7: $36 (hourly charges)
- 10M input tokens: $80
- 2M output tokens: $30
- 5 GB storage: $15
- Total usage: $161
- Bill: $161 (exceeds minimum, pay actual usage)

**Reference:** [Pinecone Assistant Pricing & Limits](https://docs.pinecone.io/guides/assistant/pricing-and-limits)

The upload script automatically validates against file limits before uploading.

---

**Installation Questions?** Review the troubleshooting section above.