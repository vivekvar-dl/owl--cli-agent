import os
import re
from typing import Tuple, Optional

def get_symbol_code(file_path: str, symbol: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[int]]:
    """
    Extracts the code for a specific symbol (function or class) from a file,
    along with its start and end line numbers.

    Args:
        file_path: The path to the source code file.
        symbol: The name of the function or class to extract.

    Returns:
        A tuple containing (code, full_content, start_line, end_line).
        Returns (None, None, None, None) if not found.
    """
    if not os.path.exists(file_path):
        return None, None, None, None
    
    with open(file_path, 'r') as f:
        content = f.read()

    if not symbol:
        return content, content, 0, len(content.splitlines())

    # This regex is more robust and handles nested code blocks better by not relying on indentation.
    # It looks for `def` or `class` and captures everything until the next line that
    # starts at the same indentation level (or less), indicating the end of the block.
    pattern = re.compile(
        r"^(?P<indentation>\s*)(?:def|class)\s+" + re.escape(symbol) + r"[\s(:]?.*?:\n(?P<body>(?:(?:\n|(?P=indentation)\s+.*))+)",
        re.MULTILINE
    )
    
    match = pattern.search(content)

    if match:
        code_block = match.group(0)
        
        # Calculate line numbers
        start_line = content.count('\n', 0, match.start()) + 1
        end_line = start_line + code_block.count('\n')
        
        return code_block.strip(), content, start_line, end_line
    
    return None, content, None, None 