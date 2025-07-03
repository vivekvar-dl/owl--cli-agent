import logging
import sys

from .cli import run_cli

# Configure logging
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the application."""
    try:
        exit_code = run_cli()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        print("\nOperation cancelled by user")
        sys.exit(130)  # 128 + SIGINT
    except Exception as e:
        logger.exception(f"Unhandled exception: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 