#!/usr/bin/env python3
import click
import anthropic
import os
from pathlib import Path
import json
import subprocess
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
import re
from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.markdown import Markdown
from .constants import SYSTEM_PROMPT
from .git_utils import get_staged_changes, get_diff, get_current_branch


def get_api_key() -> str:
    """Get API key from environment or config file."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        return api_key

    config_file = Path.home() / ".config" / "code-smell" / "config.json"
    if config_file.exists():
        try:
            return json.loads(config_file.read_text()).get("api_key")
        except Exception:
            pass
    return None


def save_api_key(api_key: str):
    """Save API key to config file."""
    config_dir = Path.home() / ".config" / "code-smell"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps({"api_key": api_key}))

class CodeSmellAnalysis:
    def __init__(self, xml_content: str):
        try:
            self.root = ET.fromstring(xml_content)
            self._validate_structure()
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML format: {str(e)}")
            
    def _validate_structure(self):
        required_elements = ['output', 'analysis_process']
        for element in required_elements:
            if self.root.find(f".//{element}") is None:
                raise ValueError(f"Missing required element: {element}")
                
    def get_flags(self) -> List[Dict[str, str]]:
        flags = []
        for flag in self.root.findall(".//flag"):
            try:
                flag_dict = {
                    element.tag: element.text.strip() 
                    for element in flag 
                    if element.text
                }
                flags.append(flag_dict)
            except AttributeError:
                continue
        return flags

    def get_overall_assessment(self) -> str:
        assessment = self.root.find(".//overall_assessment")
        return assessment.text.strip() if assessment is not None else ""

    def has_red_flags(self) -> bool:
        return len(self.root.findall(".//flag")) > 0


def format_output(analysis: CodeSmellAnalysis, console: Console):
    """Format and display the analysis results using rich."""
    console.print("\n🔍 [bold cyan]Code Smell Analysis Results[/bold cyan]\n")

    if analysis.has_red_flags():
        # Display red flags
        for flag in analysis.get_flags():
            panel = Panel(
                f"""[bold red]⚠️  Issue:[/bold red] {flag['description']}

[bold yellow]📍 Location:[/bold yellow] {flag['location']}

[bold blue]💭 Explanation:[/bold blue]
{flag['explanation']}

[bold green]💡 Suggestion:[/bold green]
{flag['suggestion']}

[bold magenta]✨ Example Fix:[/bold magenta]
{flag['example_fix']}""",
                title="[bold red]Code Smell Detected[/bold red]",
                border_style="red",
            )
            console.print(panel)
            console.print()
    else:
        # Display no red flags message
        console.print("[bold green]✅ No code smells detected![/bold green]")
        console.print()

    # Display overall assessment
    console.print(
        Panel(
            analysis.get_overall_assessment(),
            title="[bold cyan]Overall Assessment[/bold cyan]",
            border_style="cyan",
        )
    )

def generate_analysis(console, client, diff):
    formatted_prompt = SYSTEM_PROMPT.replace("{{GIT_DIFF}}", diff)
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0,
            messages=[{"role": "user", "content": formatted_prompt}],
        )

        # Extract the XML output from the response
        pattern = r"<output>(.*?)</output>"
        match = re.search(pattern, response.content[0].text, re.DOTALL)
        if not match:
            raise click.ClickException("Failed to parse analysis response")

        xml_content = match.group(0)  # Use the full match including the output tags
        analysis = CodeSmellAnalysis(xml_content)
        format_output(analysis, console)

    except Exception as e:
        raise click.ClickException(f"Error analyzing code: {str(e)}")

@click.group()
def cli():
    """Analyze git changes for code smells using AI."""
    pass


@cli.command()
@click.option("--api-key", help="Anthropic API key")
def configure(api_key):
    """Configure the API key."""
    if not api_key:
        api_key = click.prompt("Please enter your Anthropic API key", hide_input=True)

    save_api_key(api_key)
    click.echo("Configuration saved successfully!")


@cli.command()
@click.option("--compare", default="main", help="Branch to compare to")
def pr(compare):
    """Analyze staged changes for code smells."""
    console = Console()

    # Get API key
    api_key = get_api_key()
    if not api_key:
        raise click.ClickException(
            "No API key found. Please run `configure` command first or set ANTHROPIC_API_KEY environment variable."
        )

    # Initialize Claude client
    client = anthropic.Client(api_key=api_key)

    # Get staged changes
    current_branch = get_current_branch()
    diff = get_diff(current_branch, compare)
    print(f"\nDiff: {diff}")
    if not diff:
        raise click.ClickException("No staged changes found.")

    # Generate analysis
    with console.status("[bold cyan]Analyzing code smells...[/bold cyan]"):
        generate_analysis(console, client, diff)


@cli.command()
def commit():
    """Analyze staged changes for code smells."""
    console = Console()

    # Get API key
    api_key = get_api_key()
    if not api_key:
        raise click.ClickException(
            "No API key found. Please run `configure` command first or set ANTHROPIC_API_KEY environment variable."
        )

    # Initialize Claude client
    client = anthropic.Client(api_key=api_key)

    # Get staged changes
    diff = get_staged_changes()
    if not diff:
        raise click.ClickException("No staged changes found.")

    # Generate analysis
    with console.status("[bold cyan]Analyzing code smells...[/bold cyan]"):
        generate_analysis(console,client,diff)

if __name__ == "__main__":
    cli()
