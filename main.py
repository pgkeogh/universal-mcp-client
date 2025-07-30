"""Universal MCP Client - Main entry point."""
import asyncio
import sys
from pathlib import Path

from src.core.universal_client import UniversalMCPClient
from src.utils.log_config import get_logger

logger = get_logger(__name__)

async def main():
    """Universal MCP Client - supports multiple servers and domains."""
    if len(sys.argv) < 2:
        print("Universal MCP Client Usage:")
        print("  Single server: python main.py <server_path> [server_id]")
        print("  Multiple servers: python main.py server1.py server2.py server3.py")
        print("  Auto-discovery: python main.py --discover <directory>")
        print()
        print("Examples:")
        print("  python main.py ./weather_server.py")
        print("  python main.py ./weather_server.py ./finance_server.py")
        print("  python main.py --discover ./mcp_servers/")
        sys.exit(1)
    
    client = UniversalMCPClient()
    
    try:
        # Handle different invocation modes
        if sys.argv[1] == "--discover":
            directory = sys.argv[2] if len(sys.argv) > 2 else "./servers"
            print(f"🔍 Auto-discovering MCP servers in: {directory}")
            await client.auto_discover_servers(Path(directory))
        else:
            # Connect to specified servers
            for i, server_path in enumerate(sys.argv[1:], 1):
                server_id = f"server_{i}" if len(sys.argv) > 2 else Path(server_path).stem
                print(f"🔌 Connecting to server '{server_id}' at '{server_path}'...")
                await client.connect_to_server(server_id, server_path)
        
        await interactive_session(client)
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        await client.shutdown()

async def interactive_session(client: UniversalMCPClient):
    """Universal interactive session - works with any domain."""
    print("\n🚀 Universal MCP Client Started!")
    
    # Display discovered servers and their profiles
    profiles = await client.get_server_profiles()
    print(f"\n📋 Connected Servers ({len(profiles)}):")
    for server_id, profile in profiles.items():
        domain = profile.domain or "unknown"
        tool_count = sum(len(tools) for tools in profile.tool_categories.values())
        print(f"  • {server_id}: {domain} domain ({tool_count} tools)")
    
    print("\n💡 I can work with any combination of these servers!")
    print("Just ask naturally - I'll figure out which servers and tools to use.\n")
    
    while True:
        try:
            query = input("Query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            if not query:
                continue
            
            print("🤔 Analyzing query and planning workflow...", end="", flush=True)
            response = await client.process_universal_query(query)
            print(f"\r🤖 {response}\n")
            
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    asyncio.run(main())