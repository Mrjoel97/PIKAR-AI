
print("Starting import test...")
try:
    print("Importing app.fast_api_app...")
    from app.fast_api_app import app
    print("Import Successful!")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
print("Test finished.")
