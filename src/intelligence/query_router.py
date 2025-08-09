"""Query routing for universal MCP client."""
from typing import Dict, Any
from src.discovery.server_profiler import ServerProfile
from src.utils.log_config import get_logger

logger = get_logger(__name__)

class QueryRouter:
    """Routes queries to optimal servers based on capability analysis."""
    
    async def route_query(self, query: str, profiles: Dict[str, ServerProfile]) -> Dict[str, Any]:
        """Route query to best server(s) based on intent analysis."""
        logger.info(f"Routing query: {query}")
        
        # Simple routing logic for now - we'll enhance this
        query_lower = query.lower()
        
        # Weather queries
        if any(keyword in query_lower for keyword in ["weather", "temperature", "forecast"]):
            weather_servers = [sid for sid, profile in profiles.items() if profile.domain == "weather"]
            if weather_servers:
                return {"primary_server": weather_servers[0], "query_type": "weather"}
        
        # Default to first available server
        if profiles:
            return {"primary_server": list(profiles.keys())[0], "query_type": "general"}
        
        raise ValueError("No suitable servers found for query")