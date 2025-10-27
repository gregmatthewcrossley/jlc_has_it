#!/usr/bin/env python3
"""
Claude Code statusline script for monitoring pytest progress.
Displays live test statistics from the background test run.
"""

import json
import sys
import os
import re
from pathlib import Path
from collections import defaultdict

# Cache for test stats to avoid repeated file parsing
_cached_stats = None
_cached_mtime = None

def get_test_stats():
    """Extract test statistics from pytest cache or output."""
    global _cached_stats, _cached_mtime

    try:
        # Try to read pytest cache directory
        cache_dir = Path.cwd() / ".pytest_cache"
        if not cache_dir.exists():
            return None

        # Get the most recent .pytest_cache file timestamp
        try:
            cache_mtime = max(f.stat().st_mtime for f in cache_dir.rglob("*") if f.is_file())
        except (ValueError, OSError):
            return None

        # Return cached result if file hasn't changed
        if _cached_stats is not None and _cached_mtime == cache_mtime:
            return _cached_stats

        # Look for pytest output or status files
        # The conftest.py hook writes test stats, we can check if there's a status file
        status_file = Path.cwd() / ".pytest_cache" / "test_status.txt"
        if status_file.exists():
            try:
                content = status_file.read_text()
                # Parse format: "PASSED:50 FAILED:2 SKIPPED:1"
                stats = defaultdict(int)
                for part in content.strip().split():
                    if ':' in part:
                        key, val = part.split(':')
                        stats[key] = int(val)
                if stats:
                    _cached_stats = dict(stats)
                    _cached_mtime = cache_mtime
                    return _cached_stats
            except (OSError, ValueError):
                pass

        return None
    except Exception:
        return None

def parse_statusline_input():
    """Parse JSON input from Claude Code statusline."""
    try:
        data = json.loads(sys.stdin.read())
        return data
    except (json.JSONDecodeError, EOFError):
        return {}

def format_test_stats(stats):
    """Format test statistics for display."""
    if not stats:
        return None

    passed = stats.get('PASSED', 0)
    failed = stats.get('FAILED', 0)
    skipped = stats.get('SKIPPED', 0)
    total = passed + failed + skipped

    if total == 0:
        return None

    # Calculate percentage
    pct = (passed / total * 100) if total > 0 else 0

    # Build the test status string
    test_str = f"🧪 [{passed + failed + skipped}/{total}] "

    if failed > 0:
        test_str += f"✓{passed} ✗{failed}"
    else:
        test_str += f"✓{passed}"

    if skipped > 0:
        test_str += f" ⊘{skipped}"

    return test_str

def format_statusline(session_info):
    """Format the statusline display."""
    pwd = session_info.get('pwd', os.getcwd())
    git_branch = session_info.get('git_branch', '')
    model = session_info.get('model', '')

    # Build statusline components
    parts = []

    # Add model indicator (compact form)
    if model:
        # Extract just the model name (e.g., "claude-haiku" from full path)
        model_name = model.split('/')[-1] if '/' in model else model
        # Shorten if too long
        if len(model_name) > 20:
            model_name = model_name[:17] + "..."
        parts.append(f"🤖 {model_name}")

    # Add git branch if available
    if git_branch:
        parts.append(f"🌿 {git_branch}")

    # Add working directory (last component)
    if pwd:
        dir_name = pwd.split('/')[-1] or pwd
        parts.append(f"📁 {dir_name}")

    # Check for test statistics
    test_stats = get_test_stats()
    if test_stats:
        test_str = format_test_stats(test_stats)
        if test_str:
            parts.append(test_str)

    # Return formatted statusline
    if parts:
        return ' | '.join(parts)
    else:
        # Fallback to minimal display
        return "Claude Code"

def main():
    """Main statusline entry point."""
    session_info = parse_statusline_input()
    statusline = format_statusline(session_info)
    print(statusline)

if __name__ == '__main__':
    main()
