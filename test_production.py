#!/usr/bin/env python3
"""
Production Readiness Test Suite for MCP Crawl4AI
Tests all major functionality to ensure production quality
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Any

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from server import (
    mcp, Crawl4AIContext,
    crawl_url, batch_crawl, deep_crawl,
    extract_structured_data, extract_with_llm,
    crawl_with_auth, crawl_with_filter,
    extract_links, get_crawled_content,
    list_crawled_content, crawl_dynamic_content,
    crawl_with_js_execution
)
from crawl4ai import AsyncWebCrawler, BrowserConfig

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def log_test(name: str, status: str, details: str = ""):
    """Log test results"""
    symbol = "✅" if status == "passed" else "❌" if status == "failed" else "⚠️"
    print(f"{symbol} {name}: {details if details else status}")
    
    if status == "passed":
        test_results["passed"].append(name)
    elif status == "failed":
        test_results["failed"].append((name, details))
    else:
        test_results["warnings"].append((name, details))

async def create_test_context():
    """Create a test context with crawler"""
    browser_config = BrowserConfig(headless=True, verbose=False)
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.__aenter__()
    
    mock_ctx = SimpleNamespace()
    mock_ctx.request_context = SimpleNamespace()
    mock_ctx.request_context.lifespan_context = Crawl4AIContext(crawler=crawler)
    
    return mock_ctx, crawler

# Test 1: Basic Crawling
async def test_basic_crawl():
    """Test basic URL crawling"""
    print("\n📝 Testing Basic Crawling...")
    
    try:
        ctx, crawler = await create_test_context()
        
        result = await crawl_url(
            ctx,
            url="https://example.com",
            bypass_cache=True
        )
        
        data = json.loads(result)
        
        if data["success"] and data.get("content_id"):
            log_test("Basic Crawl", "passed", f"Content ID: {data['content_id']}")
        else:
            log_test("Basic Crawl", "failed", data.get("error", "Unknown error"))
            
        await crawler.__aexit__(None, None, None)
        
    except Exception as e:
        log_test("Basic Crawl", "failed", str(e))

# Test 2: Authentication
async def test_authentication():
    """Test crawling with authentication"""
    print("\n🔐 Testing Authentication...")
    
    try:
        ctx, crawler = await create_test_context()
        
        # Test with TOK website
        result = await crawl_with_auth(
            ctx,
            url="https://theoryofknowledge.net/tok-resources/tok-newsletter-archive/",
            username="tokdepartment@uwcdilijan.am",
            password="Trfz998afds#",
            wait_after_login=7000,
            content_selector=".content-area"
        )
        
        data = json.loads(result)
        
        if data["success"] and data.get("authenticated"):
            log_test("Authentication", "passed", "Successfully logged in and crawled")
        else:
            log_test("Authentication", "failed", data.get("error", "Login failed"))
            
        await crawler.__aexit__(None, None, None)
        
    except Exception as e:
        log_test("Authentication", "failed", str(e))

# Test 3: Batch Crawling
async def test_batch_crawl():
    """Test parallel URL crawling"""
    print("\n🔄 Testing Batch Crawling...")
    
    try:
        ctx, crawler = await create_test_context()
        
        urls = [
            "https://example.com",
            "https://example.org",
            "https://example.net"
        ]
        
        result = await batch_crawl(
            ctx,
            urls=urls,
            max_concurrent=2,
            bypass_cache=True
        )
        
        data = json.loads(result)
        
        if data["success"] and data["successful"] > 0:
            log_test("Batch Crawl", "passed", 
                    f"Crawled {data['successful']}/{data['total_urls']} URLs")
        else:
            log_test("Batch Crawl", "failed", "No URLs crawled successfully")
            
        await crawler.__aexit__(None, None, None)
        
    except Exception as e:
        log_test("Batch Crawl", "failed", str(e))

# Test 4: Structured Data Extraction
async def test_structured_extraction():
    """Test CSS-based data extraction"""
    print("\n📊 Testing Structured Extraction...")
    
    try:
        ctx, crawler = await create_test_context()
        
        schema = {
            "baseSelector": "body",
            "fields": {
                "title": {"selector": "h1", "type": "text"},
                "paragraphs": {"selector": "p", "type": "text", "multiple": True}
            }
        }
        
        result = await extract_structured_data(
            ctx,
            url="https://example.com",
            schema=schema,
            extraction_type="json_css"
        )
        
        data = json.loads(result)
        
        if data["success"] and data.get("extracted_data"):
            log_test("Structured Extraction", "passed", "Data extracted successfully")
        else:
            log_test("Structured Extraction", "warning", 
                    "Extraction completed but may have issues")
            
        await crawler.__aexit__(None, None, None)
        
    except Exception as e:
        log_test("Structured Extraction", "failed", str(e))

# Test 5: Link Extraction
async def test_link_extraction():
    """Test link extraction functionality"""
    print("\n🔗 Testing Link Extraction...")
    
    try:
        ctx, crawler = await create_test_context()
        
        result = await extract_links(
            ctx,
            url="https://example.com",
            preview_links=False
        )
        
        data = json.loads(result)
        
        if data["success"]:
            total_links = data.get("total_internal", 0) + data.get("total_external", 0)
            log_test("Link Extraction", "passed", f"Found {total_links} links")
        else:
            log_test("Link Extraction", "failed", data.get("error", "Unknown error"))
            
        await crawler.__aexit__(None, None, None)
        
    except Exception as e:
        log_test("Link Extraction", "failed", str(e))

# Test 6: Content Filtering
async def test_content_filtering():
    """Test content filtering capabilities"""
    print("\n🔍 Testing Content Filtering...")
    
    try:
        ctx, crawler = await create_test_context()
        
        result = await crawl_with_filter(
            ctx,
            url="https://example.com",
            filter_type="pruning",
            min_word_threshold=50
        )
        
        data = json.loads(result)
        
        if data["success"]:
            log_test("Content Filtering", "passed", "Pruning filter applied")
        else:
            log_test("Content Filtering", "failed", data.get("error", "Filter failed"))
            
        await crawler.__aexit__(None, None, None)
        
    except Exception as e:
        log_test("Content Filtering", "failed", str(e))

# Test 7: Error Handling
async def test_error_handling():
    """Test error handling for invalid inputs"""
    print("\n⚠️ Testing Error Handling...")
    
    try:
        ctx, crawler = await create_test_context()
        
        # Test with invalid URL
        result = await crawl_url(
            ctx,
            url="not-a-valid-url",
            bypass_cache=True
        )
        
        data = json.loads(result)
        
        if not data["success"] and "error" in data:
            log_test("Error Handling", "passed", "Invalid URL handled gracefully")
        else:
            log_test("Error Handling", "failed", "Should have failed with invalid URL")
            
        await crawler.__aexit__(None, None, None)
        
    except Exception as e:
        log_test("Error Handling", "passed", "Exception handled properly")

# Test 8: Content Caching
async def test_content_caching():
    """Test content storage and retrieval"""
    print("\n💾 Testing Content Caching...")
    
    try:
        ctx, crawler = await create_test_context()
        
        # First crawl
        result1 = await crawl_url(
            ctx,
            url="https://example.com",
            bypass_cache=True
        )
        
        data1 = json.loads(result1)
        
        if data1["success"] and data1.get("content_id"):
            # Try to retrieve the content
            result2 = await get_crawled_content(
                ctx,
                content_id=data1["content_id"]
            )
            
            data2 = json.loads(result2)
            
            if data2["success"] and data2["content_id"] == data1["content_id"]:
                log_test("Content Caching", "passed", "Content stored and retrieved")
            else:
                log_test("Content Caching", "failed", "Could not retrieve content")
        else:
            log_test("Content Caching", "failed", "Initial crawl failed")
            
        await crawler.__aexit__(None, None, None)
        
    except Exception as e:
        log_test("Content Caching", "failed", str(e))

# Test 9: Performance Check
async def test_performance():
    """Test crawling performance"""
    print("\n⚡ Testing Performance...")
    
    try:
        ctx, crawler = await create_test_context()
        
        start_time = time.time()
        
        result = await crawl_url(
            ctx,
            url="https://example.com",
            bypass_cache=True,
            screenshot=False
        )
        
        elapsed = time.time() - start_time
        
        data = json.loads(result)
        
        if data["success"] and elapsed < 10:  # Should complete within 10 seconds
            log_test("Performance", "passed", f"Crawled in {elapsed:.2f}s")
        elif data["success"]:
            log_test("Performance", "warning", f"Slow: {elapsed:.2f}s")
        else:
            log_test("Performance", "failed", "Crawl failed")
            
        await crawler.__aexit__(None, None, None)
        
    except Exception as e:
        log_test("Performance", "failed", str(e))

# Test 10: Memory Management
async def test_memory_management():
    """Test memory management with multiple operations"""
    print("\n💾 Testing Memory Management...")
    
    try:
        ctx, crawler = await create_test_context()
        
        # Perform multiple operations
        content_ids = []
        
        for i in range(3):
            result = await crawl_url(
                ctx,
                url=f"https://example.{['com', 'org', 'net'][i]}",
                bypass_cache=True
            )
            
            data = json.loads(result)
            if data["success"]:
                content_ids.append(data.get("content_id"))
        
        # List all content
        result = await list_crawled_content(ctx)
        data = json.loads(result)
        
        if data["success"] and data["total_items"] >= len(content_ids):
            log_test("Memory Management", "passed", 
                    f"Managed {data['total_items']} items in memory")
        else:
            log_test("Memory Management", "warning", "Some items may be missing")
            
        await crawler.__aexit__(None, None, None)
        
    except Exception as e:
        log_test("Memory Management", "failed", str(e))

# Main test runner
async def run_all_tests():
    """Run all production readiness tests"""
    print("=" * 60)
    print("🚀 MCP Crawl4AI Production Readiness Tests")
    print("=" * 60)
    
    tests = [
        test_basic_crawl,
        test_authentication,
        test_batch_crawl,
        test_structured_extraction,
        test_link_extraction,
        test_content_filtering,
        test_error_handling,
        test_content_caching,
        test_performance,
        test_memory_management
    ]
    
    for test in tests:
        await test()
    
    # Summary
    print("\n" + "=" * 60)
    print("📈 Test Summary")
    print("=" * 60)
    print(f"✅ Passed: {len(test_results['passed'])}")
    print(f"❌ Failed: {len(test_results['failed'])}")
    print(f"⚠️  Warnings: {len(test_results['warnings'])}")
    
    if test_results["failed"]:
        print("\n❌ Failed Tests:")
        for name, error in test_results["failed"]:
            print(f"  - {name}: {error}")
    
    if test_results["warnings"]:
        print("\n⚠️  Warnings:")
        for name, warning in test_results["warnings"]:
            print(f"  - {name}: {warning}")
    
    # Production readiness assessment
    print("\n" + "=" * 60)
    total_tests = len(tests)
    passed = len(test_results["passed"])
    
    if passed == total_tests:
        print("🎉 PRODUCTION READY - All tests passed!")
    elif passed >= total_tests * 0.8:
        print("✅ MOSTLY READY - Most critical tests passed")
        print("   Fix remaining issues before production deployment")
    else:
        print("❌ NOT READY - Too many failures")
        print("   Address critical issues before deployment")
    
    print("=" * 60)
    
    return test_results

if __name__ == "__main__":
    asyncio.run(run_all_tests())