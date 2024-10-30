# Code Smells CLI

A command-line tool that uses Claude AI to analyze your code changes for potential code smells and software engineering best practices violations. Get instant feedback on your commits and pull requests!

## Features

- 🔍 Analyzes git staged changes and pull requests
- 🤖 Powered by Claude AI for intelligent code review
- ⚡ Instant feedback on code quality
- 💡 Detailed suggestions for improvements
- 🎨 Beautiful CLI output with rich formatting

## Installation

### Prerequisites

- Python 3.7 or higher
- An Anthropic API key ([get one here](https://www.anthropic.com/))

### Option 1: Install with pipx (Recommended)

[pipx](https://pypa.github.io/pipx/) is the recommended installation method as it creates an isolated environment for the CLI:

```bash
# Install pipx if you haven't already
python -m pip install --user pipx
python -m pipx ensurepath

# Install code-smells
pipx install git+https://github.com/yourusername/code-smells.git
```

### Option 2: Install from source

```bash
git clone https://github.com/yourusername/code-smells.git
cd code-smells
pip install -e .
```

## Configuration

Before using the tool, you need to configure your Anthropic API key. You can do this in two ways:

1. **Environment Variable**:
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

2. **CLI Configuration**:
```bash
code-smells configure
```

## Usage

### Analyze Staged Changes

To analyze changes you've staged for commit:

```bash
code-smells commit
```

### Analyze Pull Request Changes

To analyze changes in a pull request or branch compared to main:

```bash
code-smells pr
```

Or compare against a specific branch:

```bash
code-smells pr --compare development
```

## Example Output

Here's what you'll see when running the tool:

```
🔍 Code Smell Analysis Results

╭─ Code Smell Detected ──────────────────────────────────────────────╮
│                                                                    │
│ ⚠️  Issue: Exception Handling Too Broad                            │
│                                                                    │
│ 📍 Location: get_api_key() function                               │
│                                                                    │
│ 💭 Explanation:                                                    │
│ The function catches all exceptions without specific handling,     │
│ which could mask important errors and make debugging difficult.    │
│                                                                    │
│ 💡 Suggestion:                                                     │
│ Catch specific exceptions and handle each case appropriately.      │
│ Consider logging errors for debugging.                             │
│                                                                    │
│ ✨ Example Fix:                                                    │
│ def get_api_key() -> Optional[str]:                               │
│     """Get API key from environment or config file."""            │
│     if api_key := os.getenv("ANTHROPIC_API_KEY"):                 │
│         return api_key                                            │
│                                                                   │
│     config_file = Path.home() / ".config" / "code-smell" / "config.json" │
│     try:                                                          │
│         return json.loads(config_file.read_text()).get("api_key") │
│     except FileNotFoundError:                                     │
│         logger.debug("No config file found")                      │
│     except json.JSONDecodeError:                                  │
│         logger.error("Invalid JSON in config file")               │
│     except PermissionError:                                       │
│         logger.error("Cannot access config file")                 │
│     return None                                                   │
│                                                                    │
╰────────────────────────────────────────────────────────────────────╯

╭─ Code Smell Detected ──────────────────────────────────────────────╮
│                                                                    │
│ ⚠️  Issue: Missing Error Logging                                   │
│                                                                    │
│ 📍 Location: generate_analysis() function                         │
│                                                                    │
│ 💭 Explanation:                                                    │
│ Exceptions are raised but not logged, making it difficult to       │
│ track and debug issues in production.                             │
│                                                                    │
│ 💡 Suggestion:                                                     │
│ Add logging to capture error details before raising exceptions.    │
│                                                                    │
│ ✨ Example Fix:                                                    │
│ import logging                                                     │
│                                                                    │
│ def generate_analysis(console, client, diff):                      │
│     try:                                                          │
│         response = client.messages.create(...)                     │
│         match = re.search(pattern, response.content[0].text, re.DOTALL) │
│         if not match:                                             │
│             logging.error("Failed to parse Claude response")       │
│             raise click.ClickException("Failed to parse analysis") │
│         return match.group(0)                                     │
│     except Exception as e:                                        │
│         logging.error(f"Analysis failed: {str(e)}")               │
│         raise click.ClickException(f"Error analyzing code: {str(e)}") │
│                                                                    │
╰────────────────────────────────────────────────────────────────────╯

╭─ Overall Assessment ───────────────────────────────────────────────╮
│ The code is generally well-structured but could benefit from more  │
│ robust error handling and logging. Adding specific exception       │
│ handling and proper logging would improve maintainability and      │
│ debugging capabilities. Consider implementing these changes before │
│ deploying to production.                                          │
╰────────────────────────────────────────────────────────────────────╯
```

## Software Engineering Principles

The analyzer checks for violations of key software engineering principles including:

- Complexity management
- Module depth and interfaces
- Code organization and abstraction
- Documentation quality
- Naming conventions
- Code readability

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
