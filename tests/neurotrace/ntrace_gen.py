import os
import importlib.util
from pathlib import Path
from dotenv import load_dotenv

load_dotenv('.testenv')


# Path to the generators directory
generators_path_env = os.getenv('GENERATORS_PATH')
if not generators_path_env:
    raise ValueError("The environment variable 'GENERATORS_PATH' is not set.")

# Convert to a Path object
generators_path = Path(generators_path_env)
# Check if the path is absolute
if not generators_path.is_absolute():
    # If it's relative, prepend the current working directory
    generators_path = Path.cwd() / generators_path

# Iterate over all .py files in the generators directory
for file in generators_path.glob('*.py'):
    # Skip __init__.py
    if file.name == '__init__.py':
        continue

    # Create a module name from the file name
    module_name = file.stem
    # Create the module spec
    spec = importlib.util.spec_from_file_location(module_name, file)
    # Create and load the module from the spec
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    enabled_generators = os.getenv("NTRACE_GEN_ENABLE")
    if enabled_generators == "ALL" or module_name in enabled_generators.split(","):
        if hasattr(module, 'enable_generator'):
            module.enable_generator()
            print(f"NeuroTrace Enabled: {module_name}")

