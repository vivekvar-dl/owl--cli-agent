import json
import logging
import re
import os
from typing import Dict, List, Optional, Any

import google.generativeai as genai
from google.generativeai.types import GenerationConfig, content_types

from .config import get_config

# Configure logging
logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for interacting with the Gemini API."""
    
    def __init__(self):
        """Initialize the Gemini API client."""
        config = get_config()
        genai.configure(api_key=config.api_key)
        self.model = genai.GenerativeModel(config.model)
        self.chat = self.model.start_chat(history=[])
        logger.info(f"Initialized Gemini client with model: {config.model}")

    def _get_command_generation_prompt(self) -> str:
        """Constructs the prompt for generating shell commands."""
        config = get_config()
        base_prompt = config.custom_prompt or """
        You are a helpful assistant that translates natural language instructions into shell commands.
        Your task is to:
        1. Understand the user's intention from their natural language request.
        2. Generate the appropriate shell command(s) to accomplish that task.
        3. Provide a brief explanation of what each command does.
        
        Respond with a JSON object with the following structure:
        {
            "commands": ["command1", "command2", ...],
            "explanation": "Brief explanation of what these commands do"
        }
        
        Only include the JSON in your response, nothing else.
        """

        return f"""
        {base_prompt}
        """

    def generate_shell_commands(self, user_instruction: str) -> Dict[str, Any]:
        """
        Generate shell commands from natural language instruction.
        
        Args:
            user_instruction: The natural language instruction
            
        Returns:
            Dict containing commands and explanation
        """
        full_instruction = f"{self._get_command_generation_prompt()}\\n\\nUser's request: {user_instruction}"
        return self._send_request(full_instruction)

    def generate_plan(self, user_instruction: str) -> Dict[str, Any]:
        """Generate a step-by-step plan from a high-level instruction."""
        prompt = f"""
        You are a master software engineer and systems administrator. Your task is to take a high-level user goal and decompose it into a clear, step-by-step plan. The plan should consist of logical, verifiable steps.

        Respond with a JSON object with the following structure:
        {{
            "thought": "A brief thought process on how you're creating the plan.",
            "plan": [
                "Step 1: Description of the first logical step.",
                "Step 2: Description of the second logical step.",
                "..."
            ]
        }}

        User's Goal: {user_instruction}
        """
        return self._send_request(prompt)

    def generate_command_for_step(self, goal: str, plan: List[str], history: List[Dict[str, Any]], current_step: str, override_instruction: Optional[str] = None) -> Dict[str, Any]:
        """Generates a command for a specific step in a plan, considering the history."""
        history_str = ""
        if history:
            history_str = "Here is the history of what has been done so far:\\n"
            for item in history:
                history_str += f"- Step: {item['step']}\\n"
                action = item.get('action', 'unknown')
                
                if action == 'shell':
                    commands = item.get('commands', [])
                    history_str += f"  - Action: Ran shell command `{' && '.join(commands)}`\\n"
                elif action.startswith('tool:'):
                    tool_name = action.split(':')[1]
                    args = item.get('args', {})
                    history_str += f"  - Action: Used tool `{tool_name}` with args `{args}`\\n"
                
                result = item.get('result', {})
                outcome = 'Success' if result.get('success') else 'Failure'
                history_str += f"  - Outcome: {outcome}\\n"
                
                output = result.get('output')  # For tools
                if output is None:  # For shell commands
                    stdout = result.get('stdout', '')
                    stderr = result.get('stderr', '')
                    if stdout or stderr:
                        output = f"STDOUT: {stdout}\\n  - STDERR: {stderr}"
                    else:
                        output = "No output."
                history_str += f"  - Output: {output}\\n"
        
        override_prompt_part = ""
        if override_instruction:
            override_prompt_part = f"""
            The user has provided a new instruction to correct or guide the next action.
            User's Correction: "{override_instruction}"
            You MUST prioritize this instruction. Generate an action that follows the user's new guidance for the current step.
            """
        
        prompt = f"""
        You are an autonomous agent executing a plan to achieve a goal. Your task is to generate the next command to execute OR the next tool to use.

        You have access to the following tools:
        - `read_file(file_path: str)`: Reads the entire content of a file.
        - `write_file(file_path: str, content: str)`: Writes content to a file, creating it if it doesn't exist.
        - `list_directory(path: str)`: Lists the contents of a directory with details.
        - `get_cpu_info()`: Gets detailed CPU usage and stats.
        - `get_memory_info()`: Gets detailed RAM and swap usage.
        - `get_disk_usage(path: str)`: Gets disk usage for a specific path.
        - `list_processes()`: Lists running processes with their details.

        **Important:** When asked for system information (CPU, memory, disk, processes, files), ALWAYS prefer the available tools over running shell commands like `ps`, `df`, `ls`, `dir`, etc. The tool output is structured and more reliable.

        **Observability & Remediation:**
        You can monitor files for changes using the `monitor_file` tool. This is useful for watching log files. If you find an error, you can then use another tool or command to try and fix it.

        **Policy Enforcement:**
        You can check the system for compliance with user-defined policies using the `check_policies` tool. If you find violations, you should report them and suggest a remediation action.

        **Deep System Awareness:**
        For diagnosing system issues, your primary tool should be `read_windows_event_log`. This provides direct, structured access to the OS's core event logs and is more reliable than reading plain text log files.

        Overall Goal: {goal}

        Full Plan:
        {chr(10).join(f'{i+1}. {s}' for i, s in enumerate(plan))}

        {history_str}

        {override_prompt_part}

        Now, generate the action for this step: "{current_step}"

        Consider the goal, the plan, and the execution history.
        If you need to use a tool, respond in this JSON format:
        {{
            "tool": "tool_name",
            "tool_args": {{"arg1": "value1", ...}},
            "explanation": "Why you are using this tool."
        }}

        If you need to run a shell command, respond in this JSON format:
        {{
            "commands": ["command1", "command2", ...],
            "explanation": "Brief explanation of what these commands do."
        }}
        
        If you think no action is needed (e.g., a manual verification step), return an empty commands list or tool name.
        If the previous steps failed, you might need to generate an action to fix the issue.
        Only include one of "tool" or "commands" in your response.
        Only include the JSON in your response, nothing else.
        """
        return self._send_request(prompt)

    def generate_correction(self, history: List[Dict[str, Any]], failed_action: str, stdout: str, stderr: str, override_instruction: Optional[str] = None) -> Dict[str, Any]:
        """Generates a new action to correct a failed action in a conversational context."""
        # Use the same history formatting as generate_next_action
        history_str = "This is the conversation history so far:\\n"
        for item in history:
            actor = "User" if item.get('action') == 'user_instruction' else "Agent"
            content = ""
            if actor == "User":
                content = item.get('instruction', '')
            else: # Agent action
                action_type = item.get('action', 'unknown')
                if action_type == 'shell':
                    content = f"Ran command: `{' && '.join(item.get('commands', []))}`"
                elif action_type.startswith('tool:'):
                    content = f"Used tool: `{action_type.split(':')[1]}` with args `{item.get('args')}`"
                
                result = item.get('result', {})
                if result.get('success', False):
                    content += f" -> Success. Output: {result.get('output', 'None')}"
                else:
                    content += f" -> Failed. Output: {result.get('output', 'None')}"

            history_str += f"{actor}: {content}\\n"

        override_prompt_part = ""
        if override_instruction:
            override_prompt_part = f"""
            The user has provided a new instruction to guide the correction.
            User's Correction: "{override_instruction}"
            You MUST prioritize this instruction.
            """

        prompt = f"""
        You are a conversational AI assistant. Your last action failed. Your task is to analyze the error and generate a new action to fix the issue.

        **Correction Strategy:**
        1.  Analyze the error message from the failed action.
        2.  If the cause is unclear, **use `web_search` to find information about the error message.**
        3.  Based on your analysis or the search results, propose a new action to fix the problem.

        Here is the conversation history leading to the failure:
        {history_str}

        The action that FAILED was:
        `{failed_action}`

        Its output was:
        ---
        STDOUT:
        {stdout}
        ---
        STDERR:
        {stderr}
        ---

        {override_prompt_part}

        Analyze the error and the user's instructions. Generate a new action to recover from this error and continue the conversation.

        If you need to use a tool, respond in this JSON format:
        {{
            "tool": "tool_name",
            "tool_args": {{"arg1": "value1", ...}},
            "explanation": "Why you are using this tool to correct the error."
        }}

        If you need to run a shell command, respond in this JSON format:
        {{
            "commands": ["new_command_to_try"],
            "explanation": "A brief explanation of why the previous command failed and why this new command should work."
        }}

        If you believe the error is unrecoverable, respond with an empty "commands" or "tool" field and an explanation.
        Only include the JSON in your response, nothing else.
        """
        return self._send_request(prompt)

    def generate_next_action(self, history: List[Dict[str, Any]], user_instruction: str) -> Dict[str, Any]:
        """Generates the next action in an open-ended conversational session."""
        history_str = "This is the conversation history so far:\\n"
        for item in history:
            # Simplified history for this prompt
            actor = "User" if item.get('action') == 'user_instruction' else "Agent"
            content = ""
            if actor == "User":
                content = item.get('instruction', '')
            else: # Agent action
                action_type = item.get('action', 'unknown')
                if action_type == 'shell':
                    content = f"Ran command: `{' && '.join(item.get('commands', []))}`"
                elif action_type.startswith('tool:'):
                    content = f"Used tool: `{action_type.split(':')[1]}` with args `{item.get('args')}`"
                
                result = item.get('result', {})
                if result.get('success', False):
                    content += f" -> Success. Output: {result.get('output', 'None')}"
                else:
                    content += f" -> Failed. Output: {result.get('output', 'None')}"

            history_str += f"{actor}: {content}\\n"

        prompt = f"""
        You are a conversational AI assistant that helps users accomplish tasks on their command line.
        You can run shell commands or use available tools.

        **Personalization:**
        Before you begin, you can use the `manage_profile(action='read')` tool to learn about the user and their preferences. Use this information to tailor your responses and actions.

        **Your Core Task is to answer the user's request. Follow this process rigorously:**
        1.  **Identify Necessary Information:** First, determine what information you need to answer the user's request.
        2.  **Information Gathering Strategy:**
            *   If the information is on the local system, use tools like `read_file` or `list_directory`.
            *   **If you do not know the answer or how to perform a task, your primary strategy should be to use `web_search` to find guides, documentation, or solutions.**
        3.  **Gather Raw Data:** Use your tools to get the information. Your goal in this step is ONLY to get the raw data (e.g., file contents, search results). Do not try to process or answer the question in this step.
        4.  **Analyze and Answer:** After the raw data is in the conversation history, you will be prompted again. In this next turn, analyze the data from the history (e.g., the content from `web_scrape`) and formulate the next step or the final answer.

        **System Administration:**
        When asked to install, remove, or list software, use the dedicated package management tools. Do not use raw shell commands like `choco`, `apt`, or `brew` directly.

        **Observability & Remediation:**
        You can monitor files for changes using the `monitor_file` tool. This is useful for watching log files. If you find an error, you can then use another tool or command to try and fix it.

        **Policy Enforcement:**
        You can check the system for compliance with user-defined policies using the `check_policies` tool. If you find violations, you should report them and suggest a remediation action.

        **Deep System Awareness:**
        For diagnosing system issues, your primary tool should be `read_windows_event_log`. This provides direct, structured access to the OS's core event logs and is more reliable than reading plain text log files.

        Available Tools:
        - `read_windows_event_log(log_name: str, event_count: int = 10, event_type: str = "Error")`: Reads the Windows Event Log.
        - `check_policies()`: Checks for system compliance with user-defined policies.
        - `monitor_file(file_path: str, keyword: str, timeout: int = 60)`: Watches a file for a keyword.
        - `install_package(name: str)`: Installs a software package.
        - `uninstall_package(name: str)`: Uninstalls a software package.
        - `list_packages(query: str = None)`: Lists installed packages, with an optional search query.
        - `manage_profile(action: str, key: str = None, value: any = None)`: Reads or updates the user's profile.json.
        - `web_search(query: str)`: Searches the web for a given query.
        - `web_scrape(url: str)`: Reads the text content of a web page.
        - `read_file(file_path: str)`: Reads the entire content of a file.
        - `write_file(file_path: str, content: str)`: Writes content to a file, creating it if it doesn't exist.
        - `list_directory(path: str)`: Lists the contents of a directory with details.
        - `get_cpu_info()`: Gets detailed CPU usage and stats.
        - `get_memory_info()`: Gets detailed RAM and swap usage.
        - `get_disk_usage(path: str)`: Gets disk usage for a specific path.
        - `list_processes()`: Lists running processes with their details.

        **Important:** When asked for system information (CPU, memory, disk, processes, files), ALWAYS prefer the available tools over running shell commands like `ps`, `df`, `ls`, `dir`, etc. The tool output is structured and more reliable.

        Here is the conversation history:
        {history_str}

        Here is the user's latest request:
        User: "{user_instruction}"

        Based on the user's request and the conversation so far, decide on the single next best action to take.

        If you need to use a tool, respond in this JSON format:
        {{
            "tool": "tool_name",
            "tool_args": {{"arg1": "value1", ...}},
            "explanation": "Why you are using this tool."
        }}

        If you need to run a shell command, respond in this JSON format:
        {{
            "commands": ["command1"],
            "explanation": "Brief explanation of what this command does."
        }}

        If no action is needed (e.g., the user is just asking a question that you can answer), just provide an explanation.
        {{
            "explanation": "Your text-based answer."
        }}

        Only include the JSON in your response, nothing else.
        """
        return self._send_request(prompt)

    def generate_audit_report(self, audit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generates a security audit report from collected data."""
        
        # Convert audit data to a string, handling potential large objects
        data_str = json.dumps(audit_data, indent=2, default=str)
        if len(data_str) > 30000: # Gemini has a context limit
            data_str = "Audit data is too large to display, but includes policies, packages, and system info."

        prompt = f"""
        You are a professional cybersecurity auditor. Your task is to analyze the provided system data and generate a comprehensive security report in Markdown format.

        **Report Structure:**
        1.  **Executive Summary:** A brief, high-level overview of the system's security posture.
        2.  **Policy Compliance:** A detailed analysis of any policy violations found.
        3.  **Software Inventory:** An analysis of the installed packages. Highlight any known vulnerable or outdated software (you may need to use your general knowledge).
        4.  **System Configuration:** A brief overview of the system's hardware configuration.
        5.  **Recommendations:** A numbered list of actionable recommendations to improve security.

        Here is the data collected from the system:
        {data_str}

        Now, generate the security report. Respond with a JSON object containing a single key "report" with the full Markdown report as its value.
        {{
            "report": "# Security Audit Report\\n\\n## 1. Executive Summary\\n\\n..."
        }}
        """
        return self._send_request(prompt)

    def _send_request(self, prompt: str) -> Dict[str, Any]:
        """Sends a request to the Gemini API and handles the response."""
        try:
            # The 'response_mime_type' is not supported in the user's library version.
            # The prompt strongly requests JSON, so we rely on that.
            generation_config = GenerationConfig(
                temperature=0.2,
                top_p=0.95,
                top_k=40
            )
            
            response = self.chat.send_message(
                prompt,
                generation_config=generation_config
            )
            
            response_text = response.text
            
            # Clean the response to remove markdown fences and other artifacts
            # This regex is more robust and handles cases with or without the 'json' keyword
            match = re.search(r"```(?:json)?\s*({[\s\S]*?})\s*```", response_text, re.DOTALL)
            if match:
                cleaned_text = match.group(1).strip()
            else:
                # If no markdown block is found, assume the whole text is the JSON content
                cleaned_text = response_text.strip()

            try:
                return json.loads(cleaned_text)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response: {cleaned_text}")
                # Fallback for when the model doesn't return valid JSON
                return {"error": "Failed to parse response from API", "raw_response": cleaned_text}
                
        except Exception as e:
            logger.exception(f"Error calling Gemini API: {str(e)}")
            return {"error": str(e)}

    def reset_chat(self):
        """Resets the chat history."""
        self.chat = self.model.start_chat(history=[])
        logger.info("Chat history has been reset.")


# Create a global API client instance
gemini_client = GeminiClient() 