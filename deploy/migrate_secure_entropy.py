#!/usr/bin/env python3
"""
Migration script for Pinecone Assistant MCP secure storage.

This script migrates API keys encrypted with the old hardcoded entropy
to the new cryptographically secure random entropy.

SECURITY UPDATE: Critical fix for hardcoded entropy vulnerability (C-1)
- Old: Hardcoded entropy "pinecone_assistant_entropy_v1" (publicly visible in GitHub)
- New: Cryptographically secure 256-bit random entropy (secrets.token_bytes(32))
"""

import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from config.secure_storage import SecureStorage, decrypt_data


def migrate_to_secure_entropy():
    """Migrate encrypted API keys from hardcoded to secure random entropy."""
    print("=" * 70)
    print("🔐 Pinecone Assistant MCP - Entropy Migration Tool")
    print("=" * 70)
    print()
    print("This tool migrates your API key from the old hardcoded entropy")
    print("to cryptographically secure random entropy.")
    print()
    print("⚠️  IMPORTANT:")
    print("   - This fixes a CRITICAL security vulnerability (C-1)")
    print("   - Old entropy was hardcoded and publicly visible in GitHub")
    print("   - New entropy is 256-bit cryptographically secure random")
    print()

    storage = SecureStorage()

    # Check if encrypted key file exists
    if not storage.storage_file.exists():
        print("❌ No encrypted key file found")
        print(f"   Expected location: {storage.storage_file}")
        print()
        print("Nothing to migrate. When you store a key, it will use secure entropy automatically.")
        return True

    # Check if entropy file already exists
    if storage.entropy_file.exists():
        print("✓ Secure entropy file already exists")
        print(f"  Entropy file: {storage.entropy_file}")
        print()
        print("Your API key is already using secure random entropy.")
        print("No migration needed!")
        return True

    print("📋 Migration Steps:")
    print("   1. Decrypt API key with old hardcoded entropy")
    print("   2. Generate new cryptographically secure random entropy")
    print("   3. Re-encrypt API key with new secure entropy")
    print("   4. Store new entropy file")
    print()

    # Step 1: Try to decrypt with old hardcoded entropy
    print("[1/4] Decrypting with old hardcoded entropy...")
    try:
        encrypted_data = storage.storage_file.read_bytes()
        decrypted_data = decrypt_data(encrypted_data)  # Uses old hardcoded entropy
        api_key = decrypted_data.decode('utf-8')

        # Validate decrypted key
        if not api_key.startswith("pcsk_"):
            print("❌ Decrypted data is not a valid Pinecone API key")
            print("   Migration failed")
            return False

        print(f"✓ Successfully decrypted API key: {api_key[:10]}...")

    except Exception as e:
        print(f"❌ Failed to decrypt with old entropy: {e}")
        print()
        print("Possible reasons:")
        print("  - Key was already migrated (entropy file might be missing)")
        print("  - Encrypted file is corrupted")
        print("  - File was encrypted by different user/machine")
        print()
        print("You may need to re-enter your API key manually.")
        return False

    # Step 2-4: Re-encrypt with new secure entropy (storage.store_api_key does this)
    print("[2/4] Generating cryptographically secure random entropy...")
    print("[3/4] Re-encrypting API key with new entropy...")
    print("[4/4] Storing new entropy file...")

    try:
        # Backup old file
        backup_file = storage.storage_file.with_suffix('.backup')
        storage.storage_file.rename(backup_file)
        print(f"✓ Backed up old encrypted file to: {backup_file}")

        # Store with new secure entropy
        success = storage.store_api_key(api_key)

        if success:
            print("✓ Successfully re-encrypted with secure random entropy")
            print()
            print("=" * 70)
            print("🎉 MIGRATION SUCCESSFUL!")
            print("=" * 70)
            print()
            print("Your API key is now encrypted with:")
            print(f"  ✓ Cryptographically secure 256-bit random entropy")
            print(f"  ✓ Encrypted key: {storage.storage_file}")
            print(f"  ✓ Entropy file: {storage.entropy_file}")
            print()
            print("⚠️  IMPORTANT - Backup both files:")
            print(f"     {storage.storage_file}")
            print(f"     {storage.entropy_file}")
            print()
            print("   Without the entropy file, you cannot decrypt your API key!")
            print()
            print(f"Old encrypted file backed up to: {backup_file}")
            print("You can safely delete the backup after verifying the migration worked.")
            print()

            # Verify it works
            test_key = storage.get_api_key()
            if test_key == api_key:
                print("✓ Verification: Successfully retrieved and decrypted API key")
                return True
            else:
                print("⚠️  Verification failed: Retrieved key doesn't match")
                print("   Restoring from backup...")
                storage.storage_file.unlink()
                storage.entropy_file.unlink()
                backup_file.rename(storage.storage_file)
                return False
        else:
            print("❌ Failed to re-encrypt with new entropy")
            print("   Restoring from backup...")
            backup_file.rename(storage.storage_file)
            return False

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print()
        print("Attempting to restore from backup...")
        try:
            if backup_file.exists():
                backup_file.rename(storage.storage_file)
                print("✓ Restored from backup")
        except Exception as restore_error:
            print(f"❌ Failed to restore: {restore_error}")
            print(f"   Your backup is at: {backup_file}")

        return False


def main():
    """Main entry point."""
    try:
        if sys.platform != "win32":
            print("⚠️  This tool only works on Windows (requires DPAPI)")
            print("   On Linux/Mac, API keys are stored in environment variables")
            return 1

        success = migrate_to_secure_entropy()

        if success:
            print()
            print("Next steps:")
            print("1. Test that your MCP server still works")
            print("2. Backup both the encrypted key and entropy files")
            print("3. Delete the .backup file after verification")
            return 0
        else:
            print()
            print("Migration failed. Your old encrypted key is still usable.")
            print("Contact support if you need assistance.")
            return 1

    except KeyboardInterrupt:
        print()
        print("❌ Migration cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
