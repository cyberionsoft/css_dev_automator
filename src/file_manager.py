"""
File Manager
Handles file operations with improved resource management and error handling
"""

import os
import re
import shutil
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class FileManager:
    """Manages file operations with resource management and race condition protection"""

    def __init__(self, output_directory: str):
        self.output_directory = output_directory

        self._ensure_output_directory()
        self._temp_files = []
        self._file_locks = {}
        self._lock_manager = threading.Lock()
        self._instance_id = str(uuid.uuid4())[:8]  # Unique instance identifier

    def _ensure_output_directory(self) -> None:
        """Ensure output directory exists"""
        try:
            Path(self.output_directory).mkdir(parents=True, exist_ok=True)
            # Debug: f"Output directory ready: {self.output_directory}"
        except Exception as e:
            print(f"Failed to create output directory: {e}")
            raise

    def _get_file_lock(self, file_path: str) -> threading.Lock:
        """Get or create a lock for a specific file"""
        with self._lock_manager:
            if file_path not in self._file_locks:
                self._file_locks[file_path] = threading.Lock()
            return self._file_locks[file_path]

    def _generate_unique_filename(self, base_filename: str) -> str:
        """Generate unique filename to avoid conflicts"""
        name, ext = os.path.splitext(base_filename)
        timestamp = str(int(time.time() * 1000))  # Millisecond timestamp
        return f"{name}_{self._instance_id}_{timestamp}{ext}"

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename by removing or replacing invalid characters"""
        # Remove or replace characters that are invalid in Windows filenames
        invalid_chars = r'[<>:"/\\|?*\[\]]'
        sanitized = re.sub(invalid_chars, "_", filename)

        # Remove any trailing dots or spaces
        sanitized = sanitized.strip(". ")

        # Ensure filename is not too long (Windows limit is 255 chars)
        if len(sanitized) > 200:  # Leave some room for extension
            sanitized = sanitized[:200]

        # Ensure filename is not empty
        if not sanitized:
            sanitized = "unnamed_file"

        return sanitized

    @contextmanager
    def safe_file_write(self, file_path: str):
        """Context manager for safe file writing with atomic operations"""
        temp_file = None
        try:
            # Create temporary file in the same directory
            dir_path = os.path.dirname(file_path)
            temp_file = tempfile.NamedTemporaryFile(
                mode="w", dir=dir_path, delete=False, encoding="utf-8", suffix=".tmp"
            )
            self._temp_files.append(temp_file.name)

            yield temp_file

            # Close temp file before moving
            temp_file.close()
            temp_file = None

            # Atomic move
            temp_file_path = temp_file.name
            shutil.move(temp_file_path, file_path)

            # Remove from temp files list
            if temp_file_path in self._temp_files:
                self._temp_files.remove(temp_file_path)

        except Exception as e:
            # Clean up temp file on error
            if temp_file:
                try:
                    temp_file.close()
                except:
                    pass

            # Remove temp file
            temp_file_path = getattr(temp_file, "name", None) if temp_file else None
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    if temp_file_path in self._temp_files:
                        self._temp_files.remove(temp_file_path)
                except:
                    pass

            raise e

    def save_file(self, filename: str, content: str, use_unique_name: bool = False) -> bool:
        """Save content to file with error handling and race condition protection"""
        if content is None:
            content = ""

        # Sanitize filename
        sanitized_filename = self.sanitize_filename(filename)

        # Generate unique filename if requested (for concurrent processing)
        if use_unique_name:
            sanitized_filename = self._generate_unique_filename(sanitized_filename)

        file_path = os.path.join(self.output_directory, sanitized_filename)

        # Use file-specific lock to prevent race conditions
        file_lock = self._get_file_lock(file_path)

        with file_lock:
            try:
                # Check if file already exists and handle accordingly
                if os.path.exists(file_path) and not use_unique_name:
                    # Create backup of existing file
                    backup_path = f"{file_path}.backup.{int(time.time())}"
                    try:
                        shutil.copy2(file_path, backup_path)
                        # Debug: f"Created backup: {backup_path}"
                    except Exception as e:
                        print(f"Failed to create backup: {e}")

                # Check available disk space
                if not self._check_disk_space(len(content.encode("utf-8"))):
                    print(f"Insufficient disk space for {sanitized_filename}")
                    return False

                # Write file atomically using temporary file
                temp_path = f"{file_path}.tmp.{self._instance_id}.{int(time.time() * 1000)}"
                try:
                    with open(temp_path, "w", encoding="utf-8") as f:
                        f.write(content)

                    # Atomic move
                    shutil.move(temp_path, file_path)

                    file_size_kb = len(content.encode("utf-8")) / 1024
                    print(
                        f"✅ Successfully saved '{sanitized_filename}' ({file_size_kb:.1f} KB) to '{self.output_directory}'"
                    )
                    return True

                except Exception as e:
                    # Clean up temp file on error
                    if os.path.exists(temp_path):
                        try:
                            os.unlink(temp_path)
                        except:
                            pass
                    raise e

            except PermissionError as e:
                print(f"Permission denied saving '{sanitized_filename}': {e}")
                return False
            except OSError as e:
                print(f"OS error saving '{sanitized_filename}': {e}")
                return False
            except Exception as e:
                print(f"Unexpected error saving '{sanitized_filename}': {e}")
                return False

    def _check_disk_space(self, required_bytes: int, safety_margin_mb: int = 100) -> bool:
        """Check if there's enough disk space"""
        try:
            stat = shutil.disk_usage(self.output_directory)
            available_bytes = stat.free
            required_with_margin = required_bytes + (safety_margin_mb * 1024 * 1024)

            if available_bytes < required_with_margin:
                print(
                    f"WARNING: Low disk space: {available_bytes / (1024 * 1024):.1f} MB available, "
                    f"{required_with_margin / (1024 * 1024):.1f} MB required"
                )
                return False

            return True

        except Exception as e:
            print(f"Could not check disk space: {e}")
            return True  # Assume OK if we can't check

    def get_file_stats(self, filename: str) -> dict[str, Any] | None:
        """Get file statistics"""
        sanitized_filename = self.sanitize_filename(filename)
        file_path = os.path.join(self.output_directory, sanitized_filename)

        try:
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                return {
                    "exists": True,
                    "size_bytes": stat.st_size,
                    "size_mb": stat.st_size / (1024 * 1024),
                    "created": stat.st_ctime,
                    "modified": stat.st_mtime,
                    "path": file_path,
                }
            else:
                return {"exists": False, "path": file_path}
        except Exception as e:
            print(f"Error getting file stats for {filename}: {e}")
            return None

    def cleanup_temp_files(self) -> None:
        """Clean up any remaining temporary files"""
        for temp_file in self._temp_files[:]:  # Copy list to avoid modification during iteration
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    # Debug: f"Cleaned up temp file: {temp_file}"
                self._temp_files.remove(temp_file)
            except Exception as e:
                print(f"Failed to clean up temp file {temp_file}: {e}")

    def get_output_directory_info(self) -> dict[str, Any]:
        """Get information about the output directory"""
        try:
            stat = shutil.disk_usage(self.output_directory)

            # Count files in directory
            file_count = 0
            total_size = 0

            if os.path.exists(self.output_directory):
                for item in os.listdir(self.output_directory):
                    item_path = os.path.join(self.output_directory, item)
                    if os.path.isfile(item_path):
                        file_count += 1
                        total_size += os.path.getsize(item_path)

            return {
                "path": self.output_directory,
                "exists": os.path.exists(self.output_directory),
                "file_count": file_count,
                "total_size_mb": total_size / (1024 * 1024),
                "disk_free_mb": stat.free / (1024 * 1024),
                "disk_total_mb": stat.total / (1024 * 1024),
                "disk_used_mb": (stat.total - stat.free) / (1024 * 1024),
            }

        except Exception as e:
            print(f"Error getting directory info: {e}")
            return {"path": self.output_directory, "error": str(e)}

    def create_backup(self, filename: str) -> bool:
        """Create backup of existing file"""
        sanitized_filename = self.sanitize_filename(filename)
        file_path = os.path.join(self.output_directory, sanitized_filename)

        if not os.path.exists(file_path):
            return True  # No file to backup

        try:
            backup_path = f"{file_path}.backup"
            shutil.copy2(file_path, backup_path)
            # Debug: f"Created backup: {backup_path}"
            return True
        except Exception as e:
            print(f"Failed to create backup for {filename}: {e}")
            return False

    def __del__(self):
        """Cleanup on destruction"""
        self.cleanup_temp_files()
