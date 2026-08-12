"""
cleanup_manager.py
==================
Manages project folder size by cleaning up old generated apps, checkpoints,
temporary files, and caches.
"""

import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple


def get_folder_size(folder: Path) -> int:
    """Calculate total size of a folder in bytes."""
    total = 0
    try:
        for item in folder.rglob("*"):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total


def format_size(bytes_size: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def cleanup_old_generated_apps(
    generated_apps_root: Path,
    keep_latest: int = 1,
    keep_days: Optional[int] = None
) -> Tuple[int, int]:
    """
    Clean up old generated app projects.
    
    Args:
        generated_apps_root: Path to generated_apps/projects directory
        keep_latest: Number of latest projects to keep (default: 1)
        keep_days: Keep projects modified within this many days (optional)
    
    Returns:
        Tuple of (number of projects deleted, bytes freed)
    """
    if not generated_apps_root.exists():
        return 0, 0
    
    projects = []
    for project_dir in generated_apps_root.iterdir():
        if project_dir.is_dir() and project_dir.name != "latest":
            try:
                mtime = project_dir.stat().st_mtime
                size = get_folder_size(project_dir)
                projects.append((project_dir, mtime, size))
            except (OSError, PermissionError):
                pass
    
    # Sort by modification time (newest first)
    projects.sort(key=lambda x: x[1], reverse=True)
    
    deleted_count = 0
    bytes_freed = 0
    
    # Determine cutoff time if keep_days is specified
    cutoff_time = None
    if keep_days is not None:
        cutoff_time = time.time() - (keep_days * 86400)
    
    for i, (project_dir, mtime, size) in enumerate(projects):
        should_delete = False
        
        # Keep the latest N projects
        if i >= keep_latest:
            should_delete = True
        
        # If keep_days is specified, keep recent projects
        if cutoff_time is not None and mtime > cutoff_time:
            should_delete = False
        
        if should_delete:
            try:
                # Try to delete, retry a few times if locked
                for attempt in range(3):
                    try:
                        shutil.rmtree(project_dir)
                        deleted_count += 1
                        bytes_freed += size
                        break
                    except (OSError, PermissionError) as e:
                        if attempt < 2:
                            time.sleep(0.5)
                        else:
                            print(f"Warning: Could not delete {project_dir.name}: {e}")
            except Exception as e:
                print(f"Error deleting {project_dir.name}: {e}")
    
    return deleted_count, bytes_freed


def cleanup_old_checkpoints(
    checkpoints_root: Path,
    keep_latest: int = 5,
    keep_days: Optional[int] = 7
) -> Tuple[int, int]:
    """
    Clean up old checkpoint directories.
    
    Args:
        checkpoints_root: Path to checkpoints directory
        keep_latest: Number of latest checkpoints to keep (default: 5)
        keep_days: Keep checkpoints modified within this many days (default: 7)
    
    Returns:
        Tuple of (number of checkpoints deleted, bytes freed)
    """
    if not checkpoints_root.exists():
        return 0, 0
    
    checkpoints = []
    for checkpoint_dir in checkpoints_root.iterdir():
        if checkpoint_dir.is_dir():
            try:
                checkpoint_file = checkpoint_dir / "checkpoint.json"
                if checkpoint_file.exists():
                    mtime = checkpoint_file.stat().st_mtime
                    size = get_folder_size(checkpoint_dir)
                    checkpoints.append((checkpoint_dir, mtime, size))
            except (OSError, PermissionError):
                pass
    
    # Sort by modification time (newest first)
    checkpoints.sort(key=lambda x: x[1], reverse=True)
    
    deleted_count = 0
    bytes_freed = 0
    
    # Determine cutoff time
    cutoff_time = None
    if keep_days is not None:
        cutoff_time = time.time() - (keep_days * 86400)
    
    for i, (checkpoint_dir, mtime, size) in enumerate(checkpoints):
        should_delete = False
        
        # Keep the latest N checkpoints
        if i >= keep_latest:
            should_delete = True
        
        # If keep_days is specified, keep recent checkpoints
        if cutoff_time is not None and mtime > cutoff_time:
            should_delete = False
        
        if should_delete:
            try:
                shutil.rmtree(checkpoint_dir)
                deleted_count += 1
                bytes_freed += size
            except Exception as e:
                print(f"Error deleting checkpoint {checkpoint_dir.name}: {e}")
    
    return deleted_count, bytes_freed


def cleanup_python_caches(project_root: Path) -> Tuple[int, int]:
    """
    Clean up Python cache directories.
    
    Args:
        project_root: Root directory of the project
    
    Returns:
        Tuple of (number of cache dirs deleted, bytes freed)
    """
    cache_patterns = [
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".hypothesis"
    ]
    
    deleted_count = 0
    bytes_freed = 0
    
    for pattern in cache_patterns:
        for cache_dir in project_root.rglob(pattern):
            if cache_dir.is_dir():
                try:
                    size = get_folder_size(cache_dir)
                    shutil.rmtree(cache_dir)
                    deleted_count += 1
                    bytes_freed += size
                except Exception as e:
                    print(f"Error deleting cache {cache_dir}: {e}")
    
    return deleted_count, bytes_freed


def cleanup_temporary_files(project_root: Path) -> Tuple[int, int]:
    """
    Clean up temporary files and directories.
    
    Args:
        project_root: Root directory of the project
    
    Returns:
        Tuple of (number of items deleted, bytes freed)
    """
    temp_patterns = [
        "scratch",
        "tmp",
        "temp",
        "*.tmp",
        "*.log"
    ]
    
    deleted_count = 0
    bytes_freed = 0
    
    # Clean temp directories
    for pattern in ["scratch", "tmp", "temp"]:
        temp_dir = project_root / pattern
        if temp_dir.exists() and temp_dir.is_dir():
            try:
                size = get_folder_size(temp_dir)
                shutil.rmtree(temp_dir)
                deleted_count += 1
                bytes_freed += size
            except Exception as e:
                print(f"Error deleting temp dir {temp_dir}: {e}")
    
    # Clean temp files
    for pattern in ["*.tmp", "*.log"]:
        for temp_file in project_root.rglob(pattern):
            if temp_file.is_file():
                try:
                    size = temp_file.stat().st_size
                    temp_file.unlink()
                    deleted_count += 1
                    bytes_freed += size
                except Exception as e:
                    print(f"Error deleting temp file {temp_file}: {e}")
    
    return deleted_count, bytes_freed


def cleanup_build_artifacts(project_root: Path) -> Tuple[int, int]:
    """
    Clean up build artifacts.
    
    Args:
        project_root: Root directory of the project
    
    Returns:
        Tuple of (number of items deleted, bytes freed)
    """
    build_patterns = [
        "build",
        "dist",
        "*.egg-info"
    ]
    
    deleted_count = 0
    bytes_freed = 0
    
    for pattern in build_patterns:
        if "*" in pattern:
            # Glob pattern
            for item in project_root.rglob(pattern):
                if item.is_dir():
                    try:
                        size = get_folder_size(item)
                        shutil.rmtree(item)
                        deleted_count += 1
                        bytes_freed += size
                    except Exception as e:
                        print(f"Error deleting build artifact {item}: {e}")
        else:
            # Directory name
            build_dir = project_root / pattern
            if build_dir.exists() and build_dir.is_dir():
                try:
                    size = get_folder_size(build_dir)
                    shutil.rmtree(build_dir)
                    deleted_count += 1
                    bytes_freed += size
                except Exception as e:
                    print(f"Error deleting build dir {build_dir}: {e}")
    
    return deleted_count, bytes_freed


def full_cleanup(
    project_root: Path,
    keep_latest_apps: int = 1,
    keep_latest_checkpoints: int = 5,
    keep_checkpoint_days: int = 7
) -> dict:
    """
    Perform a full cleanup of the project.
    
    Args:
        project_root: Root directory of the project
        keep_latest_apps: Number of latest generated apps to keep
        keep_latest_checkpoints: Number of latest checkpoints to keep
        keep_checkpoint_days: Keep checkpoints modified within this many days
    
    Returns:
        Dictionary with cleanup statistics
    """
    stats = {
        "generated_apps": {"count": 0, "bytes": 0},
        "checkpoints": {"count": 0, "bytes": 0},
        "python_caches": {"count": 0, "bytes": 0},
        "temp_files": {"count": 0, "bytes": 0},
        "build_artifacts": {"count": 0, "bytes": 0},
        "total_bytes_freed": 0
    }
    
    # Clean generated apps
    generated_apps_root = project_root / "generated_apps" / "projects"
    count, bytes_freed = cleanup_old_generated_apps(
        generated_apps_root,
        keep_latest=keep_latest_apps
    )
    stats["generated_apps"]["count"] = count
    stats["generated_apps"]["bytes"] = bytes_freed
    
    # Clean checkpoints
    checkpoints_root = project_root / "checkpoints"
    count, bytes_freed = cleanup_old_checkpoints(
        checkpoints_root,
        keep_latest=keep_latest_checkpoints,
        keep_days=keep_checkpoint_days
    )
    stats["checkpoints"]["count"] = count
    stats["checkpoints"]["bytes"] = bytes_freed
    
    # Clean Python caches
    count, bytes_freed = cleanup_python_caches(project_root)
    stats["python_caches"]["count"] = count
    stats["python_caches"]["bytes"] = bytes_freed
    
    # Clean temporary files
    count, bytes_freed = cleanup_temporary_files(project_root)
    stats["temp_files"]["count"] = count
    stats["temp_files"]["bytes"] = bytes_freed
    
    # Clean build artifacts
    count, bytes_freed = cleanup_build_artifacts(project_root)
    stats["build_artifacts"]["count"] = count
    stats["build_artifacts"]["bytes"] = bytes_freed
    
    # Calculate total
    stats["total_bytes_freed"] = sum(
        cat["bytes"] for cat in stats.values() if isinstance(cat, dict) and "bytes" in cat
    )
    
    return stats


def get_project_size_report(project_root: Path) -> dict:
    """
    Generate a size report for the project.
    
    Args:
        project_root: Root directory of the project
    
    Returns:
        Dictionary with size information
    """
    report = {}
    
    # Check key directories
    directories = {
        "generated_apps": project_root / "generated_apps" / "projects",
        "checkpoints": project_root / "checkpoints",
        "templates": project_root / "templates",
        "builder": project_root / "builder",
        ".venv": project_root / ".venv"
    }
    
    for name, path in directories.items():
        if path.exists():
            size = get_folder_size(path)
            report[name] = {
                "size_bytes": size,
                "size_formatted": format_size(size)
            }
        else:
            report[name] = {
                "size_bytes": 0,
                "size_formatted": "0 B"
            }
    
    # Total project size
    total_size = get_folder_size(project_root)
    report["total"] = {
        "size_bytes": total_size,
        "size_formatted": format_size(total_size)
    }
    
    return report
