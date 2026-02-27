# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Run Workflow Worker.

Entry point to start the autonomous workflow executor.
"""

import sys
import os
import asyncio

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.workflows.worker import WorkflowWorker

if __name__ == "__main__":
    print("Starting Pikar-AI Workflow Automation Worker...")
    try:
        worker = WorkflowWorker()
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        print("Worker stopped by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
