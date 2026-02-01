
import os
import sys
import subprocess
import json
import re
from typing import Optional, List, Tuple

# Re-use logic from task_manager if possible, but keep independent for now to avoid circular deps
PLAN_FILE_NAME = "plan.md"
METADATA_FILE_NAME = "metadata.json"
TRACKS_DIR = os.path.join("conductor", "tracks")

def run_git_command(args: List[str]) -> Tuple[bool, str]:
    try:
        result = subprocess.run(["git"] + args, capture_output=True, text=True, check=True)
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()

def get_active_track_path() -> Optional[str]:
    if not os.path.exists(TRACKS_DIR): return None
    for entry in os.scandir(TRACKS_DIR):
        if entry.is_dir():
            metadata_path = os.path.join(entry.path, METADATA_FILE_NAME)
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r') as f:
                        data = json.load(f)
                        if data.get("status") == "active": return entry.path
                except: pass
    return None

def find_previous_checkpoint(plan_path: str) -> str:
    """Scans plan.md reverse to find the last [checkpoint: <sha>] or returns first commit."""
    # 1. Try to find last checkpoint in plan
    try:
        with open(plan_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        matches = list(re.finditer(r'\[checkpoint:\s*([a-f0-9]+)\]', content))
        if matches:
            return matches[-1].group(1)
    except: pass

    # 2. Fallback: First commit
    success, sha = run_git_command(["rev-list", "--max-parents=0", "HEAD"])
    if success: return sha
    return "HEAD" # Should not happen in valid repo

def audit_changes():
    """Generates a list of changed files since last checkpoint."""
    track_path = get_active_track_path()
    if not track_path:
        print("Error: No active track found.")
        return

    plan_path = os.path.join(track_path, PLAN_FILE_NAME)
    prev_sha = find_previous_checkpoint(plan_path)
    
    success, output = run_git_command(["diff", "--name-only", prev_sha, "HEAD"])
    if not success:
        print(f"Error running git diff: {output}")
        return

    print(f"Audit Report (Changes since {prev_sha}):")
    print("----------------------------------------")
    print(output)
    print("----------------------------------------")
    print("Verify that all code files above have corresponding tests.")

def create_checkpoint(summary: str):
    """Creates an empty checkpoint commit and updates plan."""
    track_path = get_active_track_path()
    if not track_path: return
    plan_path = os.path.join(track_path, PLAN_FILE_NAME)

    # 1. Audit to get content for note
    prev_sha = find_previous_checkpoint(plan_path)
    _, diff_output = run_git_command(["diff", "--name-only", prev_sha, "HEAD"])

    # 2. Create Empty Commit
    commit_msg = f"conductor(checkpoint): {summary}"
    success, output = run_git_command(["commit", "--allow-empty", "-m", commit_msg])
    if not success:
        print(f"Error creating checkpoint: {output}")
        return

    # 3. Get SHA
    success, sha = run_git_command(["log", "-1", "--format=%H"])
    if not success: return
    short_sha = sha[:7]

    # 4. Attach Note
    note_content = f"Phase Checkpoint\n\nSummary: {summary}\n\nChanged Files:\n{diff_output}"
    run_git_command(["notes", "add", "-m", note_content, sha])

    # 5. Update Plan - Append checkpoint marker
    # We append it to the end of the Phase block? 
    # For now, append to the file end or user guidance location. 
    # Actually, workflow says "find heading for completed phase and append".
    # Simplified: Append to end of file for now, user can move it if strictly needed.
    
    with open(plan_path, 'a', encoding='utf-8') as f:
        f.write(f"\n\n## Phase Checkpoint [checkpoint: {short_sha}]\n")
        f.write(f"**Summary**: {summary}\n")

    # 6. Commit Plan
    run_git_command(["add", plan_path])
    run_git_command(["commit", "-m", f"conductor(plan): Record checkpoint {short_sha}"])
    
    print(f"Checkpoint created: {short_sha}")

def usage():
    print("Usage: python phase_manager.py <command> [args]")
    print("Commands:")
    print("  audit             - List changes since last checkpoint")
    print("  checkpoint \"msg\"  - Create checkpoint commit and update plan")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
        
    command = sys.argv[1]
    if command == "audit":
        audit_changes()
    elif command == "checkpoint":
        if len(sys.argv) < 3:
            print("Error: checkpoint requires summary message")
            sys.exit(1)
        create_checkpoint(sys.argv[2])
    else:
        usage()
