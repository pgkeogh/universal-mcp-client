"""Universal exceptions for MCP client operations."""

class UniversalMCPError(Exception):
    """Base exception for Universal MCP client errors."""
    pass

class MCPConnectionError(UniversalMCPError):
    """Raised when connection to MCP server fails."""
    pass

class ServerDiscoveryError(UniversalMCPError):
    """Raised when server discovery/profiling fails."""
    pass

class WorkflowPlanningError(UniversalMCPError):
    """Raised when workflow planning fails."""
    pass

class QueryRoutingError(UniversalMCPError):
    """Raised when query routing fails."""
    pass

class ServerProfileError(UniversalMCPError):
    """Raised when server profiling fails."""
    pass

class ConfigurationError(UniversalMCPError):
    """Raised when configuration is invalid."""
    pass