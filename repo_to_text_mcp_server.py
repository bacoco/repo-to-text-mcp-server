#!/usr/bin/env python3
"""
Repo-to-Text MCP Server with Shotgun-like AI Task Generation
A powerful MCP server that converts repositories to LLM-friendly text format
and uses Gemini to generate complete implementation directives for Cursor/Windsurf/Claude Desktop.
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
from typing import Dict, List, Optional, Set, Union, Any, Tuple
from dataclasses import dataclass, field
import re
import mimetypes
from datetime import datetime
import textwrap

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
        
        # Media files
        "*.jpg", "*.jpeg", "*.png", "*.gif", "*.ico", "*.svg",
        "*.mp3", "*.mp4", "*.avi", "*.mov", "*.wmv",
        
        # Archives
        "*.zip", "*.tar", "*.tar.gz", "*.rar", "*.7z",
        
        # Database files
        "*.db", "*.sqlite", "*.sqlite3",
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
    
    @staticmethod
    def detect_project_type(path: str) -> Dict[str, Any]:
        """Detect project type and suggest optimal exclusions"""
        indicators = {
            "python": ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile"],
            "node": ["package.json", "yarn.lock", "package-lock.json"],
            "react": ["package.json"],  # Check for react in deps
            "vue": ["vue.config.js", "nuxt.config.js"],
            "go": ["go.mod", "go.sum"],
            "rust": ["Cargo.toml", "Cargo.lock"],
            "java": ["pom.xml", "build.gradle", "gradle.build"],
            "dotnet": ["*.csproj", "*.sln"],
        }
        
        detected = []
        for proj_type, files in indicators.items():
            for file_pattern in files:
                if any(Path(path).rglob(file_pattern)):
                    detected.append(proj_type)
                    break
        
        return {
            "types": detected,
            "main_type": detected[0] if detected else "generic",
            "suggested_exclusions": RepoAnalyzer._get_exclusions_for_type(detected)
        }
    
    @staticmethod
    def _get_exclusions_for_type(project_types: List[str]) -> List[str]:
        """Get recommended exclusions based on project type"""
        exclusions = set(ProjectConfig.DEFAULT_EXCLUSIONS)
        
        type_specific = {
            "python": ["*.pyc", "__pycache__/", "*.egg-info/", ".pytest_cache/", "htmlcov/"],
            "node": ["node_modules/", "coverage/", ".next/", ".nuxt/"],
            "react": ["build/", "dist/"],
            "java": ["target/", "*.class", ".gradle/"],
            "rust": ["target/", "Cargo.lock"],
            "go": ["vendor/", "bin/"],
        }
        
        for proj_type in project_types:
            if proj_type in type_specific:
                exclusions.update(type_specific[proj_type])
        
        return sorted(list(exclusions))

class RepoToTextConverter:
    """Main converter class with multiple output formats"""
    
    def __init__(self, config: Optional[ProjectConfig] = None):
        self.config = config or ProjectConfig()
    
    def _should_include_file(self, file_path: str) -> bool:
        """Check if file should be included based on patterns"""
        # Check exclusions
        for pattern in self.config.exclude_patterns + self.config.DEFAULT_EXCLUSIONS:
            if fnmatch.fnmatch(file_path, pattern) or pattern in file_path:
                return False
        
        # Check if it's a binary file
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and not mime_type.startswith('text/'):
            return False
        
        # Check file size
        try:
            if os.path.getsize(file_path) > self.config.max_file_size:
                return False
        except:
            return False
        
        return True
    
    def generate_xml_format(self, root_path: str) -> str:
        """Generate clean XML format output"""
        lines = []
        lines.append("<repo-to-text>")
        lines.append(f"Directory: {os.path.basename(root_path)}")
        lines.append("")
        
        # Add directory structure
        lines.append("<directory_structure>")
        for root, dirs, files in os.walk(root_path):
            level = root.replace(root_path, '').count(os.sep)
            indent = ' ' * 2 * level
            lines.append(f"{indent}{os.path.basename(root)}/")
            sub_indent = ' ' * 2 * (level + 1)
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), root_path)
                if self._should_include_file(rel_path):
                    lines.append(f"{sub_indent}{file}")
        lines.append("</directory_structure>")
        lines.append("")
        
        # Add file contents
        for root, dirs, files in os.walk(root_path):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, root_path)
                
                if self._should_include_file(rel_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            lines.append(f'<content full_path="{rel_path}">')
                            lines.append(content)
                            lines.append('</content>')
                            lines.append('')
                    except Exception as e:
                        lines.append(f'<!-- Error reading {rel_path}: {str(e)} -->')
        
        lines.append("</repo-to-text>")
        return '\n'.join(lines)
    
    def generate_shotgun_format(self, root_path: str) -> str:
        """Generate Shotgun-compatible format"""
        lines = []
        
        for root, dirs, files in os.walk(root_path):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, root_path)
                
                if self._should_include_file(rel_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            lines.append(f"*#*#*{rel_path}*#*#*begin*#*#*")
                            lines.append(content)
                            lines.append("*#*#*end*#*#*")
                            lines.append("")
                    except:
                        continue
        
        return '\n'.join(lines)

class GeminiTaskGenerator:
    """Generates implementation tasks using Gemini's context understanding"""
    
    TASK_PROMPT_TEMPLATE = """
You are an expert software architect helping to implement new features. Analyze this codebase and requirements:

## Project Context
{project_context}

## Project Structure Analysis
{project_analysis}

## Requirements
{requirements}

## Task Type: {task_type}
## Complexity: {complexity}

Generate a comprehensive implementation plan with:

1. **Overview**: Brief summary of what needs to be done
2. **Architecture Changes**: Any structural changes needed
3. **Implementation Steps**: Detailed step-by-step implementation guide
4. **File Modifications**: Specific files to create/modify with exact changes
5. **Code Examples**: Concrete code snippets for key parts
6. **Testing Strategy**: How to test the implementation
7. **Potential Issues**: Common pitfalls and how to avoid them

Format your response for easy parsing into IDE-specific directives.
Use clear headers and bullet points.
Be extremely specific about file paths and code changes.
"""

    DIRECTIVE_FORMAT_TEMPLATE = """
Convert this implementation plan into {target_ide} directives:

{implementation_plan}

Format as step-by-step instructions that can be directly executed in {target_ide}.
Each directive should be actionable and specific.
Include exact file paths and code snippets.
"""

    @staticmethod
    def create_task_prompt(project_context: str, project_analysis: Dict, 
                          requirements: str, task_type: str, complexity: str) -> str:
        """Create prompt for Gemini to generate implementation tasks"""
        return GeminiTaskGenerator.TASK_PROMPT_TEMPLATE.format(
            project_context=project_context,
            project_analysis=json.dumps(project_analysis, indent=2),
            requirements=requirements,
            task_type=task_type,
            complexity=complexity
        )
    
    @staticmethod
    def parse_gemini_response(response: str) -> Dict[str, Any]:
        """Parse Gemini's response into structured tasks"""
        sections = {
            "overview": "",
            "architecture_changes": [],
            "implementation_steps": [],
            "file_modifications": [],
            "code_examples": [],
            "testing_strategy": "",
            "potential_issues": []
        }
        
        current_section = None
        current_content = []
        
        for line in response.split('\n'):
            # Detect section headers
            lower_line = line.lower().strip()
            if "overview" in lower_line and line.startswith("#"):
                current_section = "overview"
                current_content = []
            elif "architecture" in lower_line and line.startswith("#"):
                current_section = "architecture_changes"
                current_content = []
            elif "implementation" in lower_line and "step" in lower_line and line.startswith("#"):
                current_section = "implementation_steps"
                current_content = []
            elif "file" in lower_line and "modif" in lower_line and line.startswith("#"):
                current_section = "file_modifications"
                current_content = []
            elif "code" in lower_line and "example" in lower_line and line.startswith("#"):
                current_section = "code_examples"
                current_content = []
            elif "test" in lower_line and line.startswith("#"):
                current_section = "testing_strategy"
                current_content = []
            elif "issue" in lower_line and line.startswith("#"):
                current_section = "potential_issues"
                current_content = []
            elif current_section:
                current_content.append(line)
                
                # Update section content
                if current_section in ["overview", "testing_strategy"]:
                    sections[current_section] = '\n'.join(current_content).strip()
                else:
                    sections[current_section] = current_content
        
        return sections

    @staticmethod
    def format_for_cursor(tasks: Dict[str, Any], project_context: str = "") -> str:
        """Format tasks as Cursor/Windsurf directives"""
        output = []
        
        output.append("# 🎯 CURSOR IMPLEMENTATION DIRECTIVES")
        output.append("# Auto-generated by Repo-to-Text MCP Server (Shotgun Mode)")
        output.append(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append("")
        
        # Overview
        if tasks.get("overview"):
            output.append("## 📋 TASK OVERVIEW")
            output.append(tasks["overview"])
            output.append("")
        
        # Architecture changes
        if tasks.get("architecture_changes"):
            output.append("## 🏗️ ARCHITECTURE CHANGES")
            for change in tasks["architecture_changes"]:
                if change.strip():
                    output.append(f"- {change.strip()}")
            output.append("")
        
        # Implementation steps
        if tasks.get("implementation_steps"):
            output.append("## 📝 IMPLEMENTATION STEPS")
            for i, step in enumerate(tasks["implementation_steps"], 1):
                if step.strip():
                    output.append(f"\n### Step {i}")
                    output.append(step.strip())
            output.append("")
        
        # File modifications
        if tasks.get("file_modifications"):
            output.append("## 📁 FILE MODIFICATIONS")
            for mod in tasks["file_modifications"]:
                if mod.strip():
                    output.append(f"\n{mod.strip()}")
            output.append("")
        
        # Code examples
        if tasks.get("code_examples"):
            output.append("## 💻 CODE EXAMPLES")
            for example in tasks["code_examples"]:
                if example.strip():
                    output.append(example.strip())
            output.append("")
        
        # Testing
        if tasks.get("testing_strategy"):
            output.append("## 🧪 TESTING STRATEGY")
            output.append(tasks["testing_strategy"])
            output.append("")
        
        # Include project context if requested
        if project_context:
            output.append("\n" + "="*80)
            output.append("# PROJECT CONTEXT (for reference)")
            output.append("="*80)
            output.append(project_context)
        
        return '\n'.join(output)

    @staticmethod
    def format_for_claude_desktop(tasks: Dict[str, Any]) -> str:
        """Format tasks as Claude Desktop task breakdown"""
        output = []
        
        output.append("<!-- CLAUDE TASK MASTER -->")
        output.append("<!-- Auto-generated implementation tasks -->")
        output.append("")
        
        # Create task list
        output.append("## 🎯 Implementation Tasks")
        output.append("")
        
        task_count = 0
        
        # Convert architecture changes to tasks
        if tasks.get("architecture_changes"):
            for change in tasks["architecture_changes"]:
                if change.strip():
                    task_count += 1
                    output.append(f"### Task {task_count}: Architecture - {change.strip()}")
                    output.append("**Priority**: High")
                    output.append("**Status**: ⏳ Pending")
                    output.append("")
        
        # Convert implementation steps to tasks
        if tasks.get("implementation_steps"):
            for step in tasks["implementation_steps"]:
                if step.strip():
                    task_count += 1
                    # Extract first line as task title
                    lines = step.strip().split('\n')
                    title = lines[0].strip('- ').strip()
                    output.append(f"### Task {task_count}: {title}")
                    output.append("**Priority**: Medium")
                    output.append("**Status**: ⏳ Pending")
                    if len(lines) > 1:
                        output.append("**Details**:")
                        for line in lines[1:]:
                            output.append(line)
                    output.append("")
        
        # Add testing as final task
        if tasks.get("testing_strategy"):
            task_count += 1
            output.append(f"### Task {task_count}: Testing & Validation")
            output.append("**Priority**: High")
            output.append("**Status**: ⏳ Pending")
            output.append("**Details**:")
            output.append(tasks["testing_strategy"])
            output.append("")
        
        output.append(f"\n**Total Tasks**: {task_count}")
        output.append("**Estimated Complexity**: Based on Gemini analysis")
        
        return '\n'.join(output)

# Initialize the MCP server
server = Server("repo-to-text")

# Define available tools
@server.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools"""
    return [
        Tool(
            name="analyze_project",
            description="Analyze a project directory to understand its structure and suggest optimal settings",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the project directory"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="generate_repo_context",
            description="Convert repository to LLM-friendly text format with intelligent filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the repository"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["xml", "shotgun", "markdown"],
                        "default": "xml",
                        "description": "Output format"
                    },
                    "exclusions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                        "description": "Additional patterns to exclude"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="estimate_tokens",
            description="Estimate token count for different LLM providers",
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
                        "description": "LLM provider"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="generate_implementation_tasks",
            description="Generate implementation tasks using Gemini 2.5 Pro's understanding of your codebase",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project directory"
                    },
                    "requirements": {
                        "type": "string",
                        "description": "Detailed description of new functionality or changes needed"
                    },
                    "task_type": {
                        "type": "string",
                        "enum": ["feature", "refactor", "bugfix", "optimization", "documentation", "testing"],
                        "default": "feature",
                        "description": "Type of task being requested"
                    },
                    "target_ide": {
                        "type": "string",
                        "enum": ["cursor", "windsurf", "claude-desktop", "generic"],
                        "default": "cursor",
                        "description": "Target IDE for implementation directives"
                    },
                    "complexity": {
                        "type": "string",
                        "enum": ["simple", "moderate", "complex", "architectural"],
                        "default": "moderate",
                        "description": "Complexity level of the requested changes"
                    }
                },
                "required": ["project_path", "requirements"]
            }
        ),
        Tool(
            name="parse_gemini_response",
            description="Parse Gemini's response into actionable tasks and implementation directives",
            inputSchema={
                "type": "object",
                "properties": {
                    "gemini_response": {
                        "type": "string",
                        "description": "The complete response from Gemini 2.5 Pro"
                    },
                    "target_ide": {
                        "type": "string",
                        "enum": ["cursor", "windsurf", "claude-desktop", "generic"],
                        "default": "cursor",
                        "description": "Target IDE for formatting directives"
                    },
                    "create_tasks": {
                        "type": "boolean",
                        "default": True,
                        "description": "Create Claude task breakdown"
                    }
                },
                "required": ["gemini_response"]
            }
        ),
        Tool(
            name="generate_implementation_plan",
            description="Complete Shotgun workflow: analyze project + requirements → create Gemini prompt → format for IDE implementation",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project directory"
                    },
                    "requirements": {
                        "type": "string",
                        "description": "Detailed description of what you want to implement"
                    },
                    "target_ide": {
                        "type": "string",
                        "enum": ["cursor", "windsurf", "claude-desktop"],
                        "default": "cursor",
                        "description": "Target IDE for implementation"
                    },
                    "include_context": {
                        "type": "boolean",
                        "default": True,
                        "description": "Include full project context in output"
                    }
                },
                "required": ["project_path", "requirements"]
            }
        ),
        Tool(
            name="apply_patch",
            description="Apply a patch or set of changes back to the codebase",
            inputSchema={
                "type": "object",
                "properties": {
                    "patch_content": {
                        "type": "string",
                        "description": "The patch content or changes to apply"
                    },
                    "target_path": {
                        "type": "string",
                        "description": "Target directory to apply changes"
                    },
                    "dry_run": {
                        "type": "boolean",
                        "default": True,
                        "description": "Preview changes without applying"
                    }
                },
                "required": ["patch_content", "target_path"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[Union[TextContent, ImageContent, EmbeddedResource]]:
    """Handle tool calls"""
    
    if name == "analyze_project":
        path = arguments["path"]
        
        if not os.path.exists(path):
            return [TextContent(type="text", text=f"Error: Path '{path}' does not exist")]
        
        try:
            analyzer = RepoAnalyzer()
            project_info = analyzer.detect_project_type(path)
            
            # Count files
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
- **Detected Type(s)**: {', '.join(project_info['types']) or 'Generic'}

## File Types Distribution
""" + '\n'.join([f"- **{ext}**: {count} files" for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:10]])

            result += f"\n\n## Suggested Exclusions\n"
            for excl in project_info['suggested_exclusions'][:15]:
                result += f"- `{excl}`\n"
            
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
            config = ProjectConfig()
            config.exclude_patterns.extend(exclusions)
            converter = RepoToTextConverter(config)
            
            if format_type == "xml":
                result = converter.generate_xml_format(path)
            elif format_type == "shotgun":
                result = converter.generate_shotgun_format(path)
            else:
                result = converter.generate_xml_format(path)  # Default to XML
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error generating repo context: {str(e)}")]
    
    elif name == "estimate_tokens":
        text = arguments["text"]
        provider = arguments.get("provider", "generic")
        
        try:
            tokens = TokenEstimator.estimate_tokens(text, provider)
            limits = TokenEstimator.get_context_limits()
            
            result = f"""# Token Estimation

**Text Length**: {len(text):,} characters
**Estimated Tokens** ({provider}): {tokens:,}

## Context Limit Comparison
"""
            for model, limit in limits.items():
                percentage = (tokens/limit)*100
                result += f"- **{model}**: {limit:,} tokens | {percentage:.1f}% used\n"
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error estimating tokens: {str(e)}")]
    
    elif name == "generate_implementation_tasks":
        project_path = arguments["project_path"]
        requirements = arguments["requirements"]
        task_type = arguments.get("task_type", "feature")
        target_ide = arguments.get("target_ide", "cursor")
        complexity = arguments.get("complexity", "moderate")
        
        if not os.path.exists(project_path):
            return [TextContent(type="text", text=f"Error: Project path '{project_path}' does not exist")]
        
        try:
            # Generate project context
            config = ProjectConfig()
            converter = RepoToTextConverter(config)
            project_context = converter.generate_xml_format(project_path)
            
            # Analyze project
            analyzer = RepoAnalyzer()
            project_analysis = analyzer.detect_project_type(project_path)
            
            # Create Gemini prompt
            task_prompt = GeminiTaskGenerator.create_task_prompt(
                project_context=project_context,
                project_analysis=project_analysis,
                requirements=requirements,
                task_type=task_type,
                complexity=complexity
            )
            
            result = f"""# Generated Implementation Task Prompt

## Instructions for Gemini 2.5 Pro
Copy this prompt to Gemini 2.5 Pro to generate complete implementation directives:

```
{task_prompt}
```

## Next Steps:
1. Copy the above prompt to Gemini 2.5 Pro
2. Use the 'parse_gemini_response' tool with Gemini's response
3. The parsed result will be formatted for {target_ide}

## Project Stats:
- Context size: ~{TokenEstimator.estimate_tokens(project_context):,} tokens
- Project type: {', '.join(project_analysis['types'])}
- Task complexity: {complexity}
"""
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error generating implementation tasks: {str(e)}")]
    
    elif name == "parse_gemini_response":
        gemini_response = arguments["gemini_response"]
        target_ide = arguments.get("target_ide", "cursor")
        create_tasks = arguments.get("create_tasks", True)
        
        try:
            # Parse the response
            tasks = GeminiTaskGenerator.parse_gemini_response(gemini_response)
            
            # Format based on target IDE
            if target_ide in ["cursor", "windsurf"]:
                formatted = GeminiTaskGenerator.format_for_cursor(tasks)
            elif target_ide == "claude-desktop" and create_tasks:
                formatted = GeminiTaskGenerator.format_for_claude_desktop(tasks)
            else:
                # Generic format
                formatted = json.dumps(tasks, indent=2)
            
            result = f"""# Parsed Implementation Directives

## Target IDE: {target_ide}
## Tasks Found: {sum(1 for v in tasks.values() if v)}

{formatted}
"""
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error parsing Gemini response: {str(e)}")]
    
    elif name == "generate_implementation_plan":
        project_path = arguments["project_path"]
        requirements = arguments["requirements"]
        target_ide = arguments.get("target_ide", "cursor")
        include_context = arguments.get("include_context", True)
        
        if not os.path.exists(project_path):
            return [TextContent(type="text", text=f"Error: Project path '{project_path}' does not exist")]
        
        try:
            # This is the complete Shotgun workflow
            result = f"""# 🚀 SHOTGUN-STYLE IMPLEMENTATION PLAN GENERATOR

## Project: {os.path.basename(project_path)}
## Target IDE: {target_ide}

---

## 📋 WORKFLOW INSTRUCTIONS

### Step 1: Generate Project Context
First, let me analyze your project...
"""
            
            # Generate context
            config = ProjectConfig()
            converter = RepoToTextConverter(config)
            project_context = converter.generate_xml_format(project_path)
            
            # Analyze project
            analyzer = RepoAnalyzer()
            project_analysis = analyzer.detect_project_type(project_path)
            
            result += f"""
✅ Project analyzed!
- Type: {', '.join(project_analysis['types'])}
- Context size: ~{TokenEstimator.estimate_tokens(project_context):,} tokens

### Step 2: Gemini Prompt
Copy this complete prompt to Gemini 2.5 Pro:

```
{GeminiTaskGenerator.create_task_prompt(
    project_context=project_context if include_context else "[Project context excluded for brevity]",
    project_analysis=project_analysis,
    requirements=requirements,
    task_type="feature",
    complexity="moderate"
)}
```

### Step 3: Parse Response
After getting Gemini's response, use:
`parse_gemini_response` tool with the response

### Step 4: Implementation
The parsed directives will be formatted specifically for {target_ide}

---

## 📝 Requirements Summary
{requirements}

## 🎯 Expected Output
You'll get step-by-step implementation directives optimized for {target_ide}
"""
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error generating implementation plan: {str(e)}")]
    
    elif name == "apply_patch":
        patch_content = arguments["patch_content"]
        target_path = arguments["target_path"]
        dry_run = arguments.get("dry_run", True)
        
        return [TextContent(type="text", text=f"Patch application not yet implemented. Use dry_run=True to preview.")]
    
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
                server_version="2.0.0",  # Major version bump for Shotgun functionality
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
