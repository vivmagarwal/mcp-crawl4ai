# MCP Crawl4AI Examples

This directory contains example scripts demonstrating various features of the MCP Crawl4AI server.

## Examples

### 1. Authentication (`auth_example.py`)
Demonstrates how to crawl login-protected websites:
- Using the specialized `crawl_with_auth` tool
- Using `crawl_url` with authentication parameters
- Handling custom login forms

### Running Examples

```bash
# Make sure you're in the project root
cd mcp-crawl4ai

# Activate virtual environment
source venv/bin/activate

# Run an example
python examples/auth_example.py
```

## Authentication Example

The authentication example shows how to:
1. Login to a protected website
2. Navigate to protected content
3. Extract data after authentication
4. Save the scraped content

### Example: TOK Newsletter Archive

```python
# Using the specialized authentication tool
result = await crawl_with_auth(
    ctx,
    url="https://theoryofknowledge.net/tok-resources/tok-newsletter-archive/",
    username="tokdepartment@uwcdilijan.am",
    password="Trfz998afds#",
    wait_after_login=7000,
    content_selector=".content-area"
)
```

## Tips for Authentication

1. **Wait Times**: Allow sufficient time after login (5-10 seconds)
2. **Content Selectors**: Use selectors that appear after login
3. **Custom Selectors**: Override default selectors if needed
4. **Debugging**: Set `headless=False` to watch the login process

## Common Issues

- **Login Failed**: Check credentials and selectors
- **Content Not Found**: Increase wait time after login
- **Session Expired**: Use `bypass_cache=True` for fresh sessions