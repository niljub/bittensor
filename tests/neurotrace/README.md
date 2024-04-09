# NeuroTrace Test Suite for Bittensor

The NeuroTrace test suite for Bittensor leverages a record/replay strategy, akin to the VCR technique, to facilitate rapid and comprehensive unit testing across Bittensor's extensive and intricate classes. This approach records the inputs and outputs of functions or methods, subsequently generating tailored pytests based on this data.

## Getting Started

To set up and utilize a generator for creating these tests, follow the steps below:

### Prerequisites

Make sure that you have a virtual environment with the required packages installed.
```bash
cd path/to/neurotrace
python3 -m venv venv
. venv/bin/activate
pip install -e .
```

### Configuration

Rename `example.testenv` to `.testenv` and populate it with the necessary values corresponding to your environment setup.

### Creating a Test Generator

2. Within the directory specified by `GENERATORS_PATH`, create a Python file with a descriptive name, such as `generate_subtensor_tests.py`, to generate tests for the subtensor functionality.

3. Begin by importing the class or module that you intend to test.

4. Incorporate the NeuroTrace core decorator into your generator script:
```python
from ..ntrace_core import decorate_class_methods
```

5. Compile a list of the class methods you wish to cover with tests. For instance:
```python
methods_to_decorate = [
   "get_all_subnets_info",
   "get_subnet_info",
]
```

6. Define an `enable_generators` function within your script. This function should invoke `decorate_class_methods(classname, methods_to_decorate)`, as shown in the example below:
```python
def enable_generator():
   decorate_class_methods(subtensor, methods_to_decorate)
```

### Alternate Method

NeuroTrace may also be used directly within your code as a decorator. Simply import NeuroTrace and decorate the method or function that you wish to cover with tests and invoke it as normal. NeuroTrace will automatically generate the recording and pytest file with the appropriate class/method/function import and the test.
```python
@NeuroTrace
def some_method(self, stuff, things):
    ...
```




### Generating Tests with Btcli Invocation

7. Before running `btcli`, set the following environment variables to enable test generation:
```shell
export BTCLI_NTRACE_MODE=1
export NTRACE_GEN_MODE=1
export NTRACE_GEN_ENABLE=<ALL or comma-separated generator names without the .py>
```

8. Execute `btcli` with the commands that interact with the target methods. This will generate test files in the `NEUROTRACE` directories, as defined in your `.testenv` file. Note that multiple files may be generated for a single method if it is invoked multiple times during this process.


### Generating Tests with Programmatic Invocation

I haven't figured out the details of this yet, however, you'll just need to ensure that either your target methods are decorated directly or dynamically (using decorate_class_methods), and then invoke them.


### Running Tests

After generation, the pytest framework can run the generated test files, ~~or you can opt to use NeuroTest for execution~~.
For now, you'll need to manually create mocks for certain network calls. Future versions will autogenerate mocks.

This setup streamlines the process of creating and managing a broad suite of unit tests for Bittensor developers aiming to ensure robustness and reliability in their code.
