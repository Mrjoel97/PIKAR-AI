import inspect
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import TaskEntry

print("Inspecting InMemoryTaskStore...")
print(f"Base classes: {InMemoryTaskStore.__bases__}")

print("\nMethods:")
for name, method in inspect.getmembers(InMemoryTaskStore, predicate=inspect.isfunction):
    print(f"- {name}{inspect.signature(method)}")

print("\nTaskEntry Definition:")
try:
    print(inspect.signature(TaskEntry))
    print(TaskEntry.__annotations__)
except:
    pass
