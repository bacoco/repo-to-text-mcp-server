#!/bin/bash

echo "Installing Repo-to-Text MCP Server..."

# Install Python dependencies
pip install -r requirements.txt

# Make the server executable
chmod +x repo_to_text_mcp_server.py

# Create Claude Desktop config directory if it doesn't exist
mkdir -p ~/.claude

# Backup existing config
if [ -f ~/.claude/config.json ]; then
    cp ~/.claude/config.json ~/.claude/config.json.backup
    echo "Backed up existing Claude config to ~/.claude/config.json.backup"
fi

# Get the full path to the server script
SCRIPT_PATH="$(pwd)/repo_to_text_mcp_server.py"

# Create or update Claude Desktop config
cat > ~/.claude/config.json << EOF
{
  "mcpServers": {
    "repo-to-text": {
      "command": "python",
      "args": ["$SCRIPT_PATH"]
    }
  }
}
EOF

echo "✅ Installation complete!"
echo "   - MCP server configured in ~/.claude/config.json"
echo "   - Restart Claude Desktop to use the new server"
echo ""
echo "Usage examples:"
echo "   1. Analyze a project: 'Analyze my project at /path/to/code'"
echo "   2. Generate context: 'Generate repo context for /path/to/code in XML format'"
echo "   3. Smart suggestions: 'Suggest exclusions for /path/to/code'"