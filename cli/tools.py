import platform
import subprocess
import os
import sys
import glob
from typing import Dict, Any
import psutil
import requests
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from .config import get_config

config = get_config()

def list_files(path: str = ".") -> Dict[str, Any]:
    """Lists files and directories at a given path."""
    if not os.path.isdir(path):
        return {"success": False, "error": f"Directory not found: {path}"}
    try:
        items = os.listdir(path)
        return {"success": True, "items": items}
    except Exception as e:
        return {"success": False, "error": str(e)}

def read_file(file_path: str, start_line: int = 1, end_line: int = -1) -> Dict[str, Any]:
    """
    Reads the content of a specified file from start_line to end_line.
    If end_line is -1, it reads until the end of the file.
    """
    if not os.path.isfile(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        if start_line > len(lines):
            return {"success": False, "error": "Start line is beyond the end of the file."}

        start_index = start_line - 1
        end_index = len(lines) if end_line == -1 or end_line > len(lines) else end_line
        
        return {"success": True, "content": "".join(lines[start_index:end_index])}
    except Exception as e:
        return {"success": False, "error": str(e)}

def write_file(file_path: str, content: str) -> Dict[str, Any]:
    """
    Writes content to a specified file. Overwrites the file if it exists.
    Creates the directory if it doesn't exist.
    """
    try:
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"success": True, "message": f"File '{file_path}' written successfully."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def install_package(package_name: str) -> Dict[str, Any]:
    """
    Installs a system package using apt, yum, or pacman on Linux.
    This tool requires sudo privileges.
    """
    if sys.platform != "linux":
        return {"success": False, "error": "This tool is only available on Linux."}

    managers = {
        "apt-get": "/usr/bin/apt-get",
        "yum": "/usr/bin/yum",
        "dnf": "/usr/bin/dnf",
        "pacman": "/usr/bin/pacman",
    }
    
    manager_to_use = None
    for manager, path in managers.items():
        if os.path.exists(path):
            manager_to_use = manager
            break

    if not manager_to_use:
        return {"success": False, "error": "Could not find a supported package manager (apt, yum, dnf, pacman)."}

    try:
        result = subprocess.run(
            ["sudo", manager_to_use, "install", "-y", package_name],
            capture_output=True, text=True, check=True
        )
        return {"success": True, "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"Package installation failed: {e.stderr}"}
    except FileNotFoundError:
        return {"success": False, "error": "sudo command not found. Please ensure it is installed and in your PATH."}

def find_files(pattern: str, path: str = ".") -> Dict[str, Any]:
    """
    Finds files matching a glob pattern recursively in a given directory.
    Example: `find_files(pattern='*.py', path='./src')`
    """
    if not os.path.isdir(path):
        return {"success": False, "error": f"Directory not found: {path}"}
    try:
        results = glob.glob(os.path.join(path, f"**/{pattern}"), recursive=True)
        return {"success": True, "files": results}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_system_info() -> Dict[str, Any]:
    """Retrieves basic Linux system information (OS, CPU, Memory)."""
    if sys.platform != "linux":
        return {"success": False, "error": "This tool is only available on Linux."}
    try:
        distro_info = {}
        if hasattr(platform, 'freedesktop_os_release'):
            distro_info = platform.freedesktop_os_release()

        info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "distro": distro_info.get('PRETTY_NAME', 'N/A'),
            "architecture": platform.machine(),
            "cpu_usage_percent": psutil.cpu_percent(interval=1),
            "memory_usage_percent": psutil.virtual_memory().percent,
        }
        return {"success": True, "info": info}
    except Exception as e:
        return {"success": False, "error": str(e)}

def web_search(query: str) -> Dict[str, Any]:
    """Performs a web search using the configured Google Custom Search Engine."""
    if not config.google_api_key or not config.search_engine_id:
        return {"success": False, "error": "Web search tool not configured. Missing GOOGLE_API_KEY or PROGRAMMABLE_SEARCH_ENGINE_ID in .env file."}
    try:
        service = build("customsearch", "v1", developerKey=config.google_api_key)
        res = service.cse().list(q=query, cx=config.search_engine_id, num=5).execute()
        return {"success": True, "results": res.get('items', [])}
    except Exception as e:
        return {"success": False, "error": f"An error occurred during web search: {e}"}

def web_scrape(url: str) -> Dict[str, Any]:
    """Scrapes the text content of a given URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        clean_text = soup.get_text(separator='\n', strip=True)[:4000]
        return {"success": True, "title": soup.title.string if soup.title else "No title found", "text": clean_text}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Failed to fetch URL: {e}"}

def read_system_logs(log_count: int = 20, service_filter: str = "") -> Dict[str, Any]:
    """
    Reads recent system logs from journalctl on Linux.
    Args:
        log_count (int): The number of the most recent log entries to retrieve.
        service_filter (str): Optional: A systemd service unit to filter by (e.g., 'sshd').
    """
    if sys.platform != "linux":
        return {"success": False, "error": "This tool is only available on Linux."}

    if not os.path.exists("/usr/bin/journalctl"):
        return {"success": False, "error": "journalctl is not available on this system."}

    try:
        command = ["journalctl", "--no-pager", "-n", str(log_count)]
        if service_filter:
            command.extend(["-u", service_filter])
        
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return {"success": True, "logs": result.stdout}
    except subprocess.CalledProcessError as e:
        if "Failed to add match" in e.stderr:
                return {"success": False, "error": f"Could not find logs for service '{service_filter}'. It may not exist or have generated logs."}
        return {"success": False, "error": f"Error reading from journalctl: {e.stderr}"}
    except FileNotFoundError:
        return {"success": False, "error": "journalctl command not found even though it was detected to exist."}

TOOL_REGISTRY = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "install_package": install_package,
    "find_files": find_files,
    "get_system_info": get_system_info,
    "web_search": web_search,
    "web_scrape": web_scrape,
    "read_system_logs": read_system_logs,
}

TOOL_CONFIG = {
    "list_files": {
        "description": "Lists files and directories in a specified path.",
        "args": {"path": "The directory path to list."},
        "security_scope": "filesystem_read",
    },
    "read_file": {
        "description": "Reads the content of a specified file from a start line to an end line.",
        "args": {"file_path": "The full path to the file.", "start_line": "(Optional) The line to start reading from.", "end_line": "(Optional) The line to end reading at."},
        "security_scope": "filesystem_read",
        "file_access_blacklist": ["/etc/shadow"],
    },
    "write_file": {
        "description": "Writes or overwrites content to a specified file. Use with caution.",
        "args": {"file_path": "The full path to the file.", "content": "The content to write."},
        "security_scope": "filesystem_write",
        "file_access_blacklist": ["/etc/shadow", "/boot/*", "/etc/passwd"],
    },
    "install_package": {
        "description": "Installs a system package using the default Linux package manager (e.g., apt, yum). Requires sudo.",
        "args": {"package_name": "The name of the system package to install."},
        "security_scope": "system_write",
    },
    "find_files": {
        "description": "Finds files recursively matching a pattern (e.g., '*.log').",
        "args": {"pattern": "The glob pattern to search for.", "path": "(Optional) The directory to start searching from."},
        "security_scope": "filesystem_read",
    },
    "get_system_info": {
        "description": "Gets key information about the Linux operating system, CPU, and memory.",
        "args": {},
        "security_scope": "system_read",
    },
    "web_search": {
        "description": "Performs a web search to find information or answer questions.",
        "args": {"query": "The search query."},
        "security_scope": "network_read",
    },
    "web_scrape": {
        "description": "Extracts the text content from a single web page URL.",
        "args": {"url": "The URL to scrape."},
        "security_scope": "network_read",
    },
    "read_system_logs": {
        "description": "Reads recent system logs from journalctl. Useful for diagnosing software or system errors. Requires sudo for full access.",
        "args": {"log_count": "The number of log entries to fetch.", "service_filter": "(Optional) Filter logs for a specific systemd service unit."},
        "security_scope": "system_read",
    },
} 