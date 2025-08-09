"""Dynamic system prompt generation through server intelligence."""
import re
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from src.discovery.server_profiler import ServerProfile, ToolCategory
from src.utils.log_config import get_logger

logger = get_logger(__name__)

@dataclass
class WorkflowStep:
    """Represents a step in an inferred workflow."""
    tool_name: str
    purpose: str
    dependencies: List[str]
    outputs: List[str]
    position: int  # Order in workflow

@dataclass
class WorkflowPattern:
    """Complete workflow pattern discovered through analysis."""
    name: str
    steps: List[WorkflowStep]
    description: str
    triggers: List[str]  # Query patterns that should trigger this workflow

class WorkflowInference:
    """Infers workflows by analyzing tool relationships."""
    
    def __init__(self):
        self.workflow_patterns = {
            # Common patterns we can detect
            "api_integration": ["secret", "url", "request", "extract", "format"],
            "data_processing": ["retrieve", "process", "format"],
            "caching": ["get_cached", "compute", "cache"],
            "ai_enhanced": ["process", "ai_completion", "format"]
        }
    
    async def infer_workflows(self, tools) -> List[WorkflowPattern]:
        """Infer likely workflows from tool analysis."""
        logger.info("🧠 Inferring workflows from tool analysis...")
        
        # Analyze tool dependencies
        dependencies = await self._analyze_tool_dependencies(tools)
        
        # Build workflow graphs
        workflows = await self._build_workflow_graphs(tools, dependencies)
        
        # Generate workflow patterns
        patterns = await self._generate_workflow_patterns(workflows)
        
        logger.info(f"🧠 Discovered {len(patterns)} workflow patterns")
        return patterns
    
    async def _analyze_tool_dependencies(self, tools) -> Dict[str, List[str]]:
        """Analyze what tools depend on outputs from other tools."""
        dependencies = {}
        
        for tool in tools:
            tool_deps = []
            tool_name = tool.name.lower()
            description = (tool.description or "").lower()
            
            # Analyze naming patterns for dependencies
            if "api" in tool_name or "http" in tool_name:
                # HTTP tools typically need URLs and possibly auth
                for other_tool in tools:
                    other_name = other_tool.name.lower()
                    if "url" in other_name or "secret" in other_name:
                        tool_deps.append(other_tool.name)
            
            elif "format" in tool_name or "extract" in tool_name:
                # Format/extract tools need data from HTTP or processing tools
                for other_tool in tools:
                    other_name = other_tool.name.lower()
                    if "http" in other_name or "request" in other_name or "get" in other_name:
                        tool_deps.append(other_tool.name)
            
            elif "ai" in tool_name:
                # AI tools typically come after data processing
                for other_tool in tools:
                    other_name = other_tool.name.lower()
                    if "format" in other_name or "extract" in other_name:
                        tool_deps.append(other_tool.name)
            
            dependencies[tool.name] = tool_deps
        
        return dependencies
    
    async def _build_workflow_graphs(self, tools, dependencies) -> List[List[str]]:
        """Build likely workflow sequences."""
        workflows = []
        
        # Find "starting" tools (tools with few/no dependencies)
        starting_tools = [
            tool.name for tool in tools 
            if len(dependencies.get(tool.name, [])) == 0 
            and any(pattern in tool.name.lower() for pattern in ["get", "secret", "start"])
        ]
        
        # Build workflows starting from each starting tool
        for start_tool in starting_tools:
            workflow = await self._trace_workflow_path(start_tool, tools, dependencies)
            if len(workflow) > 1:  # Only include multi-step workflows
                workflows.append(workflow)
        
        return workflows
    
    async def _trace_workflow_path(self, start_tool: str, tools, dependencies) -> List[str]:
        """Trace a workflow path from a starting tool."""
        path = [start_tool]
        current_tool = start_tool
        
        # Find tools that depend on the current tool
        while True:
            next_tools = [
                tool_name for tool_name, deps in dependencies.items()
                if current_tool in deps and tool_name not in path
            ]
            
            if not next_tools:
                break
            
            # Choose the most likely next tool based on naming patterns
            next_tool = await self._choose_next_tool(current_tool, next_tools)
            path.append(next_tool)
            current_tool = next_tool
        
        return path
    
    async def _choose_next_tool(self, current_tool: str, candidates: List[str]) -> str:
        """Choose the most likely next tool in sequence."""
        current_lower = current_tool.lower()
        
        # Priority rules based on common patterns
        if "secret" in current_lower:
            # After secret, usually comes URL building
            for candidate in candidates:
                if "url" in candidate.lower():
                    return candidate
        
        elif "url" in current_lower:
            # After URL, usually comes HTTP request
            for candidate in candidates:
                if "http" in candidate.lower() or "request" in candidate.lower():
                    return candidate
        
        elif "http" in current_lower or "request" in current_lower:
            # After HTTP, usually comes data extraction
            for candidate in candidates:
                if "extract" in candidate.lower() or "parse" in candidate.lower():
                    return candidate
        
        elif "extract" in current_lower:
            # After extraction, usually comes formatting
            for candidate in candidates:
                if "format" in candidate.lower():
                    return candidate
        
        # Default: return first candidate
        return candidates[0] if candidates else current_tool
    
    async def _generate_workflow_patterns(self, workflows: List[List[str]]) -> List[WorkflowPattern]:
        """Generate workflow patterns with descriptions."""
        patterns = []
        
        for i, workflow in enumerate(workflows):
            # Determine workflow type and triggers
            workflow_type, triggers = await self._classify_workflow(workflow)
            
            # Build workflow steps
            steps = []
            for j, tool_name in enumerate(workflow):
                step = WorkflowStep(
                    tool_name=tool_name,
                    purpose=await self._infer_tool_purpose(tool_name),
                    dependencies=workflow[:j],  # Previous tools in sequence
                    outputs=[],  # Will be filled if needed
                    position=j + 1
                )
                steps.append(step)
            
            # Create pattern
            pattern = WorkflowPattern(
                name=f"{workflow_type}_workflow",
                steps=steps,
                description=await self._generate_workflow_description(workflow, workflow_type),
                triggers=triggers
            )
            patterns.append(pattern)
        
        return patterns
    
    async def _classify_workflow(self, workflow: List[str]) -> Tuple[str, List[str]]:
        """Classify workflow type and determine query triggers."""
        workflow_text = " ".join(workflow).lower()
        
        # API Integration Pattern
        if any(keyword in workflow_text for keyword in ["secret", "url", "http", "request"]):
            triggers = ["data", "information", "get", "fetch", "what", "show"]
            return "api_integration", triggers
        
        # Data Processing Pattern
        elif any(keyword in workflow_text for keyword in ["process", "format", "extract"]):
            triggers = ["process", "analyze", "format", "parse"]
            return "data_processing", triggers
        
        # AI Enhanced Pattern
        elif "ai" in workflow_text:
            triggers = ["recommend", "suggest", "what should", "advice"]
            return "ai_enhanced", triggers
        
        else:
            return "general", ["help", "do", "can you"]
    
    async def _infer_tool_purpose(self, tool_name: str) -> str:
        """Infer the purpose of a tool from its name."""
        name_lower = tool_name.lower()
        
        if "secret" in name_lower:
            return "Retrieve authentication credentials"
        elif "url" in name_lower:
            return "Build API endpoint URL"
        elif "http" in name_lower or "request" in name_lower:
            return "Make external API call"
        elif "extract" in name_lower:
            return "Extract specific data fields"
        elif "format" in name_lower:
            return "Format data for human reading"
        elif "ai" in name_lower:
            return "Generate AI-enhanced insights"
        elif "cache" in name_lower:
            return "Cache data for performance"
        else:
            return f"Execute {tool_name} operation"
    
    async def _generate_workflow_description(self, workflow: List[str], workflow_type: str) -> str:
        """Generate a description of the workflow."""
        if workflow_type == "api_integration":
            return f"Complete {len(workflow)}-step API integration: " + " → ".join(workflow)
        else:
            return f"{workflow_type.title()} workflow with {len(workflow)} steps"

class DynamicPromptGenerator:
    """Generates system prompts dynamically based on server analysis."""
    
    def __init__(self):
        self.workflow_inference = WorkflowInference()
    
    async def generate_system_prompt(self, profile: ServerProfile, tools) -> str:
        """Generate dynamic system prompt based on server analysis."""
        logger.info(f"🧠 Generating dynamic system prompt for {profile.domain} domain...")
        
        # Infer workflows from tool analysis
        workflows = await self.workflow_inference.infer_workflows(tools)
        
        # Build dynamic prompt sections
        sections = [
            await self._generate_header(profile),
            await self._generate_workflow_instructions(workflows, profile),
            await self._generate_tool_categories(profile),
            await self._generate_continuation_rules(workflows),
            await self._generate_domain_specific_rules(profile, workflows)
        ]
        
        prompt = "\n\n".join(filter(None, sections))
        logger.info(f"✅ Generated {len(prompt)} character dynamic system prompt")
        return prompt
    
    async def _generate_header(self, profile: ServerProfile) -> str:
        """Generate dynamic header based on domain."""
        domain = profile.domain or "general purpose"
        tool_count = len(profile.tools)
        
        return f"""You are an intelligent {domain} agent with access to {tool_count} specialized tools.

🎯 CRITICAL: Most tasks require MULTIPLE tool calls in sequence. Break every task into atomic steps and execute complete workflows."""
    
    async def _generate_workflow_instructions(self, workflows: List[WorkflowPattern], profile: ServerProfile) -> str:
        """Generate workflow instructions based on discovered patterns."""
        if not workflows:
            return "Execute tools in logical sequence based on dependencies."
        
        instructions = ["📋 DISCOVERED WORKFLOWS:"]
        
        for workflow in workflows:
            steps = " → ".join([f"{step.position}. {step.tool_name}" for step in workflow.steps])
            instructions.append(f"• {workflow.name.upper()}: {steps}")
            instructions.append(f"  Purpose: {workflow.description}")
            if workflow.triggers:
                triggers = ", ".join(workflow.triggers)
                instructions.append(f"  Triggered by: queries containing '{triggers}'")
        
        instructions.append("\n⚠️ Execute ALL steps in discovered workflows - don't stop after the first tool.")
        
        return "\n".join(instructions)
    
    async def _generate_tool_categories(self, profile: ServerProfile) -> str:
        """Generate tool category information."""
        categories = []
        for category, tools in profile.tool_categories.items():
            if tools:  # Only include categories with tools
                tool_list = ", ".join(tools)
                categories.append(f"• {category.value.title()}: {tool_list}")
        
        if categories:
            return "🔧 AVAILABLE TOOL CATEGORIES:\n" + "\n".join(categories)
        return ""
    
    async def _generate_continuation_rules(self, workflows: List[WorkflowPattern]) -> str:
        """Generate continuation rules based on workflow analysis."""
        max_steps = max([len(w.steps) for w in workflows]) if workflows else 3
        
        return f"""⚡ EXECUTION RULES:
• Execute up to {max_steps} tools in sequence without stopping
• Continue automatically between workflow steps
• Don't ask permission between tool calls
• Complete entire workflows before providing final response"""
    
    async def _generate_domain_specific_rules(self, profile: ServerProfile, workflows: List[WorkflowPattern]) -> str:
        """Generate domain-specific rules based on analysis."""
        rules = []
        
        # Weather domain specific secret guidance  
        if profile.domain == "weather":
            rules.append("🔑 CRITICAL: For get_secret tool, use EXACT secret name 'OWM-API-KEY'")
            rules.append("❌ DO NOT guess secret names like 'weather_api_key' - use 'OWM-API-KEY'")
            rules.append("🌤️ Weather API requires OpenWeatherMap key stored as 'OWM-API-KEY' in Key Vault")
        
        # Check for API integration workflow
        has_api = any("api" in w.name.lower() for w in workflows)
        if has_api:
            rules.append("🌐 For external data: Always retrieve fresh information via API calls")
        
        # Check for caching tools
        has_caching = any("cache" in w.name.lower() for w in workflows)  
        if has_caching:
            rules.append("💾 Use caching tools for performance optimization")
        
        # Check for AI enhancement
        has_ai = any("ai" in w.name.lower() for w in workflows)
        if has_ai:
            rules.append("🤖 Provide AI-enhanced insights when available")
        
        if rules:
            return "🎯 DOMAIN-SPECIFIC GUIDANCE:\n" + "\n".join(rules)
        
        return ""