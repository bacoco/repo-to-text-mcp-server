# Changelog

## [2.0.0] - 2024-12-29

### Added
- **Shotgun-style AI Task Generation**: Complete implementation workflow using Gemini 2.5 Pro
  - `generate_implementation_tasks`: Creates comprehensive Gemini prompts with full project context
  - `parse_gemini_response`: Converts Gemini output into IDE-specific directives
  - `generate_implementation_plan`: One-command complete workflow
- **Multi-IDE Support**: Format implementation directives for:
  - Cursor: Step-by-step implementation guide
  - Windsurf: Optimized workflow format
  - Claude Desktop: Task breakdown with priorities
- **Task Types**: Support for feature, refactor, bugfix, optimization, documentation, and testing tasks
- **Complexity Levels**: Simple, moderate, complex, and architectural change guidance
- **GeminiTaskGenerator Class**: Intelligent parsing of AI responses into structured tasks
- **Comprehensive Examples**: SHOTGUN_EXAMPLES.md with detailed workflows

### Changed
- Enhanced project analysis with better framework detection
- Improved token estimation for multiple providers
- Better file filtering with more intelligent defaults

### Fixed
- Binary file detection now properly excludes non-text files
- Improved error handling for file reading operations

## [1.0.0] - 2024-12-28

### Initial Release
- Repository to text conversion with multiple formats (XML, Shotgun, Markdown)
- Project analysis and type detection
- Token estimation for various LLM providers
- Intelligent file filtering and exclusion patterns
- MCP server integration for Claude Desktop
- Configuration file support
