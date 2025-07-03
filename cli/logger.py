import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from rich.logging import RichHandler
from rich.console import Console
from logging.handlers import RotatingFileHandler

from .config import get_config

def setup_logging():
    """Set up logging for the application."""
    config = get_config()
    # Ensure log directory exists
    os.makedirs(config.log_dir, exist_ok=True)
    log_file = os.path.join(config.log_dir, "gemini-cli.log")

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO if config.verbose else logging.WARNING)

    # Console handler (with Rich)
    console = Console(stderr=True)
    rich_handler = RichHandler(
        console=console, 
        show_time=True, 
        show_path=False,
        rich_tracebacks=True
    )
    rich_handler.setLevel(logging.INFO)

    # File handler (Rotating)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5  # 10 MB per file, 5 backups
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    # Add handlers to the root logger
    root_logger.addHandler(rich_handler)
    root_logger.addHandler(file_handler)
    
    # Configure specific loggers to be less verbose if needed
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logger initialized. Logs will be stored in {config.log_dir}")

def get_logger(name: str):
    """Get a logger instance."""
    return logging.getLogger(name)

class CommandLogger:
    """
    A class to log shell command executions, including stdout and stderr.
    """
    def __init__(self):
        """Initialize the command logger."""
        self.log_dir = get_config().log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        
    def log_command(
        self, 
        commands: List[str], 
        results: List[Dict[str, Any]]
    ):
        """Logs a command and its result to a file."""
        log_file_path = os.path.join(self.log_dir, "command_history.log")
        
        try:
            with open(log_file_path, "a") as f:
                f.write(f"--- Command Execution ---\\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\\n")
                f.write(f"Command: {' && '.join(commands)}\\n")
                
                for i, result in enumerate(results):
                    f.write(f"  --- Result {i+1} ---\\n")
                    f.write(f"  Success: {result['success']}\\n")
                    f.write(f"  Return Code: {result['return_code']}\\n")
                    f.write(f"  STDOUT:\\n{result['stdout']}\\n")
                    f.write(f"  STDERR:\\n{result['stderr']}\\n")
                
                f.write("--- End ---\\n\\n")
        except IOError as e:
            logger.error(f"Failed to write to command log: {e}")

    def log_command_execution(self, 
                             user_instruction: str, 
                             commands: List[str], 
                             results: List[Dict], 
                             explanation: str) -> str:
        """
        Log command execution details to a JSON file.
        
        Args:
            user_instruction: Original user instruction
            commands: List of generated commands
            results: List of execution results
            explanation: Explanation of the commands
            
        Returns:
            Path to the log file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.log_dir, f"command_{timestamp}.json")
        
        log_data = {
            "timestamp": int(time.time()),
            "datetime": datetime.now().isoformat(),
            "user_instruction": user_instruction,
            "commands": commands,
            "explanation": explanation,
            "results": results
        }
        
        try:
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            logger.info(f"Command execution logged to {log_file}")
            return log_file
        except Exception as e:
            logger.exception(f"Failed to log command execution: {str(e)}")
            return ""
    
    def get_command_history(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get command execution history.
        
        Args:
            limit: Maximum number of history entries to return
            
        Returns:
            List of command execution history entries
        """
        history = []
        
        try:
            # Get all log files
            log_files = [os.path.join(self.log_dir, f) for f in os.listdir(self.log_dir) 
                         if f.startswith("command_") and f.endswith(".json")]
            
            # Sort by modification time (newest first)
            log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            # Apply limit if specified
            if limit is not None:
                log_files = log_files[:limit]
            
            # Read each log file
            for log_file in log_files:
                try:
                    with open(log_file, 'r') as f:
                        history.append(json.load(f))
                except Exception as e:
                    logger.warning(f"Failed to read log file {log_file}: {str(e)}")
            
            return history
        except Exception as e:
            logger.exception(f"Failed to get command history: {str(e)}")
            return []

# Create a global logger instance
command_logger = CommandLogger() 