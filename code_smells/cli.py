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
        """Initialize with XML content and handle code examples properly."""
        try:
            # Try to parse with automatic CDATA wrapping first
            self.root = self._safe_parse_xml(xml_content)
            self._validate_structure()
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML format: {str(e)}")
    
    def _wrap_code_with_cdata(self, xml_string: str) -> str:
        """Wrap code examples in CDATA sections to preserve special characters."""
        def wrap_in_cdata(match: re.Match) -> str:
            content = match.group(1)
            if '<![CDATA[' in content:
                return match.group(0)
            return f'<example_fix><![CDATA[{content}]]></example_fix>'

        # Replace content in example_fix tags with CDATA wrapped version
        xml_string = re.sub(
            r'<example_fix>(.*?)</example_fix>',
            wrap_in_cdata,
            xml_string,
            flags=re.DOTALL
        )
        return xml_string

    def _safe_parse_xml(self, xml_string: str) -> ET.Element:
        """Safely parse XML string with multiple fallback strategies."""
        try:
            # First try parsing as-is
            return ET.fromstring(xml_string)
        except ET.ParseError as first_error:
            try:
                # If that fails, try wrapping code blocks with CDATA
                wrapped_xml = self._wrap_code_with_cdata(xml_string)
                return ET.fromstring(wrapped_xml)
            except ET.ParseError as second_error:
                # If both attempts fail, raise the original error
                raise first_error
            
    def _validate_structure(self):
        """Validate the required XML structure is present."""
        required_elements = ['output', 'analysis_process']
        for element in required_elements:
            if self.root.find(f".//{element}") is None:
                raise ValueError(f"Missing required element: {element}")
                
    def get_flags(self) -> List[Dict[str, str]]:
        """Extract flags from XML, properly handling CDATA sections."""
        flags = []
        for flag in self.root.findall(".//flag"):
            try:
                flag_dict = {}
                for element in flag:
                    if element.tag == 'example_fix':
                        # Handle potential CDATA content
                        text = element.text
                        if text and '<![CDATA[' in text:
                            text = text.replace('<![CDATA[', '').replace(']]>', '')
                        flag_dict[element.tag] = text.strip() if text else ""
                    else:
                        flag_dict[element.tag] = element.text.strip() if element.text else ""
                flags.append(flag_dict)
            except AttributeError:
                continue
        return flags

    def get_overall_assessment(self) -> str:
        """Get the overall assessment from the XML."""
        assessment = self.root.find(".//overall_assessment")
        return assessment.text.strip() if assessment is not None else ""

    def has_red_flags(self) -> bool:
        """Check if any red flags are present."""
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
    """Generate analysis with improved XML handling."""
    formatted_prompt = SYSTEM_PROMPT.replace("{{GIT_DIFF}}", diff)
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0,
            messages=[{"role": "user", "content": formatted_prompt}],
        )

        # Extract the XML output from the response with improved pattern matching
        print(f"\nResponse: {response.content[0].text}")

        # Look for the complete output tag including its content
        pattern = r"<output>.*?</output>"
        match = re.search(pattern, response.content[0].text, re.DOTALL)
            
        if not match:
            raise click.ClickException("Failed to parse analysis response - no output tags found")
        
        print(f"\nMatch: {match.group(0)}")
        xml_content = match.group(0)
        
        # Create analysis object with robust XML parsing
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
