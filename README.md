# Universal MCP Client

An enterprise-grade, universal MCP client that works with any MCP server through dynamic server introspection and intelligent workflow orchestration.

## Features

🎯 **Universal Compatibility**: Works with any MCP server - weather, finance, productivity, or custom domains
🔍 **Server Introspection**: Automatically discovers server capabilities and builds dynamic profiles  
🤖 **Intelligent Routing**: Routes queries to optimal servers based on intent analysis
🔗 **Multi-Server Workflows**: Orchestrates workflows across multiple servers simultaneously
🔐 **Enterprise Security**: Azure Key Vault integration for secure credential management
⚡ **Smart Caching**: Performance optimization with intelligent caching strategies

## Quick Start

```bash
# Install dependencies
uv sync

# Set up configuration
cp .env.template .env
# Edit .env with your Azure Key Vault name

# Single server
python main.py ./path/to/server.py

# Multiple servers
python main.py ./weather_server.py ./finance_server.py

# Auto-discovery
python main.py --discover ./mcp_servers/
```
