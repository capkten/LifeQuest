"""
Start LifeQuest API server and MCP server together.

Usage:
    python start_all.py                     # default: API on 8000, MCP on 3001
    python start_all.py --api-port 8000 --mcp-port 3001

The MCP server connects to the same database as the API server.
Claude Code / Hermes connect to MCP at http://<host>:3001/sse
"""

import argparse
import os
import signal
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Start LifeQuest API + MCP servers")
    parser.add_argument("--api-port", type=int, default=8000, help="API server port")
    parser.add_argument("--mcp-port", type=int, default=3001, help="MCP server port")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    args = parser.parse_args()

    backend_dir = os.path.dirname(os.path.abspath(__file__))

    procs = []

    def shutdown(sig=None, frame=None):
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        for p in procs:
            try:
                p.wait(timeout=5)
            except Exception:
                p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Start FastAPI server
    api_cmd = [
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--host", args.host, "--port", str(args.api_port),
    ]
    print(f"[start_all] API server: http://{args.host}:{args.api_port}")
    procs.append(subprocess.Popen(api_cmd, cwd=backend_dir))

    # Start MCP SSE server
    mcp_cmd = [
        sys.executable, "mcp_server.py",
        "--transport", "sse",
        "--host", args.host,
        "--port", str(args.mcp_port),
    ]
    print(f"[start_all] MCP server: http://{args.host}:{args.mcp_port}/sse")
    procs.append(subprocess.Popen(mcp_cmd, cwd=backend_dir))

    print(f"\n[start_all] Both servers started. Press Ctrl+C to stop.\n")

    # Wait for any process to exit
    try:
        while True:
            for p in procs:
                ret = p.poll()
                if ret is not None:
                    print(f"[start_all] A process exited with code {ret}")
                    shutdown()
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
