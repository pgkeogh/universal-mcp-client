"""Multi-server connection management for Universal MCP Client."""
from typing import Dict, List, Optional
from src.core.connection import MCPConnection
from src.config.settings import UniversalMCPConfig
from src.utils.log_config import get_logger
from src.utils.exceptions import MCPConnectionError

logger = get_logger(__name__)

class ServerManager:
    """Manages connections to multiple MCP servers."""
    
    def __init__(self, config: UniversalMCPConfig):
        self.config = config
        self.connections: Dict[str, MCPConnection] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize server manager."""
        if self._initialized:
            return
        
        # Any global initialization needed
        self._initialized = True
        logger.info("Server manager initialized")
    
    async def connect_to_server(self, server_id: str, server_path: str) -> None:
        """Connect to a single MCP server."""
        if server_id in self.connections:
            logger.warning(f"Server '{server_id}' already connected")
            return
        
        logger.info(f"Connecting to server '{server_id}' at '{server_path}'")
        connection = MCPConnection(server_id, server_path, self.config)
        
        try:
            await connection.connect()
            self.connections[server_id] = connection
            logger.info(f"Successfully connected to server '{server_id}'")
        except Exception as e:
            logger.error(f"Failed to connect to server '{server_id}': {e}")
            await connection.disconnect()
            raise MCPConnectionError(f"Failed to connect to '{server_id}': {e}")
    
    def get_connection(self, server_id: str) -> MCPConnection:
        """Get connection for a specific server."""
        if server_id not in self.connections:
            raise MCPConnectionError(f"Server '{server_id}' not connected")
        return self.connections[server_id]
    
    async def list_connected_servers(self) -> Dict[str, List[str]]:
        """List all connected servers and their tools."""
        return {
            server_id: [tool.name for tool in connection.tools]
            for server_id, connection in self.connections.items()
            if connection.is_connected
        }
    
    async def shutdown(self) -> None:
        """Shutdown all server connections."""
        logger.info("Shutting down all server connections...")
        for server_id in list(self.connections.keys()):
            await self.connections[server_id].disconnect()
            del self.connections[server_id]
        logger.info("All server connections shutdown")