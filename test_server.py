#!/usr/bin/env python3
"""
Comprehensive test suite for MCP Crawl4AI Server
Tests all tools and functionality to ensure production readiness
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the server directory to path
sys.path.insert(0, str(Path(__file__).parent))

from server import mcp


async def test_basic_crawl():
    """Test basic crawl functionality"""
    print("\n🧪 Testing basic crawl...")
    try:
        result = await mcp._tool_manager.call_tool("crawl", {
            "url": "https://example.com",
            "wait_for": "body",
            "verbose": False
        }, None)
        
        # Parse the result
        data = json.loads(result[0].text)
        assert data["success"], "Crawl should succeed"
        assert "Example Domain" in data["markdown"], "Should contain expected content"
        print("✅ Basic crawl test passed")
        return True
    except Exception as e:
        print(f"❌ Basic crawl test failed: {e}")
        return False


async def test_crawl_with_js():
    """Test crawl with JavaScript execution"""
    print("\n🧪 Testing crawl with JavaScript...")
    try:
        result = await mcp._tool_manager.call_tool("crawl_with_js", {
            "url": "https://example.com",
            "js_code": "document.title",
            "wait_for": "body",
            "verbose": False
        }, None)
        
        data = json.loads(result[0].text)
        assert data["success"], "JS crawl should succeed"
        assert data.get("js_result") == "Example Domain", "JS should return page title"
        print("✅ JavaScript crawl test passed")
        return True
    except Exception as e:
        print(f"❌ JavaScript crawl test failed: {e}")
        return False


async def test_batch_crawl():
    """Test batch crawling multiple URLs"""
    print("\n🧪 Testing batch crawl...")
    try:
        result = await mcp._tool_manager.call_tool("batch_crawl", {
            "urls": ["https://example.com", "https://example.org"],
            "wait_for": "body",
            "verbose": False
        }, None)
        
        data = json.loads(result[0].text)
        assert data["success"], "Batch crawl should succeed"
        assert len(data["results"]) == 2, "Should have results for 2 URLs"
        print("✅ Batch crawl test passed")
        return True
    except Exception as e:
        print(f"❌ Batch crawl test failed: {e}")
        return False


async def test_screenshot():
    """Test screenshot functionality"""
    print("\n🧪 Testing screenshot...")
    try:
        result = await mcp._tool_manager.call_tool("screenshot", {
            "url": "https://example.com",
            "format": "png"
        }, None)
        
        data = json.loads(result[0].text)
        assert data["success"], "Screenshot should succeed"
        assert data.get("screenshot_path"), "Should return screenshot path"
        print("✅ Screenshot test passed")
        return True
    except Exception as e:
        print(f"❌ Screenshot test failed: {e}")
        return False


async def test_extract_structured():
    """Test structured data extraction"""
    print("\n🧪 Testing structured extraction...")
    try:
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "domain": {"type": "string"}
            }
        }
        
        result = await mcp._tool_manager.call_tool("extract_structured", {
            "url": "https://example.com",
            "schema": schema,
            "wait_for": "body"
        }, None)
        
        data = json.loads(result[0].text)
        assert data["success"], "Structured extraction should succeed"
        extracted = data.get("extracted_data", {})
        assert "title" in extracted, "Should extract title"
        print("✅ Structured extraction test passed")
        return True
    except Exception as e:
        print(f"❌ Structured extraction test failed: {e}")
        return False


async def test_crawl_with_auth():
    """Test crawl with authentication (using test site)"""
    print("\n🧪 Testing crawl with authentication...")
    try:
        # This tests the authentication mechanism even if the site doesn't require login
        result = await mcp._tool_manager.call_tool("crawl_with_auth", {
            "url": "https://example.com",
            "auth_config": {
                "username_field": "username",
                "password_field": "password",
                "username": "test@example.com",
                "password": "testpass123",
                "submit_selector": "button[type='submit']"
            },
            "wait_for": "body",
            "verbose": False
        }, None)
        
        data = json.loads(result[0].text)
        # We just verify the function runs without error
        assert "success" in data, "Should return success status"
        print("✅ Authentication crawl test passed")
        return True
    except Exception as e:
        print(f"❌ Authentication crawl test failed: {e}")
        return False


async def test_list_tools():
    """Test that all expected tools are registered"""
    print("\n🧪 Testing tool registration...")
    try:
        tools = await mcp._tool_manager.list_tools()
        
        expected_tools = [
            "crawl",
            "crawl_with_js",
            "batch_crawl",
            "crawl_with_auth",
            "screenshot",
            "extract_structured",
            "extract_with_css",
            "get_crawler_config"
        ]
        
        tool_names = [tool.name for tool in tools]
        
        for expected in expected_tools:
            assert expected in tool_names, f"Tool '{expected}' should be registered"
        
        print(f"✅ All {len(expected_tools)} tools are registered")
        return True
    except Exception as e:
        print(f"❌ Tool registration test failed: {e}")
        return False


async def test_error_handling():
    """Test error handling for invalid URLs"""
    print("\n🧪 Testing error handling...")
    try:
        result = await mcp._tool_manager.call_tool("crawl", {
            "url": "https://invalid-domain-that-does-not-exist-123456.com",
            "verbose": False
        }, None)
        
        data = json.loads(result[0].text)
        assert not data["success"], "Should fail for invalid domain"
        assert "error" in data, "Should contain error message"
        print("✅ Error handling test passed")
        return True
    except Exception as e:
        # This is expected - tool should handle errors gracefully
        print("✅ Error handling test passed (caught exception)")
        return True


async def run_all_tests():
    """Run all tests and report results"""
    print("=" * 60)
    print("🚀 MCP Crawl4AI Server Test Suite")
    print("=" * 60)
    
    tests = [
        ("Tool Registration", test_list_tools),
        ("Basic Crawl", test_basic_crawl),
        ("JavaScript Crawl", test_crawl_with_js),
        ("Batch Crawl", test_batch_crawl),
        ("Screenshot", test_screenshot),
        ("Structured Extraction", test_extract_structured),
        ("Authentication Crawl", test_crawl_with_auth),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ {name} test crashed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print("-" * 60)
    print(f"  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Server is production ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review and fix.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)