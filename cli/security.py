import os
import json
from typing import Dict, Any, List

# To get the config, we need to add the parent directory to the path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cli.config import get_config

class SecurityManager:
    """Handles security policies and vets agent actions."""

    def __init__(self):
        """Initializes the security manager."""
        self.config = get_config()
        self.profile_path = os.path.join(self.config.config_dir, "profile.json")
        self.security_policy = self._load_security_policy()

    def _load_security_policy(self) -> Dict[str, Any]:
        """Loads the security policy from the user's profile."""
        try:
            if os.path.exists(self.profile_path):
                with open(self.profile_path, 'r') as f:
                    profile = json.load(f)
                    return profile.get("security", self._get_default_policy())
            return self._get_default_policy()
        except (json.JSONDecodeError, IOError):
            return self._get_default_policy()

    def _get_default_policy(self) -> Dict[str, Any]:
        """Returns a default, reasonably safe security policy."""
        return {
            "command_blacklist": [
                "rm", "del", "format", "mkfs", "shutdown", "reboot"
            ],
            "file_access_blacklist": [
                "/etc/shadow", "/etc/passwd", "C:\\Windows\\System32\\config"
            ],
            "allow_shell_commands": True,
            "allow_tool_usage": True
        }

    def is_action_allowed(self, action_type: str, details: Dict[str, Any]) -> tuple[bool, str]:
        """
        Checks if a given action is allowed by the security policy.

        Args:
            action_type: 'shell' or 'tool'.
            details: A dictionary with action details (e.g., commands, tool_name).

        Returns:
            A tuple (is_allowed, reason).
        """
        if action_type == 'shell':
            if not self.security_policy.get('allow_shell_commands', False):
                return False, "Shell command execution is disabled by the security policy."
            
            commands = details.get("commands", [])
            for cmd_str in commands:
                cmd_parts = cmd_str.split()
                if not cmd_parts:
                    continue
                command = cmd_parts[0]
                
                # Check command blacklist
                for blacklisted in self.security_policy.get("command_blacklist", []):
                    if command.lower() == blacklisted.lower():
                        return False, f"Command '{command}' is blacklisted by the security policy."

        elif action_type == 'tool':
            if not self.security_policy.get('allow_tool_usage', False):
                return False, "Tool usage is disabled by the security policy."

            tool_name = details.get("tool_name", "")
            tool_args = details.get("tool_args", {})

            # Check for risky file access in tools
            if tool_name in ["read_file", "write_file", "monitor_file"]:
                file_path = tool_args.get("file_path", "")
                for blacklisted in self.security_policy.get("file_access_blacklist", []):
                    if os.path.abspath(file_path).startswith(os.path.abspath(blacklisted)):
                        return False, f"Access to '{file_path}' is restricted by the security policy."
        
        return True, "Action is allowed."

# Create a global security manager instance
security_manager = SecurityManager() 