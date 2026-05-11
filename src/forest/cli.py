#!/usr/bin/env python3
"""
Forest CLI - Personal book library manager
"""

import argparse
import sys
import webbrowser
import threading
import time


def main():
    parser = argparse.ArgumentParser(
        description="Forest - Personal book library manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  forest                    Start the server and open browser
  forest --port 8080        Use a different port
  forest --no-browser       Start without opening browser
        """
    )
    
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="forest 0.1.0"
    )
    
    args = parser.parse_args()
    
    # Print banner
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ███████╗ ██████╗ ██████╗ ███████╗███████╗████████╗     ║
║   ██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔════╝╚══██╔══╝     ║
║   █████╗  ██║   ██║██████╔╝█████╗  ███████╗   ██║        ║
║   ██╔══╝  ██║   ██║██╔══██╗██╔══╝  ╚════██║   ██║        ║
║   ██║     ╚██████╔╝██║  ██║███████╗███████║   ██║        ║
║   ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝   ╚═╝        ║
║                                                           ║
║   Personal book library manager                           ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    url = f"http://{args.host}:{args.port}"
    print(f"Starting server at {url}")
    print("Press Ctrl+C to stop.\n")
    
    # Open browser after a short delay
    if not args.no_browser:
        def open_browser():
            time.sleep(1.5)
            webbrowser.open(url)
        
        threading.Thread(target=open_browser, daemon=True).start()
    
    # Import uvicorn here to avoid slow startup for --help
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn not installed. Run: pip install uvicorn[standard]")
        sys.exit(1)
    
    # Run the server
    try:
        if args.reload:
            uvicorn.run(
                "forest.main:app",
                host=args.host,
                port=args.port,
                reload=True,
                log_level="info",
            )
        else:
            from forest.main import app
            uvicorn.run(
                app,
                host=args.host,
                port=args.port,
                log_level="info",
            )
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()
