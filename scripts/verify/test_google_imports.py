import sys
print("Importing google.auth...")
try:
    import google.auth
    print("Imported google.auth")
except Exception as e:
    print(f"Error importing google.auth: {e}")

print("Importing google.genai...")
try:
    import google.genai
    print("Imported google.genai")
except Exception as e:
    print(f"Error importing google.genai: {e}")

print("Done.")
