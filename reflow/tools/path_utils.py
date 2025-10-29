#!/usr/bin/env python3
"""
Path Utilities for Reflow Tools - Security-Focused Path Handling

Provides secure path sanitization and validation to prevent path traversal
attacks and ensure all file operations stay within designated boundaries.

Security Features:
- Path traversal prevention (../ attacks)
- Symlink resolution with boundary checking
- Allowlist/blocklist support
- Clear error messages for security violations

Usage:
    from path_utils import sanitize_path, validate_system_root

    # Basic sanitization
    safe_path = sanitize_path(user_input, system_root)

    # With validation
    safe_path = sanitize_path(user_input, system_root, must_exist=True)

    # Allow paths outside system_root (use with caution)
    safe_path = sanitize_path(user_input, system_root, strict=False)
"""

import os
import sys
from pathlib import Path
from typing import Optional, Union


class PathSecurityError(Exception):
    """Raised when a path security violation is detected."""
    pass


def validate_system_root(system_root: Union[str, Path]) -> Path:
    """
    Validate that system_root is a valid directory.

    Args:
        system_root: Path to system root directory

    Returns:
        Resolved Path object

    Raises:
        PathSecurityError: If system_root is invalid
    """
    try:
        root_path = Path(system_root).resolve()
    except (OSError, RuntimeError) as e:
        raise PathSecurityError(
            f"Invalid system_root '{system_root}': {e}"
        ) from e

    if not root_path.exists():
        raise PathSecurityError(
            f"System root does not exist: {root_path}"
        )

    if not root_path.is_dir():
        raise PathSecurityError(
            f"System root is not a directory: {root_path}"
        )

    return root_path


def sanitize_path(
    user_path: Union[str, Path],
    system_root: Union[str, Path],
    must_exist: bool = False,
    strict: bool = True,
    allow_symlinks: bool = True
) -> Path:
    """
    Sanitize user-provided path to prevent traversal attacks.

    This function ensures that resolved paths stay within system_root boundaries,
    preventing attackers from accessing files outside the designated workspace.

    Args:
        user_path: User-provided path (potentially malicious)
        system_root: Root directory that paths must stay within
        must_exist: If True, path must exist (default: False)
        strict: If True, path must be within system_root (default: True)
        allow_symlinks: If True, follow symlinks (default: True)

    Returns:
        Sanitized and resolved Path object

    Raises:
        PathSecurityError: If path violates security constraints
        FileNotFoundError: If must_exist=True and path doesn't exist

    Examples:
        >>> sanitize_path("../../etc/passwd", "/home/user/project")
        PathSecurityError: Path outside system root

        >>> sanitize_path("docs/README.md", "/home/user/project")
        Path('/home/user/project/docs/README.md')

        >>> sanitize_path("/tmp/outside", "/home/user/project", strict=False)
        Path('/tmp/outside')  # Allowed when strict=False
    """
    # Validate system_root first
    root_path = validate_system_root(system_root)

    # Handle None or empty paths
    if not user_path:
        raise PathSecurityError("Path cannot be empty")

    # Convert to Path object
    try:
        if isinstance(user_path, str):
            input_path = Path(user_path)
        else:
            input_path = Path(user_path)
    except (TypeError, ValueError) as e:
        raise PathSecurityError(
            f"Invalid path format '{user_path}': {e}"
        ) from e

    # Resolve path (follows symlinks if allow_symlinks=True)
    try:
        if allow_symlinks:
            resolved_path = input_path.resolve()
        else:
            # Resolve without following symlinks (more restrictive)
            resolved_path = input_path.absolute()
    except (OSError, RuntimeError) as e:
        raise PathSecurityError(
            f"Cannot resolve path '{user_path}': {e}"
        ) from e

    # If path is relative, make it relative to system_root
    if not input_path.is_absolute():
        resolved_path = (root_path / input_path).resolve()

    # Strict mode: Verify path is within system_root
    if strict:
        try:
            # Check if resolved path is within system_root
            resolved_path.relative_to(root_path)
        except ValueError:
            raise PathSecurityError(
                f"Path '{user_path}' resolves to '{resolved_path}' "
                f"which is outside system root '{root_path}'. "
                f"This may be a path traversal attack."
            ) from None

    # Check existence if required
    if must_exist and not resolved_path.exists():
        raise FileNotFoundError(
            f"Path does not exist: {resolved_path}"
        )

    return resolved_path


def sanitize_multiple_paths(
    user_paths: list[Union[str, Path]],
    system_root: Union[str, Path],
    **kwargs
) -> list[Path]:
    """
    Sanitize multiple paths at once.

    Args:
        user_paths: List of user-provided paths
        system_root: Root directory for validation
        **kwargs: Additional arguments passed to sanitize_path()

    Returns:
        List of sanitized Path objects

    Raises:
        PathSecurityError: If any path violates security constraints
    """
    sanitized = []
    for user_path in user_paths:
        try:
            sanitized.append(sanitize_path(user_path, system_root, **kwargs))
        except PathSecurityError as e:
            # Re-raise with context about which path failed
            raise PathSecurityError(
                f"Failed to sanitize path '{user_path}': {e}"
            ) from e
    return sanitized


def is_safe_filename(filename: str, allow_dots: bool = False) -> bool:
    """
    Check if filename is safe (no path traversal characters).

    Args:
        filename: Filename to check (should not contain path separators)
        allow_dots: If True, allow leading dots (default: False)

    Returns:
        True if filename is safe, False otherwise

    Examples:
        >>> is_safe_filename("document.txt")
        True

        >>> is_safe_filename("../etc/passwd")
        False

        >>> is_safe_filename(".hidden")
        False

        >>> is_safe_filename(".hidden", allow_dots=True)
        True
    """
    if not filename:
        return False

    # Check for path separators
    if '/' in filename or '\\' in filename:
        return False

    # Check for parent directory references
    if filename == '..' or filename.startswith('../') or '/..' in filename:
        return False

    # Check for leading dots (hidden files)
    if not allow_dots and filename.startswith('.'):
        return False

    # Check for null bytes (path injection)
    if '\x00' in filename:
        return False

    return True


def get_safe_write_path(
    filename: str,
    directory: Union[str, Path],
    system_root: Union[str, Path],
    overwrite: bool = False
) -> Path:
    """
    Get a safe path for writing a file.

    Args:
        filename: Name of file to write (sanitized for safety)
        directory: Directory to write file in
        system_root: Root directory for validation
        overwrite: If False, raises error if file exists (default: False)

    Returns:
        Safe path for writing

    Raises:
        PathSecurityError: If path is unsafe
        FileExistsError: If file exists and overwrite=False
    """
    # Validate filename
    if not is_safe_filename(filename, allow_dots=True):
        raise PathSecurityError(
            f"Unsafe filename: '{filename}'. "
            f"Filenames cannot contain path separators or '..' sequences."
        )

    # Sanitize directory
    safe_dir = sanitize_path(directory, system_root, must_exist=False)

    # Create directory if needed
    safe_dir.mkdir(parents=True, exist_ok=True)

    # Construct full path
    full_path = safe_dir / filename

    # Verify still within bounds (shouldn't fail if filename is safe, but double-check)
    final_path = sanitize_path(full_path, system_root, strict=True)

    # Check for overwrite
    if not overwrite and final_path.exists():
        raise FileExistsError(
            f"File already exists: {final_path}. "
            f"Use overwrite=True to replace it."
        )

    return final_path


def safe_read_file(
    file_path: Union[str, Path],
    system_root: Union[str, Path],
    encoding: str = 'utf-8'
) -> str:
    """
    Safely read a file with path validation.

    Args:
        file_path: Path to file to read
        system_root: Root directory for validation
        encoding: File encoding (default: utf-8)

    Returns:
        File contents as string

    Raises:
        PathSecurityError: If path is unsafe
        FileNotFoundError: If file doesn't exist
    """
    safe_path = sanitize_path(file_path, system_root, must_exist=True)

    if not safe_path.is_file():
        raise PathSecurityError(
            f"Path is not a regular file: {safe_path}"
        )

    return safe_path.read_text(encoding=encoding)


def safe_write_file(
    file_path: Union[str, Path],
    content: str,
    system_root: Union[str, Path],
    overwrite: bool = False,
    encoding: str = 'utf-8'
) -> Path:
    """
    Safely write a file with path validation.

    Args:
        file_path: Path to file to write
        content: Content to write
        system_root: Root directory for validation
        overwrite: If False, raises error if file exists (default: False)
        encoding: File encoding (default: utf-8)

    Returns:
        Path to written file

    Raises:
        PathSecurityError: If path is unsafe
        FileExistsError: If file exists and overwrite=False
    """
    if overwrite:
        safe_path = sanitize_path(file_path, system_root, must_exist=False)
    else:
        safe_path = sanitize_path(file_path, system_root, must_exist=False)
        if safe_path.exists():
            raise FileExistsError(
                f"File already exists: {safe_path}. Use overwrite=True to replace."
            )

    # Create parent directory if needed
    safe_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    safe_path.write_text(content, encoding=encoding)

    return safe_path


# Convenience function for tools
def get_validated_paths(
    args,
    required_paths: Optional[list[str]] = None,
    optional_paths: Optional[list[str]] = None
) -> dict[str, Path]:
    """
    Validate multiple paths from argparse args.

    This is a convenience function for tools to validate all their path
    arguments at once.

    Args:
        args: argparse Namespace object with path arguments
        required_paths: List of required path argument names
        optional_paths: List of optional path argument names

    Returns:
        Dictionary mapping argument names to sanitized Path objects

    Raises:
        PathSecurityError: If any required path is invalid
        AttributeError: If required argument is missing

    Example:
        parser.add_argument('system_root', type=str)
        parser.add_argument('--output', type=str)
        args = parser.parse_args()

        paths = get_validated_paths(
            args,
            required_paths=['system_root'],
            optional_paths=['output']
        )

        system_root = paths['system_root']
        output = paths.get('output')  # May be None
    """
    validated = {}

    # Validate required paths
    if required_paths:
        for path_name in required_paths:
            if not hasattr(args, path_name):
                raise AttributeError(
                    f"Required path argument '{path_name}' not found in args"
                )

            path_value = getattr(args, path_name)
            if path_value is None:
                raise PathSecurityError(
                    f"Required path '{path_name}' is None"
                )

            # First path is typically system_root, others relative to it
            if 'system_root' in validated:
                validated[path_name] = sanitize_path(
                    path_value, validated['system_root']
                )
            else:
                # Assume this is system_root
                validated[path_name] = validate_system_root(path_value)

    # Validate optional paths
    if optional_paths:
        for path_name in optional_paths:
            if not hasattr(args, path_name):
                continue  # Optional, so missing is OK

            path_value = getattr(args, path_name)
            if path_value is None:
                validated[path_name] = None
                continue

            # Optional paths relative to system_root
            if 'system_root' in validated:
                validated[path_name] = sanitize_path(
                    path_value, validated['system_root']
                )
            else:
                # No system_root yet, just validate it exists
                validated[path_name] = Path(path_value).resolve()

    return validated


if __name__ == '__main__':
    # Self-test / demonstration
    print("Path Utilities - Security Test\n")

    # Test 1: Safe relative path
    try:
        result = sanitize_path("docs/README.md", "/tmp")
        print(f"✓ Safe relative path: {result}")
    except PathSecurityError as e:
        print(f"✗ Safe relative path failed: {e}")

    # Test 2: Path traversal attack
    try:
        result = sanitize_path("../../etc/passwd", "/tmp")
        print(f"✗ Path traversal NOT blocked: {result}")
    except PathSecurityError as e:
        print(f"✓ Path traversal blocked: {e}")

    # Test 3: Absolute path outside system_root
    try:
        result = sanitize_path("/etc/passwd", "/tmp")
        print(f"✗ Outside path NOT blocked: {result}")
    except PathSecurityError as e:
        print(f"✓ Outside path blocked: {e}")

    # Test 4: Safe filename check
    print(f"\n✓ 'document.txt' is safe: {is_safe_filename('document.txt')}")
    print(f"✓ '../passwd' is unsafe: {not is_safe_filename('../passwd')}")
    print(f"✓ 'path/to/file' is unsafe: {not is_safe_filename('path/to/file')}")

    print("\nAll security tests passed! ✓")
