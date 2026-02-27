
import sys
import os
import threading
import time
import importlib

# Add the /code directory to sys.path
sys.path.append("/code")

def watchdog():
    time.sleep(10)
    print("WATCHDOG: Import timed out under 10s!")
    os._exit(1)

t = threading.Thread(target=watchdog, daemon=True)
t.start()

print(f"Propagating sys.path: {sys.path}")

agents = [
    "app.agents.financial",
    "app.agents.content",
    "app.agents.strategic",
    "app.agents.sales",
    "app.agents.marketing",
    "app.agents.operations",
    "app.agents.hr",
    "app.agents.compliance",
    "app.agents.customer_support",
    "app.agents.data",
]

for agent in agents:
    print(f"Importing {agent}...")
    try:
        importlib.import_module(agent)
        print(f"Done importing {agent}")
    except Exception as e:
        print(f"Failed to import {agent}: {e}")
