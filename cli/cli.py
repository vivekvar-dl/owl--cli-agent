import argparse
import sys
from rich.console import Console

from .handlers import (
    handle_explain,
    handle_doc,
    handle_refactor,
    handle_test,
    handle_commit,
    handle_debug,
    handle_audit,
)
from .ui import display_home_page

console = Console()

def main():
    """The main entry point for the Gemini CLI Coding Assistant."""
    parser = argparse.ArgumentParser(
        description="""
        Welcome to Gemini CLI, your AI Coding Assistant for the Linux Terminal.
        
        This tool helps you explain, document, refactor, and test code without leaving your command line.
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # 'explain' command
    explain_parser = subparsers.add_parser("explain", help="Explains a source code file or a specific symbol within it.")
    explain_parser.add_argument("file_path", type=str, help="The path to the source code file.")
    explain_parser.add_argument("symbol", type=str, nargs="?", help="(Optional) The specific function or class to explain.")

    # 'doc' command
    doc_parser = subparsers.add_parser("doc", help="Generates documentation for a file or a specific symbol.")
    doc_parser.add_argument("file_path", type=str, help="The path to the source code file.")
    doc_parser.add_argument("symbol", type=str, nargs="?", help="(Optional) The specific function or class to document.")

    # 'refactor' command
    refactor_parser = subparsers.add_parser("refactor", help="Refactors a file or symbol based on an instruction.")
    refactor_parser.add_argument("file_path", type=str, help="The path to the source code file.")
    refactor_parser.add_argument("instruction", type=str, help="The natural language instruction for the refactoring.")
    refactor_parser.add_argument("symbol", type=str, nargs="?", help="(Optional) The specific function or class to refactor.")

    # 'test' command
    test_parser = subparsers.add_parser("test", help="Generates a unit test for a file or a specific symbol.")
    test_parser.add_argument("file_path", type=str, help="The path to the source code file.")
    test_parser.add_argument("symbol", type=str, nargs="?", help="(Optional) The specific function or class to generate a test for.")

    # 'debug' command
    debug_parser = subparsers.add_parser("debug", help="Debugs a file based on a traceback or error message.")
    debug_parser.add_argument("file_path", type=str, help="The path to the source code file.")
    debug_parser.add_argument("error_message", type=str, help="The traceback or error message to debug.")

    # 'audit' command
    audit_parser = subparsers.add_parser("audit", help="Audits a file or directory for security vulnerabilities.")
    audit_parser.add_argument("path", type=str, help="The path to the file or directory to audit.")

    # 'commit' command
    subparsers.add_parser("commit", help="Generates a git commit message based on staged changes.")

    # If no command is given, show the home page.
    if len(sys.argv) == 1:
        display_home_page(console)
        sys.exit(0)

    args = parser.parse_args()

    if args.command == "explain":
        handle_explain(args.file_path, args.symbol)
    elif args.command == "doc":
        handle_doc(args.file_path, args.symbol)
    elif args.command == "refactor":
        handle_refactor(args.file_path, args.instruction, args.symbol)
    elif args.command == "test":
        handle_test(args.file_path, args.symbol)
    elif args.command == "debug":
        handle_debug(args.file_path, args.error_message)
    elif args.command == "audit":
        handle_audit(args.path)
    elif args.command == "commit":
        handle_commit()

if __name__ == "__main__":
    main() 