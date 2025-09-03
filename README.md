# MCP Crawl4AI Server

A comprehensive Model Context Protocol (MCP) server that provides full access to Crawl4AI's powerful web scraping and crawling capabilities through Claude Desktop/Code. Supports authentication for login-protected sites.

## Features

### Core Crawling
- **Single URL Crawling** - Advanced single page scraping with screenshots, PDFs, and browser control
- **Batch Crawling** - Parallel crawling of multiple URLs with memory management
- **Deep Crawling** - Recursive crawling with BFS, DFS, and best-first strategies
- **Dynamic Content** - Handle JavaScript-heavy sites with scrolling and JS execution

### Data Extraction
- **Structured Extraction** - CSS and XPath selectors for precise data extraction
- **LLM Extraction** - Use GPT-4, Claude, or other models to extract semantic information
- **Link Analysis** - Extract and preview all internal/external links
- **Content Filtering** - BM25, LLM-based, and threshold filtering

### Advanced Features
- **JavaScript Execution** - Run custom JS code during crawling
- **Dynamic Loading** - Handle infinite scroll and AJAX content
- **Caching System** - Persistent storage of crawled content
- **Memory Management** - Adaptive memory control for large-scale crawling

## Installation for Claude Desktop

### Step 1: Prerequisites
- Python 3.10 or higher
- Node.js (for some MCP features)
- Chrome/Chromium browser

### Step 2: Clone and Install

```bash
# Clone the repository
git clone https://github.com/vivmagarwal/mcp-crawl4ai.git
cd mcp-crawl4ai

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Install Playwright browsers (required)
playwright install chromium
```

### Step 3: Configure Claude Desktop

1. **Find your Claude configuration file:**
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. **Edit the configuration file:**

```json
{
  "mcpServers": {
    "mcp-crawl4ai": {
      "command": "python3",
      "args": ["/absolute/path/to/mcp-crawl4ai/server.py"],
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here"
      }
    }
  }
}
```

⚠️ **Important:** Replace `/absolute/path/to/mcp-crawl4ai/server.py` with the actual path to your server.py file.

### Step 4: Restart Claude Desktop

1. Completely quit Claude Desktop (not just close the window)
2. Start Claude Desktop again
3. Look for the MCP server indicator (🔌) in the bottom-right of the input box
4. Click the indicator to verify "mcp-crawl4ai" is connected

## Configuration with Authentication

For sites requiring login, the server supports authentication:

```json
{
  "mcpServers": {
    "mcp-crawl4ai": {
      "command": "python3",
      "args": ["/path/to/mcp-crawl4ai/server.py"],
      "env": {
        "OPENAI_API_KEY": "sk-your-key",
        "DEFAULT_USERNAME": "your-username",
        "DEFAULT_PASSWORD": "your-password"
      }
    }
  }
}
```

### Environment Variables

Create a `.env` file in the project directory:

```env
# Optional: For LLM-based features
OPENAI_API_KEY=your-openai-api-key

# Transport mode (stdio or sse)
TRANSPORT=stdio

# Browser settings
HEADLESS=true
BROWSER_TYPE=chromium
```

## Usage Examples

### Basic Crawling

```python
# Crawl a single URL
result = await crawl_url(
    url="https://example.com",
    screenshot=True,
    pdf=False,
    wait_for="#content"
)

# Batch crawl multiple URLs
results = await batch_crawl(
    urls=["https://example.com", "https://example.org"],
    max_concurrent=5
)
```

### Crawling with Authentication

```python
# Crawl a login-protected site
result = await crawl_url(
    url="https://theoryofknowledge.net/tok-resources/tok-newsletter-archive/",
    username="tokdepartment@uwcdilijan.am",
    password="Trfz998afds#",
    wait_for=".content-area"  # Wait for content after login
)

# Custom login selectors if defaults don't work
result = await crawl_url(
    url="https://example.com/protected",
    username="myuser",
    password="mypass",
    login_url="https://example.com/login",  # Optional: specific login page
    username_selector="#username",  # Custom username field selector
    password_selector="#password",  # Custom password field selector
    submit_selector="#login-button"  # Custom submit button selector
)
```

### Deep Crawling

```python
# BFS deep crawl
result = await deep_crawl(
    start_url="https://docs.example.com",
    max_depth=3,
    max_pages=50,
    strategy="bfs",
    allowed_domains=["docs.example.com"]
)

# Best-first crawling with keyword focus
result = await deep_crawl(
    start_url="https://blog.example.com",
    strategy="best_first",
    keyword_focus=["AI", "machine learning", "neural networks"]
)
```

### Data Extraction

```python
# Extract structured data with CSS selectors
schema = {
    "title": "h1.article-title",
    "author": "span.author-name",
    "date": "time.publish-date",
    "content": "div.article-content"
}

result = await extract_structured_data(
    url="https://blog.example.com/article",
    schema=schema,
    extraction_type="json_css"
)

# LLM-based extraction
result = await extract_with_llm(
    url="https://example.com/product",
    instruction="Extract product name, price, and key features",
    model="gpt-4o-mini"
)
```

### Dynamic Content

```python
# Handle infinite scroll
result = await crawl_dynamic_content(
    url="https://example.com/feed",
    scroll=True,
    max_scrolls=10,
    scroll_delay=1000
)

# Execute custom JavaScript
result = await crawl_with_js_execution(
    url="https://spa.example.com",
    js_code="""
        document.querySelector('.load-more').click();
        await new Promise(r => setTimeout(r, 2000));
    """,
    wait_for_js="document.querySelectorAll('.item').length > 10"
)
```

### Content Filtering

```python
# BM25 relevance filtering
result = await crawl_with_filter(
    url="https://news.example.com",
    filter_type="bm25",
    query="artificial intelligence breakthrough",
    threshold=0.5
)

# Prune low-content sections
result = await crawl_with_filter(
    url="https://example.com",
    filter_type="pruning",
    min_word_threshold=100
)
```

## Available Tools

### Core Crawling Tools
- `crawl_url` - Comprehensive single URL crawling with optional authentication
- `crawl_with_auth` - Specialized tool for login-protected sites
- `batch_crawl` - Parallel multi-URL crawling
- `deep_crawl` - Recursive crawling with strategies

### Extraction Tools
- `extract_structured_data` - CSS/XPath data extraction
- `extract_with_llm` - LLM-powered extraction
- `extract_links` - Link extraction and preview

### Advanced Tools
- `crawl_with_js_execution` - JavaScript execution
- `crawl_dynamic_content` - Handle dynamic loading
- `crawl_with_filter` - Content filtering

### Data Management
- `get_crawled_content` - Retrieve stored content
- `list_crawled_content` - List all crawled items

## Architecture

```
mcp-crawl4ai/
├── server.py           # Main MCP server implementation
├── pyproject.toml      # Package configuration
├── README.md           # Documentation
├── .env               # Environment variables
└── cache/             # Cached crawl results
```

## Performance Tips

1. **Memory Management**: Use `max_concurrent` parameter for batch operations
2. **Caching**: Enable caching for repeated crawls
3. **Filtering**: Use content filters to reduce data size
4. **Deep Crawling**: Set reasonable `max_depth` and `max_pages` limits

## Troubleshooting

### Common Issues

1. **Browser not found**: Install Playwright browsers
   ```bash
   playwright install chromium
   ```

2. **Memory issues**: Reduce `max_concurrent` value

3. **JavaScript timeout**: Increase `js_timeout` parameter

4. **LLM features not working**: Set `OPENAI_API_KEY` in environment

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black .
ruff check .
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built on top of [Crawl4AI](https://github.com/unclecode/crawl4ai)
- Uses the [Model Context Protocol](https://modelcontextprotocol.io)
- FastMCP framework for MCP server implementation