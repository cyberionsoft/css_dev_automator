"""
CSS Dev Automator Package
A comprehensive solution for processing stored procedures with improved architecture
"""

__version__ = "2.0.0"
__author__ = "CSS Development Team"

# Import main components
from .excel_manager import ExcelManager, StoredProcedureInfo
from .gui_manager import GUIManager
from .main_processor import MainProcessor

__all__ = ["ExcelManager", "StoredProcedureInfo", "GUIManager", "MainProcessor"]
