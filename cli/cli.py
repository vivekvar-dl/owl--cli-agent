import argparse
import logging
import sys
import os
from typing import List, Optional, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from rich.padding import Padding

from .api import gemini_client
from .config import get_config
from .executor import executor
from .logger import setup_logging
from .agent import Agent
from .ui import (
    console,
    display_plan,
    display_commands,
    confirm_execution,
    display_results,
    display_history as display_history_ui,
    display_home_page,
)

# Configure logging
logger = logging.getLogger(__name__)


def run_cli() -> int:
    """Main function to run the CLI."""
    # Special handling for service commands
    if len(sys.argv) > 1 and sys.argv[1] == 'service':
        # This is a bit of a hack to allow the service infrastructure to handle its own command line.
        # It expects to be called directly, so we pass control to it.
        # We must import service here to avoid circular dependencies and runtime errors
        # if pywin32 is not installed on a non-windows system.
        try:
            from . import service
            service.handle_service_command()
            return 0
        except ImportError:
            console.print("[bold red]The 'pywin32' library is required to manage the service. Please install it.[/bold red]")
            return 1

    # If no arguments are provided, show the home page
    if len(sys.argv) == 1:
        handle_home_page()
        return 0

    setup_logging()
    config = get_config()

    parser = argparse.ArgumentParser(
        description="An intelligent CLI assistant powered by Google's Gemini API."
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # 'run' command for one-off instructions
    parser_run = subparsers.add_parser("run", help="Execute a one-off instruction.")
    parser_run.add_argument("instruction", nargs="+", help="The task for the AI to execute.")
    parser_run.add_argument("-y", "--yes", dest="auto_approve", action="store_true", help="Automatically approve commands.")

    # 'agent' command for interactive agent session
    parser_agent = subparsers.add_parser("agent", help="Start an interactive session with the autonomous agent.")
    parser_agent.add_argument("-y", "--yes", dest="auto_approve", action="store_true", help="Automatically approve agent actions.")

    # 'audit' command for security audit
    parser_audit = subparsers.add_parser("audit", help="Run a comprehensive security audit of the system.")
    
    # 'service' command for managing the background service
    # We add it here for help text, but it's handled separately above.
    subparsers.add_parser("service", help="Manage the background Windows service (install, start, stop, remove).")

    # Common arguments
    for p in [parser_run, parser_agent, parser_audit]:
        p.add_argument("--verbose", action="store_true", help="Enable verbose output.")

    args = parser.parse_args()

    # --- Configuration overrides from CLI arguments ---
    if hasattr(args, 'auto_approve') and args.auto_approve:
        config.auto_execute = True
    if args.verbose:
        config.verbose = True
        logging.getLogger().setLevel(logging.INFO)
    
    if args.command == "run":
        instruction_text = " ".join(args.instruction)
        handle_direct_instruction(instruction_text, args.auto_approve, config)
    elif args.command == "agent":
        agent = Agent(auto_approve=config.auto_execute)
        agent.start_interactive_session()
    elif args.command == "audit":
        agent = Agent(auto_approve=True) # Audits always run non-interactively
        agent.run_security_audit()
    else:
        # This part will now only be reached if a command is not handled above
        # or if 'service' is called without arguments (which the service handler will manage).
        parser.print_help()

    return 0

def handle_home_page():
    """Handles the interactive home page."""
    choice = display_home_page()
    
    if choice == '1':
        instruction = Prompt.ask("[bold cyan]Enter your instruction[/bold cyan]")
        if instruction:
            handle_direct_instruction(instruction, auto_approve=False, config=get_config())
    elif choice == '2':
        agent = Agent(auto_approve=False)
        agent.start_interactive_session()
    elif choice == '3':
        agent = Agent(auto_approve=True) # Audits run non-interactively
        agent.run_security_audit()
    elif choice == '4':
        sub_choice = Prompt.ask(
            "Service command",
            choices=["install", "start", "stop", "remove", "debug"],
            default="install"
        )
        try:
            from . import service
            # We need to manually construct the args for the service handler
            sys.argv = ['cli.py', 'service', sub_choice]
            service.handle_service_command()
        except ImportError:
            console.print("[bold red]The 'pywin32' library is required to manage the service.[/bold red]")
    elif choice == '5':
        console.print("[bold yellow]Exiting Owl CLI. Goodbye![/bold yellow]")

def handle_direct_instruction(instruction: str, auto_approve: bool, config):
    """Handles a single, direct instruction for the 'run' command."""
    cmd_response = gemini_client.generate_shell_commands(instruction)
    if "error" not in cmd_response:
        commands = cmd_response.get("commands", [])
        explanation = cmd_response.get("explanation", "")
        display_commands(commands, explanation)
        
        if auto_approve or config.auto_execute or confirm_execution():
            results = executor.execute_commands(commands)
            display_results(results)
    else:
        console.print(f"[bold red]Error: {cmd_response['error']}[/bold red]")


def start_interactive_mode():
    """Starts the interactive chat session for simple command generation."""
    console.print(Panel("Welcome to Interactive Mode!", title="[bold green]Gemini CLI[/bold green]", subtitle="Type 'exit' or 'quit' to end session."))
    while True:
        try:
            instruction = Prompt.ask("[bold cyan]>[/bold cyan]")
            if instruction.lower() in ["exit", "quit"]:
                console.print("[bold yellow]Exiting interactive mode.[/bold yellow]")
                break
            if instruction:
                handle_direct_instruction(instruction, auto_approve=False, config=get_config())
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold yellow]Exiting interactive mode.[/bold yellow]")
            break


if __name__ == "__main__":
    run_cli() 