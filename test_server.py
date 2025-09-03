#!/usr/bin/env python3
"""
Test script for MCP Crawl4AI Server
Run this to verify the server is working correctly
"""

import asyncio
import json
from server import mcp, Crawl4AIContext
from pathlib import Path
import tempfile

async def test_basic_crawl():
    """Test basic crawling functionality"""
    print("Testing basic crawl...")
    
    # Create a mock context
    from types import SimpleNamespace
    from crawl4ai import AsyncWebCrawler, BrowserConfig
    
    # Initialize crawler for testing
    browser_config = BrowserConfig(headless=True, verbose=False)
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.__aenter__()
    
    try:
        # Create test context
        mock_ctx = SimpleNamespace()
        mock_ctx.request_context = SimpleNamespace()
        mock_ctx.request_context.lifespan_context = Crawl4AIContext(crawler=crawler)
        
        # Test crawl_url tool
        from server import crawl_url
        result = await crawl_url(
            mock_ctx,
            url="https://www.example.com",
            bypass_cache=True
        )
        
        result_data = json.loads(result)
        
        if result_data["success"]:
            print("✅ Basic crawl test passed!")
            print(f"  - Content ID: {result_data.get('content_id', 'N/A')}")
            print(f"  - Title: {result_data.get('title', 'N/A')}")
            print(f"  - Content length: {result_data.get('markdown_length', 0)} chars")
        else:
            print(f"❌ Basic crawl test failed: {result_data.get('error', 'Unknown error')}")
            
    finally:
        await crawler.__aexit__(None, None, None)

async def test_structured_extraction():
    """Test structured data extraction"""
    print("\nTesting structured extraction...")
    
    from types import SimpleNamespace
    from crawl4ai import AsyncWebCrawler, BrowserConfig
    
    browser_config = BrowserConfig(headless=True, verbose=False)
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.__aenter__()
    
    try:
        mock_ctx = SimpleNamespace()
        mock_ctx.request_context = SimpleNamespace()
        mock_ctx.request_context.lifespan_context = Crawl4AIContext(crawler=crawler)
        
        # Test extract_structured_data tool
        from server import extract_structured_data
        
        schema = {
            "baseSelector": "body",
            "fields": {
                "title": {"selector": "h1", "type": "text"},
                "paragraphs": {"selector": "p", "type": "text", "multiple": True}
            }
        }
        
        result = await extract_structured_data(
            mock_ctx,
            url="https://www.example.com",
            schema=schema,
            extraction_type="json_css"
        )
        
        result_data = json.loads(result)
        
        if result_data["success"]:
            print("✅ Structured extraction test passed!")
            print(f"  - Extraction type: {result_data.get('extraction_type', 'N/A')}")
            print(f"  - Extracted fields: {list(result_data.get('extracted_data', {}).keys())}")
        else:
            print(f"❌ Structured extraction test failed: {result_data.get('error', 'Unknown error')}")
            
    finally:
        await crawler.__aexit__(None, None, None)

async def test_link_extraction():
    """Test link extraction functionality"""
    print("\nTesting link extraction...")
    
    from types import SimpleNamespace
    from crawl4ai import AsyncWebCrawler, BrowserConfig
    
    browser_config = BrowserConfig(headless=True, verbose=False)
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.__aenter__()
    
    try:
        mock_ctx = SimpleNamespace()
        mock_ctx.request_context = SimpleNamespace()
        mock_ctx.request_context.lifespan_context = Crawl4AIContext(crawler=crawler)
        
        # Test extract_links tool
        from server import extract_links
        
        result = await extract_links(
            mock_ctx,
            url="https://www.example.com",
            preview_links=False
        )
        
        result_data = json.loads(result)
        
        if result_data["success"]:
            print("✅ Link extraction test passed!")
            print(f"  - Internal links: {result_data.get('total_internal', 0)}")
            print(f"  - External links: {result_data.get('total_external', 0)}")
        else:
            print(f"❌ Link extraction test failed: {result_data.get('error', 'Unknown error')}")
            
    finally:
        await crawler.__aexit__(None, None, None)

async def test_batch_crawl():
    """Test batch crawling functionality"""
    print("\nTesting batch crawl...")
    
    from types import SimpleNamespace
    from crawl4ai import AsyncWebCrawler, BrowserConfig
    
    browser_config = BrowserConfig(headless=True, verbose=False)
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.__aenter__()
    
    try:
        mock_ctx = SimpleNamespace()
        mock_ctx.request_context = SimpleNamespace()
        mock_ctx.request_context.lifespan_context = Crawl4AIContext(crawler=crawler)
        
        # Test batch_crawl tool
        from server import batch_crawl
        
        result = await batch_crawl(
            mock_ctx,
            urls=["https://www.example.com", "https://www.example.org"],
            max_concurrent=2,
            bypass_cache=True
        )
        
        result_data = json.loads(result)
        
        if result_data["success"]:
            print("✅ Batch crawl test passed!")
            print(f"  - Total URLs: {result_data.get('total_urls', 0)}")
            print(f"  - Successful: {result_data.get('successful', 0)}")
            print(f"  - Failed: {result_data.get('failed', 0)}")
        else:
            print(f"❌ Batch crawl test failed: {result_data.get('error', 'Unknown error')}")
            
    finally:
        await crawler.__aexit__(None, None, None)

async def main():
    """Run all tests"""
    print("=" * 50)
    print("MCP Crawl4AI Server Test Suite")
    print("=" * 50)
    
    try:
        # Run tests
        await test_basic_crawl()
        await test_structured_extraction()
        await test_link_extraction()
        await test_batch_crawl()
        
        print("\n" + "=" * 50)
        print("All tests completed!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())