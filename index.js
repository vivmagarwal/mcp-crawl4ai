#!/usr/bin/env node

/**
 * MCP Crawl4AI Server - Node.js wrapper for Python MCP server
 * This wrapper enables installation via npm/npx for use with Claude Code
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Check if Python is available
function checkPython() {
  const pythonCommands = ['python3', 'python'];
  
  for (const cmd of pythonCommands) {
    try {
      const result = require('child_process').execSync(`${cmd} --version`, { 
        encoding: 'utf8',
        stdio: 'pipe' 
      });
      if (result.includes('Python 3')) {
        return cmd;
      }
    } catch (error) {
      // Continue to next command
    }
  }
  
  console.error('Error: Python 3.10+ is required but not found.');
  console.error('Please install Python from https://www.python.org');
  process.exit(1);
}

// Main function
function main() {
  const pythonCmd = checkPython();
  const serverPath = path.join(__dirname, 'server.py');
  
  // Check if server.py exists
  if (!fs.existsSync(serverPath)) {
    console.error(`Error: server.py not found at ${serverPath}`);
    console.error('The installation may be incomplete.');
    process.exit(1);
  }
  
  // Get environment variables
  const env = {
    ...process.env,
    // Ensure Python can find the modules
    PYTHONPATH: `${__dirname}:${process.env.PYTHONPATH || ''}`
  };
  
  // Pass through any API keys from environment
  if (process.env.OPENAI_API_KEY) {
    env.OPENAI_API_KEY = process.env.OPENAI_API_KEY;
  }
  
  // Only show startup message if not in stdio mode
  if (process.env.DEBUG || process.argv.includes('--debug')) {
    console.error('Starting MCP Crawl4AI Server...');
  }
  
  // Spawn the Python process
  const pythonProcess = spawn(pythonCmd, [serverPath], {
    env,
    stdio: 'inherit' // Pass through stdin/stdout/stderr
  });
  
  pythonProcess.on('error', (error) => {
    console.error('Failed to start Python server:', error.message);
    process.exit(1);
  });
  
  pythonProcess.on('exit', (code) => {
    if (code !== 0) {
      console.error(`Python server exited with code ${code}`);
    }
    process.exit(code || 0);
  });
  
  // Handle termination signals
  process.on('SIGINT', () => {
    pythonProcess.kill('SIGINT');
  });
  
  process.on('SIGTERM', () => {
    pythonProcess.kill('SIGTERM');
  });
}

// Run the server
if (require.main === module) {
  main();
}