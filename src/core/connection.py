"""Advanced connection management for MCP servers."""
import asyncio
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool

from src.config.settings import UniversalMCPConfig
from src.utils.log_config import get_logger
from src.utils.exceptions import MCPConnectionError

logger = get_logger(__name__)

class MCPConnection:
    """Manages individual MCP server connection."""
    
    def __init__(self, server_id: str, server_path: str, config: UniversalMCPConfig):
        self.server_id = server_id
        self.server_path = Path(server_path)
        self.config = config
        
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.tools: List[Tool] = []
        self._is_connected = False
    
    async def connect(self) -> None:
        """Connect to the MCP server with retry logic."""
        for attempt in range(self.config.retry_attempts):
            try:
                await self._attempt_connection()
                self._is_connected = True
                logger.info(f"Connected to server '{self.server_id}' (attempt {attempt + 1})")
                return
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    raise MCPConnectionError(f"Failed to connect to '{self.server_id}' after {self.config.retry_attempts} attempts")
    
    async def _attempt_connection(self) -> None:
        """Single connection attempt."""
        # Validate server script
        if not self.server_path.exists():
            raise FileNotFoundError(f"Server script not found: {self.server_path}")
        
        # Determine command based on file extension
        if self.server_path.suffix == '.py':
            command = "python"
        elif self.server_path.suffix == '.js':
            command = "node"
        else:
            raise ServerValidationError(f"Unsupported server script type: {self.server_path.suffix}")
        
           # Log the exact command being run
        logger.info(f"Running command: {command} {str(self.server_path)}")
        
        # Set up server parameters
        server_params = StdioServerParameters(
            command=command,
            args=[str(self.server_path)],
            env=None
        )
        
        # Create connection with timeout
        try:
            logger.info("Creating stdio transport...")
            stdio_transport = await asyncio.wait_for(
                self.exit_stack.enter_async_context(stdio_client(server_params)),
                timeout=self.config.connection_timeout
            )
            self.stdio, self.write = stdio_transport
            logger.info("stdio transport created successfully")
            
            # Initialize session
            logger.info("Creating client session...")
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )
            logger.info("Client session created successfully")

            logger.info("Initializing session...")
            await self.session.initialize()
            logger.info("Session initialized successfully")
            
            # List available tools
            response = await self.session.list_tools()
            self.tools = response.tools
            
            logger.info(f"Server '{self.server_id}' initialized with {len(self.tools)} tools: {[tool.name for tool in self.tools]}")
            
        except asyncio.TimeoutError:
            raise ConnectionError(f"Connection timeout after {self.config.connection_timeout}s")
        except Exception as e:
            logger.error(f"Connection failed with error: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            raise MCPConnectionError(f"Connection failed: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool with error handling."""
        if not self._is_connected or not self.session:
            raise ConnectionError("Not connected to server")
        
        # Validate tool exists
        if not any(tool.name == tool_name for tool in self.tools):
            available_tools = [tool.name for tool in self.tools]
            raise ValueError(f"Tool '{tool_name}' not available. Available tools: {available_tools}")
        
        try:
            logger.debug(f"Calling tool '{tool_name}' with args: {arguments}")
            result = await self.session.call_tool(tool_name, arguments)
            logger.debug(f"Tool '{tool_name}' completed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool execution failed for '{tool_name}': {e}")
            raise
    
    async def disconnect(self) -> None:
        """Gracefully disconnect from server."""
        try:
            await self.exit_stack.aclose()
            self._is_connected = False
            logger.info(f"Disconnected from server '{self.server_id}'")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self._is_connected