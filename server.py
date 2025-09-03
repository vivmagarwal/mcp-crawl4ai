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
from dataclasses import dataclass
from pathlib import Path
import hashlib
import tempfile

from mcp.server.fastmcp import FastMCP, Context
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from crawl4ai import (
    AsyncWebCrawler, 
    BrowserConfig, 
    CrawlerRunConfig,
    CacheMode,
    MemoryAdaptiveDispatcher,
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

# Data storage context
@dataclass
class Crawl4AIContext:
    """Context for the Crawl4AI MCP server"""
    crawler: Optional[AsyncWebCrawler] = None
    cache_dir: Path = None
    crawled_data: Dict[str, Any] = None

    def __post_init__(self):
        self.crawled_data = {}
        self.cache_dir = Path(tempfile.gettempdir()) / "mcp-crawl4ai-cache"
        self.cache_dir.mkdir(exist_ok=True)

@asynccontextmanager
async def crawl4ai_lifespan(server: FastMCP) -> AsyncIterator[Crawl4AIContext]:
    """
    Manages the Crawl4AI crawler lifecycle
    """
    # Create browser configuration
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        browser_type="chromium",  # Can be "chromium", "firefox", or "webkit"
    )
    
    # Initialize the crawler
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.__aenter__()
    
    context = Crawl4AIContext(crawler=crawler)
    
    try:
        yield context
    finally:
        # Clean up crawler
        await crawler.__aexit__(None, None, None)

# Initialize FastMCP server
mcp = FastMCP("mcp-crawl4ai")

# Helper functions
def generate_content_hash(content: str) -> str:
    """Generate a hash for content to use as identifier"""
    return hashlib.md5(content.encode()).hexdigest()[:12]

def save_crawled_content(context: Crawl4AIContext, url: str, content: Any) -> str:
    """Save crawled content and return its ID"""
    content_id = generate_content_hash(str(content))
    context.crawled_data[content_id] = {
        "url": url,
        "content": content,
        "timestamp": asyncio.get_event_loop().time()
    }
    
    # Also save to disk cache
    cache_file = context.cache_dir / f"{content_id}.json"
    with open(cache_file, "w") as f:
        json.dump(context.crawled_data[content_id], f, indent=2, default=str)
    
    return content_id

# Core crawling tools

@mcp.tool()
async def crawl_url(
    ctx: Context, 
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
    username_selector: str = 'input[type="text"], input[type="email"], input[name*="user"], input[name*="email"]',
    password_selector: str = 'input[type="password"]',
    submit_selector: str = 'button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Sign in")'
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
        crawler = ctx.request_context.lifespan_context.crawler
        
        # Handle authentication if credentials provided
        js_script = None
        if username and password:
            # Create login script
            js_script = f"""
            async function login() {{
                // If we need to navigate to login page first
                const currentUrl = window.location.href;
                const loginUrl = '{login_url or url}';
                
                if (loginUrl !== currentUrl && !currentUrl.includes('login')) {{
                    window.location.href = loginUrl;
                    await new Promise(resolve => setTimeout(resolve, 3000));
                }}
                
                // Find and fill username field
                const usernameField = document.querySelector('{username_selector}');
                if (usernameField) {{
                    usernameField.value = '{username}';
                    usernameField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
                
                // Find and fill password field
                const passwordField = document.querySelector('{password_selector}');
                if (passwordField) {{
                    passwordField.value = '{password}';
                    passwordField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
                
                // Submit the form
                await new Promise(resolve => setTimeout(resolve, 500));
                const submitButton = document.querySelector('{submit_selector}');
                if (submitButton) {{
                    submitButton.click();
                }} else {{
                    // Try to find form and submit it
                    const form = passwordField ? passwordField.closest('form') : document.querySelector('form');
                    if (form) form.submit();
                }}
                
                // Wait for navigation
                await new Promise(resolve => setTimeout(resolve, 5000));
            }}
            
            await login();
            """
        
        # Configure the crawl
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS if bypass_cache else CacheMode.ENABLED,
            wait_for=wait_for,
            screenshot=screenshot,
            pdf=pdf,
            remove_overlay_elements=remove_overlay,
            word_count_threshold=word_count_threshold,
            exclude_external_links=exclude_external_links,
            exclude_social_media_links=exclude_social_media_links,
            js_code=js_script,  # Changed from js_script to js_code
        )
        
        # Perform the crawl
        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            # Save the content
            content_id = save_crawled_content(
                ctx.request_context.lifespan_context,
                url,
                result
            )
            
            response = {
                "success": True,
                "content_id": content_id,
                "url": url,
                "title": result.metadata.get("title", ""),
                "markdown": result.markdown[:1000] + "..." if len(result.markdown) > 1000 else result.markdown,
                "html_length": len(result.html) if result.html else 0,
                "markdown_length": len(result.markdown) if result.markdown else 0,
                "media": result.media if result.media else {},
                "links": {
                    "internal": len(result.links.get("internal", [])),
                    "external": len(result.links.get("external", []))
                },
                "metadata": result.metadata,
            }
            
            if screenshot and result.screenshot_data:
                response["screenshot_available"] = True
                
            if pdf and result.pdf_data:
                response["pdf_available"] = True
                
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
    ctx: Context,
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
        crawler = ctx.request_context.lifespan_context.crawler
        
        # Create enhanced login script
        js_script = f"""
        async function authenticateAndNavigate() {{
            // Navigate to login page if needed
            const targetUrl = '{url}';
            const loginPageUrl = '{login_url or url}';
            
            if (!window.location.href.includes('login') && loginPageUrl !== window.location.href) {{
                window.location.href = loginPageUrl;
                await new Promise(resolve => setTimeout(resolve, 3000));
            }}
            
            // Try multiple selector strategies for username
            const usernameSelectors = [
                'input[type="email"]',
                'input[type="text"][name*="user"]',
                'input[type="text"][name*="email"]',
                'input[name="username"]',
                'input[id*="user"]',
                '#username'
            ];
            
            let usernameField = null;
            for (const selector of usernameSelectors) {{
                usernameField = document.querySelector(selector);
                if (usernameField && usernameField.offsetParent !== null) break;
            }}
            
            if (usernameField) {{
                usernameField.focus();
                usernameField.value = '{username}';
                usernameField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                usernameField.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
            
            // Try multiple selector strategies for password
            const passwordField = document.querySelector('input[type="password"]');
            if (passwordField) {{
                await new Promise(resolve => setTimeout(resolve, 500));
                passwordField.focus();
                passwordField.value = '{password}';
                passwordField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                passwordField.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
            
            // Try multiple submit strategies
            await new Promise(resolve => setTimeout(resolve, 500));
            
            const submitSelectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:contains("Login")',
                'button:contains("Sign in")',
                'button:contains("Log in")',
                '.login-button',
                '#login-button'
            ];
            
            let submitted = false;
            for (const selector of submitSelectors) {{
                const button = document.querySelector(selector);
                if (button && button.offsetParent !== null) {{
                    button.click();
                    submitted = true;
                    break;
                }}
            }}
            
            if (!submitted && passwordField) {{
                const form = passwordField.closest('form');
                if (form) {{
                    form.submit();
                    submitted = true;
                }}
            }}
            
            // Wait for login to complete
            await new Promise(resolve => setTimeout(resolve, {wait_after_login}));
            
            // Navigate to target URL if different from current
            if (targetUrl !== loginPageUrl && !window.location.href.includes(targetUrl)) {{
                window.location.href = targetUrl;
                await new Promise(resolve => setTimeout(resolve, 3000));
            }}
        }}
        
        await authenticateAndNavigate();
        """
        
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=js_script,  # Changed from js_script to js_code
            wait_for=content_selector,
            word_count_threshold=10,
            screenshot=True  # Take screenshot to verify login worked
        )
        
        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            content_id = save_crawled_content(
                ctx.request_context.lifespan_context,
                url,
                result
            )
            
            return json.dumps({
                "success": True,
                "url": url,
                "authenticated": True,
                "content_id": content_id,
                "title": result.metadata.get("title", ""),
                "content_length": len(result.markdown) if result.markdown else 0,
                "screenshot_taken": bool(result.screenshot_data),
                "message": "Successfully crawled with authentication"
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": result.error_message or "Authentication crawl failed",
                "tip": "Check login credentials and selectors"
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

@mcp.tool()
async def batch_crawl(
    ctx: Context,
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
        crawler = ctx.request_context.lifespan_context.crawler
        
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS if bypass_cache else CacheMode.ENABLED,
            word_count_threshold=word_count_threshold,
        )
        
        # Create dispatcher for memory management
        dispatcher = MemoryAdaptiveDispatcher(
            memory_threshold_percent=70.0,
            check_interval=1.0,
            max_session_permit=max_concurrent
        )
        
        # Crawl all URLs
        results = await crawler.arun_many(
            urls=urls,
            config=config,
            dispatcher=dispatcher
        )
        
        crawl_results = []
        for result in results:
            if result.success:
                content_id = save_crawled_content(
                    ctx.request_context.lifespan_context,
                    result.url,
                    result
                )
                
                crawl_results.append({
                    "url": result.url,
                    "success": True,
                    "content_id": content_id,
                    "title": result.metadata.get("title", ""),
                    "content_length": len(result.markdown) if result.markdown else 0,
                })
            else:
                crawl_results.append({
                    "url": result.url,
                    "success": False,
                    "error": result.error_message
                })
        
        return json.dumps({
            "success": True,
            "total_urls": len(urls),
            "successful": sum(1 for r in crawl_results if r["success"]),
            "failed": sum(1 for r in crawl_results if not r["success"]),
            "results": crawl_results
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

async def simple_deep_crawl(ctx, start_url, max_depth, max_pages, allowed_domains=None, exclude_patterns=None, include_patterns=None):
    """Simple deep crawl implementation without advanced strategies"""
    crawler = ctx.request_context.lifespan_context.crawler
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=10,
    )
    
    crawled_urls = []
    visited = set()
    to_visit = [(start_url, 0)]
    
    while to_visit and len(crawled_urls) < max_pages:
        url, depth = to_visit.pop(0)
        
        if url in visited or depth > max_depth:
            continue
        
        # Apply domain filter
        if allowed_domains:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            if domain not in allowed_domains:
                continue
        
        visited.add(url)
        
        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            content_id = save_crawled_content(
                ctx.request_context.lifespan_context,
                url,
                result
            )
            
            crawled_urls.append({
                "url": url,
                "depth": depth,
                "content_id": content_id,
                "title": result.metadata.get("title", ""),
                "links_found": len(result.links.get("internal", []))
            })
            
            # Add internal links to queue
            for link in result.links.get("internal", []):
                link_url = link.get("href", "")
                if link_url and link_url not in visited:
                    to_visit.append((link_url, depth + 1))
    
    return json.dumps({
        "success": True,
        "start_url": start_url,
        "strategy": "simple_bfs",
        "pages_crawled": len(crawled_urls),
        "max_depth_reached": max(c["depth"] for c in crawled_urls) if crawled_urls else 0,
        "results": crawled_urls
    }, indent=2)

@mcp.tool()
async def deep_crawl(
    ctx: Context,
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
    try:
        if not DEEP_CRAWLING_AVAILABLE:
            # Simple fallback implementation without deep crawling strategies
            return await simple_deep_crawl(ctx, start_url, max_depth, max_pages, allowed_domains, exclude_patterns, include_patterns)
            
        crawler = ctx.request_context.lifespan_context.crawler
        
        # Select crawling strategy
        if strategy == "dfs":
            crawl_strategy = DFSDeepCrawlStrategy(
                max_depth=max_depth,
                max_pages=max_pages
            )
        elif strategy == "best_first" and keyword_focus:
            scorer = KeywordRelevanceScorer(keywords=keyword_focus)
            crawl_strategy = BestFirstCrawlingStrategy(
                scorer=scorer,
                max_depth=max_depth,
                max_pages=max_pages
            )
        else:  # Default to BFS
            crawl_strategy = BFSDeepCrawlStrategy(
                max_depth=max_depth,
                max_pages=max_pages
            )
        
        # Add filters
        filters = []
        if allowed_domains:
            filters.append(DomainFilter(allowed_domains=allowed_domains))
        if exclude_patterns:
            for pattern in exclude_patterns:
                filters.append(URLPatternFilter(exclude_patterns=[pattern]))
        if include_patterns:
            for pattern in include_patterns:
                filters.append(URLPatternFilter(include_patterns=[pattern]))
        
        if filters:
            for filter in filters:
                crawl_strategy.add_filter(filter)
        
        # Configure crawl
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=10,
        )
        
        # Start deep crawl
        crawled_urls = []
        visited = set()
        to_visit = [(start_url, 0)]
        
        while to_visit and len(crawled_urls) < max_pages:
            url, depth = to_visit.pop(0)
            
            if url in visited or depth > max_depth:
                continue
                
            visited.add(url)
            
            # Crawl the URL
            result = await crawler.arun(url=url, config=config)
            
            if result.success:
                content_id = save_crawled_content(
                    ctx.request_context.lifespan_context,
                    url,
                    result
                )
                
                crawled_urls.append({
                    "url": url,
                    "depth": depth,
                    "content_id": content_id,
                    "title": result.metadata.get("title", ""),
                    "links_found": len(result.links.get("internal", []))
                })
                
                # Add internal links to queue based on strategy
                for link in result.links.get("internal", []):
                    link_url = link.get("href", "")
                    if link_url and link_url not in visited:
                        if strategy == "dfs":
                            to_visit.insert(0, (link_url, depth + 1))
                        else:
                            to_visit.append((link_url, depth + 1))
        
        return json.dumps({
            "success": True,
            "start_url": start_url,
            "strategy": strategy,
            "pages_crawled": len(crawled_urls),
            "max_depth_reached": max(c["depth"] for c in crawled_urls) if crawled_urls else 0,
            "results": crawled_urls
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

# Extraction tools

@mcp.tool()
async def extract_structured_data(
    ctx: Context,
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
        crawler = ctx.request_context.lifespan_context.crawler
        
        # Create extraction strategy
        if extraction_type == "json_css":
            extraction_strategy = JsonCssExtractionStrategy(
                schema=schema,
                multiple=multiple
            )
        else:
            return json.dumps({
                "success": False,
                "error": f"Unknown extraction type: {extraction_type}"
            }, indent=2)
        
        config = CrawlerRunConfig(
            extraction_strategy=extraction_strategy,
            cache_mode=CacheMode.BYPASS
        )
        
        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            return json.dumps({
                "success": True,
                "url": url,
                "extracted_data": result.extracted_content,
                "extraction_type": extraction_type
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
    ctx: Context,
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
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return json.dumps({
                    "success": False,
                    "error": "API key required for LLM extraction"
                }, indent=2)
        
        crawler = ctx.request_context.lifespan_context.crawler
        
        # Create LLM extraction strategy with proper configuration
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
            cache_mode=CacheMode.BYPASS
        )
        
        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            content_id = save_crawled_content(
                ctx.request_context.lifespan_context,
                url,
                result
            )
            
            return json.dumps({
                "success": True,
                "url": url,
                "content_id": content_id,
                "extracted_content": result.extracted_content,
                "model_used": model
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

# Content filtering tools

@mcp.tool()
async def crawl_with_filter(
    ctx: Context,
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
        crawler = ctx.request_context.lifespan_context.crawler
        
        # Create content filter
        if filter_type == "bm25" and query:
            content_filter = BM25ContentFilter(
                user_query=query,
                threshold=threshold
            )
        elif filter_type == "pruning":
            content_filter = PruningContentFilter(
                min_word_threshold=min_word_threshold
            )
        elif filter_type == "llm":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return json.dumps({
                    "success": False,
                    "error": "API key required for LLM filtering"
                }, indent=2)
            
            content_filter = LLMContentFilter(
                provider="openai",
                api_key=api_key,
                model="gpt-4o-mini",
                relevance_prompt=query or "relevant content"
            )
        else:
            content_filter = None
        
        config = CrawlerRunConfig(
            content_filter=content_filter,
            cache_mode=CacheMode.BYPASS
        )
        
        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            content_id = save_crawled_content(
                ctx.request_context.lifespan_context,
                url,
                result
            )
            
            return json.dumps({
                "success": True,
                "url": url,
                "content_id": content_id,
                "filter_type": filter_type,
                "content_length": len(result.markdown) if result.markdown else 0,
                "filtered": result.content_filter_results if hasattr(result, 'content_filter_results') else None
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

# Link analysis tools

@mcp.tool()
async def extract_links(
    ctx: Context,
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
        crawler = ctx.request_context.lifespan_context.crawler
        
        # First crawl to get links
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=False,
            exclude_social_media_links=False
        )
        
        result = await crawler.arun(url=url, config=config)
        
        if not result.success:
            return json.dumps({
                "success": False,
                "error": result.error_message or "Failed to extract links"
            }, indent=2)
        
        response = {
            "success": True,
            "url": url,
            "internal_links": result.links.get("internal", []),
            "external_links": result.links.get("external", []),
            "total_internal": len(result.links.get("internal", [])),
            "total_external": len(result.links.get("external", []))
        }
        
        # Generate link previews if requested
        if preview_links:
            previews = []
            
            all_links = result.links.get("internal", [])[:max_preview//2] + \
                       result.links.get("external", [])[:max_preview//2]
            
            for link_data in all_links[:max_preview]:
                link_url = link_data.get("href", "")
                if link_url:
                    try:
                        preview_result = await crawler.arun(
                            url=link_url,
                            config=CrawlerRunConfig(
                                cache_mode=CacheMode.ENABLED,
                                word_count_threshold=50,
                                screenshot=False
                            )
                        )
                        
                        if preview_result.success:
                            previews.append({
                                "url": link_url,
                                "title": preview_result.metadata.get("title", ""),
                                "description": preview_result.metadata.get("description", "")[:200],
                                "preview": preview_result.markdown[:500] if preview_result.markdown else ""
                            })
                    except:
                        pass
            
            response["link_previews"] = previews
        
        return json.dumps(response, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

# Data retrieval tools

@mcp.tool()
async def get_crawled_content(
    ctx: Context,
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
        context = ctx.request_context.lifespan_context
        
        if content_id not in context.crawled_data:
            # Try to load from cache
            cache_file = context.cache_dir / f"{content_id}.json"
            if cache_file.exists():
                with open(cache_file, "r") as f:
                    context.crawled_data[content_id] = json.load(f)
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Content ID {content_id} not found"
                }, indent=2)
        
        data = context.crawled_data[content_id]
        result = data["content"]
        
        response = {
            "success": True,
            "content_id": content_id,
            "url": data["url"],
            "markdown": result.markdown if hasattr(result, 'markdown') else "",
            "metadata": result.metadata if hasattr(result, 'metadata') else {},
            "media": result.media if hasattr(result, 'media') else {}
        }
        
        if include_html and hasattr(result, 'html'):
            response["html"] = result.html
            
        if include_screenshot and hasattr(result, 'screenshot_data'):
            response["screenshot_data"] = result.screenshot_data
        
        return json.dumps(response, indent=2, default=str)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

@mcp.tool()
async def list_crawled_content(ctx: Context) -> str:
    """
    List all crawled content in the current session
    
    Returns:
        JSON with list of all crawled content
    """
    try:
        context = ctx.request_context.lifespan_context
        
        content_list = []
        for content_id, data in context.crawled_data.items():
            content_list.append({
                "content_id": content_id,
                "url": data["url"],
                "timestamp": data.get("timestamp", 0)
            })
        
        # Also check cache directory
        for cache_file in context.cache_dir.glob("*.json"):
            content_id = cache_file.stem
            if content_id not in context.crawled_data:
                try:
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                        content_list.append({
                            "content_id": content_id,
                            "url": data.get("url", ""),
                            "timestamp": data.get("timestamp", 0),
                            "from_cache": True
                        })
                except:
                    pass
        
        return json.dumps({
            "success": True,
            "total_items": len(content_list),
            "content": content_list
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

# Advanced crawling features

@mcp.tool()
async def crawl_with_js_execution(
    ctx: Context,
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
        crawler = ctx.request_context.lifespan_context.crawler
        
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=js_code,  # Fixed parameter name
            wait_for=wait_for_js,  # Changed from wait_for_js to wait_for
            page_timeout=js_timeout  # Changed from js_timeout to page_timeout
        )
        
        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            content_id = save_crawled_content(
                ctx.request_context.lifespan_context,
                url,
                result
            )
            
            return json.dumps({
                "success": True,
                "url": url,
                "content_id": content_id,
                "js_executed": bool(js_code),
                "content_length": len(result.markdown) if result.markdown else 0,
                "title": result.metadata.get("title", "")
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": result.error_message or "JS crawl failed"
            }, indent=2)
            
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)

@mcp.tool()
async def crawl_dynamic_content(
    ctx: Context,
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
        crawler = ctx.request_context.lifespan_context.crawler
        
        js_script = None
        if scroll:
            js_script = f"""
            async function scrollPage() {{
                for(let i = 0; i < {max_scrolls}; i++) {{
                    window.scrollTo(0, document.body.scrollHeight);
                    await new Promise(resolve => setTimeout(resolve, {scroll_delay}));
                }}
            }}
            await scrollPage();
            """
        
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=js_script,  # Fixed parameter name
            wait_for=wait_for_selector,
            word_count_threshold=10
        )
        
        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            content_id = save_crawled_content(
                ctx.request_context.lifespan_context,
                url,
                result
            )
            
            return json.dumps({
                "success": True,
                "url": url,
                "content_id": content_id,
                "scrolling_applied": scroll,
                "content_length": len(result.markdown) if result.markdown else 0,
                "title": result.metadata.get("title", "")
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