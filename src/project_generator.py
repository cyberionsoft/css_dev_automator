"""
Project Generator for CSS Dev Automator
Orchestrates the generation of all files including prompts and SP execution files
"""

from pathlib import Path
from typing import Any

from .main_processor import MainProcessor
from .prompt_processor import PromptProcessor
from .solution_manager import SolutionManager


class ProjectGenerator:
    """
    Orchestrates the generation of all project files including:
    1. Processing and updating prompt templates
    2. Generating SP execution files
    3. Organizing files in the correct project folders
    """

    def __init__(self):
        """Initialize the project generator."""
        self.solution_manager = SolutionManager()
        self.prompt_processor = PromptProcessor()

    def generate_all_files(
        self, excel_data: list[dict], module_name: str, feature_name: str, solution_path: str
    ) -> dict[str, Any]:
        """
        Generate all files including prompts and SP execution files.

        Args:
            excel_data: List of SP data from Excel
            module_name: Module name from Excel
            feature_name: Feature name from Excel
            solution_path: Path to .NET solution file

        Returns:
            Generation result with success status and summary
        """
        try:
            summary = {"completed": [], "failed": [], "errors": []}

            # Get project folder paths
            project_folders = self.solution_manager.get_project_folders(solution_path)

            # Step 1: Clear SPExecution folder
            if self.solution_manager.clear_sp_execution_folder(solution_path):
                summary["completed"].append("Cleared SPExecution folder")
            else:
                summary["failed"].append("Clear SPExecution folder")
                summary["errors"].append("Failed to clear SPExecution folder")

            # Step 2: Process prompt templates
            prompt_result = self._generate_prompts(
                module_name, feature_name, project_folders["AIPrompt"]
            )

            if prompt_result["success"]:
                summary["completed"].append(
                    f"Processed {len(prompt_result['processed_files'])} prompt files"
                )
                for file_path in prompt_result["processed_files"]:
                    summary["completed"].append(f"  - Generated: {Path(file_path).name}")
            else:
                summary["failed"].append("Process prompt templates")
                if "error" in prompt_result:
                    summary["errors"].append(f"Prompt processing: {prompt_result['error']}")

                for failed_file in prompt_result.get("failed_files", []):
                    summary["errors"].append(
                        f"Prompt {failed_file['file']}: {failed_file['error']}"
                    )

            # Step 3: Generate SP execution files
            sp_result = self._generate_sp_files(excel_data, project_folders["SPExecution"])

            if sp_result["success"]:
                summary["completed"].append("Generated SP execution files")
                summary["completed"].append(
                    f"  - Processed {sp_result['total_processed']} stored procedures"
                )
                summary["completed"].append(f"  - Success: {sp_result['successful']}")
                summary["completed"].append(f"  - Failed: {sp_result['failed']}")
            else:
                summary["failed"].append("Generate SP execution files")
                if "error" in sp_result:
                    summary["errors"].append(f"SP generation: {sp_result['error']}")

            # Step 4: Log database connection status
            config_path = Path("config.json")
            if config_path.exists():
                import json

                with open(config_path) as f:
                    config = json.load(f)
                    conn_str = config.get("database", {}).get("connection_string", "")
                    if conn_str:
                        summary["completed"].append(
                            "Database connection configured from GTI.API project"
                        )
                    else:
                        summary["errors"].append("No database connection string configured")

            # Determine overall success
            overall_success = len(summary["failed"]) == 0

            return {"success": overall_success, "summary": summary}

        except Exception as e:
            return {"success": False, "error": f"File generation failed: {e}"}

    def _generate_prompts(
        self, module_name: str, feature_name: str, output_dir: Path
    ) -> dict[str, Any]:
        """
        Generate updated prompt files.

        Args:
            module_name: Module name
            feature_name: Feature name
            output_dir: Output directory for prompts

        Returns:
            Generation result
        """
        try:
            return self.prompt_processor.process_all_prompts(module_name, feature_name, output_dir)

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_sp_files(self, excel_data: list[dict], output_dir: Path) -> dict[str, Any]:
        """
        Generate SP execution files using the existing main processor.

        Args:
            excel_data: SP data from Excel
            output_dir: Output directory for SP files

        Returns:
            Generation result
        """
        try:
            # Create a temporary Excel file with the SP data
            temp_excel_path = self._create_temp_excel_file(excel_data)

            # Update configuration to use the temporary Excel file and custom output directory
            original_config = self._backup_and_update_config(temp_excel_path, output_dir)

            try:
                # Initialize and run the main processor
                processor = MainProcessor()

                if not processor.initialize():
                    return {"success": False, "error": "Failed to initialize SP processor"}

                # Process stored procedures
                result = processor.process_stored_procedures()

                # Clean up
                processor.cleanup()

                if result.get("success", True) and "error" not in result:
                    return {
                        "success": True,
                        "total_processed": result.get("total_processed", len(excel_data)),
                        "successful": result.get("successful", 0),
                        "failed": result.get("failed", 0),
                    }
                else:
                    return {"success": False, "error": result.get("error", "SP processing failed")}

            finally:
                # Restore original configuration
                self._restore_config(original_config)

                # Clean up temporary Excel file
                if temp_excel_path and temp_excel_path.exists():
                    temp_excel_path.unlink()

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _create_temp_excel_file(self, excel_data: list[dict]) -> Path:
        """
        Create a temporary Excel file with SP data.

        Args:
            excel_data: SP data

        Returns:
            Path to temporary Excel file
        """
        import polars as pl

        # Convert data to DataFrame
        df = pl.DataFrame(
            {
                "SP Name": [item["name"] for item in excel_data],
                "Type": [item["type"] for item in excel_data],
            }
        )

        # Create temporary file
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / "temp_sp_data.xlsx"

        # Write to Excel
        df.write_excel(temp_file)

        return temp_file

    def _backup_and_update_config(self, excel_path: Path, output_dir: Path) -> dict:
        """
        Backup current config and update for SP generation.

        Args:
            excel_path: Path to Excel file
            output_dir: Output directory

        Returns:
            Original configuration
        """
        import json

        config_path = Path("config.json")

        # Backup original config
        if config_path.exists():
            with open(config_path) as f:
                original_config = json.load(f)
        else:
            # Create default config if it doesn't exist
            original_config = {
                "database": {
                    "connection_string": "",
                    "connection_timeout": 30,
                    "command_timeout": 300,
                },
                "paths": {
                    "excel_file": "",
                    "output_directory": "OutputFiles",
                    "log_directory": "Logs",
                },
                "processing": {
                    "batch_size": 5,
                    "parallel_processing": True,
                    "max_workers": 3,
                    "continue_on_error": True,
                    "create_input_templates": True,
                },
                "json_extraction": {
                    "fallback_to_template": True,
                    "validate_extracted_json": True,
                    "max_json_size_mb": 10,
                },
            }

        # Update config
        updated_config = original_config.copy()
        updated_config["paths"]["excel_file"] = str(excel_path)
        updated_config["paths"]["output_directory"] = str(output_dir)

        # Write updated config
        with open(config_path, "w") as f:
            json.dump(updated_config, f, indent=4)

        return original_config

    def _restore_config(self, original_config: dict):
        """
        Restore original configuration.

        Args:
            original_config: Original configuration to restore
        """
        import json

        config_path = Path("config.json")

        with open(config_path, "w") as f:
            json.dump(original_config, f, indent=4)
