# MCP Crawl4AI - Quick Start Guide

## Installation

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the package
pip install -e .

# Or install requirements directly
pip install -r requirements.txt

# Install Playwright browsers (required)
playwright install chromium
```

### 2. Configure for Claude Code

Add this to your Claude Code MCP settings (usually in `~/Library/Application Support/Claude/claude_code_config.json`):

```json
{
  "mcpServers": {
    "mcp-crawl4ai": {
      "command": "python3",
      "args": ["/full/path/to/mcp-crawl4ai/server.py"],
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here"
      }
    }
  }
}
```

### 3. Verify Installation

```bash
# Test import
python3 -c "import server; print('✅ Server ready')"

# Run test suite
python3 test_server.py
```

## Basic Usage Examples

### Simple Web Crawling

```python
# Crawl a single page
result = await crawl_url(
    url="https://example.com"
)

# Crawl with screenshot
result = await crawl_url(
    url="https://example.com",
    screenshot=True
)

# Crawl multiple pages
results = await batch_crawl(
    urls=["https://example.com", "https://example.org"]
)
```

### Extract Structured Data

```python
# CSS selector extraction
schema = {
    "baseSelector": "article",
    "fields": {
        "title": {"selector": "h1", "type": "text"},
        "content": {"selector": "p", "type": "text", "multiple": True}
    }
}

result = await extract_structured_data(
    url="https://blog.example.com",
    schema=schema,
    extraction_type="json_css"
)
```

### Deep Crawling

```python
# Crawl website recursively
result = await deep_crawl(
    start_url="https://docs.example.com",
    max_depth=3,
    max_pages=50,
    strategy="bfs"
)
```

### LLM-Based Extraction

```python
# Extract with GPT-4
result = await extract_with_llm(
    url="https://example.com/product",
    instruction="Extract product name, price, and features",
    model="gpt-4o-mini"
)
```

## Available Tools

| Tool | Description |
|------|-------------|
| `crawl_url` | Single URL crawling with advanced options |
| `batch_crawl` | Parallel crawling of multiple URLs |
| `deep_crawl` | Recursive website crawling |
| `extract_structured_data` | CSS/XPath based extraction |
| `extract_with_llm` | AI-powered content extraction |
| `crawl_with_filter` | Content filtering during crawl |
| `extract_links` | Link extraction and preview |
| `crawl_dynamic_content` | Handle JavaScript-heavy sites |
| `get_crawled_content` | Retrieve cached content |
| `list_crawled_content` | List all cached items |

## Environment Variables

Optional configuration in `.env` file:

```env
# For LLM features
OPENAI_API_KEY=sk-your-key

# Transport mode
TRANSPORT=stdio

# Browser settings
HEADLESS=true
BROWSER_TYPE=chromium
```

## Common Issues

### Browser Not Found
```bash
playwright install chromium
```

### Import Errors
Make sure you're in the virtual environment:
```bash
source venv/bin/activate
```

### Memory Issues
Reduce concurrent crawls:
```python
batch_crawl(urls, max_concurrent=2)
```

## Support

- GitHub Issues: [Report issues here]
- Documentation: See README.md for detailed docs