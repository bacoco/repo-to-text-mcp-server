# PowerShell Installation Script for Windows

Write-Host "Installing Repo-to-Text MCP Server..." -ForegroundColor Green

# Install Python dependencies
pip install -r requirements.txt

# Get the full path to the server script
$ScriptPath = "$PWD\repo_to_text_mcp_server.py"

# Create Claude config directory
$ConfigDir = "$env:APPDATA\Claude"
if (!(Test-Path $ConfigDir)) {
    New-Item -ItemType Directory -Path $ConfigDir -Force
}

# Backup existing config
$ConfigFile = "$ConfigDir\config.json"
if (Test-Path $ConfigFile) {
    Copy-Item $ConfigFile "$ConfigFile.backup"
    Write-Host "Backed up existing Claude config" -ForegroundColor Yellow
}

# Create Claude Desktop config
$Config = @{
    mcpServers = @{
        "repo-to-text" = @{
            command = "python"
            args = @($ScriptPath)
        }
    }
} | ConvertTo-Json -Depth 10

$Config | Out-File -FilePath $ConfigFile -Encoding UTF8

Write-Host "✅ Installation complete!" -ForegroundColor Green
Write-Host "   - MCP server configured in $ConfigFile" -ForegroundColor Cyan
Write-Host "   - Restart Claude Desktop to use the new server" -ForegroundColor Cyan