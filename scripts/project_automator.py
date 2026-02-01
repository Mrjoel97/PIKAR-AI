#!/usr/bin/env python3
"""
Project Automator - Intelligent wrapper for Pikar-Ai Conductor Workflow.

This script automates the project management workflow by wrapping the strict
engineering protocols defined in `conductor_task` and `conductor_phase` skills.

Features:
- NLP Task Selection: Finds relevant tasks in plan.md using keyword matching.
- Automated Workflow: Start -> Test -> Commit -> Note -> Plan Update -> Push.
- Active Track Detection: Automatically finds the active track.
"""

import os
import sys
import subprocess
import json
import difflib
import re
from typing import Optional, List, Tuple

# Add the skills directory to path to import task_manager if needed
# But for stability, we will invoke the scripts as subprocesses or import logic directly if possible.
# Given the complex relative paths, we will re-implement the core "Find & Update" logic here
# but call the 'verify' steps via standard commands.

# Configuration
CONDUCTOR_DIR = "conductor"
TRACKS_DIR = os.path.join(CONDUCTOR_DIR, "tracks")
METADATA_FILE = "metadata.json"
PLAN_FILE = "plan.md"

def run_command(command: List[str], cwd: str = None) -> Tuple[bool, str]:
    """Runs a shell command."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False
        )
        if result.returncode != 0:
            return False, result.stderr.strip() + "\n" + result.stdout.strip()
        return True, result.stdout.strip()
    except Exception as e:
        return False, str(e)

def get_active_track() -> Optional[str]:
    """Finds the directory of the currently active track."""
    if not os.path.exists(TRACKS_DIR):
        print(f"Error: Tracks directory not found at {TRACKS_DIR}")
        return None

    for entry in os.scandir(TRACKS_DIR):
        if entry.is_dir():
            metadata_path = os.path.join(entry.path, METADATA_FILE)
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r') as f:
                        data = json.load(f)
                        if data.get("status") == "active":
                            return entry.path
                except Exception:
                    continue
    return None

def find_task_in_plan(plan_path: str, instruction: str) -> Tuple[Optional[int], Optional[str]]:
    """Finds the best matching TODO task in plan.md based on instruction."""
    if not os.path.exists(plan_path):
        return None, None

    with open(plan_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    todos = []
    for i, line in enumerate(lines):
        if "[ ]" in line:
            # Extract task text for comparison
            # Remove "- [ ] " and markdown links/formatting
            clean_text = line.replace("- [ ]", "").strip()
            clean_text = re.sub(r'\[.*?\]\(.*?\)', '', clean_text) # Remove links
            todos.append((i, clean_text, line))

    if not todos:
        return None, "No pending tasks found."

    # Simple fuzzy matching
    best_match = None
    best_score = 0.0

    # 1. Exact match (case insensitive)
    for index, text, full_line in todos:
        if instruction.lower() in text.lower():
            return index, full_line

    # 2. Sequence Matcher for similarity
    for index, text, full_line in todos:
        ratio = difflib.SequenceMatcher(None, instruction.lower(), text.lower()).ratio()
        if ratio > best_score:
            best_score = ratio
            best_match = (index, full_line)
    
    # Threshold for "found it" vs "create new"
    if best_score > 0.4:
        return best_match
    
    return None, None

def start_workflow(instruction: str):
    """Starts a task based on NLP instruction."""
    track_path = get_active_track()
    if not track_path:
        print("Error: No active track found.")
        return

    plan_path = os.path.join(track_path, PLAN_FILE)
    if not os.path.exists(plan_path):
        print(f"Error: plan.md not found in {track_path}")
        return

    # Check for WIP
    with open(plan_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if "[~]" in content:
            print("Error: A task is already IN PROGRESS. Please complete or revert it first.")
            return

    index, task_line = find_task_in_plan(plan_path, instruction)

    if index is not None:
        print(f"Found matching task: {task_line.strip()}")
        # Update to [~]
        with open(plan_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        lines[index] = lines[index].replace("[ ]", "[~]")
        
        with open(plan_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"Task started: {task_line.strip()}")
        
    else:
        print(f"No matching task found for: '{instruction}'")
        print("Creating new task...")
        # Append new task to end of plan list
        # We need to find where the list is. Assuming a "Tasks" section or end of file.
        # For simplicity, we append to the end of the file or specific section.
        # This part requires parsing the markdown structure roughly.
        
        with open(plan_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Try to find the last task line to append after
        last_task_index = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("- [") or line.strip().startswith("- [x]"):
                last_task_index = i
        
        new_line = f"- [~] {instruction}\n"
        
        if last_task_index != -1:
            lines.insert(last_task_index + 1, new_line)
        else:
            lines.append(f"\n## Tasks\n{new_line}")
            
        with open(plan_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"Created and started new task: {instruction}")

def complete_workflow(summary: str, why: str, skip_tests: bool = False):
    """Completes the current task: Test -> Commit -> Note -> Plan -> Push."""
    track_path = get_active_track()
    if not track_path:
        print("Error: No active track found.")
        return

    plan_path = os.path.join(track_path, PLAN_FILE)
    
    # 1. Run Tests (Quality Gate)
    if skip_tests:
        print("\n[1/5] Skipping Tests (User override).")
    else:
        print("\n[1/5] Running Tests...")
        
        test_commands = [
            ["make", "test"],
            ["uv", "run", "pytest"],
            ["python", "-m", "pytest"]
        ]
        
        tests_passed = False
        for cmd in test_commands:
            print(f"Trying test command: {' '.join(cmd)}")
            # Use shell=True for Windows command resolution if needed, but try direct first
            # On Windows, 'make' might be a batch file or exe.
            success, output = run_command(cmd)
            if success:
                print("Tests PASSED.")
                tests_passed = True
                break
            else:
                # Check if it was "command not found" (heuristic)
                if "not recognized" in output or "No such file" in output or "system cannot find" in output:
                    continue # Try next
                else:
                    # Real test failure
                    print(f"Tests FAILED with command {' '.join(cmd)}. Aborting.")
                    print(output)
                    return

        if not tests_passed:
            print("Could not run any test commands (make, uv run pytest, python -m pytest). Aborting.")
            return

    # 2. Identify Task
    with open(plan_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    task_index = -1
    task_line = ""
    for i, line in enumerate(lines):
        if "[~]" in line:
            task_index = i
            task_line = line
            break
            
    if task_index == -1:
        print("Error: No task currently IN PROGRESS [~].")
        return

    task_name = task_line.replace("- [~]", "").strip()
    # Remove links for clean name
    task_name_clean = re.sub(r'\[.*?\]\(.*?\)', '', task_name).strip()

    # 3. Commit Code
    print("\n[2/5] Committing Changes...")
    run_command(["git", "add", "."])
    commit_msg = f"feat: {task_name_clean}"
    success, output = run_command(["git", "commit", "-m", commit_msg])
    if not success and "nothing to commit" not in output:
        print(f"Commit failed: {output}")
        return
    elif "nothing to commit" in output:
        print("No code changes to commit (continuing for metadata update).")

    # Get SHA
    success, sha = run_command(["git", "log", "-1", "--format=%H"])
    if not success:
        print("Failed to get commit SHA.")
        return
    short_sha = sha[:7]

    # 4. Attach Git Note
    print("\n[3/5] Attaching Git Note...")
    note_content = f"Task: {task_name_clean}\n\nSummary:\n{summary}\n\nWhy:\n{why}"
    run_command(["git", "notes", "add", "-f", "-m", note_content, sha])

    # 5. Update Plan
    print("\n[4/5] Updating Plan...")
    final_line = task_line.replace("[~]", "[x]").rstrip()
    final_line = f"{final_line} [{short_sha}]\n"
    lines[task_index] = final_line
    
    with open(plan_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
        
    run_command(["git", "add", plan_path])
    run_command(["git", "commit", "-m", f"conductor(plan): Mark task '{task_name_clean[:20]}...' as complete"])

    # 6. Git Push
    print("\n[5/5] Pushing to Remote...")
    success, output = run_command(["git", "push"])
    if success:
        print("Successfully pushed changes.")
    else:
        print(f"Warning: Git push failed (Check credentials/network).\n{output}")

    print(f"\nSUCCESS: Task '{task_name_clean}' completed.")

def usage():
    print("Usage: project_automator.py [command] [args]")
    print("Commands:")
    print("  start <instruction>       - Find/Create task from 'instruction' and mark WIP")
    print("  complete <summary> <why> [skip-tests] - Commit, Note, Plan Update, and Push")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
        
    cmd = sys.argv[1].lower()
    
    if cmd == "start":
        if len(sys.argv) < 3:
            print("Error: Missing instruction.")
            sys.exit(1)
        start_workflow(" ".join(sys.argv[2:]))
        
    elif cmd == "complete":
        if len(sys.argv) < 4:
            print("Error: complete requires <summary> and <why>")
            sys.exit(1)
        skip = False
        if len(sys.argv) > 4 and sys.argv[4] == "skip-tests":
            skip = True
        complete_workflow(sys.argv[2], sys.argv[3], skip_tests=skip)
    else:
        usage()

