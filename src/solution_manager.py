"""
Solution Manager for CSS Dev Automator
Manages .NET solution files, CSS.AIReference project setup, and database connection extraction
"""

import json
import subprocess
from pathlib import Path
from typing import Any


class SolutionManager:
    """
    Manages .NET solution files and ensures CSS.AIReference project exists
    with required folder structure.
    """

    def __init__(self):
        """Initialize the solution manager."""
        self.required_folders = ["AIPrompt", "SPExecution", "SPReference", "UIReference"]
        self.project_name = "CSS.AIReference"

    def setup_solution(self, solution_path: str) -> dict[str, Any]:
        """
        Setup solution by ensuring CSS.AIReference project exists with required folders
        and extract database connection string from GTI.API project.

        Args:
            solution_path: Path to .sln file

        Returns:
            Setup result with success status, messages, and connection string
        """
        try:
            solution_path = Path(solution_path)
            solution_dir = solution_path.parent
            project_dir = solution_dir / self.project_name

            messages = []

            # Extract database connection string from GTI.API project
            connection_result = self._extract_database_connection(solution_dir, messages)

            # Check if project directory exists
            if not project_dir.exists():
                # Create new class library project
                result = self._create_class_library_project(solution_dir, messages)
                if not result:
                    return {"success": False, "error": "Failed to create CSS.AIReference project"}
            else:
                messages.append(f"Project {self.project_name} already exists")

            # Ensure project is added to solution
            self._ensure_project_in_solution(solution_path, project_dir, messages)

            # Create required folders
            self._create_required_folders(project_dir, messages)

            return {
                "success": True,
                "file_path": str(solution_path),
                "messages": messages,
                "connection_string": connection_result.get("connection_string"),
                "connection_messages": connection_result.get("messages", []),
            }

        except Exception as e:
            return {"success": False, "error": f"Solution setup failed: {e}"}

    def _create_class_library_project(self, solution_dir: Path, messages: list[str]) -> bool:
        """
        Create a new .NET 9 class library project.

        Args:
            solution_dir: Solution directory
            messages: List to append messages to

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if .NET SDK is available
            if not self._check_dotnet_sdk(messages):
                return False

            project_dir = solution_dir / self.project_name

            # Create project directory
            project_dir.mkdir(exist_ok=True)

            # Create .NET 9 class library project
            cmd = [
                "dotnet",
                "new",
                "classlib",
                "--framework",
                "net9.0",
                "--name",
                self.project_name,
                "--output",
                str(project_dir),
                "--force",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=solution_dir)

            if result.returncode == 0:
                messages.append(f"Created new .NET 9 class library: {self.project_name}")
                return True
            else:
                messages.append(f"Failed to create project: {result.stderr}")
                return False

        except Exception as e:
            messages.append(f"Error creating project: {e}")
            return False

    def _check_dotnet_sdk(self, messages: list[str]) -> bool:
        """
        Check if .NET SDK is installed and available.

        Args:
            messages: List to append messages to

        Returns:
            True if .NET SDK is available, False otherwise
        """
        try:
            result = subprocess.run(
                ["dotnet", "--version"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                messages.append(f".NET SDK version {version} detected")
                return True
            else:
                messages.append("Error: .NET SDK not found or not working properly")
                return False

        except subprocess.TimeoutExpired:
            messages.append("Error: .NET SDK check timed out")
            return False
        except FileNotFoundError:
            messages.append("Error: .NET SDK not installed. Please install .NET 9 SDK")
            return False
        except Exception as e:
            messages.append(f"Error checking .NET SDK: {e}")
            return False

    def _ensure_project_in_solution(
        self, solution_path: Path, project_dir: Path, messages: list[str]
    ):
        """
        Ensure the project is added to the solution.

        Args:
            solution_path: Path to solution file
            project_dir: Path to project directory
            messages: List to append messages to
        """
        try:
            project_file = project_dir / f"{self.project_name}.csproj"

            if not project_file.exists():
                messages.append(f"Warning: Project file not found: {project_file}")
                return

            # Add project to solution
            cmd = ["dotnet", "sln", str(solution_path), "add", str(project_file)]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=solution_path.parent)

            if result.returncode == 0:
                if "already" in result.stdout.lower():
                    messages.append(f"Project {self.project_name} already in solution")
                else:
                    messages.append(f"Added {self.project_name} to solution")
            else:
                # Check if it's already added (common case)
                if "already" in result.stderr.lower() or "duplicate" in result.stderr.lower():
                    messages.append(f"Project {self.project_name} already in solution")
                else:
                    messages.append(f"Warning: Could not add project to solution: {result.stderr}")

        except Exception as e:
            messages.append(f"Error adding project to solution: {e}")

    def _create_required_folders(self, project_dir: Path, messages: list[str]):
        """
        Create required folders in the project.

        Args:
            project_dir: Path to project directory
            messages: List to append messages to
        """
        try:
            for folder_name in self.required_folders:
                folder_path = project_dir / folder_name

                if not folder_path.exists():
                    folder_path.mkdir(parents=True, exist_ok=True)
                    messages.append(f"Created folder: {folder_name}")
                else:
                    messages.append(f"Folder already exists: {folder_name}")

        except Exception as e:
            messages.append(f"Error creating folders: {e}")

    def get_project_folders(self, solution_path: str) -> dict[str, Path]:
        """
        Get paths to the required project folders.

        Args:
            solution_path: Path to solution file

        Returns:
            Dictionary mapping folder names to paths
        """
        solution_path = Path(solution_path)
        solution_dir = solution_path.parent
        project_dir = solution_dir / self.project_name

        return {folder_name: project_dir / folder_name for folder_name in self.required_folders}

    def clear_sp_execution_folder(self, solution_path: str) -> bool:
        """
        Clear the SPExecution folder before generating new files.

        Args:
            solution_path: Path to solution file

        Returns:
            True if successful, False otherwise
        """
        try:
            folders = self.get_project_folders(solution_path)
            sp_execution_folder = folders["SPExecution"]

            if sp_execution_folder.exists():
                # Remove all files in the folder
                for file_path in sp_execution_folder.iterdir():
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        # Remove subdirectories recursively
                        import shutil

                        shutil.rmtree(file_path)

                return True

            return True  # Folder doesn't exist, consider it cleared

        except Exception as e:
            print(f"Error clearing SPExecution folder: {e}")
            return False

    def setup_css_ai_reference_project(self, solution_path: str) -> dict[str, Any]:
        """
        Setup CSS.AIReference project - alias for setup_solution method.
        This method is called by the worker tasks.

        Args:
            solution_path: Path to .sln file

        Returns:
            Setup result with success status, messages, and connection string
        """
        return self.setup_solution(solution_path)

    def validate_solution_file(self, solution_path: str) -> bool:
        """
        Validate that the given path is a valid .NET solution file.

        Args:
            solution_path: Path to solution file

        Returns:
            True if valid, False otherwise
        """
        try:
            solution_path = Path(solution_path)

            # Check if file exists and has .sln extension
            if not solution_path.exists() or solution_path.suffix.lower() != ".sln":
                return False

            # Try to read the solution file to check if it's valid
            with open(solution_path, encoding="utf-8") as f:
                content = f.read()
                # Basic check for solution file format
                if "Microsoft Visual Studio Solution File" in content:
                    return True

            return False

        except Exception:
            return False

    def _extract_database_connection(
        self, solution_dir: Path, messages: list[str]
    ) -> dict[str, Any]:
        """
        Extract database connection string from GTI.API project's appsettings.json.

        Args:
            solution_dir: Solution directory
            messages: List to append messages to

        Returns:
            Dictionary with connection string and extraction messages
        """
        try:
            # Look for GTI.API project directory
            gti_api_dir = solution_dir / "GTI.API"

            if not gti_api_dir.exists():
                # Try alternative naming patterns
                possible_names = ["Gti.API", "GTI.Api", "Gti.Api", "GTIAPI", "GtiAPI"]
                for name in possible_names:
                    alt_dir = solution_dir / name
                    if alt_dir.exists():
                        gti_api_dir = alt_dir
                        break
                else:
                    messages.append("Warning: GTI.API project not found")
                    return {
                        "connection_string": None,
                        "messages": ["GTI.API project directory not found in solution"],
                    }

            # Look for appsettings.json files
            appsettings_files = [
                gti_api_dir / "appsettings.json",
                gti_api_dir / "appsettings.Development.json",
                gti_api_dir / "appsettings.Production.json",
            ]

            connection_string = None
            connection_messages = []

            for appsettings_file in appsettings_files:
                if appsettings_file.exists():
                    try:
                        result = self._parse_connection_string_from_appsettings(appsettings_file)
                        if result["connection_string"]:
                            connection_string = result["connection_string"]
                            connection_messages.append(
                                f"Found connection string in {appsettings_file.name}"
                            )
                            messages.append(
                                f"Database connection extracted from {appsettings_file.name}"
                            )
                            break
                        else:
                            connection_messages.extend(result["messages"])
                    except Exception as e:
                        connection_messages.append(f"Error reading {appsettings_file.name}: {e}")

            if not connection_string:
                messages.append("Warning: No active connection string found in GTI.API project")
                connection_messages.append(
                    "No uncommented connection string found in any appsettings file"
                )

            return {"connection_string": connection_string, "messages": connection_messages}

        except Exception as e:
            error_msg = f"Error extracting database connection: {e}"
            messages.append(error_msg)
            return {"connection_string": None, "messages": [error_msg]}

    def _parse_connection_string_from_appsettings(self, appsettings_file: Path) -> dict[str, Any]:
        """
        Parse connection string from appsettings.json file.
        Handles JSON with comments (JSONC format).

        Args:
            appsettings_file: Path to appsettings.json file

        Returns:
            Dictionary with connection string and parsing messages
        """
        try:
            with open(appsettings_file, encoding="utf-8") as f:
                content = f.read()

            # Try to parse JSON directly first
            try:
                config = json.loads(content)
            except json.JSONDecodeError:
                # If direct parsing fails, try removing comments
                cleaned_content = self._remove_json_comments(content)
                config = json.loads(cleaned_content)

            # Look for ConnectionStrings section
            if "ConnectionStrings" not in config:
                return {
                    "connection_string": None,
                    "messages": [f"No ConnectionStrings section found in {appsettings_file.name}"],
                }

            connection_strings = config["ConnectionStrings"]

            # Find the first uncommented (active) connection string
            for key, value in connection_strings.items():
                if isinstance(value, str) and value.strip():
                    # Check if it's a valid connection string (contains common keywords)
                    if any(
                        keyword in value.lower()
                        for keyword in ["data source", "server", "database", "initial catalog"]
                    ):
                        return {
                            "connection_string": value,
                            "messages": [f"Found active connection string: {key}"],
                        }

            return {
                "connection_string": None,
                "messages": [f"No valid connection strings found in {appsettings_file.name}"],
            }

        except json.JSONDecodeError as e:
            return {
                "connection_string": None,
                "messages": [f"Invalid JSON in {appsettings_file.name}: {e}"],
            }
        except Exception as e:
            return {
                "connection_string": None,
                "messages": [f"Error parsing {appsettings_file.name}: {e}"],
            }

    def _remove_json_comments(self, content: str) -> str:
        """
        Remove comments from JSON content to make it valid JSON.
        Handles both single-line (//) and end-of-line comments.

        Args:
            content: JSON content with comments

        Returns:
            Cleaned JSON content without comments
        """
        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            # Handle end-of-line comments
            if '//' in line:
                # Find the position of // that's not inside a string
                in_string = False
                escape_next = False
                comment_pos = -1

                for i, char in enumerate(line):
                    if escape_next:
                        escape_next = False
                        continue

                    if char == '\\':
                        escape_next = True
                        continue

                    if char == '"':
                        in_string = not in_string
                        continue

                    if not in_string and char == '/' and i + 1 < len(line) and line[i + 1] == '/':
                        comment_pos = i
                        break

                if comment_pos >= 0:
                    line = line[:comment_pos].rstrip()

            # Skip lines that are only comments
            stripped = line.strip()
            if stripped.startswith('//'):
                continue

            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)
