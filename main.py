#!/usr/bin/env python3
"""
CSS Dev Automator - Main Entry Point
This application should only be started with a token from dev_manager.
If started without token, it will launch dev_manager and exit.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, continue without it
    pass

# Add the current directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.gui_manager import GUIManager
from src.token_validator import TokenValidator


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="CSS Dev Automator")
    parser.add_argument("--token", type=str, help="Authentication token from dev_manager")
    return parser.parse_args()


def start_dev_manager_and_exit():
    """Start dev_manager and exit this application"""
    try:
        # Path to dev_manager executable
        dev_manager_path = Path("C:/Program Files/DevManager/DevManager.exe")

        if dev_manager_path.exists():
            print("Starting DevManager...")
            subprocess.Popen([str(dev_manager_path)], shell=True)
            print("DevManager started. Exiting DevAutomator...")
        else:
            print("ERROR: DevManager not found at expected location.")
            print("Please ensure DevManager is properly installed.")
            return 1

    except Exception as e:
        print(f"ERROR: Failed to start DevManager: {e}")
        return 1

    return 0


def main():
    """Main entry point"""
    args = parse_arguments()

    # Check if token is provided
    if not args.token:
        print("CSS Dev Automator must be started with a token from dev_manager.")
        print("Starting dev_manager...")
        return start_dev_manager_and_exit()

    # Validate token
    token_validator = TokenValidator()
    if not token_validator.validate_token(args.token):
        print("ERROR: Invalid or expired token.")
        print("Starting dev_manager...")
        return start_dev_manager_and_exit()

    # Mark token as used (for one-time use tokens)
    token_validator.mark_token_used(args.token)

    # Token is valid, start GUI
    try:
        print("Token validated successfully. Starting CSS Dev Automator GUI...")

        # Import QApplication here to avoid issues
        from PySide6.QtWidgets import QApplication

        # Create QApplication if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Create and show GUI
        gui_manager = GUIManager()
        gui_manager.show()

        # Start the event loop
        return app.exec()

    except Exception as e:
        print(f"ERROR: Failed to start GUI: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
