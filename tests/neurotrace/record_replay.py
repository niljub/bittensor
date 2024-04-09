import logging
from functools import update_wrapper
import inspect
import json
from datetime import datetime
from pathlib import Path
from typing import Union, Callable, TypeVar
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
import os

# Configure environment
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
github_user = os.getenv("GITHUB_USER")
# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable)


class NeuroTrace:
    """
    A decorator class that records the invocation of functions or methods and
    generates a pytest file for the recorded invocation.
    """

    def __init__(self, func: F):
        print(f"Decorating function: {func.__name__}")
        self.decorated_function = func
        update_wrapper(self, func)
        self.templates_dir = Path(__file__).parent.joinpath("templates")
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.recordings_dir = Path(__file__).parent.joinpath("recordings")
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.pytests_dir = Path(__file__).parent.joinpath("tests")
        self.pytests_dir.mkdir(parents=True, exist_ok=True)
        self.generator_src = Path(__file__).parent.joinpath("tests/source")
        self.generator_src.mkdir(parents=True, exist_ok=True)

    def __call__(self, *args, **kwargs) -> Any:
        print("__call__ invoked")
        # Function or method call handling logic
        func_self = args[0] if self._is_method() else None
        caller_frame = inspect.stack()[1]
        caller_module = inspect.getmodule(caller_frame[0])
        caller_info = {
            "caller_file": caller_frame.filename,
            "caller_name": caller_frame.function,
            "caller_module": caller_module.__name__ if caller_module else None,
        }
        class_name = func_self.__class__.__name__ if func_self else None
        print("call before trys")
        try:
            result = self.decorated_function(*args, **kwargs)
            success = True
        except Exception as e:
            result = str(e)
            success = False
            print(e)

        # Generate Pytest file after recording
        print("before record and generate")
        self._record_and_generate_file(
            args, kwargs, caller_info, class_name, result, success
        )

        if not success:
            print("not success")
            raise
        print("before return")
        return result

    def __get__(self, instance, owner):
        print("__get__ invoked")
        if instance is None:
            return self

        def bound(*args, **kwargs):
            return self.__call__(instance, *args, **kwargs)

        return bound

    def _is_method(self) -> bool:
        """
        Check if the decorated function is actually a method of a class.
        """
        print("_is_method invoked")
        return (
            inspect.ismethod(self.decorated_function)
            or "." in self.decorated_function.__qualname__
        )

    @staticmethod
    def get_module_path(func):
        """Get the module import path for a given function or method."""
        module = inspect.getmodule(func)
        if module is None or module.__file__ is None:
            raise ValueError(f"Cannot determine the module for {func}")

        # Path to the module file
        module_file_path = Path(module.__file__).resolve()
        # Bittensor root
        package_root_path = Path(__file__).resolve().parents[2]
        # Calculate the relative path from the package root to the module file
        relative_path = module_file_path.relative_to(package_root_path)
        # Convert to module path
        module_path = relative_path.as_posix().rstrip(".py").replace("/", ".")
        return module_path

    def _record_and_generate_file(
        self,
        args: tuple,
        kwargs: dict,
        caller_info: dict,
        class_name: Union[str, None],
        result: Any,
        success: bool,
    ) -> None:
        """
        Handles recording the function or method call and generating a pytest file.
        """
        print("record_and_generate invoked")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        func_identifier = f"{class_name + '_' if class_name else ''}{self.decorated_function.__name__}"
        test_file_name = f"test_{func_identifier}_{timestamp}.py"
        print(f"Test file name: {test_file_name}")
        recording_filename = f"record_{func_identifier}_{timestamp}.json"
        print(f"Recording file name: {recording_filename}")
        recording_file_path = self.recordings_dir.joinpath(recording_filename)
        print(f"recording file path: {recording_file_path}")

        try:
            record = {
                "metadata": caller_info,
                "class_name": class_name,
                "function_name": self.decorated_function.__name__,
                "arguments": {"args": args, "kwargs": kwargs},
                "success": success,
                "result": result,
            }
            print("before write recording")
            with open(recording_file_path, "w") as f:
                json.dump(record, f, default=str, indent=4)
        except Exception as e:
            print(f"Error recording function call: {e}")
        finally:
            print(f"successfully wrote recording to {recording_file_path}")

        try:
            print("before generate pytest file")
            env = Environment(loader=FileSystemLoader(self.templates_dir))
            template = env.get_template("recorded_class_method_test.j2")

            arg_list = [repr(arg) for arg in args] + [
                f"{k}={repr(v)}" for k, v in kwargs.items()
            ]
            call_args = ", ".join(arg_list)
            invocation = f"{self.decorated_function.__name__}({call_args})"

            module_path = self.get_module_path(self.decorated_function)
            test_id = recording_filename.split("_")[-1].split(".")[0]
            params_dict = {
                "module_name": class_name,
                "module_path": module_path,
                "func_name": f"{class_name + '_' if class_name else ''}{self.decorated_function.__name__}",
                "invocation": invocation,
                "recording_filename": recording_filename,
                "success": success,
                "metadata": {
                    "test_id": test_id,
                    "github_user": github_user,
                    "test_file_name": test_file_name,
                    "gen_date": datetime.now().strftime("%m/%d/%Y"),
                },
            }
            # for debugging
            test_generator_source_path = self.generator_src.joinpath(
                f"gensrc_{class_name + '_' if class_name else ''}{self.decorated_function.__name__}_{test_id}.json"
            )
            with open(test_generator_source_path, "w") as fg:
                json.dump(params_dict, fg, default=str, indent=4)
            # now generate the test
            test_content = template.render(**params_dict)
            test_file_path = self.pytests_dir.joinpath(test_file_name)
            try:
                print(f"Writing TEST {test_file_path}")
                with open(test_file_path, "w") as tf:
                    tf.write(test_content)
            except Exception as e:
                print(f"Error writing test file {test_file_path} {e}")
            finally:
                print(f"Successfully wrote pytest to {test_file_path}")
        except Exception as e:
            print(f"Error generating pytest file: {e}")
