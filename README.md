# Repo-to-Text MCP Server

> **The Ultimate Bridge Between Your Codebase and LLMs**

A powerful MCP (Model Context Protocol) server that converts entire repositories into LLM-friendly text format with AI-powered analysis and intelligent filtering. Perfect for Gemini 2.5 Pro's massive 2M token context window, but works great with any LLM.

![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![MCP](https://img.shields.io/badge/MCP-compatible-purple.svg)

## 🚀 Why This is Better Than Everything Else

| Feature | Shotgun | repo-to-text | **This MCP Server** |
|---------|---------|--------------|-------------------|
| **Integration** | Manual copy-paste | Command line | ✅ **Direct Claude integration** |
| **Format** | Messy delimiters | Basic XML | ✅ **Clean, optimized XML** |
| **Intelligence** | None | None | ✅ **AI-powered analysis** |
| **Multi-format** | Shotgun only | Limited | ✅ **XML, Shotgun, Markdown** |
| **Token estimation** | None | None | ✅ **Multi-provider support** |
| **Patch application** | Manual | None | ✅ **Automated with dry-run** |
| **Project awareness** | Generic | Generic | ✅ **Framework-specific optimization** |

## ✨ Key Features

- 🧠 **AI-Powered Analysis** - Claude analyzes your project and suggests optimal exclusions
- 🎯 **Multiple Output Formats** - XML (best for LLMs), Shotgun (Cursor-compatible), Markdown
- 📊 **Token Estimation** - Know exactly how much context you're using across different LLMs
- 🔄 **Smart Chunking** - Automatically split large repos for different model limits
- 🛠 **Patch Application** - Apply LLM responses back to your codebase with dry-run safety
- 🎨 **Project-Type Aware** - Detects languages/frameworks and optimizes accordingly
- ⚡ **Blazing Fast** - Efficient file processing with intelligent filtering

## 🎯 Perfect for Gemini 2.5 Pro

This MCP server is optimized for Gemini 2.5 Pro's **2 million token context**:
- Clean XML format that Gemini loves
- Smart preprocessing to maximize context utilization  
- Token estimation to know you're using <5% of available context
- Handles massive codebases that other tools can't

## 📦 Installation

### Prerequisites
- Python 3.7+
- Claude Desktop (for MCP integration)

### Quick Install

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/repo-to-text-mcp-server.git
cd repo-to-text-mcp-server

# Install dependencies
pip install -r requirements.txt

# Run installation script
chmod +x install.sh
./install.sh
```

### Manual Installation

1. **Install Python dependencies:**
   ```bash
   pip install pyyaml pathspec mcp
   ```

2. **Configure Claude Desktop:**
   Add to your Claude Desktop config file (`~/.claude/config.json`):
   ```json
   {
     "mcpServers": {
       "repo-to-text": {
         "command": "python",
         "args": ["/path/to/repo_to_text_mcp_server.py"]
       }
     }
   }
   ```

3. **Restart Claude Desktop**

## 🚀 Quick Start

### 1. Analyze Your Project
```
Analyze my project at /path/to/my/code
```
Get comprehensive insights about your codebase with AI-powered suggestions.

### 2. Generate LLM-Ready Context
```
Generate repo context for /path/to/my/code in XML format
```
Creates clean, structured text perfect for any LLM.

### 3. Estimate Token Usage
```
Estimate tokens for Gemini 2.5 Pro
```
Know exactly how much context you're using.

## 🛠 Available Tools

| Tool | Description | Perfect For |
|------|-------------|-------------|
| `analyze_project` | Comprehensive project analysis | Understanding your codebase |
| `generate_repo_context` | Main conversion with smart filtering | Creating LLM prompts |
| `estimate_tokens` | Multi-provider token counting | Context planning |
| `preview_selection` | See what files will be included | Large project optimization |
| `suggest_exclusions` | AI-powered exclusion recommendations | Noise reduction |
| `chunk_for_llm` | Smart chunking for model limits | Handling huge repos |
| `apply_patch` | Apply LLM responses to codebase | Completing the workflow |

## 📝 Output Formats

### XML Format (Recommended)
Clean, structured format that works perfectly with all modern LLMs:
```xml
<repo-to-text>
Directory: myproject
<directory_structure>
├── src/
│   └── main.py
└── README.md
</directory_structure>
<content full_path="src/main.py">
def hello():
    print("Hello World")
</content>
</repo-to-text>
```

### Shotgun Format (Cursor Compatible)
Compatible with Cursor, Windsurf, and copy-paste workflows:
```
*#*#*src/main.py*#*#*begin*#*#*
def hello():
    print("Hello World")
*#*#*end*#*#*
```

### Markdown Format
Perfect for documentation and human reading:
```markdown
# Repository: myproject
## File Contents
### src/main.py
```python
def hello():
    print("Hello World")
```
```

## 🎯 Usage Examples

### Basic Workflow
```
# 1. Analyze first
"Analyze my React project at /Users/me/myapp"

# 2. Generate context  
"Generate repo context excluding node_modules and test files"

# 3. Use with your favorite LLM
# → Paste into Gemini 2.5 Pro, get massive patch
# → Apply back to codebase
```

### Advanced Usage
```
# Custom exclusions
"Generate repo context for /path/to/code excluding ['*.test.js', 'docs/', 'examples/']"

# Preview before generating
"Preview what files would be included from /path/to/my/large/project"

# Token optimization
"Chunk this repo context for Claude 3.5 Sonnet"

# Apply LLM patches
"Apply this patch to /path/to/code with dry run first"
```

## ⚙️ Configuration

Create `.repo-to-text-settings.yaml` in your project root for custom settings:

```yaml
gitignore-import-and-ignore: true

ignore-tree-and-content:
  - "node_modules/"
  - "__pycache__/"
  - "*.log"
  - "dist/"
  - "build/"

ignore-content-only:
  - "package-lock.json"
  - "yarn.lock"
  - "README.md"

force-include:
  - "Dockerfile"
  - "package.json"
  - "requirements.txt"
```

## 🎛 Smart Defaults

The server automatically excludes common noise:
- **Dependencies**: `node_modules/`, `venv/`, `__pycache__/`
- **Build artifacts**: `dist/`, `build/`, `target/`
- **Version control**: `.git/`, `.svn/`
- **IDE files**: `.vscode/`, `.idea/`
- **Media files**: `*.png`, `*.jpg`, `*.mp4`
- **Archives**: `*.zip`, `*.tar.gz`

And includes important files:
- **Config files**: `package.json`, `requirements.txt`, `Dockerfile`
- **Documentation**: `README.md`, `LICENSE`

## 🚀 Perfect Workflows

### Gemini 2.5 Pro Workflow (Recommended)
1. **Analyze** → Claude understands your project
2. **Generate XML** → Perfect format for Gemini's 2M context
3. **Paste & Prompt** → Get massive, coherent patches
4. **Apply safely** → Dry-run first, then apply

### Cursor/Windsurf Workflow  
1. **Generate Shotgun format** → Compatible delimiters
2. **Paste into IDE** → Direct integration
3. **Get diff responses** → Apply through IDE tools

### Multi-LLM Workflow
1. **Estimate tokens** → Know what fits where
2. **Chunk intelligently** → Split for smaller models
3. **Use best model** → Route to optimal LLM

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: mcp` | Install with `pip install mcp` |
| Server not appearing in Claude | Check config path and restart Claude Desktop |
| Permission errors | Ensure script has execute permissions |
| Large output truncated | Use exclusions or chunking |
| Binary files included | They're auto-excluded, check your patterns |

## 🤝 Contributing

Contributions welcome! Please read our contributing guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📊 Performance

- **Blazing fast**: Processes 1000+ files in milliseconds
- **Memory efficient**: Streams large files, doesn't load all in memory
- **Smart caching**: Reuses analysis results
- **Handles huge repos**: Git repositories with 10k+ files

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=YOUR_USERNAME/repo-to-text-mcp-server&type=Date)](https://github.com/YOUR_USERNAME/repo-to-text-mcp-server/stargazers)

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by [Shotgun](https://github.com/glebkudr/shotgun_code) and [repo-to-text](https://github.com/kirill-markin/repo-to-text)
- Built for the [Model Context Protocol](https://github.com/modelcontextprotocol)
- Optimized for [Gemini 2.5 Pro](https://deepmind.google/technologies/gemini/pro/)'s massive context window
- Enhanced by Claude's intelligence

## 🔗 Related Projects

- [Shotgun Code](https://github.com/glebkudr/shotgun_code) - Desktop GUI approach
- [repo-to-text](https://github.com/kirill-markin/repo-to-text) - CLI tool
- [git2gpt](https://github.com/chand1012/git2gpt) - Simple converter
- [MCP](https://github.com/modelcontextprotocol) - Model Context Protocol

---

**Transform your entire codebase into LLM-ready context with AI-powered intelligence. Perfect for Gemini 2.5 Pro's massive context window, but works brilliantly with any LLM.**

⭐ **Star this repo if it helps you build better software faster!**