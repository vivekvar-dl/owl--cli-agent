from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

from .parser import get_symbol_code
from .api import GeminiClient
from .config import get_config
from .git_utils import get_staged_diff
import subprocess
import difflib
import os
import ast

console = Console()
config = get_config()
api_key = config.api_key
gemini_client = GeminiClient(api_key=api_key, model=config.model)

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
        docstring = response.get("docstring", "No docstring provided.")
        try:
            # The model sometimes returns a string literal including quotes and escaped newlines.
            # ast.literal_eval will safely parse this into a normal string.
            docstring_content = ast.literal_eval(docstring)
            # Sometimes it might be double-encoded
            if isinstance(docstring_content, str) and docstring_content.startswith('"""'):
                 docstring_content = ast.literal_eval(docstring_content)
        except (ValueError, SyntaxError):
            # If it's not a string literal, use it as is.
            docstring_content = docstring

        # Finally, remove the outer triple quotes if they exist
        if isinstance(docstring_content, str):
            docstring_content = docstring_content.strip().strip('"""')

        console.print(Panel(docstring_content, title="Generated Docstring", border_style="green"))

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

    diff = difflib.unified_diff(
        original_code.splitlines(keepends=True),
        refactored_code.splitlines(keepends=True),
        fromfile='original',
        tofile='refactored',
    )
    console.print("\n[bold]Diff:[/bold]")
    console.print("".join(diff))

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


def handle_debug(file_path: str, error_message: str):
    """Handler for the 'debug' command."""
    console.print(f"🐛 Debugging '{file_path}'...")

    # For debugging, we'll use the whole file's content.
    # In the future, we could try to intelligently find the symbol from the traceback.
    code, _, _, _ = get_symbol_code(file_path, None)
    if not code:
        console.print(f"[bold red]Error: Could not read file '{file_path}'.[/bold red]")
        return

    response = gemini_client.generate_fix(code, error_message)

    if "error" in response:
        console.print(f"[bold red]Error from API: {response['error']}[/bold red]")
        return

    explanation = response.get("explanation", "No explanation provided.")
    fixed_code = response.get("fixed_code")

    console.print(Panel(explanation, title="Explanation of the Fix", border_style="green"))

    if fixed_code:
        console.print(Panel(Syntax(fixed_code, "python", theme="default", line_numbers=True), title="Suggested Fix", border_style="yellow"))
    else:
        console.print("[bold yellow]The model did not return a code fix.[/bold yellow]")


def handle_audit(path: str):
    """Handler for the 'audit' command."""
    if not os.path.exists(path):
        console.print(f"[bold red]Error: Path '{path}' not found.[/bold red]")
        return

    files_to_audit = []
    if os.path.isfile(path):
        if path.endswith(".py"):
            files_to_audit.append(path)
        else:
            console.print(f"[bold yellow]Skipping non-Python file: {path}[/bold yellow]")
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    files_to_audit.append(os.path.join(root, file))

    if not files_to_audit:
        console.print("[bold yellow]No Python files found to audit.[/bold yellow]")
        return

    console.print(f"🛡️  Auditing {len(files_to_audit)} Python file(s)...")

    for file_path in files_to_audit:
        console.print(f"\n[bold]Auditing: {file_path}[/bold]")
        with open(file_path, 'r') as f:
            code = f.read()

        response = gemini_client.generate_audit_report(code)

        if "error" in response:
            console.print(f"[bold red]  Error from API: {response['error']}[/bold red]")
            continue

        summary = response.get("summary", "No summary provided.")
        report = response.get("report", "No report provided.")

        console.print(f"[italic cyan]  Summary: {summary}[/italic cyan]")
        console.print(Panel(Markdown(report), title="Security Audit Report", border_style="red"))


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
