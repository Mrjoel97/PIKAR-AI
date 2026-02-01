
import os
import re
import sys
import subprocess
import json
from enum import Enum
from typing import Optional, Tuple, List, Dict

# Configuration
PLAN_FILE_NAME = "plan.md"
METADATA_FILE_NAME = "metadata.json"
TRACKS_DIR = os.path.join("conductor", "tracks")

class TaskStatus(Enum):
    TODO = "[ ]"
    IN_PROGRESS = "[~]"
    DONE = "[x]"

def get_active_track_path() -> Optional[str]:
    """Finds the active track directory based on metadata.json status."""
    if not os.path.exists(TRACKS_DIR):
        print(f"Error: Tracks directory not found at {TRACKS_DIR}")
        return None

    for entry in os.scandir(TRACKS_DIR):
        if entry.is_dir():
            metadata_path = os.path.join(entry.path, METADATA_FILE_NAME)
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r') as f:
                        data = json.load(f)
                        # print(f"DEBUG: Checking {entry.name}, status={data.get('status')}")
                        if data.get("status") == "active":
                            return entry.path
                except Exception as e:
                    print(f"Warning: Failed to read metadata for {entry.name}: {e}")
    return None

def find_plan_file() -> Optional[str]:
    """Locates the plan.md for the currently active track."""
    track_path = get_active_track_path()
    if not track_path:
        print("Error: No active track found in conductor/tracks/")
        return None
    
    plan_path = os.path.join(track_path, PLAN_FILE_NAME)
    if not os.path.exists(plan_path):
        print(f"Error: plan.md not found in active track: {plan_path}")
        return None
    
    return plan_path

def run_git_command(args: List[str]) -> Tuple[bool, str]:
    """Executes a git command and returns success/output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()

def start_task():
    """Finds next TODO task and marks it IN_PROGRESS."""
    plan_path = find_plan_file()
    if not plan_path: return

    print(f"DEBUG: Loading plan from {plan_path}")
    with open(plan_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 1. Check if ANY task is already in progress
    for i, line in enumerate(lines):
        if TaskStatus.IN_PROGRESS.value in line:
            print(f"Error: A task is already in progress at line {i+1}:")
            print(line.strip())
            print("Implementation Rule: WIP limit is 1. Complete or revert current task first.")
            return

    # 2. Find next TODO
    task_index = -1
    task_line = ""
    for i, line in enumerate(lines):
        if TaskStatus.TODO.value in line:
            task_index = i
            task_line = line
            break
    
    if task_index == -1:
        print("No pending tasks found in current plan.")
        return

    # 3. Update status
    updated_line = task_line.replace(TaskStatus.TODO.value, TaskStatus.IN_PROGRESS.value)
    lines[task_index] = updated_line
    
    with open(plan_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"Successfully started task:\n{updated_line.strip()}")
    
    # Verify Skills Registry
    try:
        sys.path.append(os.getcwd())
        from app.skills import skills_registry
        skill_count = len(skills_registry.list_all())
        print(f"\n[Conductor] Skills Registry Verification: Passed")
        print(f"[Conductor] Active Skills Loaded: {skill_count}")
        print(f"[Conductor] System enhanced with {skill_count} domain capabilities.")
    except Exception as e:
        print(f"\n[Conductor] Skills Registry Verification: FAILED")
        print(f"Error loading skills: {str(e)}")

def complete_task(summary: str, why: str):
    """Commits work, adds git note, and updates plan with completion SHA."""
    plan_path = find_plan_file()
    if not plan_path: return

    # 1. Verify we have a task in progress
    with open(plan_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    task_index = -1
    task_text = ""
    for i, line in enumerate(lines):
        if TaskStatus.IN_PROGRESS.value in line:
            task_index = i
            task_text = line
            break
            
    if task_index == -1:
        print("Error: No task is currently marked IN_PROGRESS [~]. Cannot complete.")
        return

    # 2. Add all changes and commit
    success, _ = run_git_command(["add", "."])
    if not success:
        print("Error: Failed to stage files.")
        return

    # Extract task name for commit message (simplified)
    # "[~] Task Name" -> "Task Name"
    # Regex to capture content after [~]
    match = re.search(r'\[~\]\s*(.*)', task_text)
    task_name = match.group(1).strip() if match else "task"
    
    commit_msg = f"feat: {task_name}"
    success, output = run_git_command(["commit", "-m", commit_msg])
    if not success:
        if "nothing to commit" in output:
            print("Error: No changes to commit.")
            return
        print(f"Error executing commit: {output}")
        return

    # 3. Get SHA
    success, sha = run_git_command(["log", "-1", "--format=%H"])
    if not success: return
    short_sha = sha[:7]

    # 4. Add Git Note
    note_content = f"Task: {task_name}\n\nSummary:\n{summary}\n\nWhy:\n{why}"
    success, output = run_git_command(["notes", "add", "-m", note_content, sha])
    if not success:
        print(f"Error adding git note: {output}")
        return

    # 5. Update Plan
    # Replace [~] with [x] and append SHA
    # Example: "- [~] Task A" -> "- [x] Task A [bc30dc7]"
    final_line = task_text.replace(TaskStatus.IN_PROGRESS.value, TaskStatus.DONE.value).rstrip()
    final_line = f"{final_line} [{short_sha}]\n"
    lines[task_index] = final_line

    with open(plan_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    # 6. Commit Plan Update
    run_git_command(["add", plan_path])
    run_git_command(["commit", "-m", f"conductor(plan): Mark task '{task_name[:30]}...' as complete"])

    print(f"Task completed successfully. Plan updated with SHA {short_sha}.")

def usage():
    print("Usage: python task_manager.py <command> [args]")
    print("Commands:")
    print("  start             - Marks next [ ] task as [~]")
    print("  complete \"summary\" \"why\" - Commits, notes, and marks [x]")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
        
    command = sys.argv[1]
    
    if command == "start":
        start_task()
    elif command == "complete":
        if len(sys.argv) < 4:
            print("Error: complete requires summary and why arguments")
            usage()
            sys.exit(1)
        complete_task(sys.argv[2], sys.argv[3])
    else:
        usage()
