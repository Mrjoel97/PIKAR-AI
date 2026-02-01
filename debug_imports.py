
import importlib
import sys

modules = [
    "os",
    "google.auth",
    "fastapi",
    "a2a",
    "a2a.server.apps",
    "a2a.server.request_handlers",
    "a2a.types",
    "google.adk",
    "google.adk.runners",
    "app.agent",
    "app.persistence.supabase_task_store",
]

for mod in modules:
    print(f"Trying to import {mod}...")
    try:
        importlib.import_module(mod)
        print(f"Imported {mod} successfully.")
    except Exception as e:
        print(f"Failed to import {mod}: {e}")

print("Done.")
