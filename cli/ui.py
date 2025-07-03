from typing import List, Dict, Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

console = Console()


def display_plan(response: Dict[str, Any]):
    """Displays the generated plan from the AI."""
    thought = response.get("thought")
    plan = response.get("plan")

    if not plan:
        console.print(f"[red]Error: Could not generate a plan. Response: {response.get('error', 'Unknown')}[/red]")
        return

    if thought:
        console.print(Panel(Text(thought, justify="left"), title="[bold yellow]Thought Process[/bold yellow]", border_style="yellow"))

    plan_panel = []
    for i, step in enumerate(plan, 1):
        plan_panel.append(f"[cyan]{i}.[/cyan] {step}")
    
    console.print(Panel("\\n".join(plan_panel), title="[bold green]Execution Plan[/bold green]", border_style="green"))


def display_commands(commands: List[str], explanation: str) -> None:
    """Display commands and explanation in a rich format."""
    table = Table(title="Generated Commands")
    table.add_column("Command", style="cyan")
    
    for command in commands:
        table.add_row(command)
    
    console.print(table)
    console.print(Panel(explanation, title="Explanation", border_style="green"))


def confirm_execution() -> bool:
    """Ask user to confirm command execution."""
    return Confirm.ask("Execute these commands?")


def display_results(results: List[dict]) -> None:
    """Display command execution results."""
    for result in results:
        command = result["command"]
        success = result["success"]
        stdout = result["stdout"]
        stderr = result["stderr"]
        
        title = f"[green]✓ Success: {command}" if success else f"[red]✗ Failed: {command}"
        content = stdout if stdout else "No output"
        
        if stderr:
            content = f"{content}\\n\\n[bold red]Error:[/bold red]\\n{stderr}" if content != "No output" else f"[bold red]Error:[/bold red]\\n{stderr}"
            
        console.print(Panel(content, title=title, border_style="green" if success else "red"))


def display_history(history: List[Dict[str, Any]]) -> None:
    """Display command execution history."""
    if not history:
        console.print("[yellow]No command history found.[/yellow]")
        return
    
    table = Table(title=f"Command History (Last {len(history)} Commands)")
    table.add_column("Time", style="cyan")
    table.add_column("Instruction", style="green")
    table.add_column("Commands", style="yellow")
    table.add_column("Success", style="magenta")
    
    for entry in history:
        datetime_str = entry.get("datetime", "Unknown")
        if isinstance(datetime_str, str) and len(datetime_str) > 19:
            datetime_str = datetime_str[:19].replace("T", " ")
        
        commands = entry.get("commands", [])
        commands_str = "\\n".join(commands)
        
        results = entry.get("results", [])
        success = all(result.get("success", False) for result in results) if results else False
        success_str = "[green]✓" if success else "[red]✗"
        
        table.add_row(
            datetime_str,
            entry.get("user_instruction", "Unknown"),
            commands_str,
            success_str
        )
    
    console.print(table)


def display_home_page():
    """Displays the main home page for the CLI and returns the user's choice."""
    console.print(
        Panel(
            Text("Welcome to the Owl CLI!", justify="center", style="bold green"),
            title="[bold blue]🦉 Owl CLI [/bold blue]",
            subtitle="Your OS-level AI Assistant"
        )
    )
    
    table = Table.grid(padding=(1, 2))
    table.add_column(style="cyan")
    table.add_column()
    table.add_row("1.", "Run a single, one-off command (e.g., 'list all python files')")
    table.add_row("2.", "Start an interactive session with the autonomous agent")
    table.add_row("3.", "Run a comprehensive security audit of the system")
    table.add_row("4.", "Manage the background service (install, start, stop)")
    table.add_row("5.", "Exit")
    
    console.print(table)
    
    choice = Prompt.ask(
        "\nWhat would you like to do?",
        choices=["1", "2", "3", "4", "5"],
        default="1"
    )
    return choice 