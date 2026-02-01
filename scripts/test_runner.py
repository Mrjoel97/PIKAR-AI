#!/usr/bin/env python3
import sys
import subprocess
import os

def run_tests():
    """Runs tests using the best available method."""
    print("Detecting test environment...")
    
    # 1. Try 'make test' (Standard for Unix/CI)
    if os.path.exists("Makefile"):
        try:
            print("Attempting 'make test'...")
            subprocess.run(["make", "test"], check=True)
            return
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("'make test' failed or make not found. Falling back...")

    # 2. Try 'uv run pytest' (If using uv)
    try:
        print("Attempting 'uv run pytest'...")
        subprocess.run(["uv", "run", "pytest"], check=True)
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("'uv' not found or failed. Falling back...")

    # 3. Try 'pytest' (Direct)
    try:
        print("Attempting 'pytest' direct...")
        subprocess.run([sys.executable, "-m", "pytest"], check=True)
        return
    except subprocess.CalledProcessError:
        print("pytest failed.")
        sys.exit(1)
    except Exception as e:
        print(f"Error running pytest: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
