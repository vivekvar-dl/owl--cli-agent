import json
import logging
import re
import os
from typing import Dict, List, Optional, Any

import google.generativeai as genai
from google.generativeai.types import GenerationConfig, content_types

from .config import get_config
from .tools import TOOL_CONFIG

# Configure logging
logger = logging.getLogger(__name__)


class GeminiClient:
    """A client for interacting with the Google Gemini API."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro-latest"):
        """
        Initializes the GeminiClient.

        Args:
            api_key: The Google API key.
            model: The model to use for generation.
        """
        self.api_key = api_key
        self.model_name = model
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        self.config = get_config()
        self.chat = self.model.start_chat(history=[])
        logger.info(f"Initialized Gemini client with model: {self.model.model_name}")

    def _get_command_generation_prompt(self) -> str:
        """Constructs the prompt for generating shell commands."""
        config = self.config
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

    def generate_shell_commands(self, instruction: str) -> Dict[str, Any]:
        """
        Generates shell commands from a natural language instruction.
        This is used for the 'run' command.
        """
        prompt = self._construct_shell_command_prompt(instruction)
        try:
            response = self.model.generate_content(prompt)
            # Assuming the response is a JSON string
            return self._parse_json_response(response.text)
        except Exception as e:
            logger.error(f"Error generating shell commands: {e}")
            return {"error": str(e)}

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

    def generate_next_action(self, conversation_history: List[Dict[str, str]], user_instruction: str) -> Dict[str, Any]:
        """
        Generates the next action for the autonomous agent, which can be a tool call or a shell command.
        """
        prompt = self._construct_agent_prompt(conversation_history, user_instruction)
        try:
            response = self.model.generate_content(prompt)
            return self._parse_json_response(response.text)
        except Exception as e:
            logger.error(f"Error generating next agent action: {e}")
            return {"error": str(e)}

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
            response = self.model.generate_content(prompt)
            # Basic parsing, assuming JSON is the primary output format
            return self._parse_json_response(response.text)
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return {"error": str(e)}

    def reset_chat(self):
        """Resets the chat history."""
        self.chat = self.model.start_chat(history=[])
        logger.info("Chat history has been reset.")

    def _construct_shell_command_prompt(self, instruction: str) -> str:
        """Constructs the prompt for generating simple shell commands."""
        return f"""
You are an expert Linux terminal assistant. Your task is to convert a natural language instruction into a sequence of executable Linux shell commands.

**Constraints:**
- You must operate on a standard Linux environment (like Ubuntu with a bash shell).
- The output must be a single, valid JSON object.
- The JSON object must have two keys: "commands" (a list of strings) and "explanation" (a brief, one-sentence explanation).
- Do not include any text or formatting outside of the JSON object.
- The commands should be simple, single-line commands. Avoid complex scripts.
- Assume standard Linux utilities like `grep`, `awk`, `sed`, `find`, `ps`, etc., are available.

**Instruction:**
"{instruction}"

**JSON Output:**
"""

    def _construct_agent_prompt(self, conversation_history: List[Dict[str, str]], user_instruction: str) -> str:
        """Constructs the prompt for the autonomous agent."""
        tool_definitions = self._get_tool_definitions()
        
        # Simplified history formatting
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])

        return f"""
You are Owl, a highly capable autonomous AI assistant operating on a Linux system. Your goal is to achieve the user's objective by thinking step-by-step and using the tools at your disposal.

**Current Operating System: Linux**

**Available Tools:**
You have access to a set of tools for interacting with the system. You can also execute any standard Linux shell command.

{tool_definitions}

**Execution Flow:**
1.  **Analyze**: Understand the user's request in the context of the conversation history.
2.  **Plan**: Formulate a step-by-step plan.
3.  **Act**: Choose ONE action to take. This can be either calling one of the predefined tools OR executing a shell command.
4.  **Respond**: Your response MUST be a single, valid JSON object containing your next action.

**JSON Response Format:**
Your entire response must be a single JSON object with the following structure:
- `thought`: (string) Your reasoning and plan for the next step.
- `action`: (string) The type of action: either "tool" or "shell".
- `tool_name`: (string, required if action is "tool") The name of the tool to use.
- `tool_args`: (object, required if action is "tool") The arguments for the tool.
- `commands`: (list of strings, required if action is "shell") The shell commands to execute.
- `explanation`: (string) A brief explanation of what the action will do.
- `final_answer`: (string, optional) If you have fully completed the user's request, provide the final answer here.

**Conversation History:**
{history_str}

**User's Latest Instruction:**
"{user_instruction}"

**Your JSON Response:**
"""

    def _get_tool_definitions(self) -> str:
        """Formats the TOOL_CONFIG into a string for the prompt."""
        lines = []
        for name, config in TOOL_CONFIG.items():
            arg_str = ", ".join([f"{k}: {v}" for k, v in config.get("args", {}).items()])
            lines.append(f"- `{name}({arg_str})`: {config['description']}")
        return "\n".join(lines)

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Safely parses a JSON string from the model's response."""
        try:
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            
            return json.loads(response_text)
        except (json.JSONDecodeError, IndexError) as e:
            logger.error(f"Failed to parse JSON response: '{response_text}'. Error: {e}")
            return {"error": "Invalid or unexpected response format from the model."}
        except Exception as e:
            logger.error(f"An unexpected error occurred during JSON parsing: {e}")
            return {"error": "An unexpected error occurred."}

    def generate_explanation(self, code: str) -> Dict[str, Any]:
        """Generates an explanation for a piece of code."""
        prompt = f"""
You are an expert software engineer. Your task is to explain the following code snippet in a clear, concise way.
Focus on the code's purpose, how it works, and its key components. The output should be in Markdown format.

**Code Snippet:**
```python
{code}
```

**Explanation (in Markdown):**
"""
        try:
            response = self.model.generate_content(prompt)
            return {"explanation": response.text}
        except Exception as e:
            return {"error": str(e)}

    def generate_docstring(self, code: str) -> Dict[str, Any]:
        """Generates a docstring for a function or class."""
        prompt = f"""
You are a senior Python developer who writes excellent documentation.
Generate a high-quality, Google-style docstring for the following code.

**Code:**
```python
{code}
```

Respond with a single JSON object containing one key, "docstring", with the generated docstring as its value.
Do not include any other text or formatting.
"""
        return self._send_request(prompt)

    def generate_test(self, code: str) -> Dict[str, Any]:
        """Generates a unit test for a piece of code."""
        prompt = f"""
You are a software engineer specializing in Test-Driven Development.
Write a simple unit test for the following code using the `unittest` library.
The test should be self-contained in a single file.

**Code to Test:**
```python
{code}
```

Respond with a single JSON object containing one key, "test_code", with the generated Python test code as its value.
"""
        return self._send_request(prompt)

    def generate_commit_message(self, diff: str) -> Dict[str, Any]:
        """Generates a git commit message from a diff."""
        prompt = f"""
You are a senior software engineer who writes excellent, conventional git commit messages.
Based on the following `git diff --staged` output, generate a concise and descriptive commit message.

The commit message should follow the Conventional Commits specification:
- Format: `<type>[optional scope]: <description>`
- Example types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.

**Staged Diff:**
```diff
{diff}
```

Respond with a single JSON object containing one key, "commit_message", with the generated message as its value.
"""
        return self._send_request(prompt)

    def generate_refactor(self, code: str, instruction: str) -> Dict[str, Any]:
        """Generates a refactored version of a piece of code."""
        prompt = f"""
You are an expert software engineer who specializes in writing clean, efficient, and maintainable code.
Your task is to refactor the following code snippet based on the user's instruction.
The refactored code must maintain the original functionality.

**User's Refactoring Instruction:**
"{instruction}"

**Original Code:**
```python
{code}
```

Respond with a single JSON object containing one key, "refactored_code", with the newly refactored code as its value.
Only provide the code for the function/class that was refactored.
"""
        return self._send_request(prompt)


# Create a global API client instance
gemini_client = GeminiClient(api_key=get_config().api_key) 