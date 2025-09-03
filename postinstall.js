#!/usr/bin/env node

/**
 * Post-install script for MCP Crawl4AI
 * Checks and installs Python dependencies
 */

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

console.log('📦 MCP Crawl4AI - Post-install Setup');
console.log('=====================================');

// Check Python
function checkPython() {
  const pythonCommands = ['python3', 'python'];
  
  for (const cmd of pythonCommands) {
    try {
      const result = execSync(`${cmd} --version`, { encoding: 'utf8', stdio: 'pipe' });
      if (result.includes('Python 3')) {
        const version = result.match(/Python (\d+)\.(\d+)/);
        if (version && parseInt(version[1]) === 3 && parseInt(version[2]) >= 10) {
          console.log(`✅ Found ${result.trim()}`);
          return cmd;
        }
      }
    } catch (error) {
      // Continue
    }
  }
  
  console.error('❌ Python 3.10+ is required but not found.');
  console.error('   Please install Python from https://www.python.org');
  return null;
}

// Check and install Python packages
function checkPythonPackages(pythonCmd) {
  console.log('\n📚 Checking Python dependencies...');
  
  const requiredPackages = [
    'fastmcp',
    'crawl4ai',
    'python-dotenv'
  ];
  
  const missingPackages = [];
  
  for (const pkg of requiredPackages) {
    try {
      execSync(`${pythonCmd} -c "import ${pkg.replace('-', '_')}"`, { stdio: 'pipe' });
      console.log(`   ✅ ${pkg} - installed`);
    } catch (error) {
      console.log(`   ⚠️  ${pkg} - not installed`);
      missingPackages.push(pkg);
    }
  }
  
  if (missingPackages.length > 0) {
    console.log('\n📥 Installing missing packages...');
    console.log('   This may take a few minutes...\n');
    
    try {
      // Try to install missing packages
      for (const pkg of missingPackages) {
        console.log(`   Installing ${pkg}...`);
        try {
          if (pkg === 'crawl4ai') {
            execSync(`${pythonCmd} -m pip install crawl4ai>=0.6.0 --quiet`, { stdio: 'inherit' });
          } else if (pkg === 'fastmcp') {
            execSync(`${pythonCmd} -m pip install fastmcp>=2.12.0 --quiet`, { stdio: 'inherit' });
          } else {
            execSync(`${pythonCmd} -m pip install ${pkg} --quiet`, { stdio: 'inherit' });
          }
          console.log(`   ✅ ${pkg} installed successfully`);
        } catch (error) {
          console.log(`   ❌ Failed to install ${pkg}`);
          console.log(`      Please run: pip install ${pkg}`);
        }
      }
    } catch (error) {
      console.error('\n⚠️  Some packages could not be installed automatically.');
      console.error('   Please install them manually:');
      console.error(`   ${pythonCmd} -m pip install ${missingPackages.join(' ')}`);
    }
  }
}

// Check Playwright
function checkPlaywright(pythonCmd) {
  console.log('\n🎭 Checking Playwright browsers...');
  
  try {
    execSync('playwright --version', { stdio: 'pipe' });
    console.log('   ✅ Playwright CLI found');
    
    // Check if Chromium is installed
    try {
      const result = execSync('playwright list', { encoding: 'utf8', stdio: 'pipe' });
      if (result.includes('chromium')) {
        console.log('   ✅ Chromium browser installed');
      } else {
        console.log('   ⚠️  Chromium not found');
        console.log('   Installing Chromium...');
        try {
          execSync('playwright install chromium', { stdio: 'inherit' });
          console.log('   ✅ Chromium installed successfully');
        } catch (error) {
          console.log('   ❌ Failed to install Chromium');
          console.log('      Please run: playwright install chromium');
        }
      }
    } catch (error) {
      console.log('   ⚠️  Could not check Playwright browsers');
      console.log('      Please run: playwright install chromium');
    }
  } catch (error) {
    console.log('   ⚠️  Playwright not found');
    console.log('      After installation, run: playwright install chromium');
  }
}

// Main setup
function main() {
  const pythonCmd = checkPython();
  
  if (!pythonCmd) {
    console.error('\n❌ Setup incomplete - Python required');
    return;
  }
  
  checkPythonPackages(pythonCmd);
  checkPlaywright(pythonCmd);
  
  console.log('\n=====================================');
  console.log('✨ MCP Crawl4AI Setup Complete!');
  console.log('\nTo use with Claude Code:');
  console.log('  claude mcp add crawl4ai -- npx -y mcp-crawl4ai');
  console.log('\nOr add to config manually:');
  console.log('  {');
  console.log('    "mcpServers": {');
  console.log('      "crawl4ai": {');
  console.log('        "command": "npx",');
  console.log('        "args": ["-y", "mcp-crawl4ai"],');
  console.log('        "env": {');
  console.log('          "OPENAI_API_KEY": "your-key-here"');
  console.log('        }');
  console.log('      }');
  console.log('    }');
  console.log('  }');
  console.log('=====================================');
}

// Run setup
main();