import logging
import json
from typing import Dict, List, Any
import os
import sys
import platform
import subprocess

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.json import JSON

from .api import gemini_client
from .executor import executor
from .ui import display_commands, display_results, console, confirm_execution
from . import tools
from .security import security_manager

logger = logging.getLogger(__name__)

class Agent:
    """An autonomous agent that can execute multi-step plans or engage in interactive sessions."""

    def __init__(self, auto_approve: bool = False):
        self.history: List[Dict[str, Any]] = []
        self.auto_approve = auto_approve
        self.max_retries = 3

    def start_interactive_session(self):
        """Starts a continuous, interactive session with the user."""
        console.print(Panel("Welcome to the Interactive Agent Session!", title="[bold green]Agent Mode[/bold green]", subtitle="Type 'quit' or 'exit' to end."))
        
        while True:
            try:
                user_instruction = Prompt.ask("[bold cyan]You[/bold cyan]")
                if user_instruction.lower() in ["quit", "exit"]:
                    console.print("[bold yellow]Ending agent session.[/bold yellow]")
                    break
                
                if not user_instruction:
                    continue
                
                # Add user instruction to history for context
                self.history.append({"action": "user_instruction", "instruction": user_instruction})
                self.execute_step(user_instruction)

            except (KeyboardInterrupt, EOFError):
                console.print("\n[bold yellow]Ending agent session.[/bold yellow]")
                break
    
    def execute_step(self, instruction: str):
        """Executes a single step based on an instruction, with retries."""
        # For now, we can frame the instruction as a single-step plan
        # This allows us to reuse the existing logic without a major rewrite yet.
        # In the future, we can make this more sophisticated.
        step = instruction 
        
        # This part is extracted from the old `run` method's loop
        retries = 0
        success = False
        cmd_response = None
        user_input = "y" # Default to yes for the first attempt

        # Use the new conversational API call
        with console.status(f"[yellow]Figuring out next action...[/yellow]"):
            cmd_response = gemini_client.generate_next_action(
                history=self.history, user_instruction=instruction
            )

        while retries < self.max_retries and not success:
            if cmd_response is None: # Should not happen, but for safety
                console.print("[red]Error: Failed to get a response from the AI.[/red]")
                break
            
            if "error" in cmd_response:
                console.print(f"[red]Error generating command: {cmd_response['error']}[/red]")
                break

            commands = cmd_response.get("commands", [])
            explanation = cmd_response.get("explanation", "No explanation provided.")
            
            if not commands and not cmd_response.get("tool"):
                console.print("[yellow]  -> AI decided no action was necessary.[/yellow]\\n")
                self.history.append({
                    "step": step, "action": "none", "explanation": explanation,
                    "result": {"success": True, "output": "No action taken."}
                })
                success = True
                continue

            # Display action for user
            if "tool" in cmd_response:
                tool_name = cmd_response["tool"]
                tool_args = cmd_response.get("tool_args", {})
                console.print(Panel(f"Tool: [cyan]{tool_name}[/cyan]\\nArgs: [yellow]{tool_args}[/yellow]\\n\\n{explanation}", title="[bold blue]Proposed Tool Call[/bold blue]"))
            else:
                display_commands(commands, explanation)

            # Get user input in interactive mode
            if not self.auto_approve:
                user_input = Prompt.ask(
                    "[bold yellow]Agent[/bold yellow]",
                    default="y"
                ).lower()

                if user_input in ["q", "quit"]:
                    console.print("[yellow]Cancelling current action.[/yellow]")
                    return
                
                if user_input in ["s", "skip"]:
                    console.print("[yellow]  -> Skipping action.[/yellow]\\n")
                    self.history.append({
                        "step": step, "action": "skip", "explanation": "User skipped action.",
                        "result": {"success": True, "output": "User skipped action."}
                    })
                    break 
                
                if user_input != "y":
                    with console.status("[yellow]Re-generating action with new instructions...[/yellow]"):
                        # Use the new conversational API call
                        cmd_response = gemini_client.generate_next_action(
                            history=self.history, user_instruction=user_input
                        )
                    console.clear() 
                    console.print(Panel(f"Current Task: [bold green]{user_input}[/bold green]", title="[bold cyan]Agent Status[/bold cyan]"))
                    continue

            # Execute action
            step_success, output = self._perform_action(cmd_response)

            if step_success:
                success = True
            else:
                retries += 1
                console.print(f"[bold yellow]An action failed. Attempting self-correction ({retries}/{self.max_retries}).[/bold yellow]")
                
                failed_action_str = f"Tool: {cmd_response['tool']}({cmd_response.get('tool_args')})" if 'tool' in cmd_response else " && ".join(commands)

                if retries < self.max_retries:
                    with console.status("[yellow]Generating correction...[/yellow]"):
                        correction_override = user_input if user_input not in ["y", "s", "q"] else None
                        cmd_response = gemini_client.generate_correction(
                            history=self.history,
                            failed_action=failed_action_str,
                            stdout=output.get("stdout", str(output)), 
                            stderr=output.get("stderr", ""),
                            override_instruction=correction_override
                        )
                    console.print("[bold cyan]Correction Attempt:[/bold cyan]")
        
        if not success:
            console.print(f"[bold red]Failed to execute step '{step}' after {self.max_retries} retries.[/bold red]")


    def _perform_action(self, response: Dict[str, Any]) -> tuple[bool, Dict[str, Any]]:
        """Performs the action specified by the AI's response after vetting it."""
        commands = response.get("commands", [])
        explanation = response.get("explanation", "")
        
        if "tool" in response:
            tool_name = response["tool"]
            tool_args = response.get("tool_args", {})
            
            # --- Security Check ---
            is_allowed, reason = security_manager.is_action_allowed(
                action_type='tool', 
                details={"tool_name": tool_name, "tool_args": tool_args}
            )
            if not is_allowed:
                console.print(f"[bold red]Action Denied:[/bold red] {reason}")
                history_entry = { "success": False, "output": f"Action denied by security policy: {reason}" }
                self.history.append({ "action": f"denied_tool:{tool_name}", "args": tool_args, "explanation": explanation, "result": history_entry })
                return False, history_entry
            
            if hasattr(tools, tool_name):
                tool_func = getattr(tools, tool_name)
                tool_result = tool_func(**tool_args)
                
                success = tool_result.get("success", False)

                # If the result is a dictionary, format it as pretty JSON.
                # Otherwise, display the raw content/message/error.
                display_data = {k: v for k, v in tool_result.items() if k != 'success'}
                if isinstance(tool_result, dict):
                    output_display = JSON.from_data(display_data)
                else:
                    output_display = (
                        tool_result.get("content") or 
                        tool_result.get("message") or 
                        str(tool_result.get("error", "Unknown error"))
                    )

                console.print(Panel(output_display, title=f"[blue]Tool Output: {tool_name}[/blue]", border_style="green" if success else "red"))

                self.history.append({
                    "action": f"tool:{tool_name}", "args": response.get("tool_args", {}), "explanation": explanation, "result": tool_result
                })
                return success, tool_result
            else:
                console.print(f"[red]Error: Unknown tool '{tool_name}'[/red]")
                history_entry = { "success": False, "output": f"Tool '{tool_name}' not found." }
                self.history.append({
                    "action": f"tool:{tool_name}", "args": response.get("tool_args", {}), "explanation": explanation, "result": history_entry
                })
                return False, history_entry
        else:
            # --- Security Check for Shell Commands ---
            is_allowed, reason = security_manager.is_action_allowed(action_type='shell', details={"commands": commands})
            if not is_allowed:
                console.print(f"[bold red]Action Denied:[/bold red] {reason}")
                history_entry = { "success": False, "output": f"Action denied by security policy: {reason}" }
                self.history.append({ "action": "denied_shell", "commands": commands, "explanation": explanation, "result": history_entry })
                return False, history_entry

            results = executor.execute_commands(commands)
            display_results(results)

            success = all(r["success"] for r in results)
            output = results[0] if len(results) == 1 else {"success": success, "stdout": "Multiple commands executed", "stderr": ""}
            
            self.history.append({
                "action": "shell", "commands": commands, "explanation": explanation, "result": output
            })
            return success, output 

    def run_security_audit(self):
        """Runs a comprehensive security audit."""
        console.print(Panel("Starting Automated Security Audit", title="[bold red]Security Audit Mode[/bold red]"))
        
        audit_data = {}
        
        with console.status("[yellow]Gathering system information...[/yellow]"):
            audit_data['os_info'] = { "name": os.name, "platform": sys.platform, "release": platform.release() }
            audit_data['policies'] = tools.check_policies()
            audit_data['packages'] = tools.list_packages()
            audit_data['cpu_info'] = tools.get_cpu_info()
            audit_data['memory_info'] = tools.get_memory_info()

        console.print("[green]System information collected.[/green]")

        if os.name == 'nt':
            with console.status("[yellow]Querying Windows Security Event Log...[/yellow]"):
                # This command queries the 'Security' log for the last 10 critical/error/warning events.
                # It's a reliable way to get a snapshot of recent security-relevant events.
                command = "wevtutil qe Security /q:\"*[System[(Level=1 or Level=2 or Level=3)]]\" /c:10 /rd:true /f:text"
                try:
                    # We directly use a tool-like function here for simplicity
                    result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
                    audit_data['windows_security_events'] = result.stdout
                except subprocess.CalledProcessError as e:
                    error_message = f"Failed to retrieve Windows security events (run as administrator?).\nError: {e.stderr}"
                    console.print(f"[bold red]{error_message}[/bold red]")
                    audit_data['windows_security_events'] = {"error": error_message}
                except FileNotFoundError:
                    error_message = "Could not find 'wevtutil'. Is this a non-standard Windows environment?"
                    console.print(f"[bold red]{error_message}[/bold red]")
                    audit_data['windows_security_events'] = {"error": error_message}
        else:
            # Placeholder for Linux audit
            audit_data['linux_audit_status'] = "Linux audit commands would run here."

        console.print("[green]Audit data collection complete.[/green]")
        
        with console.status("[yellow]Generating security report...[/yellow]"):
            report = gemini_client.generate_audit_report(audit_data)
            
        if "error" in report:
            console.print(f"[red]Error generating report: {report.get('error')}[/red]")
            raw_response = report.get('raw_response')
            if raw_response:
                console.print(f"Raw Response:\n{raw_response}")
            return # Stop if report generation fails

        console.print(Panel(report.get("report", "No report generated."), title="[bold green]Security Audit Report[/bold green]"))
        
        report_file = "security_audit_report.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report.get("report", ""))
        console.print(f"\n[green]Report saved to [bold cyan]{report_file}[/bold cyan][/green]")

    def run_background_tasks(self):
        """The main execution loop for when the agent runs as a service."""
        logger.info("Running background tasks: checking policies.")
        
        # Check for policy violations
        policy_result = tools.check_policies()
        
        if not policy_result.get("success", False):
            logger.error(f"Failed to check policies: {policy_result.get('error')}")
            return
            
        violations = policy_result.get("violations", [])
        if violations:
            logger.warning(f"Found {len(violations)} policy violations.")
            # In a more advanced implementation, the agent could be prompted
            # to generate a remediation plan here.
            for v in violations:
                logger.warning(f"  - Policy Violation: {v['policy']} | Details: {v['details']}")
        else:
            logger.info("Policy check complete. No violations found.") 