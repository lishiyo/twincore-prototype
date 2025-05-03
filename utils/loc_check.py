#!/usr/bin/env python3
"""
Line of Code (LOC) Scanner

This script scans the project directory for files that exceed a specified line count limit.
It helps enforce the architecture guideline of keeping modules small and focused.
"""

import os
import argparse
from pathlib import Path
from typing import List, Tuple, Set


def count_lines(file_path: Path) -> int:
    """Count the number of lines in a file.
    
    Args:
        file_path: Path to the file to count lines for
        
    Returns:
        Number of lines in the file
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except (UnicodeDecodeError, IsADirectoryError, PermissionError):
        # Skip binary files, directories, or files we can't read
        return 0
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0


def scan_directory(
    directory: Path, 
    max_lines: int = 500,
    ignore_dirs: Set[str] = None, 
    file_extensions: Set[str] = None
) -> List[Tuple[Path, int]]:
    """Scan a directory for files exceeding the maximum line count.
    
    Args:
        directory: Directory to scan
        max_lines: Maximum acceptable line count
        ignore_dirs: Set of directory names to ignore
        file_extensions: Set of file extensions to scan (if None, scan all text files)
        
    Returns:
        List of tuples containing file paths and line counts for files exceeding max_lines
    """
    if ignore_dirs is None:
        ignore_dirs = {'.git', '.pytest_cache', '__pycache__', '.venv', 'venv', 'node_modules', '.hypothesis'}
    
    if file_extensions is None:
        file_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.md'}
        
    large_files = []

    for root, dirs, files in os.walk(directory):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        # Check each file
        for file in files:
            file_path = Path(root) / file
            
            # Skip files without extensions we care about
            if file_extensions and not any(file.endswith(ext) for ext in file_extensions):
                continue
                
            line_count = count_lines(file_path)
            if line_count > max_lines:
                large_files.append((file_path, line_count))
                
    return large_files


def format_results(results: List[Tuple[Path, int]], base_dir: Path) -> str:
    """Format scan results into a readable string.
    
    Args:
        results: List of (file_path, line_count) tuples
        base_dir: Base directory to make paths relative to
        
    Returns:
        Formatted result string
    """
    if not results:
        return "No files exceeding the line limit were found. All good! 👍"
        
    formatted_results = [
        f"Found {len(results)} file(s) exceeding the line limit:"
    ]
    
    # Sort by line count (largest first)
    sorted_results = sorted(results, key=lambda x: x[1], reverse=True)
    
    for file_path, line_count in sorted_results:
        try:
            relative_path = file_path.relative_to(base_dir)
        except ValueError:
            relative_path = file_path
        formatted_results.append(f"  - {relative_path}: {line_count} lines")
        
    return "\n".join(formatted_results)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Scan for files exceeding a line count limit')
    parser.add_argument(
        '--dir', type=str, default='.',
        help='Directory to scan (default: current directory)'
    )
    parser.add_argument(
        '--max-lines', type=int, default=500,
        help='Maximum acceptable line count (default: 500)'
    )
    parser.add_argument(
        '--ignore', type=str, nargs='+', default=None,
        help='Directory names to ignore (in addition to defaults)'
    )
    parser.add_argument(
        '--extensions', type=str, nargs='+', default=None,
        help='File extensions to scan (default: common code file extensions)'
    )
    args = parser.parse_args()

    base_dir = Path(args.dir).resolve()
    
    ignore_dirs = {'.git', '.pytest_cache', '__pycache__', '.venv', 'venv', 'node_modules', '.hypothesis'}
    if args.ignore:
        ignore_dirs.update(args.ignore)
        
    file_extensions = None
    if args.extensions:
        file_extensions = set(ext if ext.startswith('.') else f'.{ext}' for ext in args.extensions)
    
    print(f"Scanning {base_dir} for files with more than {args.max_lines} lines...")
    large_files = scan_directory(
        base_dir, 
        max_lines=args.max_lines,
        ignore_dirs=ignore_dirs,
        file_extensions=file_extensions
    )
    
    print(format_results(large_files, base_dir))
    
    # Return non-zero exit code if large files were found
    return 1 if large_files else 0


if __name__ == '__main__':
    exit(main()) 