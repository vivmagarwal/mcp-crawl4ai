#!/usr/bin/env python3
"""
MCP Crawl4AI Installation Verification Script
Run this after installation to verify everything is working correctly
"""

import sys
import subprocess
import json
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.10 or higher"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 10:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Requires 3.10+")
        return False

def check_imports():
    """Check if all required packages can be imported"""
    packages = {
        'mcp': 'MCP SDK',
        'crawl4ai': 'Crawl4AI',
        'httpx': 'HTTPX',
        'dotenv': 'Python-dotenv'
    }
    
    all_ok = True
    for package, name in packages.items():
        try:
            __import__(package)
            print(f"✅ {name} - Installed")
        except ImportError:
            print(f"❌ {name} - Not installed")
            all_ok = False
    
    return all_ok

def check_playwright():
    """Check if Playwright browsers are installed"""
    try:
        result = subprocess.run(
            ['playwright', 'list'],
            capture_output=True,
            text=True
        )
        if 'chromium' in result.stdout.lower():
            print("✅ Playwright Chromium - Installed")
            return True
        else:
            print("❌ Playwright Chromium - Not installed")
            print("  Run: playwright install chromium")
            return False
    except Exception as e:
        print(f"❌ Playwright - Error: {e}")
        return False

def check_server():
    """Check if the server can be imported"""
    try:
        # Just check if server module can be imported
        import server
        print(f"✅ MCP Server - Module loaded successfully")
        return True
    except Exception as e:
        print(f"❌ MCP Server - Error: {e}")
        return False

def check_claude_config():
    """Check Claude Desktop configuration"""
    config_paths = [
        Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
        Path.home() / ".config" / "Claude" / "claude_desktop_config.json",
        Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json" if sys.platform == "win32" else None
    ]
    
    config_found = False
    mcp_configured = False
    
    for path in config_paths:
        if path and path.exists():
            config_found = True
            try:
                with open(path) as f:
                    config = json.load(f)
                    if "mcpServers" in config and "mcp-crawl4ai" in config["mcpServers"]:
                        mcp_configured = True
                        print(f"✅ Claude Config - MCP server configured at {path}")
                    else:
                        print(f"⚠️  Claude Config - Found at {path} but mcp-crawl4ai not configured")
            except Exception as e:
                print(f"⚠️  Claude Config - Error reading {path}: {e}")
            break
    
    if not config_found:
        print("ℹ️  Claude Config - Not found (Claude Desktop may not be installed)")
    
    return config_found and mcp_configured

def main():
    print("=" * 50)
    print("MCP Crawl4AI Installation Verification")
    print("=" * 50)
    print()
    
    print("Checking Requirements:")
    print("-" * 30)
    
    checks = {
        "Python Version": check_python_version(),
        "Required Packages": check_imports(),
        "Playwright Browsers": check_playwright(),
        "MCP Server": check_server(),
    }
    
    print()
    print("Checking Configuration:")
    print("-" * 30)
    claude_ok = check_claude_config()
    
    print()
    print("=" * 50)
    
    all_critical_ok = all(checks.values())
    
    if all_critical_ok:
        print("✅ All critical components installed successfully!")
        if not claude_ok:
            print("⚠️  Claude Desktop configuration needs to be set up")
            print()
            print("Add this to your Claude config file:")
            print(json.dumps({
                "mcpServers": {
                    "mcp-crawl4ai": {
                        "command": "python3",
                        "args": [str(Path(__file__).parent / "server.py")],
                        "env": {
                            "OPENAI_API_KEY": "your-key-here"
                        }
                    }
                }
            }, indent=2))
    else:
        print("❌ Some components are missing. Please install them:")
        if not checks["Required Packages"]:
            print("  Run: pip install -e .")
        if not checks["Playwright Browsers"]:
            print("  Run: playwright install chromium")
    
    print("=" * 50)

if __name__ == "__main__":
    import os
    main()