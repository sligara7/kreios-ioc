#!/usr/bin/env python3
"""
JSON Utilities for Reflow Tools

Provides safe JSON loading with validation, helpful error messages,
and optional schema validation.

Part of v3.4.0 security enhancements (Issue #2: SV-02)
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False


class JSONValidationError(Exception):
    """Raised when JSON validation fails."""
    pass


def safe_load_json(
    file_path: Path,
    schema: Optional[Dict[str, Any]] = None,
    file_type_description: str = "JSON file"
) -> Dict[str, Any]:
    """
    Safely load and validate JSON file with helpful error messages.

    Args:
        file_path: Path to JSON file
        schema: Optional JSON schema for validation
        file_type_description: Human-readable description (e.g., "workflow file", "architecture file")

    Returns:
        Parsed JSON data as dictionary

    Raises:
        JSONValidationError: If JSON is invalid or fails schema validation
        FileNotFoundError: If file doesn't exist

    Example:
        # Basic usage (syntax validation only)
        data = safe_load_json(Path("workflow.json"), file_type_description="workflow")

        # With schema validation
        with open("schemas/workflow_schema.json") as f:
            schema = json.load(f)
        data = safe_load_json(Path("workflow.json"), schema=schema, file_type_description="workflow")
    """
    # Ensure Path object
    file_path = Path(file_path)

    # Check file exists
    if not file_path.exists():
        raise FileNotFoundError(
            f"{file_type_description.capitalize()} not found: {file_path}\n"
            f"Please ensure the file exists and the path is correct."
        )

    # Load JSON with syntax validation
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise JSONValidationError(
            f"Invalid JSON syntax in {file_type_description}: {file_path}\n"
            f"Error at line {e.lineno}, column {e.colno}: {e.msg}\n\n"
            f"Common issues:\n"
            f"  - Missing closing bracket/brace\n"
            f"  - Trailing comma in array or object\n"
            f"  - Unquoted strings or keys\n"
            f"  - Single quotes instead of double quotes\n\n"
            f"Use a JSON validator (e.g., jsonlint.com) to debug the syntax error."
        ) from e
    except UnicodeDecodeError as e:
        raise JSONValidationError(
            f"File encoding error in {file_type_description}: {file_path}\n"
            f"Expected UTF-8 encoding. Error: {e}\n\n"
            f"Try converting the file to UTF-8 encoding."
        ) from e
    except Exception as e:
        raise JSONValidationError(
            f"Failed to read {file_type_description}: {file_path}\n"
            f"Error: {e}"
        ) from e

    # Schema validation (optional)
    if schema is not None:
        if not JSONSCHEMA_AVAILABLE:
            # Warn but don't fail if jsonschema not installed
            print(f"WARNING: jsonschema library not available. Skipping schema validation for {file_path}")
            print("Install with: pip install jsonschema>=4.0.0")
        else:
            try:
                jsonschema.validate(data, schema)
            except jsonschema.ValidationError as e:
                # Format error path for clarity
                error_path = ".".join(str(p) for p in e.path) if e.path else "root"

                raise JSONValidationError(
                    f"Schema validation failed for {file_type_description}: {file_path}\n"
                    f"Error at '{error_path}': {e.message}\n\n"
                    f"This means the JSON file structure doesn't match the expected format.\n"
                    f"Please check the documentation for the correct {file_type_description} structure."
                ) from e
            except jsonschema.SchemaError as e:
                raise JSONValidationError(
                    f"Invalid schema definition for {file_type_description}\n"
                    f"Schema error: {e.message}\n\n"
                    f"This is a bug in the Reflow schema definitions. Please report it."
                ) from e

    return data


def safe_load_json_with_schema_path(
    file_path: Path,
    schema_path: Optional[Path] = None,
    file_type_description: str = "JSON file"
) -> Dict[str, Any]:
    """
    Safely load JSON file and validate against schema file.

    Convenience wrapper around safe_load_json() that loads schema from file.

    Args:
        file_path: Path to JSON file to load
        schema_path: Path to JSON schema file (optional)
        file_type_description: Human-readable description

    Returns:
        Parsed JSON data as dictionary

    Example:
        data = safe_load_json_with_schema_path(
            Path("workflows/00-setup.json"),
            schema_path=Path("schemas/workflow_schema.json"),
            file_type_description="workflow file"
        )
    """
    schema = None
    if schema_path is not None:
        # Load schema
        try:
            with open(schema_path) as f:
                schema = json.load(f)
        except FileNotFoundError:
            print(f"WARNING: Schema file not found: {schema_path}")
            print("Proceeding without schema validation")
        except json.JSONDecodeError as e:
            print(f"WARNING: Invalid JSON in schema file: {schema_path}")
            print(f"Error: {e}")
            print("Proceeding without schema validation")

    return safe_load_json(file_path, schema=schema, file_type_description=file_type_description)


def validate_required_fields(
    data: Dict[str, Any],
    required_fields: list[str],
    file_description: str = "JSON data"
) -> None:
    """
    Validate that required fields are present in JSON data.

    Args:
        data: Parsed JSON data dictionary
        required_fields: List of required field names
        file_description: Description for error messages

    Raises:
        JSONValidationError: If required fields are missing

    Example:
        data = safe_load_json(Path("workflow.json"))
        validate_required_fields(
            data,
            ["workflow_metadata", "workflow_steps"],
            file_description="workflow file"
        )
    """
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        raise JSONValidationError(
            f"Missing required fields in {file_description}:\n"
            f"  - " + "\n  - ".join(missing_fields) + "\n\n"
            f"Required fields: {', '.join(required_fields)}\n"
            f"Please add the missing fields to the JSON file."
        )


def validate_json_type(
    data: Any,
    expected_type: type,
    field_name: str = "root",
    file_description: str = "JSON data"
) -> None:
    """
    Validate that JSON data is of expected type.

    Args:
        data: JSON data to validate
        expected_type: Expected Python type (dict, list, str, int, etc.)
        field_name: Name of field being validated
        file_description: Description for error messages

    Raises:
        JSONValidationError: If data is wrong type

    Example:
        data = safe_load_json(Path("workflow.json"))
        validate_json_type(data, dict, field_name="workflow", file_description="workflow file")
        validate_json_type(data["workflow_steps"], list, field_name="workflow_steps")
    """
    if not isinstance(data, expected_type):
        actual_type = type(data).__name__
        expected_type_name = expected_type.__name__

        raise JSONValidationError(
            f"Type error in {file_description} at field '{field_name}':\n"
            f"  Expected: {expected_type_name}\n"
            f"  Got: {actual_type}\n\n"
            f"Please ensure '{field_name}' is a {expected_type_name}."
        )


# Backward compatibility: alias for tools that might import json.load
load_json = safe_load_json
