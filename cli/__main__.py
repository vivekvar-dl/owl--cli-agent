"""
This allows the CLI to be run as a module with `python -m cli`.
"""
from dotenv import load_dotenv
load_dotenv()

from .cli import main

if __name__ == "__main__":
    main() 