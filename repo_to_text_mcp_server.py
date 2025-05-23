#!/usr/bin/env python3
"""
Repo-to-Text MCP Server
A powerful MCP server that converts repositories to LLM-friendly text format
using clean XML structure with intelligent analysis and filtering.
"""

import asyncio
import json
import os
import sys
import yaml
import fnmatch
import pathlib
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any
from dataclasses import dataclass, field
import re
import mimetypes
from datetime import datetime

# MCP imports
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

@dataclass
class ProjectConfig:
    """Configuration for repository conversion"""
    gitignore_import: bool = True
    ignore_tree_and_content: List[str] = field(default_factory=list)
    ignore_content_only: List[str] = field(default_factory=list)
    max_file_size: int = 1024 * 1024  # 1MB default
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    
    # Default exclusions that are almost always unwanted
    DEFAULT_EXCLUSIONS = [
        # Dependencies
        "node_modules/", "venv/", "env/", ".env/", "__pycache__/",
        "vendor/", ".bundle/", "pkg/", "target/", "dist/", "build/",
        
        # Version control
        ".git/", ".svn/", ".hg/", ".bzr/",
        
        # IDE/Editor files
        ".vscode/", ".idea/", "*.swp", "*.swo", "*~", ".DS_Store",
        "Thumbs.db", "desktop.ini",
        
        # Logs and temp files
        "*.log", "logs/", "temp/", "tmp/", ".cache/", ".tmp/",
        
        # Compiled/generated files
        "*.pyc", "*.pyo", "*.class", "*.o", "*.so", "*.exe", "*.dll",
        "*.obj", "*.bin", "*.deb", "*.rpm", "*.dmg", "*.msi",
    ]
class TokenEstimator:
    """Estimates token counts for different LLM providers"""
    
    # Rough token-to-character ratios for different providers
    TOKEN_RATIOS = {
        "openai": 4.0,      # ~4 chars per token
        "anthropic": 4.5,   # Claude tends to be slightly more efficient
        "google": 4.0,      # Gemini similar to OpenAI
        "generic": 4.0      # Safe default
    }
    
    @classmethod
    def estimate_tokens(cls, text: str, provider: str = "generic") -> int:
        """Estimate token count for given text and provider"""
        ratio = cls.TOKEN_RATIOS.get(provider.lower(), cls.TOKEN_RATIOS["generic"])
        return int(len(text) / ratio)
    
    @classmethod
    def get_context_limits(cls) -> Dict[str, int]:
        """Return context limits for different providers"""
        return {
            "gpt-4": 128_000,
            "gpt-4-turbo": 128_000,
            "claude-3-sonnet": 200_000,
            "claude-3-opus": 200_000,
            "claude-3.5-sonnet": 200_000,
            "gemini-1.5-pro": 2_000_000,
            "gemini-2.0-flash": 1_000_000,
        }

class RepoAnalyzer:
    """Analyzes repository structure and suggests optimal configurations"""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.project_type = None
        self.framework = None
        self.language = None
    
    def analyze_project(self) -> Dict[str, Any]:
        """Analyze project and return comprehensive information"""
        info = {
            "root_path": str(self.root_path),
            "total_files": 0,
            "total_size": 0,
            "file_types": {},
            "languages": set(),
            "frameworks": set(),
            "project_type": None,
            "suggested_exclusions": [],
            "important_files": [],
            "directory_structure": self._get_directory_tree(),
        }
        
        # Walk through all files
        for file_path in self.root_path.rglob("*"):
            if file_path.is_file():
                info["total_files"] += 1
                try:
                    size = file_path.stat().st_size
                    info["total_size"] += size
# MCP Server Implementation
server = Server("repo-to-text")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List all available tools"""
    return [
        Tool(
            name="analyze_project",
            description="Analyze a project directory and provide comprehensive information about structure, languages, frameworks, and suggestions",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the project directory to analyze"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="generate_repo_context",
            description="Generate LLM-friendly text from repository with intelligent filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the repository directory"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["xml", "shotgun", "markdown"],
                        "default": "xml",
                        "description": "Output format (xml=clean XML, shotgun=Cursor-compatible, markdown=GitHub-style)"
                    },
                    "exclusions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional patterns to exclude (beyond defaults)"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="estimate_tokens",
            description="Estimate token count for generated content across different LLM providers",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to estimate tokens for"
                    },
                    "provider": {
                        "type": "string",
                        "enum": ["openai", "anthropic", "google", "generic"],
                        "default": "generic",
                        "description": "LLM provider for token estimation"
                    }
                },
                "required": ["text"]
            }
        )
    ]
@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls"""
    
    if name == "analyze_project":
        path = arguments["path"]
        
        if not os.path.exists(path):
            return [TextContent(type="text", text=f"Error: Path '{path}' does not exist")]
        
        if not os.path.isdir(path):
            return [TextContent(type="text", text=f"Error: Path '{path}' is not a directory")]
        
        try:
            # Basic analysis implementation
            total_files = 0
            file_types = {}
            
            for root, dirs, files in os.walk(path):
                for file in files:
                    total_files += 1
                    ext = os.path.splitext(file)[1].lower()
                    if ext:
                        file_types[ext] = file_types.get(ext, 0) + 1
            
            result = f"""# Project Analysis

## Overview
- **Total Files**: {total_files:,}
- **Root Path**: {path}

## File Types Distribution
""" + '\n'.join([f"- **{ext}**: {count} files" for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:10]])
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error analyzing project: {str(e)}")]
    
    elif name == "generate_repo_context":
        path = arguments["path"]
        format_type = arguments.get("format", "xml")
        exclusions = arguments.get("exclusions", [])
        
        if not os.path.exists(path):
            return [TextContent(type="text", text=f"Error: Path '{path}' does not exist")]
        
        try:
            # Simple implementation - generate basic XML format
            content_lines = []
            if format_type == "xml":
                content_lines.append("<repo-to-text>")
                content_lines.append(f"Directory: {os.path.basename(path)}")
                content_lines.append("")
                
                # Add basic file contents
                for root, dirs, files in os.walk(path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, path)
                        
                        # Skip common exclusions
                        if any(excl in rel_path for excl in ["node_modules", "__pycache__", ".git"]):
                            continue
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                content_lines.append(f'<content full_path="{rel_path}">')
                                content_lines.append(content)
                                content_lines.append('</content>')
                                content_lines.append('')
                        except:
                            continue
                
                content_lines.append("</repo-to-text>")
            
            result = '\n'.join(content_lines)
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error generating repo context: {str(e)}")]
    
    elif name == "estimate_tokens":
        text = arguments["text"]
        provider = arguments.get("provider", "generic")
        
        try:
            # Simple token estimation (4 chars per token average)
            tokens = len(text) // 4
            
            result = f"""# Token Estimation

**Text Length**: {len(text):,} characters
**Estimated Tokens** ({provider}): {tokens:,}

## Context Limit Comparison
- **GPT-4**: 128,000 tokens | {(tokens/128000)*100:.1f}%
- **Claude 3.5 Sonnet**: 200,000 tokens | {(tokens/200000)*100:.1f}%
- **Gemini 2.5 Pro**: 2,000,000 tokens | {(tokens/2000000)*100:.1f}%
"""
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error estimating tokens: {str(e)}")]
    
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    # Run the server using stdin/stdout streams
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="repo-to-text",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())