"""
Prompt Processor for CSS Dev Automator
Processes generic prompt templates and updates them with specific entity and module names
"""

import sys
from pathlib import Path
from typing import Any


def get_resource_path(relative_path: str) -> Path:
    """
    Get the absolute path to a resource file.

    This function handles both development and PyInstaller executable environments.
    In development, it returns the path relative to the project root.
    In PyInstaller onefile mode, it returns the path to the extracted temporary files.

    Args:
        relative_path: Path relative to the project root (e.g., "Templates/Prompts")

    Returns:
        Absolute path to the resource file
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        # Development mode - use project root
        base_path = Path(__file__).parent.parent

    return base_path / relative_path


class PromptProcessor:
    """
    Processes prompt templates by replacing generic placeholders with specific
    entity and module names from the Excel data.
    """

    def __init__(self):
        """Initialize the prompt processor."""
        # Use resource path for PyInstaller compatibility
        self.template_dir = get_resource_path("Templates/Prompts")
        # Define multiple placeholder patterns that might be used in templates
        self.placeholder_patterns = {
            # Square brackets
            "[YourEntityName]": "",
            "[YourModuleName]": "",
            "[EntityName]": "",
            "[ModuleName]": "",
            # Curly braces
            "{YourEntityName}": "",
            "{YourModuleName}": "",
            "{EntityName}": "",
            "{ModuleName}": "",
            "{MODULE_NAME}": "",
            "{ENTITY_NAME}": "",
            "{Entity_NAME}": "",
            # Other variations
            "YourEntityName": "",
            "YourModuleName": "",
        }

    def process_all_prompts(
        self, module_name: str, feature_name: str, output_dir: Path
    ) -> dict[str, Any]:
        """
        Process all prompt templates and save updated versions.

        Args:
            module_name: Module name from Excel
            feature_name: Feature/Entity name from Excel
            output_dir: Directory to save processed prompts (AIPrompt folder)

        Returns:
            Processing result with success status and details
        """
        try:
            # Update all placeholder patterns with the provided values
            self._update_placeholders(module_name, feature_name)

            processed_files = []
            failed_files = []

            # Process each prompt file
            for prompt_file in self.template_dir.glob("Prompt*.txt"):
                try:
                    result = self._process_single_prompt(prompt_file, output_dir)
                    if result["success"]:
                        processed_files.append(result["output_file"])
                    else:
                        failed_files.append({"file": prompt_file.name, "error": result["error"]})

                except Exception as e:
                    failed_files.append({"file": prompt_file.name, "error": str(e)})

            return {
                "success": len(failed_files) == 0,
                "processed_files": processed_files,
                "failed_files": failed_files,
                "total_files": len(processed_files) + len(failed_files),
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to process prompts: {e}"}

    def _process_single_prompt(self, prompt_file: Path, output_dir: Path) -> dict[str, Any]:
        """
        Process a single prompt template file.

        Args:
            prompt_file: Path to prompt template file
            output_dir: Output directory

        Returns:
            Processing result
        """
        try:
            # Read template content
            with open(prompt_file, encoding="utf-8") as f:
                content = f.read()

            # Replace placeholders
            updated_content = self._replace_placeholders(content)

            # Create output file path
            output_file = output_dir / prompt_file.name

            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)

            # Write updated content
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(updated_content)

            return {"success": True, "output_file": str(output_file)}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _update_placeholders(self, module_name: str, entity_name: str):
        """
        Update all placeholder patterns with the provided values.

        Args:
            module_name: Module name from Excel
            entity_name: Entity name from Excel
        """
        # Update all entity name patterns
        self.placeholder_patterns["[YourEntityName]"] = entity_name
        self.placeholder_patterns["[EntityName]"] = entity_name
        self.placeholder_patterns["{YourEntityName}"] = entity_name
        self.placeholder_patterns["{EntityName}"] = entity_name
        self.placeholder_patterns["{ENTITY_NAME}"] = entity_name.upper()
        self.placeholder_patterns["{Entity_NAME}"] = entity_name
        self.placeholder_patterns["YourEntityName"] = entity_name

        # Update all module name patterns
        self.placeholder_patterns["[YourModuleName]"] = module_name
        self.placeholder_patterns["[ModuleName]"] = module_name
        self.placeholder_patterns["{YourModuleName}"] = module_name
        self.placeholder_patterns["{ModuleName}"] = module_name
        self.placeholder_patterns["{MODULE_NAME}"] = module_name.upper()
        self.placeholder_patterns["YourModuleName"] = module_name

    def _replace_placeholders(self, content: str) -> str:
        """
        Replace placeholders in content with actual values using multiple patterns.

        Args:
            content: Template content

        Returns:
            Updated content with placeholders replaced
        """
        updated_content = content

        # Replace all placeholder patterns
        for placeholder, value in self.placeholder_patterns.items():
            if value:  # Only replace if we have a value
                updated_content = updated_content.replace(placeholder, value)

        return updated_content

    def get_available_prompts(self) -> list[str]:
        """
        Get list of available prompt template files.

        Returns:
            List of prompt file names
        """
        try:
            return [f.name for f in self.template_dir.glob("Prompt*.txt")]
        except Exception:
            return []

    def validate_template_directory(self) -> bool:
        """
        Validate that the template directory exists and contains prompt files.

        Returns:
            True if valid, False otherwise
        """
        try:
            if not self.template_dir.exists():
                return False

            prompt_files = list(self.template_dir.glob("Prompt*.txt"))
            return len(prompt_files) > 0

        except Exception:
            return False

    def preview_processed_prompt(
        self, prompt_file_name: str, module_name: str, feature_name: str
    ) -> str:
        """
        Preview how a prompt would look after processing without saving it.

        Args:
            prompt_file_name: Name of prompt file to preview
            module_name: Module name
            feature_name: Feature name

        Returns:
            Processed content or error message
        """
        try:
            prompt_file = self.template_dir / prompt_file_name

            if not prompt_file.exists():
                return f"Error: Prompt file '{prompt_file_name}' not found"

            # Read template content
            with open(prompt_file, encoding="utf-8") as f:
                content = f.read()

            # Create temporary instance to avoid modifying the main placeholders
            temp_processor = PromptProcessor()
            temp_processor._update_placeholders(module_name, feature_name)

            # Replace placeholders
            updated_content = temp_processor._replace_placeholders(content)

            return updated_content

        except Exception as e:
            return f"Error previewing prompt: {e}"
