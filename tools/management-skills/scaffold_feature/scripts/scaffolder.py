
import os
import sys

def create_directory(path: str):
    if not os.path.exists(path):
        os.makedirs(path)
        # Ensure __init__.py exists
        with open(os.path.join(path, "__init__.py"), 'w') as f:
            pass

def to_camel_case(snake_str: str) -> str:
    return "".join(x.capitalize() for x in snake_str.lower().split("_"))

def scaffold_feature(feature_name: str, layer: str = "app"):
    """
    Scaffolds a new feature following TDD:
    1. Creates/Verifies tests/unit/test_<feature>.py
    2. Creates/Verifies <layer>/<feature>.py
    """
    
    # Paths
    base_dir = os.getcwd()
    test_dir = os.path.join(base_dir, "tests", "unit")
    impl_dir = os.path.join(base_dir, layer)

    # Ensure directories exist
    create_directory(test_dir)
    create_directory(impl_dir)

    test_file = os.path.join(test_dir, f"test_{feature_name}.py")
    impl_file = os.path.join(impl_dir, f"{feature_name}.py")

    # 1. Create Test File (If not exists)
    if not os.path.exists(test_file):
        class_name = to_camel_case(feature_name)
        content = f"""
import pytest
from {layer}.{feature_name} import {class_name}

def test_{feature_name}_initialization():
    obj = {class_name}()
    assert obj is not None
"""
        with open(test_file, 'w') as f:
            f.write(content.strip() + "\n")
        print(f"[created] {test_file}")
    else:
        print(f"[exists]  {test_file}")

    # 2. Create Implementation File (If not exists)
    if not os.path.exists(impl_file):
        class_name = to_camel_case(feature_name)
        content = f"""
class {class_name}:
    def __init__(self):
        pass
"""
        with open(impl_file, 'w') as f:
            f.write(content.strip() + "\n")
        print(f"[created] {impl_file}")
    else:
        print(f"[exists]  {impl_file}")

    print("\nScaffold complete. Run tests using:")
    print(f"make test")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scaffolder.py <feature_name> [layer]")
        sys.exit(1)
    
    name = sys.argv[1]
    layer = sys.argv[2] if len(sys.argv) > 2 else "app"
    
    scaffold_feature(name, layer)
