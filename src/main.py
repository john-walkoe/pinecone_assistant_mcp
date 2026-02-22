"""Main entry point for USPTO Pinecone Assistant MCP server."""

import sys
from pathlib import Path

def main() -> None:
    """Main entry point."""
    # Import here to avoid issues when run as script
    try:
        from .server import run_server
    except ImportError:
        # When run as script, use absolute import
        src_dir = Path(__file__).parent
        sys.path.insert(0, str(src_dir))
        from server import run_server
    
    run_server()

if __name__ == "__main__":
    main()