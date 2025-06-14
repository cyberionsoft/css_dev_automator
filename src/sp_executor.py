"""
Stored Procedure Executor
Handles execution of stored procedures with dynamic parameter detection
"""

import json
import re
import time
from typing import Any

import pyodbc

from .database_manager import DatabaseManager


class SPExecutionError(Exception):
    """Base class for SP execution errors"""

    pass


class SPTimeoutError(SPExecutionError):
    """Raised when SP execution times out"""

    pass


class SPPermissionError(SPExecutionError):
    """Raised when SP execution fails due to permissions"""

    pass


class SPSyntaxError(SPExecutionError):
    """Raised when SP has syntax errors"""

    pass


class SPConnectionError(SPExecutionError):
    """Raised when database connection fails during SP execution"""

    pass


class StoredProcedureExecutor:
    """Executes stored procedures with dynamic parameter detection"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def execute_stored_procedure(
        self, sp_name: str, input_json: str, sp_definition: str
    ) -> str | None:
        """Execute stored procedure with retry mechanism and better error handling"""
        if not input_json:
            print(f"No input JSON provided for {sp_name}, using empty JSON")
            input_json = "{}"

        # Retry configuration
        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                # Analyze SP signature to determine execution strategy
                sp_signature = self._analyze_sp_signature(sp_definition)

                # Execute using the appropriate strategy
                if sp_signature["has_output_params"]:
                    return self._execute_with_output_params(sp_name, input_json, sp_signature)
                else:
                    return self._execute_simple(sp_name, input_json)

            except (SPConnectionError, SPTimeoutError) as e:
                # Retryable errors
                if attempt < max_retries - 1:
                    print(f"Retryable error for {sp_name} (attempt {attempt + 1}): {e}")
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    print(f"Failed to execute SP {sp_name} after {max_retries} attempts: {e}")
                    return self._create_error_response(
                        f"Execution failed after retries: {e}", "RETRYABLE_ERROR"
                    )

            except (SPPermissionError, SPSyntaxError) as e:
                # Non-retryable errors
                print(f"Non-retryable error for {sp_name}: {e}")
                return self._create_error_response(str(e), "PERMANENT_ERROR")

            except Exception as e:
                # Unknown errors - categorize and handle
                error_category = self._categorize_error(e)
                if error_category in ["TIMEOUT", "CONNECTION"] and attempt < max_retries - 1:
                    print(
                        f"Retrying {sp_name} due to {error_category} (attempt {attempt + 1}): {e}"
                    )
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    print(f"Failed to execute SP {sp_name}: {e}")
                    return self._create_error_response(str(e), error_category)

        return self._create_error_response("Maximum retries exceeded", "MAX_RETRIES_EXCEEDED")

    def _analyze_sp_signature(self, sp_definition: str) -> dict[str, Any]:
        """Analyze stored procedure signature to understand parameters with better type detection"""
        signature = {
            "has_output_params": False,
            "output_params": [],
            "input_params": [],
            "has_return_value": False,
        }

        if not sp_definition:
            return signature

        # Enhanced parameter pattern to capture more type information
        param_pattern = r"@(\w+)\s+((?:\w+(?:\s*\([^)]+\))?(?:\s+(?:IDENTITY|NOT\s+NULL|NULL))*)+)\s*(?:=\s*([^,\n]+?))?\s*(?:,|\s+|$|OUTPUT)"
        matches = re.finditer(param_pattern, sp_definition, re.IGNORECASE | re.MULTILINE)

        for match in matches:
            param_name = match.group(1)
            param_type_full = match.group(2).strip()
            default_value = match.group(3)

            # Check if OUTPUT appears after this parameter
            match_end = match.end()
            next_part = sp_definition[match_end : match_end + 20]
            is_output = "OUTPUT" in next_part.upper()

            # Parse the full type information
            type_info = self._parse_parameter_type(param_type_full)

            param_info = {
                "name": param_name,
                "type": type_info["base_type"],
                "full_type": param_type_full,
                "size": type_info.get("size"),
                "precision": type_info.get("precision"),
                "scale": type_info.get("scale"),
                "nullable": type_info.get("nullable", True),
                "default": default_value,
                "is_output": is_output,
            }

            if is_output:
                signature["has_output_params"] = True
                signature["output_params"].append(param_info)
            else:
                signature["input_params"].append(param_info)

        # Check for return value pattern
        if re.search(r"EXEC\s+@\w+\s*=", sp_definition, re.IGNORECASE):
            signature["has_return_value"] = True

        return signature

    def _parse_parameter_type(self, type_string: str) -> dict[str, Any]:
        """Parse SQL parameter type string to extract detailed type information"""
        type_info = {
            "base_type": "NVARCHAR",
            "size": None,
            "precision": None,
            "scale": None,
            "nullable": True,
        }

        type_upper = type_string.upper()

        # Extract base type
        base_type_match = re.match(r"(\w+)", type_upper)
        if base_type_match:
            type_info["base_type"] = base_type_match.group(1)

        # Extract size/precision information
        size_match = re.search(r"\(([^)]+)\)", type_upper)
        if size_match:
            size_part = size_match.group(1)
            if "," in size_part:
                # Precision and scale (e.g., DECIMAL(18,2))
                parts = size_part.split(",")
                type_info["precision"] = int(parts[0].strip())
                type_info["scale"] = int(parts[1].strip())
            else:
                # Just size (e.g., VARCHAR(50))
                if size_part.upper() == "MAX":
                    type_info["size"] = "MAX"
                else:
                    try:
                        type_info["size"] = int(size_part)
                    except ValueError:
                        type_info["size"] = size_part

        # Check nullability
        if "NOT NULL" in type_upper:
            type_info["nullable"] = False

        return type_info

    def _execute_with_output_params(
        self, sp_name: str, input_json: str, signature: dict[str, Any]
    ) -> str:
        """Execute SP with output parameters"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Build dynamic SQL based on actual parameters
                output_declarations = []
                output_selects = []

                for param in signature["output_params"]:
                    param_name = param["name"]
                    param_type = self._normalize_sql_type(param)

                    output_declarations.append(f"DECLARE @{param_name} {param_type};")
                    output_selects.append(f"@{param_name} as {param_name}")

                # Build the execution SQL
                output_params_clause = ""
                if signature["output_params"]:
                    output_params_clause = ", " + ", ".join(
                        f"@{p['name']} OUTPUT" for p in signature["output_params"]
                    )

                sql_parts = [
                    "DECLARE @Json NVARCHAR(MAX) = ?;",
                    *output_declarations,
                    f"EXEC {sp_name} @Json{output_params_clause};",
                    f"SELECT {', '.join(output_selects)};"
                    if output_selects
                    else "SELECT 'No output parameters' as Message;",
                ]

                sql = "\n".join(sql_parts)

                # Debug: f"Executing SP with output params: {sp_name}"
                cursor.execute(sql, input_json)

                # Process all result sets
                all_results = self._process_all_result_sets(cursor)

                # Get output parameters (should be the last result set)
                output_params = None
                if all_results:
                    last_result = all_results[-1]
                    if "ResultSet_" in last_result:
                        output_data = last_result[list(last_result.keys())[0]]
                        if output_data:
                            output_params = output_data[0]  # First row contains output params

                return self._create_success_response(
                    all_results[:-1] if len(all_results) > 1 else [], output_params
                )

        except pyodbc.Error as e:
            print(f"Database error executing {sp_name}: {e}")
            return self._create_error_response(f"Database error: {e}")
        except Exception as e:
            print(f"Unexpected error executing {sp_name}: {e}")
            return self._create_error_response(f"Execution error: {e}")

    def _execute_simple(self, sp_name: str, input_json: str) -> str:
        """Execute SP without output parameters"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                sql = f"EXEC {sp_name} ?"

                # Debug: f"Executing simple SP: {sp_name}"
                cursor.execute(sql, input_json)

                # Process all result sets
                all_results = self._process_all_result_sets(cursor)

                return self._create_success_response(all_results, None)

        except pyodbc.Error as e:
            print(f"Database error executing {sp_name}: {e}")
            return self._create_error_response(f"Database error: {e}")
        except Exception as e:
            print(f"Unexpected error executing {sp_name}: {e}")
            return self._create_error_response(f"Execution error: {e}")

    def _process_all_result_sets(self, cursor) -> list[dict[str, Any]]:
        """Process all result sets from cursor"""
        all_results = []
        result_set_count = 0

        while True:
            try:
                if cursor.description:  # Check if there are columns
                    rows = cursor.fetchall()
                    columns = [column[0] for column in cursor.description]

                    results = []
                    for row in rows:
                        row_dict = dict(zip(columns, row, strict=False))

                        # Parse JSON strings in columns
                        for key, value in row_dict.items():
                            if isinstance(value, str) and value.strip():
                                row_dict[key] = self._try_parse_json(value)

                        results.append(row_dict)

                    all_results.append({f"ResultSet_{result_set_count}": results})
                    result_set_count += 1

                # Try to move to next result set
                if not cursor.nextset():
                    break

            except pyodbc.Error:
                # No more result sets
                break

        return all_results

    def _try_parse_json(self, value: str) -> Any:
        """Try to parse a string as JSON, return original if not JSON"""
        stripped_value = value.strip()
        if (stripped_value.startswith("{") and stripped_value.endswith("}")) or (
            stripped_value.startswith("[") and stripped_value.endswith("]")
        ):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        return value

    def _normalize_sql_type(self, param_info: dict[str, Any]) -> str:
        """Normalize SQL type for declarations using detailed parameter information"""
        base_type = param_info.get("base_type", "NVARCHAR").upper()
        size = param_info.get("size")
        precision = param_info.get("precision")
        scale = param_info.get("scale")
        full_type = param_info.get("full_type", "")

        # If we have the full type, try to use it directly
        if full_type and "(" in full_type:
            return full_type.upper()

        # Build type based on detailed information
        if base_type in ["DECIMAL", "NUMERIC"]:
            if precision and scale is not None:
                return f"{base_type}({precision},{scale})"
            else:
                return f"{base_type}(18,2)"  # Safe default

        elif base_type in ["VARCHAR", "NVARCHAR", "CHAR", "NCHAR"]:
            if size:
                if str(size).upper() == "MAX":
                    return f"{base_type}(MAX)"
                else:
                    return f"{base_type}({size})"
            else:
                # Use reasonable defaults based on type
                if base_type in ["VARCHAR", "NVARCHAR"]:
                    return f"{base_type}(4000)"  # Safe default
                else:
                    return f"{base_type}(255)"

        elif base_type in ["VARBINARY", "BINARY"]:
            if size:
                if str(size).upper() == "MAX":
                    return f"{base_type}(MAX)"
                else:
                    return f"{base_type}({size})"
            else:
                return f"{base_type}(8000)"

        elif base_type == "FLOAT":
            if precision:
                return f"FLOAT({precision})"
            else:
                return "FLOAT"

        elif base_type in ["DATETIME2", "TIME", "DATETIMEOFFSET"]:
            if precision:
                return f"{base_type}({precision})"
            else:
                return f"{base_type}(7)"  # Default precision

        # Simple types that don't need parameters
        elif base_type in [
            "INT",
            "BIGINT",
            "SMALLINT",
            "TINYINT",
            "BIT",
            "REAL",
            "MONEY",
            "SMALLMONEY",
            "DATETIME",
            "DATE",
            "UNIQUEIDENTIFIER",
            "TEXT",
            "NTEXT",
            "IMAGE",
            "TIMESTAMP",
            "ROWVERSION",
        ]:
            return base_type

        # Unknown type - use safe default
        else:
            print(f"Unknown SQL type: {base_type}, using NVARCHAR(4000)")
            return "NVARCHAR(4000)"

    def _create_success_response(
        self, result_sets: list[dict[str, Any]], output_params: dict[str, Any] | None
    ) -> str:
        """Create success response JSON"""
        response = {
            "ExecutionStatus": "Success",
            "ResultSets": result_sets,
            "OutputParameters": output_params,
            "Timestamp": self._get_timestamp(),
        }
        return json.dumps(response, indent=4, default=str)

    def _create_error_response(self, error_message: str, error_category: str = "UNKNOWN") -> str:
        """Create error response JSON with categorization"""
        response = {
            "ExecutionStatus": "Error",
            "ErrorMessage": error_message,
            "ErrorCategory": error_category,
            "ResultSets": [],
            "OutputParameters": None,
            "Timestamp": self._get_timestamp(),
        }
        return json.dumps(response, indent=4)

    def _categorize_error(self, error: Exception) -> str:
        """Categorize error for better handling"""
        error_str = str(error).lower()

        if isinstance(error, pyodbc.Error):
            return self._categorize_pyodbc_error(error)
        elif "timeout" in error_str or "timed out" in error_str:
            return "TIMEOUT"
        elif "connection" in error_str or "network" in error_str:
            return "CONNECTION"
        elif "permission" in error_str or "access denied" in error_str:
            return "PERMISSION"
        elif "syntax" in error_str or "invalid" in error_str:
            return "SYNTAX"
        else:
            return "UNKNOWN"

    def _categorize_pyodbc_error(self, error: pyodbc.Error) -> str:
        """Categorize pyodbc errors and return appropriate error category string"""
        error_str = str(error).lower()

        if "timeout" in error_str or "query timeout" in error_str:
            return "TIMEOUT"
        elif "permission denied" in error_str or "access denied" in error_str:
            return "PERMISSION"
        elif "syntax error" in error_str or "invalid syntax" in error_str:
            return "SYNTAX"
        elif "connection" in error_str or "network" in error_str:
            return "CONNECTION"
        else:
            return "DATABASE_ERROR"

    def _get_timestamp(self) -> str:
        """Get current timestamp as string"""
        from datetime import datetime

        return datetime.now().isoformat()
