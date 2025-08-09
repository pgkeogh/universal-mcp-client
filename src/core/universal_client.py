"""Universal MCP Client - works with any MCP server through introspection."""
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path

from src.core.server_manager import ServerManager
from src.discovery.server_profiler import ServerProfiler, ServerProfile
from src.intelligence.query_router import QueryRouter
from src.intelligence.workflow_planner import WorkflowPlanner
from src.config.settings import UniversalMCPConfig
from src.utils.log_config import get_logger
from src.utils.exceptions import UniversalMCPError

logger = get_logger(__name__)

class UniversalMCPClient:
    """Universal MCP client that adapts to any server through introspection."""
    
    def __init__(self, config: Optional[UniversalMCPConfig] = None):
        self.config = config or UniversalMCPConfig.create()
        self.config.validate()
        
        # Core components
        self.server_manager = ServerManager(self.config)
        self.server_profiler = ServerProfiler()
        self.query_router = QueryRouter()
        self.workflow_planner = WorkflowPlanner()
        
        # State
        self.server_profiles: Dict[str, ServerProfile] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the universal client."""
        if self._initialized:
            return
        
        try:
            await self.server_manager.initialize()
            self._initialized = True
            logger.info("Universal MCP Client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Universal MCP Client: {e}")
            raise UniversalMCPError(f"Client initialization failed: {e}")
    
    async def connect_to_server(self, server_id: str, server_path: str) -> None:
        """Connect to an MCP server and build its profile."""
        if not self._initialized:
            await self.initialize()
        
        logger.info(f"Connecting to server '{server_id}' at '{server_path}'")
        
        # Connect through server manager
        await self.server_manager.connect_to_server(server_id, server_path)
        
        # Build server profile through introspection
        connection = self.server_manager.get_connection(server_id)
        profile = await self.server_profiler.profile_server(connection)
        self.server_profiles[server_id] = profile
        
        logger.info(f"Server '{server_id}' profiled: {profile.domain} domain with {len(profile.tools)} tools")
    
    async def auto_discover_servers(self, directory: Path) -> None:
        """Auto-discover and connect to MCP servers in a directory."""
        if not self._initialized:
            await self.initialize()
        
        logger.info(f"Auto-discovering servers in: {directory}")
        
        # Find potential server scripts
        server_files = []
        for pattern in ["*.py", "*.js"]:
            server_files.extend(directory.glob(pattern))
        
        if not server_files:
            raise UniversalMCPError(f"No server scripts found in: {directory}")
        
        # Connect to discovered servers
        for server_file in server_files:
            server_id = server_file.stem
            try:
                await self.connect_to_server(server_id, str(server_file))
            except Exception as e:
                logger.warning(f"Failed to connect to {server_file}: {e}")
        
        if not self.server_profiles:
            raise UniversalMCPError("No servers successfully connected")
        
        logger.info(f"Successfully connected to {len(self.server_profiles)} servers")

  
    async def _generate_system_prompt(self, profile: ServerProfile) -> str:
        """Generate dynamic system prompt based on server profile analysis."""
        logger.info(f"🧠 GENERATING SYSTEM PROMPT for {profile.server_id} {profile.server_configuration} ({profile.domain})")

                # ADD THIS DEBUG
        print(f"🔍 DEBUG: Profile server_configuration: {getattr(profile, 'server_configuration', 'NOT FOUND')}")
        
        from src.adapters.prompt_generator import DynamicPromptGenerator
        
        generator = DynamicPromptGenerator()
        connection = self.server_manager.get_connection(profile.server_id)
        
        logger.info(f"🧠 Analyzing {len(connection.tools)} tools for prompt generation")
        
        # Generate prompt based on actual tool analysis, not hardcoded rules
        prompt = await generator.generate_system_prompt(profile, connection.tools)
        
        logger.info(f"🧠 Generated {len(prompt)} character system prompt")
        logger.info(f"🧠 System prompt: {prompt}")
    
        return prompt

    async def process_universal_query(self, query: str) -> str:
        """Process any query using optimal server selection and workflow planning."""
        if not self.server_profiles:
            raise UniversalMCPError("No servers connected")
        
        logger.info(f"Processing universal query: {query}")
        
        # Analyze query and route to best server(s)
        routing_plan = await self.query_router.route_query(query, self.server_profiles)
        
        # Plan workflow based on query and selected servers
        workflow = await self.workflow_planner.plan_workflow(
            query, routing_plan, self.server_profiles
        )
        
        # 🔧 FIX: Add the original query to the workflow
        workflow["original_query"] = query
        
        # Execute workflow
        result = await self._execute_universal_workflow(workflow)
        
        return result

    async def _execute_universal_workflow(self, workflow: Dict[str, Any]) -> str:
        """Execute a universal workflow across multiple servers."""
        primary_server = workflow.get("primary_server")
        if not primary_server:
            raise UniversalMCPError("No primary server identified in workflow")
        
        # Get the server connection and profile
        connection = self.server_manager.get_connection(primary_server)
        profile = self.server_profiles[primary_server]
        
        # Build available tools for OpenAI
        available_tools = []
        for tool in connection.tools:
            available_tools.append({
                "type": "function",
                "function": {
                    "name": f"{primary_server}_{tool.name}",
                    "description": f"[{primary_server}] {tool.description}",
                    "parameters": tool.inputSchema
                },
                "_server_id": primary_server,
                "_original_name": tool.name
            })
        
        # Show what we're sending to OpenAI
        for tool in available_tools:
            if "secret" in tool["function"]["name"]:
                print(f"🔍 DEBUG: Secret tool sent to OpenAI: {tool['function']}")

        # 🎯 HERE: Generate dynamic system prompt based on server profile
        system_prompt = await self._generate_system_prompt(profile)
        
        # 🔧 FIX: Use the original query from workflow
        original_query = workflow.get("original_query", "Process this request")
        
        # Execute using OpenAI tool calling
        return await self._execute_openai_workflow(original_query, available_tools, system_prompt)
    
    async def _execute_openai_workflow(self, query: str, available_tools: List[dict], system_prompt: str) -> str:
        """Execute workflow using OpenAI tool calling (adapted from your proven client)."""
        # Initialize OpenAI client if needed
        if not hasattr(self, 'openai_client') or not self.openai_client:
            from openai import AsyncOpenAI
            api_key = await self.config.get_openai_api_key()
            self.openai_client = AsyncOpenAI(api_key=api_key)
        
        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        # Call OpenAI with tools
        response = await self.openai_client.chat.completions.create(
            model=self.config.openai_model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=messages,
            tools=[{k: v for k, v in tool.items() if not k.startswith('_')} for tool in available_tools]
        )
        
        # Process response (adapt your existing _process_response logic)
        return await self._process_universal_response(response, messages, available_tools)

    async def _process_universal_response(self, response, messages, available_tools):
        """Process OpenAI response with tool execution (simplified from your proven pattern)."""
        final_text = []
        message = response.choices[0].message
        
        if message.content:
            final_text.append(message.content)
        
        # Handle tool calls
        if message.tool_calls:
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [tc.model_dump() for tc in message.tool_calls]
            })
            
            # Execute each tool call
            for tool_call in message.tool_calls:
                await self._execute_single_tool(tool_call, available_tools, messages, final_text)
            
            # Check if workflow incomplete and continue (your proven continuation logic)
            if self._workflow_incomplete(messages):
                messages.append({
                    "role": "user", 
                    "content": "Continue with the next step in the workflow."
                })
                
                # Recursive call for continuation
                continue_response = await self.openai_client.chat.completions.create(
                    model=self.config.openai_model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    messages=messages,
                    tools=[{k: v for k, v in tool.items() if not k.startswith('_')} for tool in available_tools]
                )
                
                continuation = await self._process_universal_response(continue_response, messages, available_tools)
                final_text.append(continuation)
            else:
                # Get final response
                await self._get_final_response(messages, final_text)
        
        return "\n".join(final_text)

    async def _execute_single_tool(self, tool_call, available_tools, messages, final_text):
        """Execute a single tool call (adapted from your proven pattern)."""
        import json
        
        tool_name = tool_call.function.name
        try:
            tool_args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            tool_args = {}
        
        # Find tool info
        tool_info = next((t for t in available_tools if t["function"]["name"] == tool_name), None)
        if not tool_info:
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": f"Error: Tool '{tool_name}' not found"
            })
            return
        
        # Execute tool
        server_id = tool_info["_server_id"]
        original_name = tool_info["_original_name"]
        connection = self.server_manager.get_connection(server_id)
        
        try:
            logger.info(f"🔧 Executing {server_id}:{original_name} with args: {tool_args}")
            result = await connection.call_tool(original_name, tool_args)
            final_text.append(f"[Executed {server_id}:{original_name}]")
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result.content)
            })
        except Exception as e:
            error_msg = f"Tool execution failed: {e}"
            logger.error(f"❌ {error_msg}")
            final_text.append(f"[Error: {error_msg}]")
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": error_msg
            })

    def _workflow_incomplete(self, messages) -> bool:
        """Check if workflow is incomplete (your proven logic)."""
        recent_tools = []
        for msg in reversed(messages[-10:]):
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    recent_tools.append(tc["function"]["name"])
        
        # Check for weather workflow completion based on discovered patterns
        has_get_secret = any("get_secret" in tool for tool in recent_tools)
        has_build_url = any("build_api_url" in tool for tool in recent_tools) 
        has_http_request = any("http_request" in tool for tool in recent_tools)
        has_extract_data = any("extract_data_fields" in tool for tool in recent_tools)
        has_format_data = any("format_data" in tool for tool in recent_tools)
        
        completed_steps = sum([has_get_secret, has_build_url, has_http_request, has_extract_data, has_format_data])
        
        if 1 <= completed_steps < 5:
            logger.info(f"🔄 Workflow incomplete: {completed_steps}/5 steps completed")
            return True
        
        return False

    async def _get_final_response(self, messages, final_text):
        """Get final response from OpenAI."""
        try:
            final_response = await self.openai_client.chat.completions.create(
                model=self.config.openai_model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=messages
            )
            
            if final_response.choices[0].message.content:
                final_text.append(final_response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Error getting final response: {e}")
            final_text.append(f"[Error getting final response: {e}]")

    async def get_server_profiles(self) -> Dict[str, ServerProfile]:
        """Get all server profiles."""
        return self.server_profiles.copy()
    
    async def list_connected_servers(self) -> Dict[str, List[str]]:
        """List connected servers and their tools."""
        return await self.server_manager.list_connected_servers()
    
    async def shutdown(self) -> None:
        """Shutdown all connections."""
        logger.info("Shutting down Universal MCP client...")
        await self.server_manager.shutdown()
        logger.info("Universal MCP client shutdown complete")