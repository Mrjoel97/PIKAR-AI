import app.agents.strategic.tools
import inspect

for name, obj in inspect.getmembers(app.agents.strategic.tools):
    print(f"{name}: {obj}")
