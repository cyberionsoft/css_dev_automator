"""
Excel Manager for CSS Dev Automator
Handles reading and processing Excel files containing stored procedure information
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

import polars as pl


@dataclass
class StoredProcedureInfo:
    """Information about a stored procedure from Excel"""
    name: str
    type: str
    row_number: int = 0


class ExcelManager:
    """Manages Excel file operations for stored procedure data"""

    def __init__(self, excel_file_path: str):
        """
        Initialize Excel manager with file path.
        
        Args:
            excel_file_path: Path to Excel file
        """
        self.excel_file_path = Path(excel_file_path)
        self.required_columns = ["SP Name", "Type"]

    def read_stored_procedures(self) -> List[StoredProcedureInfo]:
        """
        Read stored procedures from Excel file.
        
        Returns:
            List of StoredProcedureInfo objects
            
        Raises:
            FileNotFoundError: If Excel file doesn't exist
            ValueError: If required columns are missing
        """
        if not self.excel_file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {self.excel_file_path}")

        try:
            # Read Excel file using Polars
            df = pl.read_excel(self.excel_file_path)
            
            # Validate required columns
            self._validate_columns(df)
            
            # Convert to StoredProcedureInfo objects
            sp_list = []
            for i, row in enumerate(df.iter_rows(named=True), 1):
                sp_name = str(row.get("SP Name", "")).strip()
                sp_type = str(row.get("Type", "")).strip()
                
                # Skip empty rows
                if not sp_name or not sp_type:
                    continue
                    
                sp_info = StoredProcedureInfo(
                    name=sp_name,
                    type=sp_type,
                    row_number=i
                )
                sp_list.append(sp_info)
            
            if not sp_list:
                raise ValueError("No valid stored procedure data found in Excel file")
                
            return sp_list
            
        except Exception as e:
            raise ValueError(f"Error reading Excel file: {e}")

    def _validate_columns(self, df: pl.DataFrame):
        """
        Validate that required columns exist in the DataFrame.
        
        Args:
            df: Polars DataFrame
            
        Raises:
            ValueError: If required columns are missing
        """
        missing_columns = []
        for col in self.required_columns:
            if col not in df.columns:
                missing_columns.append(col)
        
        if missing_columns:
            raise ValueError(
                f"Missing required columns: {missing_columns}. "
                f"Available columns: {list(df.columns)}"
            )

    def validate_excel_file(self) -> tuple[bool, str]:
        """
        Validate Excel file format and content.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not self.excel_file_path.exists():
                return False, f"Excel file not found: {self.excel_file_path}"
            
            # Try to read the file
            df = pl.read_excel(self.excel_file_path)
            
            # Check for required columns
            missing_columns = []
            for col in self.required_columns:
                if col not in df.columns:
                    missing_columns.append(col)
            
            if missing_columns:
                return False, f"Missing required columns: {missing_columns}"
            
            # Check if there's any data
            if df.height == 0:
                return False, "Excel file is empty"
            
            # Check for valid data rows
            valid_rows = 0
            for row in df.iter_rows(named=True):
                sp_name = str(row.get("SP Name", "")).strip()
                sp_type = str(row.get("Type", "")).strip()
                
                if sp_name and sp_type:
                    valid_rows += 1
            
            if valid_rows == 0:
                return False, "No valid stored procedure data found"
            
            return True, f"Valid Excel file with {valid_rows} stored procedures"
            
        except Exception as e:
            return False, f"Error validating Excel file: {e}"

    def get_summary(self) -> dict:
        """
        Get summary information about the Excel file.
        
        Returns:
            Dictionary with summary information
        """
        try:
            sp_list = self.read_stored_procedures()
            
            # Count by type
            type_counts = {}
            for sp in sp_list:
                type_counts[sp.type] = type_counts.get(sp.type, 0) + 1
            
            return {
                "total_procedures": len(sp_list),
                "type_breakdown": type_counts,
                "file_path": str(self.excel_file_path),
                "valid": True
            }
            
        except Exception as e:
            return {
                "total_procedures": 0,
                "type_breakdown": {},
                "file_path": str(self.excel_file_path),
                "valid": False,
                "error": str(e)
            }

    @staticmethod
    def validate_excel_file_static(file_path: str) -> bool:
        """
        Static method to validate Excel file format and content.

        Args:
            file_path: Path to Excel file

        Returns:
            True if valid, False otherwise
        """
        try:
            excel_manager = ExcelManager(file_path)
            is_valid, _ = excel_manager.validate_excel_file()
            return is_valid
        except Exception:
            return False

    @staticmethod
    def extract_sp_data(file_path: str) -> dict:
        """
        Static method to extract stored procedure data from Excel file.

        Args:
            file_path: Path to Excel file

        Returns:
            Dictionary with success status and data
        """
        try:
            excel_manager = ExcelManager(file_path)
            sp_list = excel_manager.read_stored_procedures()

            # Convert to dictionary format expected by GUI
            data = []
            module_name = ""
            entity_name = ""

            # Read the Excel file to get module and entity names
            df = pl.read_excel(Path(file_path))

            # Extract module and entity names from first data row
            if df.height > 0:
                first_row = df.row(0, named=True)
                module_name = str(first_row.get("Module Name", "")).strip()
                entity_name = str(first_row.get("Entity Name", "")).strip()

                # Clean and convert to PascalCase
                module_name = ExcelManager._to_pascal_case(module_name)
                entity_name = ExcelManager._to_pascal_case(entity_name)

            # Convert SP list to dictionary format
            for sp in sp_list:
                data.append({
                    "name": sp.name,
                    "type": sp.type,
                    "row_number": sp.row_number
                })

            return {
                "success": True,
                "data": data,
                "module_name": module_name,
                "entity_name": entity_name,
                "total_count": len(data)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "module_name": "",
                "entity_name": "",
                "total_count": 0
            }

    @staticmethod
    def _to_pascal_case(text: str) -> str:
        """
        Convert text to PascalCase.

        Args:
            text: Input text

        Returns:
            PascalCase formatted text
        """
        if not text:
            return ""

        # Remove leading/trailing whitespace and split by spaces
        words = text.strip().split()

        # Capitalize first letter of each word and join
        pascal_case = "".join(word.capitalize() for word in words if word)

        return pascal_case
