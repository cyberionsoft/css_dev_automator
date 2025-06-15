"""
GUI Manager for CSS Dev Automator
Provides the main GUI interface with 4 core features using PySide6
"""

import shutil
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    from .excel_validator import ExcelValidator
    from .project_generator import ProjectGenerator
    from .solution_manager import SolutionManager
except ImportError:
    from excel_validator import ExcelValidator
    from project_generator import ProjectGenerator
    from solution_manager import SolutionManager


class WorkerSignals(QObject):
    """
    Signals for worker threads to communicate with the main UI thread.
    """
    progress = Signal(str)  # Progress message
    finished = Signal(bool, str)  # Success status and message
    error = Signal(str)  # Error message


class BaseWorker(QRunnable):
    """
    Base worker class for background tasks.
    """

    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    def run(self):
        """Override this method in subclasses."""
        pass


class ExcelProcessingWorker(BaseWorker):
    """
    Worker for processing Excel files in background.
    """

    def __init__(self, file_path: str, excel_validator):
        super().__init__()
        self.file_path = file_path
        self.excel_validator = excel_validator

    def run(self):
        """Process Excel file validation."""
        try:
            self.signals.progress.emit(f"Processing Excel file: {self.file_path}")

            # Validate Excel structure and data
            validation_result = self.excel_validator.validate_excel_file(self.file_path)

            if validation_result["valid"]:
                self.signals.finished.emit(True, str(validation_result))
            else:
                self.signals.finished.emit(False, validation_result.get("error", "Unknown validation error"))

        except Exception as e:
            self.signals.error.emit(f"Error processing Excel file: {e}")


class SolutionProcessingWorker(BaseWorker):
    """
    Worker for processing solution files in background.
    """

    def __init__(self, file_path: str, solution_manager):
        super().__init__()
        self.file_path = file_path
        self.solution_manager = solution_manager

    def run(self):
        """Process solution file setup."""
        try:
            self.signals.progress.emit(f"Processing solution file: {self.file_path}")

            # Validate and setup solution
            setup_result = self.solution_manager.setup_solution(self.file_path)

            if setup_result["success"]:
                self.signals.finished.emit(True, str(setup_result))
            else:
                self.signals.finished.emit(False, setup_result.get("error", "Unknown setup error"))

        except Exception as e:
            self.signals.error.emit(f"Error processing solution file: {e}")


class GenerationWorker(BaseWorker):
    """
    Worker for file generation in background.
    """

    def __init__(self, project_generator, excel_data, module_name, feature_name, solution_path):
        super().__init__()
        self.project_generator = project_generator
        self.excel_data = excel_data
        self.module_name = module_name
        self.feature_name = feature_name
        self.solution_path = solution_path

    def run(self):
        """Process file generation."""
        try:
            self.signals.progress.emit("Starting file generation...")

            # Generate files using the project generator
            generation_result = self.project_generator.generate_all_files(
                excel_data=self.excel_data,
                module_name=self.module_name,
                feature_name=self.feature_name,
                solution_path=self.solution_path,
            )

            if generation_result["success"]:
                self.signals.finished.emit(True, str(generation_result))
            else:
                self.signals.finished.emit(False, generation_result.get("error", "Unknown generation error"))

        except Exception as e:
            self.signals.error.emit(f"Error during file generation: {e}")


class GUIManager(QMainWindow):
    """
    Main GUI manager for CSS Dev Automator.
    Provides interface for:
    1. Download Excel template
    2. Browse and validate Excel files
    3. Browse .NET solution files
    4. Generate files and prompts
    """

    def __init__(self):
        """Initialize the GUI manager."""
        super().__init__()

        # Initialize components
        self.excel_validator = ExcelValidator()
        self.solution_manager = SolutionManager()
        self.project_generator = ProjectGenerator()

        # Thread pool for background tasks
        self.thread_pool = QThreadPool()

        # State variables
        self.excel_file_path = None
        self.solution_file_path = None
        self.excel_data = None
        self.module_name = None
        self.feature_name = None
        self.database_connection_string = None

        # Operation flags to prevent double-clicks
        self.excel_processing = False
        self.solution_processing = False
        self.generation_processing = False

        # Setup UI
        self.setWindowTitle("CSS Dev Automator")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)

        self._setup_gui()
        self._log_status("CSS Dev Automator initialized successfully.")

    def _setup_gui(self):
        """Setup the main GUI interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Title
        title_label = QLabel("CSS Dev Automator")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Arial", 16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)

        # Features section
        features_layout = QVBoxLayout()
        features_layout.setSpacing(20)

        # Feature 1: Download Excel Template
        feature1_group = QGroupBox("1. Download Excel Template")
        feature1_layout = QHBoxLayout(feature1_group)

        self.download_btn = QPushButton("Download Excel Template")
        self.download_btn.setMinimumHeight(40)
        self.download_btn.clicked.connect(self._download_excel_template)
        feature1_layout.addWidget(self.download_btn)

        features_layout.addWidget(feature1_group)

        # Feature 2: Browse Excel File
        feature2_group = QGroupBox("2. Browse Excel File")
        feature2_layout = QVBoxLayout(feature2_group)

        self.browse_excel_btn = QPushButton("Browse Excel File")
        self.browse_excel_btn.setMinimumHeight(40)
        self.browse_excel_btn.clicked.connect(self._browse_excel_file)
        feature2_layout.addWidget(self.browse_excel_btn)

        self.excel_status_label = QLabel("No file selected")
        self.excel_status_label.setStyleSheet("color: gray;")
        feature2_layout.addWidget(self.excel_status_label)

        features_layout.addWidget(feature2_group)

        # Feature 3: Browse Solution File
        feature3_group = QGroupBox("3. Browse Solution File")
        feature3_layout = QVBoxLayout(feature3_group)

        self.browse_solution_btn = QPushButton("Browse Solution File")
        self.browse_solution_btn.setMinimumHeight(40)
        self.browse_solution_btn.clicked.connect(self._browse_solution_file)
        feature3_layout.addWidget(self.browse_solution_btn)

        self.solution_status_label = QLabel("No file selected")
        self.solution_status_label.setStyleSheet("color: gray;")
        feature3_layout.addWidget(self.solution_status_label)

        features_layout.addWidget(feature3_group)

        # Feature 4: Generate
        feature4_group = QGroupBox("4. Generate Files")
        feature4_layout = QVBoxLayout(feature4_group)

        self.generate_btn = QPushButton("Generate")
        self.generate_btn.setMinimumHeight(50)
        self.generate_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        self.generate_btn.clicked.connect(self._generate_files)
        feature4_layout.addWidget(self.generate_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        feature4_layout.addWidget(self.progress_bar)

        features_layout.addWidget(feature4_group)

        main_layout.addLayout(features_layout)

        # Status/Log area
        status_group = QGroupBox("Status & Logs")
        status_layout = QVBoxLayout(status_group)

        self.status_text = QTextEdit()
        self.status_text.setMinimumHeight(200)
        self.status_text.setReadOnly(True)
        status_layout.addWidget(self.status_text)

        main_layout.addWidget(status_group)

    def _log_status(self, message: str):
        """Log a status message to the status area."""
        self.status_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.status_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _download_excel_template(self):
        """Download Excel template to Downloads folder."""
        try:
            # Source template path
            template_path = Path("Templates/Excel/DataTemplate.xlsx")

            if not template_path.exists():
                QMessageBox.critical(
                    self, "Error", "Excel template not found in Templates/Excel/DataTemplate.xlsx"
                )
                return

            # Destination path (Downloads folder)
            downloads_path = Path.home() / "Downloads"
            destination_path = downloads_path / "DataTemplate.xlsx"

            # Copy file
            shutil.copy2(template_path, destination_path)

            self._log_status(f"Excel template downloaded to: {destination_path}")
            QMessageBox.information(self, "Success", f"Excel template downloaded to:\n{destination_path}")

        except Exception as e:
            error_msg = f"Failed to download Excel template: {e}"
            self._log_status(error_msg)
            QMessageBox.critical(self, "Error", error_msg)

    def _browse_excel_file(self):
        """Browse and validate Excel file."""
        try:
            # Prevent double-clicks
            if self.excel_processing:
                return

            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Excel File",
                "",
                "Excel files (*.xlsx *.xls);;All files (*.*)"
            )

            if not file_path:
                return

            self._log_status(f"Selected Excel file: {file_path}")

            # Set processing flag and disable button
            self.excel_processing = True
            self.browse_excel_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress

            # Create and start worker
            worker = ExcelProcessingWorker(file_path, self.excel_validator)
            worker.signals.progress.connect(self._log_status)
            worker.signals.finished.connect(self._on_excel_processing_finished)
            worker.signals.error.connect(self._on_excel_processing_error)

            self.thread_pool.start(worker)

        except Exception as e:
            error_msg = f"Error browsing Excel file: {e}"
            self._log_status(error_msg)
            QMessageBox.critical(self, "Error", error_msg)

    @Slot(bool, str)
    def _on_excel_processing_finished(self, success: bool, result_str: str):
        """Handle Excel processing completion."""
        try:
            # Reset processing flag and re-enable button
            self.excel_processing = False
            self.browse_excel_btn.setEnabled(True)
            self.progress_bar.setVisible(False)

            if success:
                # Parse result string back to dict (this is a simplified approach)
                import ast
                validation_result = ast.literal_eval(result_str)

                self.excel_file_path = validation_result.get("file_path")
                self.excel_data = validation_result["data"]
                self.module_name = validation_result["module_name"]
                self.feature_name = validation_result["feature_name"]

                self.excel_status_label.setText("✓ Valid Excel file loaded")
                self.excel_status_label.setStyleSheet("color: green;")
                self._log_status("Excel file validated successfully.")
                self._log_status(f"Module Name: {self.module_name}")
                self._log_status(f"Feature Name: {self.feature_name}")
                self._log_status(f"Found {len(self.excel_data)} stored procedures.")
            else:
                self.excel_status_label.setText("✗ Invalid Excel file")
                self.excel_status_label.setStyleSheet("color: red;")
                error_msg = f"Excel validation failed: {result_str}"
                self._log_status(error_msg)
                QMessageBox.critical(self, "Validation Error", error_msg)

        except Exception as e:
            self._log_status(f"Error processing Excel result: {e}")

    @Slot(str)
    def _on_excel_processing_error(self, error_msg: str):
        """Handle Excel processing error."""
        self.excel_processing = False
        self.browse_excel_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.excel_status_label.setText("✗ Error processing file")
        self.excel_status_label.setStyleSheet("color: red;")
        self._log_status(error_msg)
        QMessageBox.critical(self, "Processing Error", error_msg)

    def _browse_solution_file(self):
        """Browse .NET solution file."""
        try:
            # Prevent double-clicks
            if self.solution_processing:
                return

            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select .NET Solution File",
                "",
                "Solution files (*.sln);;All files (*.*)"
            )

            if not file_path:
                return

            self._log_status(f"Selected solution file: {file_path}")

            # Set processing flag and disable button
            self.solution_processing = True
            self.browse_solution_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress

            # Create and start worker
            worker = SolutionProcessingWorker(file_path, self.solution_manager)
            worker.signals.progress.connect(self._log_status)
            worker.signals.finished.connect(self._on_solution_processing_finished)
            worker.signals.error.connect(self._on_solution_processing_error)

            self.thread_pool.start(worker)

        except Exception as e:
            error_msg = f"Error browsing solution file: {e}"
            self._log_status(error_msg)
            QMessageBox.critical(self, "Error", error_msg)

    @Slot(bool, str)
    def _on_solution_processing_finished(self, success: bool, result_str: str):
        """Handle solution processing completion."""
        try:
            # Reset processing flag and re-enable button
            self.solution_processing = False
            self.browse_solution_btn.setEnabled(True)
            self.progress_bar.setVisible(False)

            if success:
                # Parse result string back to dict
                import ast
                setup_result = ast.literal_eval(result_str)

                self.solution_file_path = setup_result.get("file_path")
                self.database_connection_string = setup_result.get("connection_string")

                self.solution_status_label.setText("✓ Solution setup complete")
                self.solution_status_label.setStyleSheet("color: green;")
                self._log_status("Solution setup completed successfully.")

                for message in setup_result.get("messages", []):
                    self._log_status(f"  - {message}")

                # Log connection string status
                if self.database_connection_string:
                    self._log_status("✓ Database connection string extracted successfully")
                    # Show partial connection string for verification (hide sensitive parts)
                    masked_conn = self._mask_connection_string(self.database_connection_string)
                    self._log_status(f"  Connection: {masked_conn}")
                    # Update configuration with the extracted connection string
                    self._update_database_configuration(self.database_connection_string)
                else:
                    self._log_status("⚠ Warning: No database connection string found")
                    self._log_status("  SP generation will use existing config.json connection")

                # Log connection extraction messages
                for conn_msg in setup_result.get("connection_messages", []):
                    self._log_status(f"  - {conn_msg}")
            else:
                self.solution_status_label.setText("✗ Solution setup failed")
                self.solution_status_label.setStyleSheet("color: red;")
                error_msg = f"Solution setup failed: {result_str}"
                self._log_status(error_msg)
                QMessageBox.critical(self, "Setup Error", error_msg)

        except Exception as e:
            self._log_status(f"Error processing solution result: {e}")

    @Slot(str)
    def _on_solution_processing_error(self, error_msg: str):
        """Handle solution processing error."""
        self.solution_processing = False
        self.browse_solution_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.solution_status_label.setText("✗ Error processing file")
        self.solution_status_label.setStyleSheet("color: red;")
        self._log_status(error_msg)
        QMessageBox.critical(self, "Processing Error", error_msg)

    def _generate_files(self):
        """Generate all files and prompts."""
        try:
            # Prevent double-clicks
            if self.generation_processing:
                return

            # Check prerequisites
            if not self._check_prerequisites():
                return

            self._log_status("Starting file generation...")

            # Set processing flag and disable button
            self.generation_processing = True
            self.generate_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress

            # Create and start worker
            worker = GenerationWorker(
                self.project_generator,
                self.excel_data,
                self.module_name,
                self.feature_name,
                self.solution_file_path
            )
            worker.signals.progress.connect(self._log_status)
            worker.signals.finished.connect(self._on_generation_finished)
            worker.signals.error.connect(self._on_generation_error)

            self.thread_pool.start(worker)

        except Exception as e:
            error_msg = f"Error during file generation: {e}"
            self._log_status(error_msg)
            QMessageBox.critical(self, "Error", error_msg)

    @Slot(bool, str)
    def _on_generation_finished(self, success: bool, result_str: str):
        """Handle generation completion."""
        try:
            # Reset processing flag and re-enable button
            self.generation_processing = False
            self.generate_btn.setEnabled(True)
            self.progress_bar.setVisible(False)

            if success:
                # Parse result string back to dict
                import ast
                generation_result = ast.literal_eval(result_str)

                self._log_status("File generation completed successfully!")

                # Show summary
                summary = generation_result.get("summary", {})
                self._log_status("\nGeneration Summary:")
                self._log_status(f"  - Completed tasks: {len(summary.get('completed', []))}")
                self._log_status(f"  - Failed tasks: {len(summary.get('failed', []))}")
                self._log_status(f"  - Errors: {len(summary.get('errors', []))}")

                for task in summary.get("completed", []):
                    self._log_status(f"    ✓ {task}")

                for task in summary.get("failed", []):
                    self._log_status(f"    ✗ {task}")

                for error in summary.get("errors", []):
                    self._log_status(f"    ! {error}")

                QMessageBox.information(
                    self, "Success", "File generation completed! Check the status area for details."
                )
            else:
                error_msg = f"File generation failed: {result_str}"
                self._log_status(error_msg)
                QMessageBox.critical(self, "Generation Error", error_msg)

        except Exception as e:
            self._log_status(f"Error processing generation result: {e}")

    @Slot(str)
    def _on_generation_error(self, error_msg: str):
        """Handle generation error."""
        self.generation_processing = False
        self.generate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self._log_status(error_msg)
        QMessageBox.critical(self, "Generation Error", error_msg)

    def _check_prerequisites(self) -> bool:
        """Check if all prerequisites are met for generation."""
        missing = []
        warnings = []

        if not self.excel_file_path or not self.excel_data:
            missing.append("Valid Excel file")

        if not self.solution_file_path:
            missing.append("Solution file")

        if not self.module_name or not self.feature_name:
            missing.append("Module and Feature names from Excel")

        # Check for database connection
        if not self.database_connection_string:
            warnings.append("No database connection string extracted from solution")

        # Check if config.json exists
        config_path = Path("config.json")
        if not config_path.exists():
            warnings.append("config.json file not found")

        if missing:
            error_msg = f"Missing prerequisites: {', '.join(missing)}"
            self._log_status(error_msg)
            QMessageBox.critical(self, "Prerequisites Missing", error_msg)
            return False

        if warnings:
            warning_msg = f"Warnings: {', '.join(warnings)}"
            self._log_status(f"⚠ {warning_msg}")

            # Ask user if they want to continue despite warnings
            result = QMessageBox.question(
                self, "Prerequisites Warning", f"{warning_msg}\n\nDo you want to continue anyway?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if result != QMessageBox.Yes:
                return False

        return True

    def _update_database_configuration(self, connection_string: str):
        """
        Update the application's database configuration with the extracted connection string.

        Args:
            connection_string: Database connection string from GTI.API
        """
        try:
            import json

            config_path = Path("config.json")

            if config_path.exists():
                # Read current configuration
                with open(config_path, encoding="utf-8") as f:
                    config = json.load(f)

                # Update database connection string
                if "database" not in config:
                    config["database"] = {}

                config["database"]["connection_string"] = connection_string

                # Write updated configuration
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=4)

                self._log_status("✓ Database configuration updated successfully")

            else:
                self._log_status(
                    "⚠ Warning: config.json not found, database configuration not updated"
                )

        except Exception as e:
            error_msg = f"Error updating database configuration: {e}"
            self._log_status(error_msg)

    def _mask_connection_string(self, connection_string: str) -> str:
        """
        Mask sensitive information in connection string for display.

        Args:
            connection_string: Original connection string

        Returns:
            Masked connection string safe for display
        """
        try:
            import re

            # Mask password/pwd values
            masked = re.sub(
                r"(pwd|password)\s*=\s*[^;]+", r"\1=***", connection_string, flags=re.IGNORECASE
            )

            # Mask user ID if it looks sensitive
            masked = re.sub(
                r"(user\s*id)\s*=\s*([^;]+)",
                lambda m: f"{m.group(1)}={m.group(2) if len(m.group(2)) <= 3 else m.group(2)[:3] + '***'}",
                masked,
                flags=re.IGNORECASE,
            )

            # Truncate if too long
            if len(masked) > 100:
                masked = masked[:97] + "..."

            return masked

        except Exception:
            return "Connection string (masked for security)"

    def run(self):
        """Run the GUI application."""
        # Just show the window - QApplication should already exist
        self.show()
