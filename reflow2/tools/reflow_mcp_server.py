#!/usr/bin/env python3
"""
Reflow MCP (Model Context Protocol) Server

This server exposes reflow workflow resources, tools, and prompts through
the standardized MCP interface, enabling LLM clients to interact with
reflow workflows in a type-safe, discoverable manner.

Usage:
    python3 reflow_mcp_server.py --reflow-root /path/to/reflow [--port 3000]
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
import argparse
import subprocess
import logging

# Import secure path handling (v3.4.0 security fix - SV-01)
from path_utils import validate_system_root, PathSecurityError

# Import JSON validation (v3.4.0 security fix - SV-02)
from json_utils import safe_load_json, JSONValidationError

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Resource,
        Tool,
        TextContent,
        ImageContent,
        EmbeddedResource,
        Prompt,
        PromptMessage,
        GetPromptResult,
        INVALID_PARAMS,
        INTERNAL_ERROR
    )
except ImportError:
    print("ERROR: MCP SDK not installed")
    print("Install with: pip install mcp")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reflow-mcp-server")


class ReflowMCPServer:
    """MCP Server for Reflow Workflows"""
    
    def __init__(self, reflow_root: Path):
        self.reflow_root = Path(reflow_root).resolve()
        self.server = Server("reflow-mcp-server")
        self.current_system: Optional[str] = None
        
        # Verify reflow root
        if not (self.reflow_root / "tools").exists():
            raise RuntimeError(f"Invalid reflow root: {reflow_root}")
        
        # Register handlers
        self._register_resource_handlers()
        self._register_tool_handlers()
        self._register_prompt_handlers()
        
        logger.info(f"Reflow MCP Server initialized at {self.reflow_root}")
    
    def _register_resource_handlers(self):
        """Register MCP resource handlers"""
        
        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List all available reflow resources"""
            resources = []
            
            # Workflow definition resources
            resources.append(Resource(
                uri="reflow://workflow/decision_flow",
                name="Decision Flow Workflow",
                description="Main decision flow workflow definition",
                mimeType="application/json"
            ))
            
            # System resources (if current system is set)
            if self.current_system:
                system_path = self.reflow_root / "systems" / self.current_system
                if system_path.exists():
                    resources.extend([
                        Resource(
                            uri=f"reflow://system/{self.current_system}/context/memory",
                            name=f"{self.current_system} - Working Memory",
                            description="Current workflow state and system context",
                            mimeType="application/json"
                        ),
                        Resource(
                            uri=f"reflow://system/{self.current_system}/context/progress",
                            name=f"{self.current_system} - Progress Tracker",
                            description="Current step and substep progress",
                            mimeType="application/json"
                        ),
                        Resource(
                            uri=f"reflow://system/{self.current_system}/context/focus",
                            name=f"{self.current_system} - Current Focus",
                            description="Current workflow focus and objectives",
                            mimeType="text/markdown"
                        ),
                        Resource(
                            uri=f"reflow://system/{self.current_system}/context/log",
                            name=f"{self.current_system} - Process Log",
                            description="Detailed process execution log",
                            mimeType="text/markdown"
                        )
                    ])
            
            # List all available systems
            systems_dir = self.reflow_root / "systems"
            if systems_dir.exists():
                for system_dir in systems_dir.iterdir():
                    if system_dir.is_dir():
                        resources.append(Resource(
                            uri=f"reflow://systems/{system_dir.name}/info",
                            name=f"System: {system_dir.name}",
                            description=f"Information about {system_dir.name} system",
                            mimeType="application/json"
                        ))
            
            # RAG resources
            if self.current_system:
                embeddings_dir = system_path / "context" / "embeddings"
                if embeddings_dir.exists():
                    resources.append(Resource(
                        uri=f"reflow://rag/{self.current_system}/status",
                        name=f"{self.current_system} - RAG Status",
                        description="RAG embeddings generation status and metrics",
                        mimeType="application/json"
                    ))
            
            # Validation resources
            resources.append(Resource(
                uri="reflow://validation/tools_status",
                name="Validation Tools Status",
                description="Status of all validation tools",
                mimeType="application/json"
            ))
            
            return resources
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read a specific resource by URI"""
            logger.info(f"Reading resource: {uri}")
            
            if uri == "reflow://workflow/decision_flow":
                decision_flow_path = self.reflow_root / "decision_flow.json"
                with open(decision_flow_path, 'r') as f:
                    return f.read()
            
            # Parse system resource URIs
            if uri.startswith("reflow://system/"):
                parts = uri.replace("reflow://system/", "").split("/")
                system_name = parts[0]
                resource_type = "/".join(parts[1:])
                
                system_path = self.reflow_root / "systems" / system_name
                if not system_path.exists():
                    raise ValueError(f"System not found: {system_name}")
                
                if resource_type == "context/memory":
                    file_path = system_path / "context" / "working_memory.json"
                elif resource_type == "context/progress":
                    file_path = system_path / "context" / "step_progress_tracker.json"
                elif resource_type == "context/focus":
                    file_path = system_path / "context" / "current_focus.md"
                elif resource_type == "context/log":
                    file_path = system_path / "context" / "process_log.md"
                else:
                    raise ValueError(f"Unknown resource type: {resource_type}")
                
                if not file_path.exists():
                    return json.dumps({"error": f"File not found: {file_path.name}"})
                
                with open(file_path, 'r') as f:
                    return f.read()
            
            # System info
            if uri.startswith("reflow://systems/"):
                system_name = uri.replace("reflow://systems/", "").replace("/info", "")
                system_path = self.reflow_root / "systems" / system_name
                
                if not system_path.exists():
                    raise ValueError(f"System not found: {system_name}")
                
                # Gather system info
                info = {
                    "system_name": system_name,
                    "path": str(system_path),
                    "exists": True,
                    "has_context": (system_path / "context").exists(),
                    "has_specs": (system_path / "specs").exists(),
                    "has_services": (system_path / "services").exists(),
                    "has_docs": (system_path / "docs").exists()
                }
                
                # Check for key files
                if info["has_context"]:
                    context_files = ["working_memory.json", "step_progress_tracker.json", "current_focus.md"]
                    info["context_files"] = {
                        f: (system_path / "context" / f).exists() for f in context_files
                    }
                
                return json.dumps(info, indent=2)
            
            # RAG status
            if uri.startswith("reflow://rag/"):
                system_name = uri.replace("reflow://rag/", "").replace("/status", "")
                system_path = self.reflow_root / "systems" / system_name
                embeddings_dir = system_path / "context" / "embeddings"
                
                if not embeddings_dir.exists():
                    return json.dumps({"error": "RAG not initialized", "system": system_name})
                
                summary_file = embeddings_dir / "generation_summary.json"
                if summary_file.exists():
                    with open(summary_file, 'r') as f:
                        return f.read()
                else:
                    return json.dumps({"error": "No generation summary found"})
            
            # Validation tools status
            if uri == "reflow://validation/tools_status":
                tools_dir = self.reflow_root / "tools"
                validation_tools = [
                    "validate_architecture.py",
                    "system_of_systems_graph.py",
                    "validate_foundational_alignment.py",
                    "verify_component_contract.py"
                ]
                
                status = {
                    "tools": {
                        tool: (tools_dir / tool).exists() for tool in validation_tools
                    },
                    "all_available": all((tools_dir / tool).exists() for tool in validation_tools)
                }
                
                return json.dumps(status, indent=2)
            
            raise ValueError(f"Unknown resource URI: {uri}")
    
    def _register_tool_handlers(self):
        """Register MCP tool handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available reflow tools"""
            return [
                Tool(
                    name="set_current_system",
                    description="Set the current working system for subsequent operations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "system_name": {
                                "type": "string",
                                "description": "Name of the system to set as current"
                            }
                        },
                        "required": ["system_name"]
                    }
                ),
                Tool(
                    name="validate_architecture",
                    description="Validate service architecture JSON files for template compliance",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "system_name": {
                                "type": "string",
                                "description": "Name of the system to validate (uses current if not specified)"
                            }
                        }
                    }
                ),
                Tool(
                    name="generate_rag_embeddings",
                    description="Generate or update RAG embeddings for a system",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "system_name": {
                                "type": "string",
                                "description": "Name of the system (uses current if not specified)"
                            },
                            "force_rebuild": {
                                "type": "boolean",
                                "description": "Force rebuild even if embeddings are up-to-date",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="retrieve_rag_context",
                    description="Retrieve relevant context using RAG semantic search",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Query string for semantic search"
                            },
                            "strategy": {
                                "type": "string",
                                "enum": ["on_step_start", "on_degradation_detected", "on_tool_execution", "on_user_query", "periodic_refresh"],
                                "description": "Retrieval strategy to use"
                            },
                            "system_name": {
                                "type": "string",
                                "description": "System name (uses current if not specified)"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="verify_system_isolation",
                    description="Verify that the system is properly isolated (correct working directory)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "system_name": {
                                "type": "string",
                                "description": "System name to verify (uses current if not specified)"
                            }
                        }
                    }
                ),
                Tool(
                    name="analyze_system_structure",
                    description="Analyze the structure of a system for integration planning",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "system_name": {
                                "type": "string",
                                "description": "System name to analyze (uses current if not specified)"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_current_step_instructions",
                    description="Get detailed instructions for the current workflow step",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "system_name": {
                                "type": "string",
                                "description": "System name (uses current if not specified)"
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent]:
            """Execute a tool with given arguments"""
            logger.info(f"Calling tool: {name} with args: {arguments}")
            
            try:
                if name == "set_current_system":
                    system_name = arguments["system_name"]
                    system_path = self.reflow_root / "systems" / system_name
                    
                    if not system_path.exists():
                        return [TextContent(
                            type="text",
                            text=json.dumps({"error": f"System not found: {system_name}"})
                        )]
                    
                    self.current_system = system_name
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "current_system": system_name,
                            "system_path": str(system_path)
                        }, indent=2)
                    )]
                
                # Get system name for operations
                system_name = arguments.get("system_name", self.current_system)
                if not system_name:
                    return [TextContent(
                        type="text",
                        text=json.dumps({"error": "No system specified and no current system set. Use set_current_system first."})
                    )]
                
                system_path = self.reflow_root / "systems" / system_name
                
                if name == "validate_architecture":
                    result = subprocess.run(
                        ["python3", str(self.reflow_root / "tools" / "validate_architecture.py"), str(system_path)],
                        capture_output=True,
                        text=True
                    )
                    
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "tool": "validate_architecture",
                            "system": system_name,
                            "exit_code": result.returncode,
                            "stdout": result.stdout,
                            "stderr": result.stderr,
                            "success": result.returncode == 0
                        }, indent=2)
                    )]
                
                elif name == "generate_rag_embeddings":
                    force_flag = ["--force-rebuild"] if arguments.get("force_rebuild", False) else []
                    result = subprocess.run(
                        ["python3", str(self.reflow_root / "tools" / "generate_rag_embeddings.py"), str(system_path)] + force_flag,
                        capture_output=True,
                        text=True
                    )
                    
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "tool": "generate_rag_embeddings",
                            "system": system_name,
                            "exit_code": result.returncode,
                            "stdout": result.stdout,
                            "stderr": result.stderr,
                            "success": result.returncode == 0
                        }, indent=2)
                    )]
                
                elif name == "retrieve_rag_context":
                    query = arguments["query"]
                    strategy = arguments.get("strategy")
                    
                    cmd = ["python3", str(self.reflow_root / "tools" / "retrieve_rag_context.py"), str(system_path), "--query", query]
                    if strategy:
                        cmd.extend(["--strategy", strategy])
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    return [TextContent(
                        type="text",
                        text=result.stdout if result.returncode == 0 else json.dumps({
                            "error": "RAG retrieval failed",
                            "stderr": result.stderr
                        })
                    )]
                
                elif name == "verify_system_isolation":
                    # Check working_memory.json matches system name
                    memory_file = system_path / "context" / "working_memory.json"
                    if not memory_file.exists():
                        return [TextContent(
                            type="text",
                            text=json.dumps({"error": "working_memory.json not found", "isolated": False})
                        )]
                    
                    memory = safe_load_json(memory_file, file_type_description="working memory")
                    
                    isolated = memory.get("system_name") == system_name
                    
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "system_name": system_name,
                            "memory_system_name": memory.get("system_name"),
                            "isolated": isolated,
                            "system_path": str(system_path)
                        }, indent=2)
                    )]
                
                elif name == "analyze_system_structure":
                    tool_path = self.reflow_root / "tools" / "analyze_system_structure.py"
                    if not tool_path.exists():
                        return [TextContent(
                            type="text",
                            text=json.dumps({"error": "analyze_system_structure.py not found"})
                        )]
                    
                    result = subprocess.run(
                        ["python3", str(tool_path), str(system_path)],
                        capture_output=True,
                        text=True
                    )
                    
                    return [TextContent(
                        type="text",
                        text=result.stdout if result.returncode == 0 else json.dumps({
                            "error": "Analysis failed",
                            "stderr": result.stderr
                        })
                    )]
                
                elif name == "get_current_step_instructions":
                    # Read step_progress_tracker.json
                    tracker_file = system_path / "context" / "step_progress_tracker.json"
                    if not tracker_file.exists():
                        return [TextContent(
                            type="text",
                            text=json.dumps({"error": "step_progress_tracker.json not found"})
                        )]
                    
                    tracker = safe_load_json(tracker_file, file_type_description="step progress tracker")
                    
                    current_step = tracker.get("current_step")
                    
                    # Try to find workflow file for current step
                    workflow_dirs = ["architecture", "development", "feature_update"]
                    instructions = None
                    
                    for wf_dir in workflow_dirs:
                        workflow_path = self.reflow_root / wf_dir
                        if workflow_path.exists():
                            for wf_file in workflow_path.glob("*.json"):
                                try:
                                    wf_data = safe_load_json(wf_file, file_type_description="workflow file")
                                except JSONValidationError:
                                    continue

                                if "steps" in wf_data:
                                    for step in wf_data["steps"]:
                                        if step.get("id") == current_step or step.get("step_id") == current_step:
                                            instructions = step
                                            break
                                
                                if instructions:
                                    break
                        if instructions:
                            break
                    
                    if instructions:
                        return [TextContent(
                            type="text",
                            text=json.dumps({
                                "current_step": current_step,
                                "instructions": instructions
                            }, indent=2)
                        )]
                    else:
                        return [TextContent(
                            type="text",
                            text=json.dumps({
                                "current_step": current_step,
                                "error": "Instructions not found for current step"
                            })
                        )]
                
                else:
                    return [TextContent(
                        type="text",
                        text=json.dumps({"error": f"Unknown tool: {name}"})
                    )]
            
            except Exception as e:
                logger.error(f"Tool execution error: {e}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)})
                )]
    
    def _register_prompt_handlers(self):
        """Register MCP prompt handlers"""
        
        @self.server.list_prompts()
        async def list_prompts() -> List[Prompt]:
            """List all available prompt templates"""
            return [
                Prompt(
                    name="critical_behavioral_rules",
                    description="CRITICAL behavioral rules that must always be followed",
                    arguments=[]
                ),
                Prompt(
                    name="step_start_context",
                    description="Context for starting a new workflow step",
                    arguments=[
                        {"name": "step_id", "description": "Step identifier (e.g., Arch-01)", "required": True}
                    ]
                ),
                Prompt(
                    name="degradation_correction",
                    description="Corrective context when degradation is detected",
                    arguments=[
                        {"name": "signal_type", "description": "Type of degradation signal", "required": True}
                    ]
                ),
                Prompt(
                    name="system_context",
                    description="Complete system context (memory, progress, focus)",
                    arguments=[
                        {"name": "system_name", "description": "System name (uses current if not specified)", "required": False}
                    ]
                )
            ]
        
        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: Dict[str, str]) -> GetPromptResult:
            """Get a prompt template with arguments"""
            logger.info(f"Getting prompt: {name} with args: {arguments}")
            
            try:
                if name == "critical_behavioral_rules":
                    decision_flow_path = self.reflow_root / "decision_flow.json"
                    decision_flow = safe_load_json(decision_flow_path, file_type_description="decision flow")
                    
                    rules = decision_flow.get("context_management", {}).get("CRITICAL_BEHAVIORAL_RULES", {})
                    
                    prompt_text = "**CRITICAL BEHAVIORAL RULES - MANDATORY**\n\n"
                    prompt_text += "**NEVER GENERATE REPORTS:**\n"
                    for rule in rules.get("NEVER_GENERATE_REPORTS", []):
                        prompt_text += f"- {rule}\n"
                    
                    prompt_text += "\n**MANDATORY WORKFLOW ADHERENCE:**\n"
                    for rule in rules.get("MANDATORY_WORKFLOW_ADHERENCE", []):
                        prompt_text += f"- {rule}\n"
                    
                    prompt_text += "\n**CONTEXT CONTINUITY:**\n"
                    for rule in rules.get("CONTEXT_CONTINUITY", []):
                        prompt_text += f"- {rule}\n"
                    
                    return GetPromptResult(
                        description="Critical behavioral rules for workflow execution",
                        messages=[
                            PromptMessage(
                                role="user",
                                content=TextContent(type="text", text=prompt_text)
                            )
                        ]
                    )
                
                elif name == "step_start_context":
                    step_id = arguments.get("step_id")
                    if not step_id:
                        raise ValueError("step_id is required")
                    
                    # Get critical rules
                    decision_flow_path = self.reflow_root / "decision_flow.json"
                    decision_flow = safe_load_json(decision_flow_path, file_type_description="decision flow")
                    
                    rules = decision_flow.get("context_management", {}).get("CRITICAL_BEHAVIORAL_RULES", {})
                    
                    # Find step instructions
                    workflow_dirs = ["architecture", "development", "feature_update"]
                    instructions = None
                    
                    for wf_dir in workflow_dirs:
                        workflow_path = self.reflow_root / wf_dir
                        if workflow_path.exists():
                            for wf_file in workflow_path.glob("*.json"):
                                try:
                                    wf_data = safe_load_json(wf_file, file_type_description="workflow file")
                                except JSONValidationError:
                                    continue

                                if "steps" in wf_data:
                                    for step in wf_data["steps"]:
                                        if step.get("id") == step_id or step.get("step_id") == step_id:
                                            instructions = step
                                            break
                                
                                if instructions:
                                    break
                        if instructions:
                            break
                    
                    prompt_text = f"**STEP START CONTEXT: {step_id}**\n\n"
                    prompt_text += "**CRITICAL RULES:**\n"
                    for rule in rules.get("NEVER_GENERATE_REPORTS", [])[:3]:
                        prompt_text += f"- {rule}\n"
                    
                    prompt_text += f"\n**CURRENT STEP INSTRUCTIONS:**\n"
                    if instructions:
                        prompt_text += f"Step: {step_id}\n"
                        prompt_text += f"Description: {instructions.get('description', 'N/A')}\n"
                        prompt_text += f"\nFull Instructions:\n```json\n{json.dumps(instructions, indent=2)}\n```\n"
                    else:
                        prompt_text += f"Instructions not found for step {step_id}\n"
                    
                    return GetPromptResult(
                        description=f"Context for starting step {step_id}",
                        messages=[
                            PromptMessage(
                                role="user",
                                content=TextContent(type="text", text=prompt_text)
                            )
                        ]
                    )
                
                elif name == "degradation_correction":
                    signal_type = arguments.get("signal_type")
                    if not signal_type:
                        raise ValueError("signal_type is required")
                    
                    decision_flow_path = self.reflow_root / "decision_flow.json"
                    decision_flow = safe_load_json(decision_flow_path, file_type_description="decision flow")
                    
                    rules = decision_flow.get("context_management", {}).get("CRITICAL_BEHAVIORAL_RULES", {})
                    
                    prompt_text = f"**DEGRADATION DETECTED: {signal_type}**\n\n"
                    prompt_text += "**CORRECTIVE ACTION REQUIRED**\n\n"
                    
                    if "report" in signal_type.lower():
                        prompt_text += "**NEVER GENERATE REPORTS:**\n"
                        for rule in rules.get("NEVER_GENERATE_REPORTS", []):
                            prompt_text += f"- {rule}\n"
                    
                    if "workflow" in signal_type.lower():
                        prompt_text += "\n**MANDATORY WORKFLOW ADHERENCE:**\n"
                        for rule in rules.get("MANDATORY_WORKFLOW_ADHERENCE", []):
                            prompt_text += f"- {rule}\n"
                    
                    prompt_text += "\n**STOP CURRENT ACTION AND REVIEW THESE RULES BEFORE PROCEEDING**"
                    
                    return GetPromptResult(
                        description=f"Corrective context for {signal_type}",
                        messages=[
                            PromptMessage(
                                role="user",
                                content=TextContent(type="text", text=prompt_text)
                            )
                        ]
                    )
                
                elif name == "system_context":
                    system_name = arguments.get("system_name", self.current_system)
                    if not system_name:
                        raise ValueError("No system specified and no current system set")
                    
                    system_path = self.reflow_root / "systems" / system_name
                    
                    # Read context files
                    memory_file = system_path / "context" / "working_memory.json"
                    progress_file = system_path / "context" / "step_progress_tracker.json"
                    focus_file = system_path / "context" / "current_focus.md"
                    
                    prompt_text = f"**SYSTEM CONTEXT: {system_name}**\n\n"
                    
                    if memory_file.exists():
                        memory = safe_load_json(memory_file, file_type_description="working memory")
                        prompt_text += "**Working Memory:**\n```json\n"
                        prompt_text += json.dumps(memory, indent=2)
                        prompt_text += "\n```\n\n"
                    
                    if progress_file.exists():
                        progress = safe_load_json(progress_file, file_type_description="step progress tracker")
                        prompt_text += "**Progress Tracker:**\n```json\n"
                        prompt_text += json.dumps(progress, indent=2)
                        prompt_text += "\n```\n\n"
                    
                    if focus_file.exists():
                        with open(focus_file, 'r') as f:
                            focus = f.read()
                        prompt_text += "**Current Focus:**\n"
                        prompt_text += focus
                        prompt_text += "\n"
                    
                    return GetPromptResult(
                        description=f"Complete context for system {system_name}",
                        messages=[
                            PromptMessage(
                                role="user",
                                content=TextContent(type="text", text=prompt_text)
                            )
                        ]
                    )
                
                else:
                    raise ValueError(f"Unknown prompt: {name}")
            
            except Exception as e:
                logger.error(f"Prompt generation error: {e}", exc_info=True)
                raise
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    parser = argparse.ArgumentParser(description="Reflow MCP Server")
    parser.add_argument(
        "--reflow-root",
        default=".",
        help="Path to reflow root directory"
    )

    args = parser.parse_args()

    # Security: Validate reflow root path (v3.4.0 fix - SV-01)
    try:
        reflow_root = validate_system_root(args.reflow_root)
    except PathSecurityError as e:
        print(f"ERROR: Path security violation: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"ERROR: Reflow root does not exist: {args.reflow_root}")
        sys.exit(1)

    server = ReflowMCPServer(str(reflow_root))
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
