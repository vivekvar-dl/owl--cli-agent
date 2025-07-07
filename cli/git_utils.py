import subprocess
from typing import Tuple

def get_staged_diff() -> Tuple[str or None, str or None]:
    """
    Gets the diff of staged changes in the current Git repository.

    Returns:
        A tuple containing (the diff string, an error string).
        If there are no staged changes, the diff string will be empty.
        If an error occurs, the diff string will be None.
    """
    try:
        # Check if it's a git repository
        subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], check=True, capture_output=True)
        
        # Get the staged diff
        result = subprocess.run(
            ["git", "diff", "--staged"],
            capture_output=True,
            text=True,
            check=True
        )
        
        if not result.stdout:
            return "", "No staged changes found. Use 'git add' to stage your changes."
            
        return result.stdout, None
        
    except FileNotFoundError:
        return None, "Git command not found. Please ensure Git is installed and in your PATH."
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.strip()
        if "not a git repository" in error_message:
            return None, "This is not a Git repository."
        return None, f"An error occurred while running git: {error_message}" 