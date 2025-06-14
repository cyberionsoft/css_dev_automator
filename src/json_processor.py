"""
JSON Processor
Handles JSON extraction from stored procedures and template generation
"""

import json
import re
from typing import Any

from .config_manager import JsonExtractionConfig


class TimeoutError(Exception):
    """Raised when regex operation times out"""

    pass


def timeout_handler(signum, frame):
    """Signal handler for regex timeout"""
    raise TimeoutError("Regex operation timed out")


class JsonProcessor:
    """Processes JSON extraction and template generation"""

    def __init__(self, config: JsonExtractionConfig):
        self.config = config

        # Enhanced regex patterns for JSON extraction
        self.json_patterns = [
            # EXEC with single quotes
            r"EXEC\s+\[.*?\]\s+'(\{.*?\})'",
            r"EXEC\s+\[.*?\]\s+'(\[.*?\])'",
            # EXEC with double quotes
            r"EXEC\s+\[.*?\]\s+\"(\{.*?\})\"",
            r"EXEC\s+\[.*?\]\s+\"(\[.*?\])\"",
            # Parameter assignment patterns
            r"@Json\s*=\s*'(\{.*?\})'",
            r"@Json\s*=\s*'(\[.*?\])'",
            r"@Json\s*=\s*\"(\{.*?\})\"",
            r"@Json\s*=\s*\"(\[.*?\])\"",
            # EXECUTE patterns
            r"EXECUTE\s+\[.*?\]\s+'(\{.*?\})'",
            r"EXECUTE\s+\[.*?\]\s+'(\[.*?\])'",
            # More flexible patterns
            r"@Json\s*=\s*N?'(\{[^']*\})'",
            r"@Json\s*=\s*N?'(\[[^\]]*\])'",
            # JSON in comments
            r"/\*.*?(\{.*?\}).*?\*/",
            r"--.*?(\{.*?\})",
        ]

    def extract_input_json(self, sp_definition: str, sp_name: str) -> str | None:
        """Extract input JSON from stored procedure definition with fallback options"""
        if not sp_definition:
            print(f"No SP definition provided for {sp_name}")
            return None

        # Check size limit
        if len(sp_definition) > self.config.max_json_size_mb * 1024 * 1024:
            print(f"SP definition too large for {sp_name}")
            return None

        # Try to extract JSON using patterns
        extracted_json = self._extract_with_patterns(sp_definition, sp_name)

        if extracted_json:
            # Validate extracted JSON
            if self.config.validate_extracted_json:
                if self._validate_json(extracted_json):
                    # Debug: f"Successfully extracted and validated JSON for {sp_name}"
                    return extracted_json
                else:
                    print(f"Extracted JSON is invalid for {sp_name}")
                    if self.config.fallback_to_template:
                        return self._generate_template_from_sp(sp_definition, sp_name)
            else:
                return extracted_json

        # Fallback to template generation
        if self.config.fallback_to_template:
            print(f"Falling back to template generation for {sp_name}")
            return self._generate_template_from_sp(sp_definition, sp_name)

        return None

    def _extract_with_patterns(self, sp_definition: str, sp_name: str) -> str | None:
        """Extract JSON using regex patterns with timeout protection"""
        # Limit input size to prevent memory issues
        if len(sp_definition) > 1024 * 1024:  # 1MB limit
            print(f"SP definition too large for {sp_name}, truncating")
            sp_definition = sp_definition[: 1024 * 1024]

        for i, pattern in enumerate(self.json_patterns):
            try:
                # Use timeout protection for regex operations
                matches = self._safe_regex_finditer(pattern, sp_definition, timeout_seconds=5)

                for match in matches:
                    json_str = match.group(1)

                    # Limit JSON string size
                    if len(json_str) > 100 * 1024:  # 100KB limit
                        print(f"JSON string too large for {sp_name}, skipping")
                        continue

                    # Clean up the JSON string
                    cleaned_json = self._clean_json_string(json_str)

                    # Try to parse and format
                    try:
                        parsed_json = json.loads(cleaned_json)
                        formatted_json = json.dumps(parsed_json, indent=4)
                        # Debug: f"Pattern {i+1} matched for {sp_name}"
                        return formatted_json
                    except json.JSONDecodeError:
                        continue

            except TimeoutError:
                print(f"Regex timeout with pattern {i + 1} for {sp_name}")
                continue
            except re.error as e:
                print(f"Regex error with pattern {i + 1}: {e}")
                continue

        return None

    def _safe_regex_finditer(self, pattern: str, text: str, timeout_seconds: int = 5):
        """Perform regex finditer with timeout protection"""
        import threading

        result = []
        exception = None

        def regex_worker():
            nonlocal result, exception
            try:
                result = list(re.finditer(pattern, text, re.DOTALL | re.IGNORECASE))
            except Exception as e:
                exception = e

        thread = threading.Thread(target=regex_worker)
        thread.daemon = True
        thread.start()
        thread.join(timeout_seconds)

        if thread.is_alive():
            # Thread is still running, regex is taking too long
            raise TimeoutError(f"Regex operation timed out after {timeout_seconds} seconds")

        if exception:
            raise exception

        return result

    def _clean_json_string(self, json_str: str) -> str:
        """Clean and normalize JSON string safely"""
        if not json_str or len(json_str) > 100 * 1024:  # 100KB limit
            return json_str

        try:
            # Remove excessive whitespace but preserve structure
            cleaned = re.sub(r"\s*\n\s*", " ", json_str, count=1000)  # Limit replacements
            cleaned = re.sub(r"\s+", " ", cleaned, count=1000).strip()

            # Fix common issues with limited scope
            # Remove trailing commas before closing braces/brackets
            cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned, count=100)

            # Fix single quotes to double quotes - use safer pattern
            # Only replace quotes around property names, not values
            cleaned = re.sub(r"'(\w+)':", r'"\1":', cleaned, count=100)

            return cleaned
        except Exception as e:
            print(f"Error cleaning JSON string: {e}")
            return json_str  # Return original if cleaning fails

    def _validate_json(self, json_str: str) -> bool:
        """Validate JSON string"""
        try:
            json.loads(json_str)
            return True
        except json.JSONDecodeError:
            # Debug: f"JSON validation failed: {e}"
            return False

    def _generate_template_from_sp(self, sp_definition: str, sp_name: str) -> str | None:
        """Generate JSON template from stored procedure parameters"""
        try:
            # Extract parameter information from SP definition
            parameters = self._extract_parameters(sp_definition)

            if not parameters:
                print(f"No parameters found for template generation: {sp_name}")
                return self._generate_basic_template()

            # Generate template based on parameters
            template = self._build_template_from_parameters(parameters)

            print(f"Generated template with {len(parameters)} parameters for {sp_name}")
            return json.dumps(template, indent=4)

        except Exception as e:
            print(f"Failed to generate template for {sp_name}: {e}")
            return self._generate_basic_template()

    def _extract_parameters(self, sp_definition: str) -> list[dict[str, Any]]:
        """Extract parameter information from stored procedure"""
        parameters = []

        # Pattern to match parameter declarations
        param_pattern = r"@(\w+)\s+(\w+(?:\([^)]+\))?)\s*(?:=\s*([^,\n]+))?"

        matches = re.finditer(param_pattern, sp_definition, re.IGNORECASE)

        for match in matches:
            param_name = match.group(1)
            param_type = match.group(2)
            default_value = match.group(3)

            # Skip output parameters and system parameters
            if "OUTPUT" in sp_definition[match.end() : match.end() + 20].upper():
                continue
            if param_name.lower() in ["json", "guid", "errornumber", "errormessage"]:
                continue

            parameters.append(
                {
                    "name": param_name,
                    "type": param_type.lower(),
                    "default": default_value.strip() if default_value else None,
                }
            )

        return parameters

    def _build_template_from_parameters(self, parameters: list[dict[str, Any]]) -> dict[str, Any]:
        """Build JSON template from parameters"""
        template = {}

        for param in parameters:
            param_name = param["name"]
            param_type = param["type"].lower()
            default_value = param["default"]

            # Generate appropriate default value based on type
            if "int" in param_type:
                template[param_name] = 0
            elif "bit" in param_type or "bool" in param_type:
                template[param_name] = False
            elif "decimal" in param_type or "float" in param_type or "money" in param_type:
                template[param_name] = 0.0
            elif "date" in param_type or "time" in param_type:
                template[param_name] = "2024-01-01T00:00:00"
            elif "varchar" in param_type or "nvarchar" in param_type or "char" in param_type:
                template[param_name] = ""
            else:
                template[param_name] = None

            # Use default value if available
            if default_value and default_value.lower() not in ["null", "none"]:
                try:
                    # Try to parse the default value
                    if default_value.isdigit():
                        template[param_name] = int(default_value)
                    elif default_value.replace(".", "").isdigit():
                        template[param_name] = float(default_value)
                    elif default_value.lower() in ["true", "false"]:
                        template[param_name] = default_value.lower() == "true"
                    else:
                        template[param_name] = default_value.strip("'\"")
                except:
                    pass

        return template

    def _generate_basic_template(self) -> str:
        """Generate a basic JSON template"""
        basic_template = {"Id": 0, "UserId": 1, "BizUnit": 1}
        return json.dumps(basic_template, indent=4)

    def create_input_template(self, sp_name: str, sp_type: str) -> str:
        """Create a basic input template for a given SP type"""
        templates = {
            "Get": {"Id": 1},
            "List": {"PageNumber": 1, "PageSize": 10, "SearchTerm": ""},
            "Save": {"Id": 0, "UserId": 1, "BizUnit": 1},
            "Delete": {"Id": 1, "UserId": 1},
            "Update": {"Id": 1, "UserId": 1, "BizUnit": 1},
        }

        template = templates.get(sp_type, {"Id": 0})
        print(f"Created basic template for {sp_name} (type: {sp_type})")
        return json.dumps(template, indent=4)
