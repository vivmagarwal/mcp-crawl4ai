#!/usr/bin/env python3
"""
Example: Crawling a login-protected website
This example shows how to use the MCP Crawl4AI server to crawl protected content
"""

import asyncio
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server import mcp, Crawl4AIContext
from types import SimpleNamespace
from crawl4ai import AsyncWebCrawler, BrowserConfig

async def test_authenticated_crawl():
    """Test crawling a login-protected website"""
    
    # Initialize crawler
    browser_config = BrowserConfig(headless=False, verbose=True)  # headless=False to see the login process
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.__aenter__()
    
    try:
        # Create mock context
        mock_ctx = SimpleNamespace()
        mock_ctx.request_context = SimpleNamespace()
        mock_ctx.request_context.lifespan_context = Crawl4AIContext(crawler=crawler)
        
        # Import the crawl_with_auth tool
        from server import crawl_with_auth
        
        print("Testing authenticated crawl of TOK Newsletter Archive...")
        print("-" * 50)
        
        # Crawl the protected TOK newsletter archive
        result = await crawl_with_auth(
            mock_ctx,
            url="https://theoryofknowledge.net/tok-resources/tok-newsletter-archive/",
            username="tokdepartment@uwcdilijan.am",
            password="Trfz998afds#",
            wait_after_login=7000,  # Wait 7 seconds after login
            content_selector=".content-area"  # Wait for main content area
        )
        
        # Parse and display results
        result_data = json.loads(result)
        
        if result_data["success"]:
            print("✅ Authentication successful!")
            print(f"Title: {result_data.get('title', 'N/A')}")
            print(f"Content Length: {result_data.get('content_length', 0)} characters")
            print(f"Content ID: {result_data.get('content_id', 'N/A')}")
            print(f"Screenshot Taken: {result_data.get('screenshot_taken', False)}")
            
            # Now retrieve the full content
            from server import get_crawled_content
            
            full_content = await get_crawled_content(
                mock_ctx,
                content_id=result_data["content_id"]
            )
            
            content_data = json.loads(full_content)
            if content_data["success"]:
                print("\nExtracted Content Preview:")
                print("-" * 50)
                print(content_data["markdown"][:500] + "...")
                
                # Save to file
                output_file = Path("tok_newsletter_archive.md")
                output_file.write_text(content_data["markdown"])
                print(f"\n✅ Full content saved to: {output_file}")
        else:
            print(f"❌ Authentication failed: {result_data.get('error', 'Unknown error')}")
            if 'tip' in result_data:
                print(f"Tip: {result_data['tip']}")
    
    finally:
        await crawler.__aexit__(None, None, None)
        print("\nCrawler closed.")

async def test_simple_auth():
    """Test basic authentication with crawl_url"""
    
    # Initialize crawler
    browser_config = BrowserConfig(headless=True, verbose=False)
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.__aenter__()
    
    try:
        # Create mock context
        mock_ctx = SimpleNamespace()
        mock_ctx.request_context = SimpleNamespace()
        mock_ctx.request_context.lifespan_context = Crawl4AIContext(crawler=crawler)
        
        # Import the standard crawl_url tool
        from server import crawl_url
        
        print("\nTesting crawl_url with authentication...")
        print("-" * 50)
        
        # Use the standard crawl_url with authentication parameters
        result = await crawl_url(
            mock_ctx,
            url="https://theoryofknowledge.net/tok-resources/tok-newsletter-archive/",
            username="tokdepartment@uwcdilijan.am",
            password="Trfz998afds#",
            screenshot=True,
            wait_for=".content-area"
        )
        
        result_data = json.loads(result)
        
        if result_data["success"]:
            print("✅ Crawl with auth successful!")
            print(f"Content ID: {result_data.get('content_id', 'N/A')}")
            print(f"Title: {result_data.get('title', 'N/A')}")
        else:
            print(f"❌ Crawl failed: {result_data.get('error', 'Unknown error')}")
            
    finally:
        await crawler.__aexit__(None, None, None)

if __name__ == "__main__":
    print("=" * 50)
    print("MCP Crawl4AI Authentication Example")
    print("=" * 50)
    
    # Run the authenticated crawl test
    asyncio.run(test_authenticated_crawl())
    
    # Also test the basic crawl_url with auth
    asyncio.run(test_simple_auth())