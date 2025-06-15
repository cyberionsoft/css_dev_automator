"""
Configuration Manager
Simplified configuration management for CSS Dev Automator
Used by legacy components (main_processor.py) for backward compatibility
"""

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def get_resource_path(relative_path: str) -> Path:
    """
    Get the absolute path to a resource file.

    This function handles both development and PyInstaller executable environments.
    In development, it returns the path relative to the project root.
    In PyInstaller onefile mode, it returns the path to the extracted temporary files.

    Args:
        relative_path: Path relative to the project root (e.g., "config.json")

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


@dataclass
class DatabaseConfig:
    """Database configuration for legacy components"""
    connection_string: str
    connection_timeout: int = 30
    command_timeout: int = 300


@dataclass
class PathsConfig:
    """Paths configuration for legacy components"""
    excel_file: str
    output_directory: str
    log_directory: str


@dataclass
class ProcessingConfig:
    """Processing configuration for legacy components"""
    batch_size: int = 5
    parallel_processing: bool = True
    max_workers: int = 3
    continue_on_error: bool = True
    create_input_templates: bool = True


@dataclass
class JsonExtractionConfig:
    """JSON extraction configuration for legacy components"""
    fallback_to_template: bool = True
    validate_extracted_json: bool = True
    max_json_size_mb: int = 10


@dataclass
class LoggingConfig:
    """Logging configuration for legacy components"""
    level: str = "INFO"
    console_output: bool = True
    file_output: bool = True
    max_log_size_mb: int = 50
    backup_count: int = 5


class ConfigManager:
    """
    Simplified configuration manager for legacy components.

    Note: The new GUI-based CSS Dev Automator does NOT use this class.
    This is kept only for backward compatibility with main_processor.py
    and related legacy components.
    """

    def __init__(self, config_path: str = "config.json"):
        # Use resource path for PyInstaller compatibility
        if config_path == "config.json":
            self.config_path = str(get_resource_path("config.json"))
        else:
            self.config_path = config_path
        self._config_data: dict[str, Any] | None = None
        self.load_config()

    def load_config(self) -> None:
        """Load configuration from file with minimal validation"""
        try:
            if not os.path.exists(self.config_path):
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

            with open(self.config_path, encoding="utf-8") as f:
                self._config_data = json.load(f)

            # Basic validation - just check required sections exist
            required_sections = ["database", "paths", "processing", "json_extraction"]
            for section in required_sections:
                if section not in self._config_data:
                    raise ValueError(f"Missing required configuration section: {section}")

        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")

    # Removed complex validation methods - not needed for GUI workflow
    # Legacy components can handle missing/invalid config gracefully

    @property
    def database(self) -> DatabaseConfig:
        """Get database configuration"""
        db_data = self._config_data["database"]
        return DatabaseConfig(
            connection_string=db_data["connection_string"],
            connection_timeout=db_data.get("connection_timeout", 30),
            command_timeout=db_data.get("command_timeout", 300),
        )

    @property
    def paths(self) -> PathsConfig:
        """Get paths configuration"""
        paths_data = self._config_data["paths"]
        return PathsConfig(
            excel_file=paths_data["excel_file"],
            output_directory=paths_data["output_directory"],
            log_directory=paths_data["log_directory"],
        )

    @property
    def processing(self) -> ProcessingConfig:
        """Get processing configuration"""
        proc_data = self._config_data["processing"]
        return ProcessingConfig(
            batch_size=proc_data.get("batch_size", 5),
            parallel_processing=proc_data.get("parallel_processing", True),
            max_workers=proc_data.get("max_workers", 3),
            continue_on_error=proc_data.get("continue_on_error", True),
            create_input_templates=proc_data.get("create_input_templates", True),
        )

    @property
    def json_extraction(self) -> JsonExtractionConfig:
        """Get JSON extraction configuration"""
        json_data = self._config_data["json_extraction"]
        return JsonExtractionConfig(
            fallback_to_template=json_data.get("fallback_to_template", True),
            validate_extracted_json=json_data.get("validate_extracted_json", True),
            max_json_size_mb=json_data.get("max_json_size_mb", 10),
        )

    @property
    def logging(self) -> LoggingConfig:
        """Get logging configuration"""
        log_data = self._config_data["logging"]
        return LoggingConfig(
            level=log_data.get("level", "INFO"),
            console_output=log_data.get("console_output", True),
            file_output=log_data.get("file_output", True),
            max_log_size_mb=log_data.get("max_log_size_mb", 50),
            backup_count=log_data.get("backup_count", 5),
        )

    def update_connection_string(self, connection_string: str) -> None:
        """Update the database connection string"""
        self._config_data["database"]["connection_string"] = connection_string

        # Save updated configuration
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config_data, f, indent=4)
