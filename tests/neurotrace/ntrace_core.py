import inspect
import json
import logging
import os
import types
from datetime import datetime
from functools import update_wrapper
from pathlib import Path
from typing import Any, Callable, TypeVar, Union

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader


# Configure environment
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
# Configure typevar for bound methods
F = TypeVar("F", bound=Callable)


# Dynamic decorator
def decorate_class_methods(cls, method_names):
    for name in method_names:
        if hasattr(cls, name) and isinstance(getattr(cls, name), types.FunctionType):
            original_method = getattr(cls, name)
            decorated_method = NeuroTrace(original_method)
            setattr(cls, name, decorated_method)


class NeuroTrace:
    """
    A decorator class that records the invocation of functions or methods and
    generates a pytest file for the recorded invocation.
    """

    def __init__(self, func: Callable):
        logger.debug(f"NeuroTracing function: {func.__name__}")
        self.decorated_function = func
        update_wrapper(self, func)

        self.base_dir = Path(__file__).parent
        self.templates_dir = self.create_dir(os.getenv("NEUROTRACE_TEMPLATES_DIR"))
        self.pytests_dir = self.create_dir(os.getenv("NEUROTRACE_PYTESTS_DIR"))
        self.recordings_dir = self.create_dir(os.getenv("NEUROTRACE_RECORDINGS_DIR"))
        self.gen_params = self.create_dir(os.getenv("NEUROTRACE_PARAMS_DIR"))

    def create_dir(self, name: str) -> Path:
        """Create a directory if it doesn't exist and return its Path object."""
        directory = self.base_dir.joinpath(name)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def __call__(self, *args, **kwargs) -> Any:
        func_self = args[0] if self._is_method() else None
        caller_frame = inspect.stack()[1]
        caller_info = {
            "caller_file": caller_frame.filename,
            "caller_name": caller_frame.function,
            "caller_module": inspect.getmodule(caller_frame[0]).__name__,
        }
        class_name = func_self.__class__.__name__ if func_self else None

        try:
            result = self.decorated_function(*args, **kwargs)
            success = True
        except Exception as e:
            result = str(e)
            success = False
            logger.debug(e)

        self._record_and_generate_file(args, kwargs, caller_info, class_name, result, success)
        if not success:
            raise

        return result

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return lambda *args, **kwargs: self.__call__(instance, *args, **kwargs)

    def _is_method(self) -> bool:
        """Check if the decorated function is actually a method of a class."""
        return inspect.ismethod(self.decorated_function) or "." in self.decorated_function.__qualname__

    @staticmethod
    def get_module_path(func) -> str:
        """Get the module import path for a given function or method."""
        module = inspect.getmodule(func)
        module_file_path = Path(module.__file__).resolve()
        package_root_path = Path(__file__).resolve().parents[2]
        relative_path = module_file_path.relative_to(package_root_path)
        logger.debug(f"Module filesystem path: {module_file_path}")
        return relative_path.as_posix().rstrip(".py").replace("/", ".")

    def _record_and_generate_file(
        self,
        args: tuple,
        kwargs: dict,
        caller_info: dict,
        class_name: Union[str, None],
        result: Any,
        success: bool,
    ) -> None:
        """Handles recording the function or method call and generating a pytest file."""
        logger.debug("record_and_generate invoked")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        func_identifier = f"{class_name + '_' if class_name else ''}{self.decorated_function.__name__}"
        recording_filename = f"record_{func_identifier}_{timestamp}.json"
        recording_file_path = self.recordings_dir.joinpath(recording_filename)

        record = {
            "metadata": caller_info,
            "class_name": class_name,
            "function_name": self.decorated_function.__name__,
            "arguments": {"args": args, "kwargs": kwargs},
            "success": success,
            "result": result,
        }

        with open(recording_file_path, "w") as rf:
            json.dump(record, rf, default=str, indent=4)

        self._generate_pytest_file(args, kwargs, class_name, recording_filename, success, func_identifier, timestamp)

    def _generate_pytest_file(self, args: tuple, kwargs: dict, class_name: str, recording_filename: str,
                             success: bool, func_identifier: str, timestamp: str) -> None:
        """Generate the pytest file from template."""
        env = Environment(loader=FileSystemLoader(self.templates_dir))
        template = env.get_template("recorded_class_method_test.j2")
        arg_list = [repr(arg) for arg in args] + [f"{k}={repr(v)}" for k, v in kwargs.items()]
        params_dict = {
            "module_name": class_name,
            "module_path": self.get_module_path(self.decorated_function),
            "func_name": func_identifier,
            "invocation": f"{self.decorated_function.__name__}({', '.join(arg_list)})",
            "recording_filename": recording_filename,
            "success": success,
            "metadata": {
                "test_id": timestamp,
                "test_file_name": f"test_{func_identifier}_{timestamp}.py",
                "gen_date": datetime.now().strftime("%m/%d/%Y"),
                "github_user": os.environ.get("GITHUB_USER"),
            },
        }

        # write params_dict to file for observability and debugging
        test_params_path = self.gen_params.joinpath(
            f"params_{class_name + '_' if class_name else ''}{self.decorated_function.__name__}_{timestamp}.json"
        )
        with open(test_params_path, "w") as fg:
            json.dump(params_dict, fg, default=str, indent=4)

        # now generate the test
        test_content = template.render(**params_dict)
        test_file_path = self.pytests_dir.joinpath(params_dict["metadata"]["test_file_name"])
        with open(test_file_path, "w") as tf:
            tf.write(test_content)
