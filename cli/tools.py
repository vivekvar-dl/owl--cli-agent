import os
from typing import Dict, Any, Optional
import psutil
from googleapiclient.discovery import build
import requests
from bs4 import BeautifulSoup
import json
import subprocess
import sys
import time

from .config import get_config

def _run_subprocess(command: list[str]) -> Dict[str, Any]:
    """A helper to run subprocess commands and return structured output."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return {"success": True, "stdout": result.stdout, "stderr": result.stderr}
    except FileNotFoundError:
        return {"success": False, "error": f"Command not found: {command[0]}. Please ensure it is installed and in your PATH."}
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"Command failed with exit code {e.returncode}", "stdout": e.stdout, "stderr": e.stderr}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

def install_package(name: str) -> Dict[str, Any]:
    """
    Installs a package using the appropriate system package manager.
    Detects the OS and uses 'choco' for Windows, 'apt-get' for Debian/Ubuntu, etc.
    """
    platform = sys.platform
    if platform == "win32":
        command = ["choco", "install", name, "-y"]
    elif platform == "linux":
        # This is a simplification. A real implementation would check for apt, yum, etc.
        command = ["sudo", "apt-get", "install", "-y", name]
    elif platform == "darwin":
        command = ["brew", "install", name]
    else:
        return {"success": False, "error": f"Unsupported operating system: {platform}"}

    return _run_subprocess(command)

def uninstall_package(name: str) -> Dict[str, Any]:
    """
    Uninstalls a package using the appropriate system package manager.
    """
    platform = sys.platform
    if platform == "win32":
        command = ["choco", "uninstall", name, "-y"]
    elif platform == "linux":
        command = ["sudo", "apt-get", "remove", "-y", name]
    elif platform == "darwin":
        command = ["brew", "uninstall", name]
    else:
        return {"success": False, "error": f"Unsupported operating system: {platform}"}

    return _run_subprocess(command)

def list_packages(query: Optional[str] = None) -> Dict[str, Any]:
    """
    Lists installed packages, optionally filtering by a query.
    """
    platform = sys.platform
    if platform == "win32":
        command = ["choco", "list"]
        if query:
            command.extend(["--include", query])
    elif platform == "linux":
        command = ["apt", "list", "--installed"]
        if query:
            # This is complex in apt, requires piping to grep.
            # For a robust tool, we'd handle this better.
            return _run_subprocess(["sh", "-c", f"apt list --installed | grep {query}"])
    elif platform == "darwin":
        command = ["brew", "list"]
        if query:
             return _run_subprocess(["sh", "-c", f"brew list | grep {query}"])
    else:
        return {"success": False, "error": f"Unsupported operating system: {platform}"}
    
    return _run_subprocess(command)

def read_file(file_path: str) -> Dict[str, Any]:
    """
    Reads the content of a file.

    Args:
        file_path: The path to the file to read.

    Returns:
        A dictionary containing the success status and the file content or an error message.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"success": True, "content": content}
    except FileNotFoundError:
        return {"success": False, "error": f"File not found: {file_path}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

def write_file(file_path: str, content: str) -> Dict[str, Any]:
    """
    Writes content to a file. Creates the directory if it doesn't exist.

    Args:
        file_path: The path to the file to write to.
        content: The content to write to the file.

    Returns:
        A dictionary containing the success status or an error message.
    """
    try:
        # Ensure the directory exists
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"success": True, "message": f"Successfully wrote to {file_path}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

def get_cpu_info() -> Dict[str, Any]:
    """
    Gets detailed CPU information.

    Returns:
        A dictionary containing CPU times, per-CPU usage, and overall stats.
    """
    try:
        return {
            "success": True,
            "cpu_times": psutil.cpu_times()._asdict(),
            "cpu_percent_per_cpu": psutil.cpu_percent(interval=1, percpu=True),
            "cpu_count": psutil.cpu_count(),
            "cpu_load_avg": psutil.getloadavg(),
        }
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

def get_memory_info() -> Dict[str, Any]:
    """
    Gets detailed memory and swap information.

    Returns:
        A dictionary containing virtual memory and swap memory stats.
    """
    try:
        return {
            "success": True,
            "virtual_memory": psutil.virtual_memory()._asdict(),
            "swap_memory": psutil.swap_memory()._asdict(),
        }
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

def get_disk_usage(path: str = '/') -> Dict[str, Any]:
    """
    Gets disk usage information for a given path.

    Args:
        path: The path to get disk usage for (e.g., '/', 'C:\\'). Defaults to '/'.

    Returns:
        A dictionary containing disk usage statistics.
    """
    try:
        usage = psutil.disk_usage(path)
        return {
            "success": True,
            "total": f"{usage.total / (1024**3):.2f} GB",
            "used": f"{usage.used / (1024**3):.2f} GB",
            "free": f"{usage.free / (1024**3):.2f} GB",
            "percent_used": f"{usage.percent}%"
        }
    except FileNotFoundError:
        return {"success": False, "error": f"Path not found: {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def list_processes() -> Dict[str, Any]:
    """
    Lists running processes with their details.

    Returns:
        A dictionary containing a list of process details.
    """
    procs = []
    try:
        for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_info']):
            procs.append(p.info)
        # Sort by memory usage
        procs = sorted(procs, key=lambda x: x['memory_info'].rss, reverse=True)
        return {"success": True, "processes": procs[:20]} # Return top 20 by memory
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

def list_directory(path: str = '.') -> Dict[str, Any]:
    """
    Lists the contents of a directory, providing details for each item.

    Args:
        path: The path to the directory to list. Defaults to the current directory.

    Returns:
        A dictionary containing lists of files and directories with their details.
    """
    try:
        items = os.listdir(path)
        files = []
        directories = []

        for item in items:
            item_path = os.path.join(path, item)
            try:
                if os.path.isdir(item_path):
                    directories.append({
                        "name": item,
                        "path": item_path,
                    })
                else:
                    stat = os.stat(item_path)
                    files.append({
                        "name": item,
                        "path": item_path,
                        "size_bytes": stat.st_size,
                        "modified_at": stat.st_mtime,
                    })
            except (FileNotFoundError, PermissionError):
                # Ignore files that can't be accessed
                continue
        
        return {
            "success": True,
            "path": os.path.abspath(path),
            "directories": directories,
            "files": files,
        }
    except FileNotFoundError:
        return {"success": False, "error": f"Directory not found: {path}"}
    except Exception as e:
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

def web_search(query: str) -> Dict[str, Any]:
    """
    Performs a web search using Google's Custom Search API.
    """
    config = get_config()
    if not config.google_api_key or not config.search_engine_id:
        return {
            "success": False,
            "error": "Google API key or Search Engine ID is not configured."
        }
    try:
        service = build("customsearch", "v1", developerKey=config.google_api_key)
        res = service.cse().list(q=query, cx=config.search_engine_id, num=5).execute()
        results = res.get('items', [])
        return {
            "success": True,
            "results": [{"title": r['title'], "link": r['link'], "snippet": r['snippet']} for r in results]
        }
    except Exception as e:
        return {"success": False, "error": f"An error occurred during web search: {str(e)}"}

def web_scrape(url: str) -> Dict[str, Any]:
    """
    Scrapes the text content of a single web page.

    Args:
        url: The URL to scrape.

    Returns:
        A dictionary containing the text content or an error message.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Raise an exception for bad status codes
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
            
        text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\\n'.join(chunk for chunk in chunks if chunk)
        
        return {"success": True, "content": text[:5000]} # Limit content size
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Failed to retrieve URL {url}: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"An error occurred while scraping the URL: {str(e)}"}

def manage_profile(action: str, key: Optional[str] = None, value: Optional[Any] = None) -> Dict[str, Any]:
    """
    Manages the user's profile.json file.

    Args:
        action: The action to perform ('read', 'write', 'get', 'set').
        key: The key to get or set in the profile.
        value: The value to set for a key (only for 'set' action).

    Returns:
        A dictionary with the result of the operation.
    """
    config = get_config()
    profile_path = os.path.join(config.config_dir, "profile.json")

    # Ensure a default profile exists
    if not os.path.exists(profile_path):
        with open(profile_path, 'w') as f:
            json.dump({
                "name": "User", 
                "preferences": {"default_tool": "shell"},
                "policies": [
                    {"name": "no_root_processes", "enabled": False, "description": "Ensures no processes are running with root or SYSTEM privileges."}
                ],
                "security": {
                    "command_blacklist": ["rm", "del", "format", "mkfs", "shutdown", "reboot"],
                    "file_access_blacklist": ["/etc/shadow", "/etc/passwd", "C:\\\\Windows\\\\System32\\\\config"],
                    "allow_shell_commands": True,
                    "allow_tool_usage": True
                }
            }, f, indent=2)

    try:
        with open(profile_path, 'r+') as f:
            profile_data = json.load(f)

            if action == 'read':
                return {"success": True, "profile": profile_data}
            
            elif action == 'get':
                if not key:
                    return {"success": False, "error": "A 'key' must be provided for the 'get' action."}
                return {"success": True, "key": key, "value": profile_data.get(key)}

            elif action == 'set':
                if not key:
                    return {"success": False, "error": "A 'key' must be provided for the 'set' action."}
                
                # Navigate nested keys if necessary, e.g., "preferences.editor"
                keys = key.split('.')
                d = profile_data
                for k in keys[:-1]:
                    d = d.setdefault(k, {})
                d[keys[-1]] = value

                # Go back to the beginning of the file to overwrite
                f.seek(0)
                json.dump(profile_data, f, indent=2)
                f.truncate()
                return {"success": True, "message": f"Set '{key}' to '{value}' in profile."}
            
            else:
                return {"success": False, "error": f"Invalid action '{action}'. Must be one of 'read', 'get', 'set'."}

    except Exception as e:
        return {"success": False, "error": f"An error occurred while managing the profile: {str(e)}"}

def check_policies() -> Dict[str, Any]:
    """
    Checks the system state against policies defined in profile.json.
    """
    config = get_config()
    profile_path = os.path.join(config.config_dir, "profile.json")

    if not os.path.exists(profile_path):
        return {"success": True, "violations": [], "message": "No profile found, no policies to check."}

    with open(profile_path, 'r') as f:
        profile = json.load(f)
    
    policies = profile.get("policies", [])
    if not policies:
        return {"success": True, "violations": [], "message": "No policies defined in profile."}

    violations = []
    for policy in policies:
        if not policy.get("enabled", False):
            continue
        
        policy_name = policy.get("name")
        if policy_name == "no_root_processes":
            try:
                for p in psutil.process_iter(['username']):
                    # 'root' on linux/mac, 'SYSTEM' on windows
                    if p.info['username'] == 'root' or p.info['username'] == 'SYSTEM':
                        violations.append({"policy": policy_name, "details": f"Found root-level process: {p.info}"})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Add more policy checks here in the future
        # e.g., check for open ports, firewall rules, etc.

    if violations:
        return {"success": True, "violations": violations, "message": f"Found {len(violations)} policy violations."}
    
    return {"success": True, "violations": [], "message": "All checked policies are compliant."}

def monitor_file(file_path: str, keyword: str, timeout: int = 60) -> Dict[str, Any]:
    """
    Monitors a file for a specific keyword until it's found or a timeout is reached.
    This is a long-running tool.

    Args:
        file_path: The path to the file to monitor.
        keyword: The keyword to search for in new lines.
        timeout: The maximum time to monitor in seconds.

    Returns:
        A dictionary indicating if the keyword was found.
    """
    start_time = time.time()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Go to the end of the file
            f.seek(0, 2)
            
            while time.time() - start_time < timeout:
                line = f.readline()
                if not line:
                    time.sleep(1) # Wait for new content
                    continue
                
                if keyword in line:
                    return {
                        "success": True, 
                        "found": True,
                        "line": line.strip(),
                        "message": f"Keyword '{keyword}' found."
                    }
        
        return {
            "success": True, 
            "found": False, 
            "message": f"Timeout reached. Keyword '{keyword}' not found in {file_path} within {timeout}s."
        }
    except FileNotFoundError:
        return {"success": False, "error": f"File not found: {file_path}"}
    except Exception as e:
        return {"success": False, "error": f"An error occurred while monitoring the file: {str(e)}"}

def read_windows_event_log(log_name: str, event_count: int = 10, event_type: str = "Error") -> Dict[str, Any]:
    """
    Reads recent events from a specified Windows Event Log.

    Args:
        log_name: The name of the log to read (e.g., 'Application', 'System', 'Security').
        event_count: The number of recent events to retrieve.
        event_type: The type of event to filter for (e.g., 'Error', 'Warning', 'Information').

    Returns:
        A dictionary containing a list of event records.
    """
    if sys.platform != "win32":
        return {"success": False, "error": "This tool is only available on Windows."}

    try:
        import win32evtlog
        import win32evtlogutil
        
        server = 'localhost'
        logtype = log_name
        
        hand = win32evtlog.OpenEventLog(server, logtype)
        flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
        total = win32evtlog.GetNumberOfEventLogRecords(hand)
        
        events = []
        if total > 0:
            raw_events = win32evtlog.ReadEventLog(hand, flags, 0)
            
            event_type_map = {
                "Error": win32evtlog.EVENTLOG_ERROR_TYPE,
                "Warning": win32evtlog.EVENTLOG_WARNING_TYPE,
                "Information": win32evtlog.EVENTLOG_INFORMATION_TYPE,
            }
            target_type = event_type_map.get(event_type)

            for event in raw_events:
                if len(events) >= event_count:
                    break
                
                if target_type and event.EventType != target_type:
                    continue

                events.append({
                    "source_name": event.SourceName,
                    "event_id": event.EventID,
                    "time_generated": event.TimeGenerated.Format(),
                    "event_type": event.EventType,
                    "message": win32evtlogutil.SafeFormatMessage(event, logtype)
                })
        
        win32evtlog.CloseEventLog(hand)
        
        return {"success": True, "events": events}
    except ImportError:
        return {"success": False, "error": "The 'pywin32' library is required. Please install it."}
    except Exception as e:
        # Check for specific "access denied" error
        if "Access is denied" in str(e):
             return {"success": False, "error": f"Access denied to '{log_name}' log. The agent may need to run with elevated privileges to access this log."}
        return {"success": False, "error": f"An unexpected error occurred: {str(e)}"} 