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
