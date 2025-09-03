#!/usr/bin/env python3
"""
Simple test to verify MCP Crawl4AI works
"""

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))

from server import crawl_url, Crawl4AIContext
from crawl4ai import AsyncWebCrawler, BrowserConfig

async def test_simple():
    """Test basic crawling functionality"""
    print("Testing MCP Crawl4AI Server...")
    
    # Create context
    browser_config = BrowserConfig(headless=True, verbose=False)
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.__aenter__()
    
    try:
        # Create mock context
        mock_ctx = SimpleNamespace()
        mock_ctx.request_context = SimpleNamespace()
        mock_ctx.request_context.lifespan_context = Crawl4AIContext(crawler=crawler)
        
        # Test crawl
        print("Crawling example.com...")
        result = await crawl_url(
            mock_ctx,
            url="https://example.com",
            bypass_cache=True
        )
        
        data = json.loads(result)
        
        if data["success"]:
            print(f"✅ Success! Content ID: {data.get('content_id')}")
            print(f"   Title: {data.get('title')}")
            print(f"   Content length: {data.get('markdown_length', 0)} chars")
        else:
            print(f"❌ Failed: {data.get('error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await crawler.__aexit__(None, None, None)
        print("Test complete.")

if __name__ == "__main__":
    asyncio.run(test_simple())