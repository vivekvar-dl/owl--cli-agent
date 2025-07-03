import logging
import subprocess
import shlex
import platform
from typing import Dict, List, Tuple, Optional

# Configure logging
logger = logging.getLogger(__name__)


class CommandExecutor:
    """Handles execution of shell commands."""
    
    def execute_command(self, command: str) -> Tuple[bool, str, str]:
        """
        Execute a single shell command.
        
        Args:
            command: The shell command to execute
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        logger.info(f"Executing command: {command}")
        
        try:
            # Check if we're on Windows
            is_windows = platform.system() == "Windows"
            
            if is_windows:
                # On Windows, use shell=True to execute commands
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    shell=True
                )
            else:
                # On Unix-like systems, use shlex to properly handle command arguments
                args = shlex.split(command)
                
                # Execute the command and capture output
                process = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            
            stdout, stderr = process.communicate()
            success = process.returncode == 0
            
            if success:
                logger.info(f"Command executed successfully: {command}")
            else:
                logger.error(f"Command failed with return code {process.returncode}: {command}")
                logger.error(f"stderr: {stderr}")
                
            return success, stdout, stderr
            
        except Exception as e:
            logger.exception(f"Error executing command '{command}': {str(e)}")
            return False, "", str(e)
    
    def execute_commands(self, commands: List[str]) -> List[Dict]:
        """
        Execute a list of commands in sequence.
        
        Args:
            commands: List of shell commands to execute
            
        Returns:
            List of execution results for each command
        """
        results = []
        
        for command in commands:
            success, stdout, stderr = self.execute_command(command)
            results.append({
                "command": command,
                "success": success,
                "stdout": stdout,
                "stderr": stderr
            })
            
            # If a command fails, stop execution
            if not success:
                logger.warning(f"Stopping execution after command failure: {command}")
                break
                
        return results


# Create a global executor instance
executor = CommandExecutor() 