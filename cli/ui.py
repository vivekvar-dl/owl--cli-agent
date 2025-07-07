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


def display_home_page(console: Console):
    """Displays the interactive home page for the AI Coding Assistant."""
    console.print(Panel(
        Text("Gemini CLI - Your AI Coding Assistant", justify="center"),
        title="✨ Welcome ✨",
        border_style="blue"
    ))
    
    console.print(
        Text(
            "This tool helps you understand, document, and improve your code directly from the terminal.",
            justify="center"
        )
    )

    table = Table.grid(padding=(1, 2))
    table.add_column(style="cyan", justify="right")
    table.add_column(style="white")
    table.add_column(style="green")
    
    table.add_row(
        "explain",
        "[dim]→[/dim]",
        "Explains a source code file or a specific function/class."
    )
    table.add_row(
        "doc",
        "[dim]→[/dim]",
        "Generates documentation for your code."
    )
    table.add_row(
        "refactor",
        "[dim]→[/dim]",
        "Suggests improvements and refactors your code."
    )
    table.add_row(
        "test",
        "[dim]→[/dim]",
        "Generates unit tests for your code."
    )
    table.add_row(
        "commit",
        "[dim]→[/dim]",
        "Generates a git commit message for your staged changes."
    )
    
    console.print("\n[bold]Available Commands:[/bold]")
    console.print(table)
    
    console.print("\n[bold]Example Usage:[/bold]")
    console.print("  gemini-cli explain my_script.py my_function")
    console.print("  gemini-cli doc services/api.py")
    console.print("  gemini-cli commit")


def display_generated_commands(console: Console, commands: list, explanation: str):
    """Displays the commands generated by the AI."""
    table = Table(title="Generated Commands", show_header=True, header_style="bold magenta")
    table.add_column("Command")
    for cmd in commands:
        table.add_row(cmd)
    
    console.print(table)
    console.print(Panel(explanation, title="Explanation", border_style="green"))


def display_tool_call(console: Console, tool_name: str, tool_args: dict, explanation: str):
    """Displays a tool call from the agent."""
    panel_content = f"[bold]Tool:[/bold] {tool_name}\n"
    panel_content += f"[bold]Arguments:[/bold] {tool_args}\n\n"
    panel_content += f"[italic]{explanation}[/italic]"
    
    console.print(Panel(
        panel_content,
        title="🤖 Proposed Tool Call",
        border_style="yellow"
    ))


def display_tool_output(console: Console, tool_name: str, output: dict):
    """Displays the output of a tool execution."""
    console.print(Panel(
        str(output),
        title=f"Tool Output: {tool_name}",
        border_style="green"
    ))


def display_final_answer(console: Console, answer: str):
    """Displays the agent's final answer."""
    console.print(Panel(
        f"[bold green]Final Answer:[/bold green] {answer}",
        title="✅ Task Complete",
        border_style="green"
    )) 