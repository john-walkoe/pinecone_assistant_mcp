#!/usr/bin/env python3
"""
Upload documents to existing Pinecone Assistant
Supports all Pinecone Assistant file types: .md, .txt, .pdf, .docx, .json
Handles both direct files and combined_documents.zip extraction
"""

import os
import sys
import argparse
from pathlib import Path
import io

# Fix Windows console encoding issues with emoji/unicode characters
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7 fallback
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def upload_files_to_assistant(api_key: str, assistant_name: str, use_uspto_metadata: bool = False,
                             zip_only: bool = False, loose_only: bool = False):
    """Upload documents to the existing Pinecone Assistant

    Args:
        api_key: Pinecone API key
        assistant_name: Name of the assistant
        use_uspto_metadata: If True, use USPTO-specific metadata. If False, use generic metadata.
        zip_only: If True, only extract and upload from combined_documents.zip
        loose_only: If True, only upload loose files from combined_documents/ folder
    """

    try:
        from pinecone import Pinecone
    except ImportError:
        print("ERROR: pinecone package not found. Run: pip install --upgrade pinecone pinecone-plugin-assistant")
        return False

    # Initialize Pinecone client
    try:
        pc = Pinecone(api_key=api_key)
        assistant = pc.assistant.Assistant(assistant_name=assistant_name)
        print(f"✓ Connected to assistant: {assistant_name}")
    except Exception as e:
        print(f"ERROR: Failed to connect to assistant: {e}")
        return False

    # Define files to upload with metadata
    script_dir = Path(__file__).parent
    documents_dir = script_dir / "combined_documents"
    zip_file = documents_dir / "combined_documents.zip"

    # Determine which files to process based on flags
    extract_zip = not loose_only  # Extract unless loose-only
    include_loose = not zip_only  # Include loose files unless zip-only

    # Track which files we extracted (so we can clean them up later)
    extracted_files = set()

    # Extract zip file if needed
    if extract_zip and zip_file.exists():
        print("Found combined_documents.zip, extracting...")
        try:
            import zipfile
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                # Track the files we're extracting
                extracted_files = {documents_dir / name for name in zip_ref.namelist()}
                zip_ref.extractall(documents_dir)
            print("✓ Successfully extracted documents from zip file")
        except Exception as e:
            print(f"ERROR: Failed to extract zip file: {e}")
            return False
    elif zip_only and not zip_file.exists():
        print(f"ERROR: --zip-only specified but {zip_file} not found")
        return False

    # Define metadata based on document type
    if use_uspto_metadata:
        print("Using USPTO-specific metadata")
        files_to_upload = [
        {
            "path": documents_dir / "Combined_Training_Materials.md",
            "metadata": {
                "document_type": "uspto_training",
                "section": "examination_guidance", 
                "source": "combined_materials",
                "category": "training",
                "agency": "uspto"
            }
        },
        {
            "path": documents_dir / "Combined_MPEP_Updates.md", 
            "metadata": {
                "document_type": "mpep_updates",
                "section": "policy_updates",
                "source": "combined_updates", 
                "category": "current_guidance",
                "agency": "uspto",
                "timeframe": "2024-2025"
            }
        },
        {
            "path": documents_dir / "Combined_MPEP_9th_Edition_Part1.md",
            "metadata": {
                "document_type": "mpep_manual",
                "section": "chapters_1_5",
                "source": "mpep_9th_edition",
                "category": "statutory_guidance", 
                "agency": "uspto",
                "part": "1_of_4"
            }
        },
        {
            "path": documents_dir / "Combined_MPEP_9th_Edition_Part2.md",
            "metadata": {
                "document_type": "mpep_manual",
                "section": "chapters_6_12", 
                "source": "mpep_9th_edition",
                "category": "statutory_guidance",
                "agency": "uspto", 
                "part": "2_of_4"
            }
        },
        {
            "path": documents_dir / "Combined_MPEP_9th_Edition_Part3.md",
            "metadata": {
                "document_type": "mpep_manual",
                "section": "chapters_13_20",
                "source": "mpep_9th_edition", 
                "category": "statutory_guidance",
                "agency": "uspto",
                "part": "3_of_4"
            }
        },
        {
            "path": documents_dir / "Combined_MPEP_9th_Edition_Part4.md",
            "metadata": {
                "document_type": "mpep_manual",
                "section": "chapters_21_plus",
                "source": "mpep_9th_edition",
                "category": "statutory_guidance",
                "agency": "uspto",
                "part": "4_of_4"
            }
        },
        {
            "path": documents_dir / "mpep-9015-appx-l-July-2025.md",
            "metadata": {
                "document_type": "mpep_appendix",
                "section": "appendix_l",
                "source": "mpep_9th_edition",
                "category": "examination_guidelines",
                "agency": "uspto",
                "appendix": "L",
                "title": "Guidelines for Examination Under 35 U.S.C. § 112",
                "effective_date": "July_2025"
            }
        },
        {
            "path": documents_dir / "mpep-9020-appx-r-July-2025.md",
            "metadata": {
                "document_type": "mpep_appendix",
                "section": "appendix_r",
                "source": "mpep_9th_edition",
                "category": "patent_rules",
                "agency": "uspto",
                "appendix": "R",
                "title": "Patent Rules (37 CFR)",
                "effective_date": "July_2025"
            }
        }
    ]
    else:
        print("Using generic metadata")

        # Define known zip files (these would be extracted from combined_documents.zip)
        known_zip_files = {
            "Combined_Training_Materials.md",
            "Combined_MPEP_Updates.md",
            "Combined_MPEP_9th_Edition_Part1.md",
            "Combined_MPEP_9th_Edition_Part2.md",
            "Combined_MPEP_9th_Edition_Part3.md",
            "Combined_MPEP_9th_Edition_Part4.md",
            "mpep-9015-appx-l-July-2025.md",
            "mpep-9020-appx-r-July-2025.md"
        }

        # Collect all supported file types based on flags
        # Pinecone Assistant supports: .md, .txt, .pdf, .docx, .json
        supported_extensions = ['.md', '.txt', '.pdf', '.docx', '.json']
        document_files = []
        
        for ext in supported_extensions:
            for doc_file in documents_dir.glob(f"*{ext}"):
                is_from_zip = doc_file.name in known_zip_files

                # Include based on flags
                if loose_only:
                    # Only include files NOT from zip
                    if not is_from_zip:
                        document_files.append(doc_file)
                elif zip_only:
                    # Only include files FROM zip
                    if is_from_zip:
                        document_files.append(doc_file)
                else:
                    # Include all files (default)
                    document_files.append(doc_file)

        if not document_files:
            if loose_only:
                print("ERROR: No loose document files found (only zip files present)")
                print("Supported file types: .md, .txt, .pdf, .docx, .json")
            elif zip_only:
                print("ERROR: No document files from zip found")
                print("Supported file types: .md, .txt, .pdf, .docx, .json")
            else:
                print("ERROR: No supported document files found in documents directory")
                print("Supported file types: .md, .txt, .pdf, .docx, .json")
            return False

        print(f"Detected {len(document_files)} custom documents to upload")
        print(f"File types found: {', '.join(set(f.suffix for f in document_files))}")

        files_to_upload = []
        for idx, doc_file in enumerate(document_files, 1):
            files_to_upload.append({
                "path": doc_file,
                "metadata": {
                    "document_type": "custom_document",
                    "source": "user_provided",
                    "category": "reference",
                    "file_number": idx,
                    "filename": doc_file.stem,  # filename without extension
                    "file_type": doc_file.suffix[1:]  # extension without the dot
                }
            })

        print(f"Prepared {len(files_to_upload)} documents for upload")

    # Check if all files exist
    missing_files = []
    for file_info in files_to_upload:
        if not file_info["path"].exists():
            missing_files.append(str(file_info["path"]))
    
    if missing_files:
        print("ERROR: Missing files:")
        for file in missing_files:
            print(f"  - {file}")
        return False
    
    print(f"Found {len(files_to_upload)} files to upload")

    # Pre-upload validation: Check file sizes and plan limits
    print("\nValidating files before upload...")
    print("=" * 60)

    total_size_mb = 0
    oversized_files = []
    warnings = []

    for file_info in files_to_upload:
        file_path = file_info["path"]
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        total_size_mb += file_size_mb

        file_ext = file_path.suffix.lower()

        # Check file size limits based on Pinecone Assistant plan limits
        if file_ext in ['.md', '.txt', '.docx', '.json']:
            if file_size_mb > 10:
                oversized_files.append(f"{file_path.name} ({file_size_mb:.1f}MB > 10MB limit for {file_ext} files)")
        elif file_ext == '.pdf':
            if file_size_mb > 100:
                oversized_files.append(f"{file_path.name} ({file_size_mb:.1f}MB > 100MB limit for PDF files)")
            elif file_size_mb > 10:
                warnings.append(f"{file_path.name} ({file_size_mb:.1f}MB) - PDF files 10-100MB require Standard+ plan")

    print(f"Total files: {len(files_to_upload)}")
    print(f"Total size: {total_size_mb:.2f} MB")
    print(f"File types: {', '.join(set(f['path'].suffix for f in files_to_upload))}")

    # Plan limit warnings
    if len(files_to_upload) > 10:
        warnings.append(f"Uploading {len(files_to_upload)} files - Starter plan limit is 10 files per assistant")

    if total_size_mb > 1024:  # 1 GB
        warnings.append(f"Total size {total_size_mb:.2f}MB exceeds Starter plan 1GB storage limit")

    if oversized_files:
        print("\n⚠ ERROR: The following files exceed size limits:")
        for file_warning in oversized_files:
            print(f"  ✗ {file_warning}")
        print("\nPlease reduce file sizes or split large files before uploading.")
        return False

    if warnings:
        print("\n⚠ WARNINGS:")
        for warning in warnings:
            print(f"  • {warning}")
        print("\nPlan Limits Reference:")
        print("  Starter:            10 files, 1GB storage, 10MB (.md/.txt/.docx/.json), 10MB (.pdf)")
        print("  Standard/Enterprise: 10,000 files, unlimited storage, 10MB (.md/.txt/.docx/.json), 100MB (.pdf)")
        print("")

        proceed = input("Do you want to proceed with upload? (y/N): ")
        if proceed.lower() != 'y':
            print("Upload cancelled by user")
            return False

    print("\n✓ All files validated successfully")

    # Upload each file with rate limiting and progress tracking
    import time

    upload_results = []
    success_count = 0
    failure_count = 0
    total_files = len(files_to_upload)

    print(f"\nStarting upload of {total_files} files...")
    print("=" * 60)
    print("\n⏱️  UPLOAD TIME ESTIMATE:")
    print("   First file:  5-10 minutes (depends on file size and network)")
    print("   Other files: 2-5 minutes each")
    print(f"   Total estimate: {5 + (total_files - 1) * 3}-{10 + (total_files - 1) * 5} minutes")
    print("\n💡 TIP: To track real-time upload progress, check the Pinecone Console:")
    print("   https://app.pinecone.io/ → Your Assistant → Files tab")
    print("   You'll see a progress bar for each file there!")
    print("=" * 60)

    for idx, file_info in enumerate(files_to_upload, 1):
        file_path = file_info["path"]
        metadata = file_info["metadata"]

        # Progress indicator
        progress_pct = (idx / total_files) * 100
        print(f"\n[{idx}/{total_files}] ({progress_pct:.0f}%) Uploading {file_path.name}...", end='', flush=True)

        try:
            # Check file size (should be under 10MB)
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 10:
                print(f"\n  WARNING: {file_path.name} is {file_size_mb:.1f}MB (over 10MB limit)")

            # Show working indicator
            print(" (uploading...)", end='', flush=True)

            # Use a reasonable timeout for file uploads (10 minutes for large files)
            upload_timeout = 600  # 10 minutes in seconds
            response = assistant.upload_file(
                file_path=str(file_path),
                metadata=metadata,
                timeout=upload_timeout
            )

            upload_results.append({
                "filename": file_path.name,
                "file_id": response.get("id"),
                "status": "success",
                "size_mb": round(file_size_mb, 2)
            })

            # Show success on the same line
            print(f"\r[{idx}/{total_files}] ({progress_pct:.0f}%) ✓ Successfully uploaded {file_path.name} ({file_size_mb:.1f}MB)" + " " * 20)
            success_count += 1

            # Rate limiting: wait 1 second between uploads (except for the last one)
            if idx < total_files:
                print("  ⏱ Waiting 1 second (rate limiting)...")
                time.sleep(1)

        except Exception as e:
            error_msg = str(e)
            print(f"  ✗ Failed to upload {file_path.name}: {error_msg}")

            # Provide specific error guidance
            if "429" in error_msg or "rate limit" in error_msg.lower():
                print("     → Rate limit exceeded. Waiting 5 seconds before continuing...")
                time.sleep(5)
            elif "413" in error_msg or "too large" in error_msg.lower():
                print("     → File too large for your plan. Consider splitting the file.")
            elif "403" in error_msg or "forbidden" in error_msg.lower():
                print("     → Permission denied. Check your API key and plan limits.")
            elif "storage" in error_msg.lower() or "quota" in error_msg.lower():
                print("     → Storage quota exceeded. Upgrade plan or remove old files.")

            upload_results.append({
                "filename": file_path.name,
                "file_id": None,
                "status": "failed",
                "error": error_msg
            })
            failure_count += 1

    print("\n" + "=" * 60)
    
    # Display summary
    print(f"\nUpload Summary: {success_count} successful, {failure_count} failed")
    
    if success_count > 0:
        print("\nSuccessful uploads:")
        for result in upload_results:
            if result["status"] == "success":
                print(f"  ✓ {result['filename']} - {result['size_mb']}MB (ID: {result['file_id']})")
    
    if failure_count > 0:
        print("\nFailed uploads:")
        for result in upload_results:
            if result["status"] == "failed":
                print(f"  ✗ {result['filename']} - {result['error']}")
    
    # Check upload status and verify file processing
    print("\n" + "=" * 60)
    print("UPLOAD VERIFICATION - Checking what made it to the assistant...")
    print("=" * 60)

    try:
        files_response = assistant.list_files()

        # Handle both list return (direct list) and dict return ({'files': [...]})
        if isinstance(files_response, list):
            all_files = files_response
        else:
            all_files = files_response.get('files', [])

        # Create a mapping of file IDs to file info for quick lookup
        # Handle both dict-like objects and objects with attributes
        files_by_id = {}
        for f in all_files:
            file_id = f.get('id') if hasattr(f, 'get') else getattr(f, 'id', None)
            if file_id:
                files_by_id[file_id] = f

        print(f"\n✓ Assistant currently has {len(all_files)} total files")

        # Track what we attempted vs what succeeded
        attempted_count = len(upload_results)
        upload_succeeded_count = len([r for r in upload_results if r['status'] == 'success'])
        upload_failed_count = len([r for r in upload_results if r['status'] == 'failed'])

        print(f"\nUpload Results:")
        print(f"  Files attempted: {attempted_count}")
        print(f"  Upload succeeded: {upload_succeeded_count}")
        print(f"  Upload failed: {upload_failed_count}")

        print(f"\n{'='*60}")
        print("DETAILED FILE-BY-FILE VERIFICATION:")
        print(f"{'='*60}")

        files_ready = 0
        files_processing = 0
        files_failed = 0
        files_missing = 0

        for idx, result in enumerate(upload_results, 1):
            filename = result['filename']

            # Check if upload even succeeded
            if result['status'] == 'failed':
                print(f"\n[{idx}/{attempted_count}] ❌ {filename}")
                print(f"    Upload Status: FAILED (never reached assistant)")
                print(f"    Error: {result['error']}")
                files_missing += 1
                continue

            # Upload succeeded - now check if it's in the assistant
            file_id = result['file_id']
            file_info = files_by_id.get(file_id)

            if not file_info:
                print(f"\n[{idx}/{attempted_count}] ⚠️ {filename}")
                print(f"    Upload Status: Succeeded")
                print(f"    Assistant Status: NOT FOUND (may have been deleted or upload incomplete)")
                print(f"    File ID: {file_id}")
                files_missing += 1
                continue

            # File is in the assistant - check its processing status
            # Handle both dict-like and object-like file info
            if hasattr(file_info, 'get'):
                status = file_info.get('status', 'unknown')
                progress = file_info.get('percent_done', 0)
                created_on = file_info.get('created_on', '')
                updated_on = file_info.get('updated_on', '')
                error_msg = file_info.get('error', file_info.get('error_message', 'Unknown error'))
            else:
                status = getattr(file_info, 'status', 'unknown')
                progress = getattr(file_info, 'percent_done', 0)
                created_on = getattr(file_info, 'created_on', '')
                updated_on = getattr(file_info, 'updated_on', '')
                error_msg = getattr(file_info, 'error', getattr(file_info, 'error_message', 'Unknown error'))

            # Handle percent_done as either 0-1 float or 0-100 integer
            if progress <= 1:
                progress_pct = progress * 100
            else:
                progress_pct = progress

            if status == 'Available':
                print(f"\n[{idx}/{attempted_count}] ✅ {filename}")
                print(f"    Upload Status: Succeeded")
                print(f"    Assistant Status: AVAILABLE (Ready to use)")
                print(f"    Processing: 100% complete")
                if created_on:
                    print(f"    Created: {created_on}")
                files_ready += 1

            elif status == 'Processing':
                print(f"\n[{idx}/{attempted_count}] ⏳ {filename}")
                print(f"    Upload Status: Succeeded")
                print(f"    Assistant Status: PROCESSING")
                print(f"    Processing: {progress_pct:.0f}% complete")
                if updated_on:
                    print(f"    Last updated: {updated_on}")
                files_processing += 1

            elif status == 'Failed':
                print(f"\n[{idx}/{attempted_count}] ❌ {filename}")
                print(f"    Upload Status: Succeeded")
                print(f"    Assistant Status: FAILED (processing error)")
                print(f"    Error: {error_msg}")
                if created_on:
                    print(f"    Created: {created_on}")
                files_failed += 1

            else:
                print(f"\n[{idx}/{attempted_count}] ⚠️ {filename}")
                print(f"    Upload Status: Succeeded")
                print(f"    Assistant Status: {status.upper()}")
                print(f"    Processing: {progress_pct:.0f}% complete")
                if updated_on:
                    print(f"    Last updated: {updated_on}")
                files_processing += 1

        # Summary
        print("\n" + "=" * 60)
        print("FINAL VERIFICATION SUMMARY:")
        print("=" * 60)
        print(f"\nWhat you tried to upload:  {attempted_count} files")
        print(f"What made it to assistant: {upload_succeeded_count - files_missing} files")
        print(f"\nBreakdown:")
        print(f"  ✅ Ready & Available:     {files_ready} files")
        print(f"  ⏳ Still Processing:      {files_processing} files")
        print(f"  ❌ Failed Processing:     {files_failed} files")
        print(f"  ⚠️  Missing/Not Found:     {files_missing} files")

        if files_ready == attempted_count:
            print(f"\n🎉 SUCCESS! All {attempted_count} files uploaded and ready to use!")
        elif files_ready + files_processing == attempted_count:
            print(f"\n✓ Good! {files_ready} files ready, {files_processing} still processing.")
            print("  Wait a few minutes and files should be ready.")
        else:
            print(f"\n⚠️  WARNING: Not all files made it successfully!")
            print(f"  Expected: {attempted_count} files")
            print(f"  Ready: {files_ready} files")
            print(f"  Issues: {files_failed + files_missing} files")

        if files_processing > 0:
            print("\nℹ️  Files marked as 'Processing' will be available shortly.")
            print("   Check status again in a few minutes.")

        if files_failed > 0 or files_missing > 0:
            print("\n⚠️  Common reasons for failures:")
            print("  • File size exceeds limits (10MB for .md/.txt/.docx/.json, 100MB for .pdf)")
            print("  • Plan limits reached:")
            print("    - Starter plan: 10 files per assistant, 1GB storage")
            print("    - Standard/Enterprise: 10,000 files, unlimited storage")
            print("  • Invalid file format or corrupted content")
            print("  • Metadata exceeds 16KB limit")
            print("  • Network issues during upload")

    except Exception as e:
        print(f"\n⚠️  Could not verify upload status: {e}")
        print("Files may have uploaded successfully, but status verification failed.")
        print(f"Uploaded {success_count} files, but unable to confirm assistant status.")
    
    # Configure USPTO system prompt if using default documents and upload succeeded
    if use_uspto_metadata and success_count > 0:
        print("\n" + "=" * 60)
        print("CONFIGURING USPTO SYSTEM PROMPT...")
        print("=" * 60)

        prompt_file = script_dir / "assistant_system_prompt.txt"
        if prompt_file.exists():
            try:
                system_prompt = prompt_file.read_text(encoding="utf-8").strip()
                print(f"Loaded system prompt from: {prompt_file.name}")

                # Preserve existing metadata when updating instructions
                try:
                    existing_info = pc.assistant.describe_assistant(assistant_name=assistant_name)
                    existing_metadata = getattr(getattr(existing_info, 'assistant', existing_info), 'metadata', None)
                except Exception:
                    existing_metadata = None

                pc.assistant.update_assistant(
                    assistant_name=assistant_name,
                    instructions=system_prompt,
                    metadata=existing_metadata if existing_metadata else None
                )
                print("✓ USPTO system prompt configured successfully!")
                print("  Assistant will now use IRAC methodology for patent law analysis.")
            except Exception as e:
                print(f"⚠  Could not configure system prompt: {e}")
                print(f"   You can set it manually via: deploy/manage_assistant.ps1")
        else:
            print(f"⚠  System prompt file not found: {prompt_file}")
            print(f"   Expected: deploy/assistant_system_prompt.txt")

    # Clean up ONLY files that were extracted from zip (not user's loose files)
    if extracted_files and success_count > 0:
        print("\nCleaning up extracted files from zip...")
        print("(Note: Loose files in combined_documents/ folder are preserved)")
        deleted_count = 0
        try:
            for file_info in files_to_upload:
                file_path = file_info["path"]
                # Only delete if this file was extracted from the zip
                if file_path in extracted_files and file_path.exists():
                    file_path.unlink()
                    print(f"  Deleted (extracted): {file_path.name}")
                    deleted_count += 1
                elif file_path.exists() and file_path not in extracted_files:
                    print(f"  Preserved (loose file): {file_path.name}")

            if deleted_count > 0:
                print(f"✓ Cleanup completed - deleted {deleted_count} extracted file(s)")
            else:
                print("✓ No extracted files to clean up")
        except Exception as e:
            print(f"Warning: Could not clean up some files: {e}")
    
    return success_count > 0

def main():
    parser = argparse.ArgumentParser(description="Upload documents to Pinecone Assistant")
    parser.add_argument("--api-key", required=False,
                        help="Pinecone Assistant API key (or use stdin/PINECONE_ASSISTANT_API_KEY env var)")
    parser.add_argument("--assistant-name", default="my-assistant", help="Assistant name (default: my-assistant)")
    parser.add_argument("--use-uspto-metadata", action="store_true",
                        help="Use USPTO-specific metadata for default documents (default: generic metadata)")
    parser.add_argument("--zip-only", action="store_true",
                        help="Only extract and upload from combined_documents.zip (ignore loose files)")
    parser.add_argument("--loose-only", action="store_true",
                        help="Only upload loose files from combined_documents/ folder (ignore zip file)")

    args = parser.parse_args()

    # Validate mutually exclusive options
    if args.zip_only and args.loose_only:
        print("ERROR: Cannot use both --zip-only and --loose-only flags")
        return 1

    # SECURITY: Prefer stdin or environment variable over command-line
    if args.api_key:
        api_key = args.api_key
        print("WARNING: API key passed via command-line is visible in process listings. "
              "Consider using stdin instead.", file=sys.stderr)
    elif not sys.stdin.isatty():
        # Read from stdin if piped
        api_key = sys.stdin.read().strip()
    else:
        # Try environment variable
        api_key = os.environ.get("PINECONE_ASSISTANT_API_KEY", "")

    if not api_key:
        print("ERROR: API key required via --api-key, stdin, or PINECONE_ASSISTANT_API_KEY env var")
        return 1

    # Validate API key format
    if not api_key.startswith("pcsk_"):
        print("ERROR: API key must start with 'pcsk_'")
        return 1

    print("Pinecone Assistant File Upload")
    print("=" * 40)

    success = upload_files_to_assistant(
        api_key,
        args.assistant_name,
        args.use_uspto_metadata,
        zip_only=args.zip_only,
        loose_only=args.loose_only
    )
    
    if success:
        print("\n✓ Upload process completed successfully!")
        print("\nNext steps:")
        print("1. Wait a few minutes for document processing to complete")
        print("2. Test the assistant with a sample query")
        print("3. Configure the MCP server environment variables")
        return 0
    else:
        print("\n✗ Upload process failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())