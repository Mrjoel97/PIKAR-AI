
import importlib
import sys

modules = [
    "google.adk",
    "google.adk.events",
    "google.adk.models",
    "google.adk.runners",
    "google.adk.sessions",
    "google.adk.artifacts",
    "google.adk.a2a",
]

for mod in modules:
    print(f"Trying to import {mod}...")
    try:
        importlib.import_module(mod)
        print(f"Imported {mod} successfully.")
    except Exception as e:
        print(f"Failed to import {mod}: {e}")

print("Done.")
