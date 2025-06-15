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


class StatusLogger:
    """Redirect print statements to GUI status area when GUI is available."""

    def __init__(self, gui_manager=None):
        self.gui_manager = gui_manager
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def write(self, text):
        """Write text to GUI status area if available, otherwise to original stdout."""
        if self.gui_manager and hasattr(self.gui_manager, '_log_status'):
            # Only log non-empty, non-whitespace text
            text = text.strip()
            if text:
                self.gui_manager._log_status(text)
        else:
            # Fallback to original stdout
            self.original_stdout.write(text)

    def flush(self):
        """Flush the output."""
        if hasattr(self.original_stdout, 'flush'):
            self.original_stdout.flush()


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
            # Use subprocess without shell=True for better security
            subprocess.Popen([str(dev_manager_path)])
            return 0
        else:
            # Show error dialog instead of print for GUI mode
            try:
                from PySide6.QtWidgets import QApplication, QMessageBox
                app = QApplication.instance()
                if app is None:
                    app = QApplication(sys.argv)

                QMessageBox.critical(
                    None,
                    "DevManager Not Found",
                    "DevManager not found at expected location.\nPlease ensure DevManager is properly installed."
                )
            except ImportError:
                # Fallback to print if GUI not available
                print("ERROR: DevManager not found at expected location.")
                print("Please ensure DevManager is properly installed.")
            return 1

    except Exception as e:
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)

            QMessageBox.critical(None, "Error", f"Failed to start DevManager: {e}")
        except ImportError:
            print(f"ERROR: Failed to start DevManager: {e}")
        return 1


def main():
    """Main entry point"""
    args = parse_arguments()

    # Check if token is provided
    if not args.token:
        return start_dev_manager_and_exit()

    # Validate token
    token_validator = TokenValidator()
    if not token_validator.validate_token(args.token):
        return start_dev_manager_and_exit()

    # Mark token as used (for one-time use tokens)
    token_validator.mark_token_used(args.token)

    # Token is valid, start GUI
    try:
        # Import QApplication here to avoid issues
        from PySide6.QtWidgets import QApplication

        # Create QApplication if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Create and show GUI
        gui_manager = GUIManager()

        # Set up status logger to redirect print statements to GUI
        status_logger = StatusLogger(gui_manager)
        sys.stdout = status_logger
        sys.stderr = status_logger

        # Log initial status
        gui_manager._log_status("Token validated successfully. Starting CSS Dev Automator GUI...")

        gui_manager.show()

        # Start the event loop
        return app.exec()

    except Exception as e:
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Error", f"Failed to start GUI: {e}")
        except ImportError:
            print(f"ERROR: Failed to start GUI: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
