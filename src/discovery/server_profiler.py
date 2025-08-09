"""Server capability analysis and profiling for universal adaptation."""
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
from enum import Enum

from src.utils.log_config import get_logger

logger = get_logger(__name__)

class ToolCategory(Enum):
    """Universal tool categories for any domain."""
    DATA_RETRIEVAL = "data_retrieval"
    DATA_PROCESSING = "data_processing"
    EXTERNAL_API = "external_api"
    STORAGE_CACHE = "storage_cache"
    AI_ENHANCEMENT = "ai_enhancement"
    SECURITY = "security"
    UTILITIES = "utilities"
    UNKNOWN = "unknown"

@dataclass
class ServerProfile:
    """Complete server capability profile built through introspection."""
    server_id: str
    domain: Optional[str]  # weather, finance, productivity, etc.
    tools: List[str]  # Tool names
    tool_categories: Dict[ToolCategory, List[str]]
    workflow_patterns: List[str]  # Detected workflow patterns
    data_sources: Set[str]  # External APIs/services this server uses
    capabilities: Dict[str, any]  # Detailed analysis
    server_configuration: Dict[str, Any] = None

class ServerProfiler:
    """Analyzes any MCP server to build dynamic capability profiles."""
    
    async def profile_server(self, connection) -> ServerProfile:
        """Build comprehensive server profile through introspection."""
        logger.info(f"Profiling server: {connection.server_id}")
        
        # Basic tool analysis
        tool_names = [tool.name for tool in connection.tools]
        tool_categories = await self._categorize_tools(connection.tools)
        
        # Domain detection based on tool patterns
        domain = await self._detect_domain(connection.tools)
        
        # Workflow pattern analysis
        patterns = await self._analyze_workflow_patterns(connection.tools)
        
        # Data source identification
        data_sources = await self._identify_data_sources(connection.tools)
        
        profile = ServerProfile(
            server_id=connection.server_id,
            domain=domain,
            tools=tool_names,
            tool_categories=tool_categories,
            workflow_patterns=patterns,
            data_sources=data_sources,
            capabilities=await self._analyze_capabilities(connection.tools)
        )
        
        logger.info(f"Server '{connection.server_id}' profiled: {domain} domain, {len(tool_names)} tools")
        return profile
    
    async def _categorize_tools(self, tools) -> Dict[ToolCategory, List[str]]:
        """Categorize tools into universal categories."""
        categories = {category: [] for category in ToolCategory}
        
        for tool in tools:
            category = await self._classify_tool(tool)
            categories[category].append(tool.name)
        
        return categories
    
    async def _classify_tool(self, tool) -> ToolCategory:
        """Classify a single tool into a category."""
        tool_name = tool.name.lower()
        description = tool.description.lower() if tool.description else ""
        
        # Pattern matching for universal classification
        if any(keyword in tool_name for keyword in ["get", "fetch", "retrieve", "read"]):
            return ToolCategory.DATA_RETRIEVAL
        elif any(keyword in tool_name for keyword in ["cache", "store", "save"]):
            return ToolCategory.STORAGE_CACHE
        elif any(keyword in tool_name for keyword in ["http", "api", "request", "url"]):
            return ToolCategory.EXTERNAL_API
        elif any(keyword in tool_name for keyword in ["format", "process", "parse", "extract"]):
            return ToolCategory.DATA_PROCESSING
        elif any(keyword in tool_name for keyword in ["ai", "completion", "generate"]):
            return ToolCategory.AI_ENHANCEMENT
        elif any(keyword in tool_name for keyword in ["secret", "key", "auth"]):
            return ToolCategory.SECURITY
        else:
            return ToolCategory.UNKNOWN
    
    async def _analyze_tool_schemas(self, tools) -> Dict[str, Any]:
        """Analyze tool schemas for configuration hints."""
        config = {"secret_names": [], "expected_parameters": {}}
        
        for tool in tools:
            if "secret" in tool.name.lower() and hasattr(tool, 'inputSchema'):
                schema = tool.inputSchema
                
                # Debug: Let's see what's actually in the schema
                print(f"🔍 Analyzing schema for {tool.name}: {schema}")
                
                if isinstance(schema, dict) and 'properties' in schema:
                    secret_prop = schema['properties'].get('secret_name', {})
                    
                    # Extract examples, enums, or hints from description
                    if 'examples' in secret_prop:
                        print(f"✅ Found examples in schema: {secret_prop['examples']}")
                        config["secret_names"].extend(secret_prop['examples'])
                    
                    elif 'enum' in secret_prop:
                        print(f"✅ Found enum in schema: {secret_prop['enum']}")
                        config["secret_names"].extend(secret_prop['enum'])
                    
                    elif 'description' in secret_prop:
                        # Parse description for patterns like "OWM-API-KEY"
                        desc = secret_prop['description']
                        print(f"🔍 Parsing description: {desc}")
                        
                        import re
                        # Look for quoted strings that look like secret names
                        patterns = re.findall(r"['\"]([A-Z][A-Z0-9_-]*(?:API|KEY)[A-Z0-9_-]*)['\"]", desc)
                        if patterns:
                            print(f"✅ Extracted secret patterns: {patterns}")
                            config["secret_names"].extend(patterns)
        
        print(f"🔍 Discovered secret names: {config['secret_names']}")
        return config

    async def _detect_domain(self, tools) -> Optional[str]:
        """Detect server domain based on tool patterns."""
        tool_names = " ".join([tool.name.lower() for tool in tools])
        tool_descriptions = " ".join([tool.description.lower() for tool in tools if tool.description])
        combined_text = f"{tool_names} {tool_descriptions}"
        
        # Domain detection patterns
        if any(keyword in combined_text for keyword in ["weather", "temperature", "forecast"]):
            return "weather"
        elif any(keyword in combined_text for keyword in ["finance", "stock", "price", "market"]):
            return "finance"
        elif any(keyword in combined_text for keyword in ["calendar", "task", "todo", "schedule"]):
            return "productivity"
        elif any(keyword in combined_text for keyword in ["file", "document", "storage"]):
            return "filesystem"
        else:
            return "general"
    
    async def _analyze_workflow_patterns(self, tools) -> List[str]:
        """Analyze common workflow patterns based on tool combinations."""
        patterns = []
        tool_names = [tool.name.lower() for tool in tools]
        
        # Common workflow patterns
        if "get_secret" in tool_names and "http_request" in tool_names:
            patterns.append("authenticated_api_workflow")
        
        if "cache_data" in tool_names and "get_cached_data" in tool_names:
            patterns.append("caching_workflow")
        
        if "ai_completion" in tool_names:
            patterns.append("ai_enhanced_workflow")
        
        return patterns
    
    async def _identify_data_sources(self, tools) -> Set[str]:
        """Identify external data sources this server connects to."""
        data_sources = set()
        
        for tool in tools:
            description = tool.description.lower() if tool.description else ""
            
            # Look for API mentions
            if "openweathermap" in description or "owm" in description:
                data_sources.add("OpenWeatherMap API")
            elif "api" in description and "http" in tool.name.lower():
                data_sources.add("External API")
        
        return data_sources
    
    async def _analyze_capabilities(self, tools) -> Dict[str, any]:
        """Detailed capability analysis."""
        return {
            "tool_count": len(tools),
            "has_caching": any("cache" in tool.name.lower() for tool in tools),
            "has_ai_features": any("ai" in tool.name.lower() for tool in tools),
            "has_external_apis": any("http" in tool.name.lower() for tool in tools),
            "has_security": any("secret" in tool.name.lower() for tool in tools)
        }