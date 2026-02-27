
import sys
import os

# Add the current directory to sys.path
sys.path.append(os.getcwd())

print("Attempting to import app.main...")
try:
    import app.main
    print("Successfully imported app.main")
except Exception as e:
    print(f"Failed to import app.main: {e}")
    import traceback
    traceback.print_exc()
