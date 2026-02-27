import inspect
from a2a.server.tasks import InMemoryTaskStore

print("Inspecting InMemoryTaskStore...")
print(f"Base classes: {InMemoryTaskStore.__bases__}")

# Get the base class (Protocol)
TaskStoreProtocol = InMemoryTaskStore.__bases__[0]
print(f"Protocol: {TaskStoreProtocol}")

print("\nProtocol Methods:")
for name, method in inspect.getmembers(TaskStoreProtocol, predicate=inspect.isfunction):
    print(f"- {name}{inspect.signature(method)}")

print("\nInMemory Implementation:")
for name, method in inspect.getmembers(InMemoryTaskStore, predicate=inspect.isfunction):
    if not name.startswith("_"):
        print(f"- {name}{inspect.signature(method)}")
