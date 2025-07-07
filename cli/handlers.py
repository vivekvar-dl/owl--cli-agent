from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.diff import Diff

from .parser import get_symbol_code
from .api import GeminiClient
from .config import get_config, get_gemini_api_key
from .git_utils import get_staged_diff
import subprocess

console = Console()
config = get_config()
api_key = get_gemini_api_key(config)
gemini_client = GeminiClient(api_key=api_key)

def _apply_refactoring(file_path: str, original_content: str, refactored_code: str, start_line: int, end_line: int) -> bool:
    """Replaces the old code block with the refactored code in the file."""
    lines = original_content.splitlines(True) # Keep endings
    
    # Lines are 1-based, list indices are 0-based
    start_index = start_line - 1
    
    # The end_line from the parser is inclusive, so no change needed for slicing
    new_lines = lines[:start_index] + [refactored_code + '\n'] + lines[end_line:]
    
    try:
        with open(file_path, 'w') as f:
            f.writelines(new_lines)
        return True
    except IOError as e:
        console.print(f"[bold red]Error writing to file {file_path}: {e}[/bold red]")
        return False

def handle_explain(file_path: str, symbol: str or None):
    """Handler for the 'explain' command."""
    console.print(f"📄 Explaining '{symbol or file_path}'...")
    
    code, file_content, _, _ = get_symbol_code(file_path, symbol)
    if not code:
        console.print(f"[bold red]Error: Could not find '{symbol or file_path}'.[/bold red]")
        return

    response = gemini_client.generate_explanation(code)
    if "error" in response:
        console.print(f"[bold red]Error from API: {response['error']}[/bold red]")
    else:
        console.print(Markdown(response.get("explanation", "No explanation provided.")))

def handle_doc(file_path: str, symbol: str or None):
    """Handler for the 'doc' command."""
    console.print(f"📝 Generating documentation for '{symbol or file_path}'...")
    
    code, file_content, _, _ = get_symbol_code(file_path, symbol)
    if not code:
        console.print(f"[bold red]Error: Could not find '{symbol or file_path}'.[/bold red]")
        return
        
    response = gemini_client.generate_docstring(code)
    if "error" in response:
        console.print(f"[bold red]Error from API: {response['error']}[/bold red]")
    else:
        console.print(Panel(response.get("docstring", "No docstring provided."), title="Generated Docstring", border_style="green"))

def handle_refactor(file_path: str, instruction: str, symbol: str or None):
    """Handler for the 'refactor' command."""
    console.print(f"🛠️ Refactoring '{symbol or file_path}'...")

    original_code, file_content, start_line, end_line = get_symbol_code(file_path, symbol)
    if not original_code or file_content is None or start_line is None or end_line is None:
        console.print(f"[bold red]Error: Could not find '{symbol or file_path}'.[/bold red]")
        return

    response = gemini_client.generate_refactor(original_code, instruction)
    if "error" in response:
        console.print(f"[bold red]Error from API: {response['error']}[/bold red]")
        return
    
    refactored_code = response.get("refactored_code")
    if not refactored_code:
        console.print("[bold yellow]The model did not return any code to refactor.[/bold yellow]")
        return

    diff = Diff(original_code.splitlines(), refactored_code.splitlines(), fromfile="Original", tofile="Refactored")
    console.print(diff)

    if console.input("\n [bold yellow]Apply these changes? [y/n]:[/] ").lower() == "y":
        if _apply_refactoring(file_path, file_content, refactored_code, start_line, end_line):
            console.print("[bold green]✅ Refactoring applied successfully![/bold green]")
        else:
            console.print("[bold red]Failed to apply refactoring.[/bold red]")


def handle_test(file_path: str, symbol: str or None):
    """Handler for the 'test' command."""
    console.print(f"🧪 Generating tests for '{symbol or file_path}'...")

    code, file_content, _, _ = get_symbol_code(file_path, symbol)
    if not code:
        console.print(f"[bold red]Error: Could not find '{symbol or file_path}'.[/bold red]")
        return

    response = gemini_client.generate_test(code)
    if "error" in response:
        console.print(f"[bold red]Error from API: {response['error']}[/bold red]")
    else:
        console.print(Panel(response.get("test_code", "No test code provided."), title="Generated Unit Test", border_style="green"))


def handle_commit():
    """Handler for the 'commit' command."""
    console.print("✍️ Generating commit message...")
    
    diff, error = get_staged_diff()

    if error:
        console.print(f"[bold red]Error: {error}[/bold red]")
        return
    
    if not diff.strip():
        console.print("[bold yellow]No staged changes to commit.[/bold yellow]")
        return

    response = gemini_client.generate_commit_message(diff)
    if "error" in response:
        console.print(f"[bold red]Error from API: {response['error']}[/bold red]")
    else:
        commit_message = response.get("commit_message", "Could not generate commit message.")
        console.print(Panel(commit_message, title="Suggested Commit Message", border_style="green"))
        
        if console.input(" [bold yellow]Apply this commit message? [y/n]:[/] ").lower() == "y":
            try:
                subprocess.run(["git", "commit", "-m", commit_message], check=True)
                console.print("[bold green]✅ Commit successful![/bold green]")
            except subprocess.CalledProcessError:
                console.print("[bold red]Failed to apply commit.[/bold red]")
            except FileNotFoundError:
                console.print("[bold red]Git command not found.[/bold red]") 