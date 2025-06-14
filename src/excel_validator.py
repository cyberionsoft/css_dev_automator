"""
Excel Validator for CSS Dev Automator
Validates Excel files with the new format including Module Name and Feature Name columns
"""

import re
from typing import Any

import polars as pl


class ExcelValidator:
    """
    Validates Excel files for CSS Dev Automator.
    Expected format:
    - SP Name: Stored procedure names (multiple rows)
    - Type: Procedure types (multiple rows)
    - Module Name: C# class name (single row)
    - Feature Name: C# class name (single row)
    """

    def __init__(self):
        """Initialize the Excel validator."""
        self.required_columns = ["SP Name", "Type", "Module Name", "Entity Name"]
        self.valid_types = ["Get", "List", "Save", "Delete", "Update", "Create"]

    def validate_excel_file(self, file_path: str) -> dict[str, Any]:
        """
        Validate Excel file structure and data.

        Args:
            file_path: Path to Excel file

        Returns:
            Dictionary with validation results
        """
        try:
            # Read Excel file
            df = pl.read_excel(file_path)

            # Validate structure
            structure_result = self._validate_structure(df)
            if not structure_result["valid"]:
                return structure_result

            # Validate data
            data_result = self._validate_data(df)
            if not data_result["valid"]:
                return data_result

            # Extract and clean data
            cleaned_data = self._extract_and_clean_data(df)

            return {
                "valid": True,
                "file_path": file_path,
                "data": cleaned_data["sp_data"],
                "module_name": cleaned_data["module_name"],
                "feature_name": cleaned_data["feature_name"],
            }

        except Exception as e:
            return {"valid": False, "error": f"Failed to read Excel file: {e}"}

    def _validate_structure(self, df: pl.DataFrame) -> dict[str, Any]:
        """
        Validate Excel file structure.

        Args:
            df: Polars DataFrame

        Returns:
            Validation result
        """
        # Check if required columns exist
        missing_columns = []
        for col in self.required_columns:
            if col not in df.columns:
                missing_columns.append(col)

        if missing_columns:
            return {
                "valid": False,
                "error": f"Missing required columns: {', '.join(missing_columns)}",
            }

        # Check if DataFrame has data
        if df.height == 0:
            return {"valid": False, "error": "Excel file is empty"}

        return {"valid": True}

    def _validate_data(self, df: pl.DataFrame) -> dict[str, Any]:
        """
        Validate Excel file data.

        Args:
            df: Polars DataFrame

        Returns:
            Validation result
        """
        # Validate SP Names
        sp_names = df["SP Name"].drop_nulls()
        if sp_names.len() == 0:
            return {"valid": False, "error": "No valid SP Names found"}

        # Validate Types
        types = df["Type"].drop_nulls()
        if types.len() == 0:
            return {"valid": False, "error": "No valid Types found"}

        # Check if SP Names and Types have same count
        if sp_names.len() != types.len():
            return {
                "valid": False,
                "error": "SP Name and Type columns must have the same number of entries",
            }

        # Validate Type values
        invalid_types = []
        for type_val in types:
            if type_val not in self.valid_types:
                invalid_types.append(type_val)

        if invalid_types:
            return {
                "valid": False,
                "error": f"Invalid types found: {', '.join(set(invalid_types))}. Valid types: {', '.join(self.valid_types)}",
            }

        # Validate Module Name (should have exactly one non-null value)
        module_names = df["Module Name"].drop_nulls()
        if module_names.len() == 0:
            return {"valid": False, "error": "Module Name is required"}
        elif module_names.len() > 1:
            unique_modules = module_names.unique()
            if unique_modules.len() > 1:
                return {
                    "valid": False,
                    "error": f"Multiple different Module Names found: {', '.join(unique_modules.to_list())}. Only one Module Name is allowed.",
                }

        # Validate Feature Name (should have exactly one non-null value)
        feature_names = df["Entity Name"].drop_nulls()  # Note: "Entity Name" is the correct column name
        if feature_names.len() == 0:
            return {"valid": False, "error": "Entity Name is required"}
        elif feature_names.len() > 1:
            unique_features = feature_names.unique()
            if unique_features.len() > 1:
                return {
                    "valid": False,
                    "error": f"Multiple different Entity Names found: {', '.join(unique_features.to_list())}. Only one Entity Name is allowed.",
                }

        return {"valid": True}

    def _extract_and_clean_data(self, df: pl.DataFrame) -> dict[str, Any]:
        """
        Extract and clean data from validated DataFrame.

        Args:
            df: Polars DataFrame

        Returns:
            Cleaned data
        """
        # Extract SP data (only non-null rows)
        sp_data = []

        # Get non-null SP names and types
        for i in range(df.height):
            sp_name = df["SP Name"][i]
            sp_type = df["Type"][i]

            # Check for both None and empty string
            if (
                sp_name is not None
                and sp_type is not None
                and str(sp_name).strip()
                and str(sp_type).strip()
            ):
                sp_data.append({"name": str(sp_name).strip(), "type": str(sp_type).strip()})

        # Extract Module Name and Entity Name (get first non-null value)
        module_name = df["Module Name"].drop_nulls()[0]
        feature_name = df["Entity Name"].drop_nulls()[0]  # Note: "Entity Name" is the correct column name

        # Clean and convert to PascalCase
        cleaned_module_name = self._to_pascal_case(str(module_name))
        cleaned_feature_name = self._to_pascal_case(str(feature_name))

        return {
            "sp_data": sp_data,
            "module_name": cleaned_module_name,
            "feature_name": cleaned_feature_name,
        }

    def _to_pascal_case(self, text: str) -> str:
        """
        Convert text to PascalCase (C# class name format).
        Removes spaces and special characters, capitalizes first letter of each word.

        Args:
            text: Input text

        Returns:
            PascalCase string
        """
        # Remove special characters and split by spaces/underscores/hyphens
        words = re.findall(r"[a-zA-Z0-9]+", text)

        # Capitalize first letter of each word
        pascal_case = "".join(word.capitalize() for word in words)

        # Ensure it starts with a letter (C# class name requirement)
        if pascal_case and not pascal_case[0].isalpha():
            pascal_case = "Class" + pascal_case

        return pascal_case if pascal_case else "DefaultClass"

    def validate_template_structure(self, template_path: str) -> bool:
        """
        Validate that the template Excel file has the correct structure.

        Args:
            template_path: Path to template Excel file

        Returns:
            True if template is valid, False otherwise
        """
        try:
            df = pl.read_excel(template_path)

            # Check if all required columns exist
            for col in self.required_columns:
                if col not in df.columns:
                    return False

            return True

        except Exception:
            return False
