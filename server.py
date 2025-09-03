#!/usr/bin/env python3
"""
MCP Server for Crawl4AI - Comprehensive web crawling capabilities
Provides full access to Crawl4AI's powerful features through MCP protocol
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import tempfile

from mcp.server.fastmcp import FastMCP

from crawl4ai import (
    AsyncWebCrawler, 
    BrowserConfig, 
    CrawlerRunConfig,
    CacheMode,
    LLMExtractionStrategy,
    JsonCssExtractionStrategy,
    CosineStrategy,
    LLMContentFilter,
    BM25ContentFilter,
    PruningContentFilter,
    DefaultMarkdownGenerator,
)

try:
    from crawl4ai.deep_crawling import (
        BFSDeepCrawlStrategy,
        DFSDeepCrawlStrategy,
        BestFirstCrawlingStrategy,
        URLPatternFilter,
        DomainFilter,
        ContentTypeFilter,
        KeywordRelevanceScorer,
    )
    DEEP_CRAWLING_AVAILABLE = True
except ImportError:
    DEEP_CRAWLING_AVAILABLE = False

# Global storage for crawled data
CRAWLED_DATA: Dict[str, Any] = {}
CACHE_DIR = Path(tempfile.gettempdir()) / "mcp-crawl4ai-cache"
CACHE_DIR.mkdir(exist_ok=True)

# Global crawler instance
CRAWLER_INSTANCE: Optional[AsyncWebCrawler] = None

async def get_crawler() -> AsyncWebCrawler:
    """Get or create the global crawler instance"""
    global CRAWLER_INSTANCE
    
    if CRAWLER_INSTANCE is None:
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            browser_type="chromium",
        )
        CRAWLER_INSTANCE = AsyncWebCrawler(config=browser_config)
        await CRAWLER_INSTANCE.__aenter__()
    
    return CRAWLER_INSTANCE

async def cleanup_crawler():
    """Clean up the global crawler instance"""
    global CRAWLER_INSTANCE
    if CRAWLER_INSTANCE is not None:
        try:
            await CRAWLER_INSTANCE.__aexit__(None, None, None)
        except:
            pass
        CRAWLER_INSTANCE = None

# Initialize FastMCP server
mcp = FastMCP("mcp-crawl4ai")

# Helper functions
def generate_content_hash(content: str) -> str:
    """Generate a hash for content to use as identifier"""
    return hashlib.md5(content.encode()).hexdigest()[:12]

def save_crawled_content(url: str, content: Any) -> str:
    """Save crawled content and return its ID"""
    content_id = generate_content_hash(str(content))
    CRAWLED_DATA[content_id] = {
        "url": url,
        "content": content,
        "timestamp": asyncio.get_event_loop().time()
    }
    
    # Also save to disk cache
    cache_file = CACHE_DIR / f"{content_id}.json"
    with open(cache_file, "w") as f:
        json.dump(CRAWLED_DATA[content_id], f, indent=2, default=str)
    
    return content_id

# Core crawling tools

@mcp.tool()
async def crawl_url(
    url: str,
    wait_for: Optional[str] = None,
    screenshot: bool = False,
    pdf: bool = False,
    remove_overlay: bool = True,
    bypass_cache: bool = False,
    word_count_threshold: int = 10,
    exclude_external_links: bool = False,
    exclude_social_media_links: bool = True,
    username: Optional[str] = None,
    password: Optional[str] = None,
    login_url: Optional[str] = None,
    username_selector: str = "input[type='text'], input[type='email'], input[name*='user'], input[name*='email']",
    password_selector: str = "input[type='password']",
    submit_selector: str = "button[type='submit'], input[type='submit'], button:has-text('Login'), button:has-text('Sign in')"
) -> str:
    """
    Crawl a single URL with comprehensive options and authentication support
    
    Args:
        url: The URL to crawl
        wait_for: CSS selector to wait for before extracting content
        screenshot: Whether to take a screenshot
        pdf: Whether to generate a PDF
        remove_overlay: Whether to remove popups/overlays
        bypass_cache: Whether to bypass cache
        word_count_threshold: Minimum word count threshold
        exclude_external_links: Exclude external links from results
        exclude_social_media_links: Exclude social media links
        username: Username for authentication
        password: Password for authentication
        login_url: URL of the login page (if different from target URL)
        username_selector: CSS selector for username field
        password_selector: CSS selector for password field
        submit_selector: CSS selector for submit button
    
    Returns:
        JSON with crawled content, metadata, and content ID
    """
    try:
        crawler = await get_crawler()
        
        # Prepare JS code for authentication if credentials provided
        js_code = None
        if username and password:
            js_code = f"""
            (async () => {{
                // Wait for login form
                await new Promise(r => setTimeout(r, 1000));
                
                // Find and fill username
                const userInput = document.querySelector('{username_selector}');
                if (userInput) {{
                    userInput.value = '{username}';
                    userInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
                
                // Find and fill password
                const passInput = document.querySelector('{password_selector}');
                if (passInput) {{
                    passInput.value = '{password}';
                    passInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
                
                // Submit form
                await new Promise(r => setTimeout(r, 500));
                const submitBtn = document.querySelector('{submit_selector}');
                if (submitBtn) {{
                    submitBtn.click();
                }} else {{
                    // Try to submit the form directly
                    const form = userInput ? userInput.closest('form') : null;
                    if (form) form.submit();
                }}
                
                // Wait for navigation
                await new Promise(r => setTimeout(r, 3000));
            }})();
            """
        
        # Navigate to login URL first if provided
        if login_url and username and password:
            # First, navigate to login page and authenticate
            login_config = CrawlerRunConfig(
                js_code=js_code,
                wait_for=wait_for or "body",
                remove_overlay_elements=remove_overlay,
                cache_mode=CacheMode.BYPASS if bypass_cache else CacheMode.ENABLED,
                word_count_threshold=word_count_threshold,
                exclude_external_links=exclude_external_links,
                exclude_social_media_links=exclude_social_media_links,
                screenshot=False,
                pdf=False,
                verbose=True
            )
            
            await crawler.arun(
                url=login_url,
                config=login_config
            )
            
            # Now navigate to the actual URL
            js_code = None  # Don't run auth code again
        
        # Configure the crawl
        config = CrawlerRunConfig(
            js_code=js_code,
            wait_for=wait_for or "body",
            remove_overlay_elements=remove_overlay,
            cache_mode=CacheMode.BYPASS if bypass_cache else CacheMode.ENABLED,
            word_count_threshold=word_count_threshold,
            exclude_external_links=exclude_external_links,
            exclude_social_media_links=exclude_social_media_links,
            screenshot=screenshot,
            pdf=pdf,
            verbose=True,
            markdown_generator=DefaultMarkdownGenerator()
        )
        
        # Perform the crawl
        result = await crawler.arun(
            url=url,
            config=config
        )
        
        if result.success:
            # Save the crawled content
            content_id = save_crawled_content(url, result)
            
            response = {
                "success": True,
                "url": url,
                "content_id": content_id,
                "title": result.metadata.get("title", ""),
                "description": result.metadata.get("description", ""),
                "markdown": result.markdown[:1000] + "..." if len(result.markdown) > 1000 else result.markdown,
                "word_count": len(result.markdown.split()),
                "links_count": len(result.links.get("internal", [])) + len(result.links.get("external", [])),
                "metadata": result.metadata
            }
            
            if screenshot and result.screenshot_base64:
                response["screenshot"] = result.screenshot_base64[:100] + "..."
            
            if pdf and result.pdf_base64:
                response["pdf"] = result.pdf_base64[:100] + "..."
            
            return json.dumps(response, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": result.error_message or "Crawl failed"
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

@mcp.tool()
async def crawl_with_auth(
    url: str,
    username: str,
    password: str,
    login_url: Optional[str] = None,
    wait_after_login: int = 5000,
    content_selector: Optional[str] = None
) -> str:
    """
    Specialized tool for crawling login-protected websites
    
    Args:
        url: Target URL to crawl after login
        username: Login username
        password: Login password
        login_url: URL of login page (uses target URL if not specified)
        wait_after_login: Time to wait after login (ms)
        content_selector: CSS selector to wait for after login
        
    Returns:
        JSON with crawled content from authenticated session
    """
    try:
        crawler = await get_crawler()
        
        # Use login_url if provided, otherwise use the main URL
        auth_url = login_url or url
        
        # JavaScript to perform login
        login_js = f"""
        (async () => {{
            console.log('Starting authentication...');
            
            // Wait for page to load
            await new Promise(r => setTimeout(r, 2000));
            
            // Try multiple selectors for username field
            const userSelectors = [
                'input[type="email"]',
                'input[type="text"]',
                'input[name*="user"]',
                'input[name*="email"]',
                'input[id*="user"]',
                'input[id*="email"]',
                '#username',
                '#email'
            ];
            
            let userInput = null;
            for (const selector of userSelectors) {{
                userInput = document.querySelector(selector);
                if (userInput) break;
            }}
            
            if (userInput) {{
                userInput.focus();
                userInput.value = '{username}';
                userInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                userInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                console.log('Username entered');
            }}
            
            // Find password field
            const passInput = document.querySelector('input[type="password"]');
            if (passInput) {{
                passInput.focus();
                passInput.value = '{password}';
                passInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                passInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                console.log('Password entered');
            }}
            
            // Wait a bit
            await new Promise(r => setTimeout(r, 1000));
            
            // Try multiple selectors for submit button
            const submitSelectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Login")',
                'button:has-text("Sign in")',
                'button:has-text("Submit")',
                '.login-button',
                '#login-button'
            ];
            
            let submitted = false;
            for (const selector of submitSelectors) {{
                const submitBtn = document.querySelector(selector);
                if (submitBtn) {{
                    submitBtn.click();
                    submitted = true;
                    console.log('Form submitted via button');
                    break;
                }}
            }}
            
            // If no button found, try submitting the form
            if (!submitted && userInput) {{
                const form = userInput.closest('form');
                if (form) {{
                    form.submit();
                    console.log('Form submitted directly');
                }}
            }}
            
            // Wait for navigation
            await new Promise(r => setTimeout(r, {wait_after_login}));
            console.log('Authentication complete');
        }})();
        """
        
        # First crawl with authentication
        auth_config = CrawlerRunConfig(
            js_code=login_js,
            wait_for=content_selector or "body",
            remove_overlay_elements=True,
            cache_mode=CacheMode.BYPASS,
            verbose=True
        )
        
        # Perform login
        if auth_url != url:
            await crawler.arun(url=auth_url, config=auth_config)
            
            # Then navigate to target URL
            config = CrawlerRunConfig(
                wait_for=content_selector or "body",
                remove_overlay_elements=True,
                cache_mode=CacheMode.BYPASS,
                verbose=True,
                markdown_generator=DefaultMarkdownGenerator()
            )
            result = await crawler.arun(url=url, config=config)
        else:
            # Login and crawl in one go
            result = await crawler.arun(url=auth_url, config=auth_config)
        
        if result.success:
            content_id = save_crawled_content(url, result)
            
            return json.dumps({
                "success": True,
                "url": url,
                "content_id": content_id,
                "authenticated": True,
                "title": result.metadata.get("title", ""),
                "markdown": result.markdown[:1000] + "..." if len(result.markdown) > 1000 else result.markdown,
                "word_count": len(result.markdown.split()),
                "metadata": result.metadata
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": result.error_message or "Authentication or crawl failed"
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

@mcp.tool()
async def batch_crawl(
    urls: List[str],
    max_concurrent: int = 5,
    bypass_cache: bool = False,
    word_count_threshold: int = 10
) -> str:
    """
    Crawl multiple URLs in parallel
    
    Args:
        urls: List of URLs to crawl
        max_concurrent: Maximum concurrent crawls
        bypass_cache: Whether to bypass cache
        word_count_threshold: Minimum word count threshold
        
    Returns:
        JSON with results for all URLs
    """
    try:
        crawler = await get_crawler()
        
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS if bypass_cache else CacheMode.ENABLED,
            word_count_threshold=word_count_threshold,
            verbose=False,
            markdown_generator=DefaultMarkdownGenerator()
        )
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def crawl_single(url: str) -> Dict[str, Any]:
            async with semaphore:
                try:
                    result = await crawler.arun(url=url, config=config)
                    
                    if result.success:
                        content_id = save_crawled_content(url, result)
                        return {
                            "url": url,
                            "success": True,
                            "content_id": content_id,
                            "title": result.metadata.get("title", ""),
                            "word_count": len(result.markdown.split())
                        }
                    else:
                        return {
                            "url": url,
                            "success": False,
                            "error": result.error_message or "Crawl failed"
                        }
                except Exception as e:
                    return {
                        "url": url,
                        "success": False,
                        "error": str(e)
                    }
        
        # Crawl all URLs concurrently
        tasks = [crawl_single(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        # Summary statistics
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        
        return json.dumps({
            "success": True,
            "total_urls": len(urls),
            "successful": successful,
            "failed": failed,
            "results": results
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

@mcp.tool()
async def deep_crawl(
    start_url: str,
    max_depth: int = 3,
    max_pages: int = 100,
    strategy: str = "bfs",
    allowed_domains: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    include_patterns: Optional[List[str]] = None,
    keyword_focus: Optional[List[str]] = None
) -> str:
    """
    Perform deep crawling starting from a URL
    
    Args:
        start_url: Starting URL for deep crawl
        max_depth: Maximum depth to crawl
        max_pages: Maximum number of pages to crawl
        strategy: Crawl strategy - "bfs", "dfs", or "best_first"
        allowed_domains: List of allowed domains
        exclude_patterns: URL patterns to exclude
        include_patterns: URL patterns to include
        keyword_focus: Keywords for relevance-based crawling
        
    Returns:
        JSON with deep crawl results
    """
    if not DEEP_CRAWLING_AVAILABLE:
        return json.dumps({
            "success": False,
            "error": "Deep crawling features not available. Please install crawl4ai with deep crawling support."
        }, indent=2)
    
    try:
        crawler = await get_crawler()
        
        # Set up filters
        filters = []
        if allowed_domains:
            filters.append(DomainFilter(allowed_domains=allowed_domains))
        if exclude_patterns:
            filters.append(URLPatternFilter(exclude_patterns=exclude_patterns))
        if include_patterns:
            filters.append(URLPatternFilter(include_patterns=include_patterns))
        
        # Choose strategy
        if strategy == "dfs":
            crawl_strategy = DFSDeepCrawlStrategy(
                max_depth=max_depth,
                max_pages=max_pages,
                url_filters=filters
            )
        elif strategy == "best_first" and keyword_focus:
            scorer = KeywordRelevanceScorer(keywords=keyword_focus)
            crawl_strategy = BestFirstCrawlingStrategy(
                max_depth=max_depth,
                max_pages=max_pages,
                url_filters=filters,
                scorer=scorer
            )
        else:  # Default to BFS
            crawl_strategy = BFSDeepCrawlStrategy(
                max_depth=max_depth,
                max_pages=max_pages,
                url_filters=filters
            )
        
        config = CrawlerRunConfig(
            verbose=True,
            cache_mode=CacheMode.ENABLED,
            markdown_generator=DefaultMarkdownGenerator()
        )
        
        # Perform deep crawl
        pages_crawled = []
        async for result in crawl_strategy.crawl(crawler, start_url, config):
            if result.success:
                content_id = save_crawled_content(result.url, result)
                pages_crawled.append({
                    "url": result.url,
                    "content_id": content_id,
                    "title": result.metadata.get("title", ""),
                    "depth": result.metadata.get("depth", 0),
                    "word_count": len(result.markdown.split())
                })
        
        return json.dumps({
            "success": True,
            "start_url": start_url,
            "pages_crawled": len(pages_crawled),
            "max_depth_reached": max(p.get("depth", 0) for p in pages_crawled) if pages_crawled else 0,
            "results": pages_crawled
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

@mcp.tool()
async def extract_structured_data(
    url: str,
    schema: Dict[str, Any],
    extraction_type: str = "json_css",
    multiple: bool = False
) -> str:
    """
    Extract structured data from a webpage using CSS or XPath selectors
    
    Args:
        url: URL to extract data from
        schema: Extraction schema mapping fields to selectors
        extraction_type: Type of extraction - "json_css" or "regex"
        multiple: Whether to extract multiple items
        
    Returns:
        JSON with extracted structured data
    """
    try:
        crawler = await get_crawler()
        
        if extraction_type == "json_css":
            extraction_strategy = JsonCssExtractionStrategy(
                schema=schema,
                multiple=multiple
            )
        else:
            return json.dumps({
                "success": False,
                "error": f"Unsupported extraction type: {extraction_type}"
            }, indent=2)
        
        config = CrawlerRunConfig(
            extraction_strategy=extraction_strategy,
            verbose=True
        )
        
        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            content_id = save_crawled_content(url, result)
            
            return json.dumps({
                "success": True,
                "url": url,
                "content_id": content_id,
                "extracted_data": result.extracted_structured_data,
                "metadata": result.metadata
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": result.error_message or "Extraction failed"
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

@mcp.tool()
async def extract_with_llm(
    url: str,
    instruction: str,
    model: str = "gpt-4o-mini",
    api_key: Optional[str] = None,
    schema: Optional[Dict[str, Any]] = None,
    temperature: float = 0.7
) -> str:
    """
    Extract data from a webpage using LLM
    
    Args:
        url: URL to extract data from
        instruction: Instruction for the LLM
        model: LLM model to use
        api_key: API key for the LLM service
        schema: Optional schema for structured extraction
        temperature: LLM temperature parameter
        
    Returns:
        JSON with LLM-extracted data
    """
    try:
        crawler = await get_crawler()
        
        # Use environment variable if API key not provided
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            return json.dumps({
                "success": False,
                "error": "OpenAI API key required. Set OPENAI_API_KEY environment variable or provide api_key parameter."
            }, indent=2)
        
        extraction_strategy = LLMExtractionStrategy(
            provider="openai",
            api_key=api_key,
            model=model,
            instruction=instruction,
            schema=schema,
            temperature=temperature
        )
        
        config = CrawlerRunConfig(
            extraction_strategy=extraction_strategy,
            verbose=True
        )
        
        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            content_id = save_crawled_content(url, result)
            
            return json.dumps({
                "success": True,
                "url": url,
                "content_id": content_id,
                "extracted_data": result.extracted_structured_data or result.extracted_content,
                "metadata": result.metadata
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": result.error_message or "LLM extraction failed"
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

@mcp.tool()
async def crawl_with_filter(
    url: str,
    filter_type: str = "bm25",
    query: Optional[str] = None,
    min_word_threshold: int = 50,
    threshold: float = 0.3
) -> str:
    """
    Crawl a URL with content filtering
    
    Args:
        url: URL to crawl
        filter_type: Type of filter - "bm25", "pruning", or "llm"
        query: Query for relevance filtering (for BM25)
        min_word_threshold: Minimum word threshold for pruning
        threshold: Relevance threshold
        
    Returns:
        JSON with filtered crawl results
    """
    try:
        crawler = await get_crawler()
        
        if filter_type == "bm25" and query:
            content_filter = BM25ContentFilter(query=query, threshold=threshold)
        elif filter_type == "pruning":
            content_filter = PruningContentFilter(threshold=min_word_threshold)
        elif filter_type == "llm":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return json.dumps({
                    "success": False,
                    "error": "OpenAI API key required for LLM filtering"
                }, indent=2)
            content_filter = LLMContentFilter(
                provider="openai",
                api_key=api_key,
                model="gpt-4o-mini"
            )
        else:
            content_filter = None
        
        config = CrawlerRunConfig(
            content_filter=content_filter,
            verbose=True,
            markdown_generator=DefaultMarkdownGenerator()
        )
        
        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            content_id = save_crawled_content(url, result)
            
            return json.dumps({
                "success": True,
                "url": url,
                "content_id": content_id,
                "filter_type": filter_type,
                "markdown_length": len(result.markdown),
                "filtered_content": result.markdown[:1000] + "..." if len(result.markdown) > 1000 else result.markdown,
                "metadata": result.metadata
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": result.error_message or "Filtered crawl failed"
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

@mcp.tool()
async def extract_links(
    url: str,
    preview_links: bool = False,
    max_preview: int = 10
) -> str:
    """
    Extract and optionally preview links from a webpage
    
    Args:
        url: URL to extract links from
        preview_links: Whether to generate link previews
        max_preview: Maximum number of links to preview
        
    Returns:
        JSON with extracted links and optional previews
    """
    try:
        crawler = await get_crawler()
        
        config = CrawlerRunConfig(
            verbose=True,
            exclude_external_links=False,
            exclude_social_media_links=False
        )
        
        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            all_links = []
            
            # Combine internal and external links
            for link_type in ["internal", "external"]:
                if link_type in result.links:
                    for link in result.links[link_type]:
                        all_links.append({
                            "url": link,
                            "type": link_type
                        })
            
            # Preview links if requested
            previews = []
            if preview_links and all_links:
                preview_count = min(max_preview, len(all_links))
                for i in range(preview_count):
                    link_url = all_links[i]["url"]
                    try:
                        preview_result = await crawler.arun(
                            url=link_url,
                            config=CrawlerRunConfig(
                                word_count_threshold=10,
                                verbose=False
                            )
                        )
                        if preview_result.success:
                            previews.append({
                                "url": link_url,
                                "title": preview_result.metadata.get("title", ""),
                                "description": preview_result.metadata.get("description", "")
                            })
                    except:
                        pass
            
            content_id = save_crawled_content(url, result)
            
            response = {
                "success": True,
                "url": url,
                "content_id": content_id,
                "total_links": len(all_links),
                "internal_links": len([l for l in all_links if l["type"] == "internal"]),
                "external_links": len([l for l in all_links if l["type"] == "external"]),
                "links": all_links[:50]  # Limit to first 50 links in response
            }
            
            if previews:
                response["previews"] = previews
            
            return json.dumps(response, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": result.error_message or "Link extraction failed"
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

@mcp.tool()
async def get_crawled_content(
    content_id: str,
    include_html: bool = False,
    include_screenshot: bool = False
) -> str:
    """
    Retrieve previously crawled content by ID
    
    Args:
        content_id: ID of the crawled content
        include_html: Whether to include raw HTML
        include_screenshot: Whether to include screenshot data
        
    Returns:
        JSON with the crawled content
    """
    try:
        if content_id in CRAWLED_DATA:
            data = CRAWLED_DATA[content_id]
            result = data["content"]
            
            response = {
                "success": True,
                "content_id": content_id,
                "url": data["url"],
                "markdown": result.markdown,
                "metadata": result.metadata,
                "links": result.links
            }
            
            if include_html and result.cleaned_html:
                response["html"] = result.cleaned_html
            
            if include_screenshot and result.screenshot_base64:
                response["screenshot"] = result.screenshot_base64
            
            return json.dumps(response, indent=2)
        else:
            # Try to load from cache
            cache_file = CACHE_DIR / f"{content_id}.json"
            if cache_file.exists():
                with open(cache_file, "r") as f:
                    data = json.load(f)
                return json.dumps({
                    "success": True,
                    "content_id": content_id,
                    "url": data["url"],
                    "note": "Loaded from cache (limited data available)"
                }, indent=2)
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Content with ID {content_id} not found"
                }, indent=2)
                
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

@mcp.tool()
async def list_crawled_content() -> str:
    """
    List all crawled content in the current session
    
    Returns:
        JSON with list of all crawled content
    """
    try:
        contents = []
        
        # From memory
        for content_id, data in CRAWLED_DATA.items():
            contents.append({
                "content_id": content_id,
                "url": data["url"],
                "timestamp": data["timestamp"],
                "source": "memory"
            })
        
        # From cache files
        for cache_file in CACHE_DIR.glob("*.json"):
            content_id = cache_file.stem
            if content_id not in CRAWLED_DATA:
                try:
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                    contents.append({
                        "content_id": content_id,
                        "url": data.get("url", "unknown"),
                        "timestamp": data.get("timestamp", 0),
                        "source": "cache"
                    })
                except:
                    pass
        
        return json.dumps({
            "success": True,
            "total_items": len(contents),
            "contents": contents
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

@mcp.tool()
async def crawl_with_js_execution(
    url: str,
    js_code: Optional[str] = None,
    wait_for_js: Optional[str] = None,
    js_timeout: int = 30000
) -> str:
    """
    Crawl a page with JavaScript execution
    
    Args:
        url: URL to crawl
        js_code: JavaScript code to execute on the page
        wait_for_js: JavaScript condition to wait for
        js_timeout: Timeout for JavaScript execution in ms
        
    Returns:
        JSON with crawl results after JS execution
    """
    try:
        crawler = await get_crawler()
        
        config = CrawlerRunConfig(
            js_code=js_code,
            wait_for=wait_for_js or "body",
            page_timeout=js_timeout,
            verbose=True,
            markdown_generator=DefaultMarkdownGenerator()
        )
        
        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            content_id = save_crawled_content(url, result)
            
            response = {
                "success": True,
                "url": url,
                "content_id": content_id,
                "js_executed": bool(js_code),
                "markdown": result.markdown[:1000] + "..." if len(result.markdown) > 1000 else result.markdown,
                "metadata": result.metadata
            }
            
            # If JS was executed and returned a value
            if js_code and "js_result" in result.__dict__:
                response["js_result"] = str(result.js_result)
            
            return json.dumps(response, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": result.error_message or "JS execution crawl failed"
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

@mcp.tool()
async def crawl_dynamic_content(
    url: str,
    scroll: bool = True,
    scroll_delay: int = 1000,
    max_scrolls: int = 10,
    wait_for_selector: Optional[str] = None
) -> str:
    """
    Crawl dynamically loaded content with scrolling
    
    Args:
        url: URL to crawl
        scroll: Whether to scroll the page
        scroll_delay: Delay between scrolls in ms
        max_scrolls: Maximum number of scrolls
        wait_for_selector: CSS selector to wait for
        
    Returns:
        JSON with dynamically loaded content
    """
    try:
        crawler = await get_crawler()
        
        # JavaScript to handle scrolling
        scroll_js = f"""
        (async () => {{
            let scrollCount = 0;
            const maxScrolls = {max_scrolls};
            const scrollDelay = {scroll_delay};
            
            while (scrollCount < maxScrolls) {{
                const prevHeight = document.body.scrollHeight;
                window.scrollTo(0, document.body.scrollHeight);
                
                await new Promise(r => setTimeout(r, scrollDelay));
                
                const newHeight = document.body.scrollHeight;
                if (newHeight === prevHeight) {{
                    // No new content loaded
                    break;
                }}
                
                scrollCount++;
            }}
            
            return scrollCount;
        }})();
        """ if scroll else None
        
        config = CrawlerRunConfig(
            js_code=scroll_js,
            wait_for=wait_for_selector or "body",
            verbose=True,
            markdown_generator=DefaultMarkdownGenerator()
        )
        
        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            content_id = save_crawled_content(url, result)
            
            return json.dumps({
                "success": True,
                "url": url,
                "content_id": content_id,
                "scrolling_enabled": scroll,
                "markdown_length": len(result.markdown),
                "content": result.markdown[:2000] + "..." if len(result.markdown) > 2000 else result.markdown,
                "metadata": result.metadata
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": result.error_message or "Dynamic crawl failed"
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

if __name__ == "__main__":
    # Run the MCP server
    import sys
    
    # Check if running with stdio or SSE transport
    transport = os.getenv("TRANSPORT", "stdio")
    
    if transport == "sse":
        asyncio.run(mcp.run_sse_async())
    else:
        asyncio.run(mcp.run_stdio_async())