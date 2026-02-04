
import sys
import os
# Ensure CWD is in path to favor local
sys.path.insert(0, os.getcwd())

import app
import app.routers.onboarding

print(f"CWD: {os.getcwd()}")
print(f"app file: {app.__file__}")
print(f"onboarding file: {app.routers.onboarding.__file__}")
