import inspect
import json
import os
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Type


class RRController:
    @staticmethod
    def record(func: Callable) -> Callable:
        """
        Decorator method for recording the invocation of functions or methods,
        including input arguments, return values, and exceptions. The records
        are saved as JSON files, named to reflect the context of the call, and
        contain metadata about the caller and the function itself.

        Args:
            func (Callable): The function to decorate.

        Returns:
            Callable: The wrapped function.
        """

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Preparing metadata
            caller_frame = inspect.stack()[1]
            caller_module = inspect.getmodule(caller_frame[0])
            caller_info = {
                'caller_file': caller_frame.filename,
                'caller_name': caller_frame.function,
                'caller_module': caller_module.__name__ if caller_module else None
            }
            func_class = getattr(func, "__self__", None)
            class_name = func_class.__class__.__name__ if func_class else None

            # Execute the function, record output or exception
            try:
                result = func(*args, **kwargs)
                success = True
            except Exception as e:
                result = str(e)
                success = False

            record = {
                'metadata': caller_info,
                'class_name': class_name,
                'function_name': func.__name__,
                'arguments': {'args': args, 'kwargs': kwargs},
                'success': success,
                'result': result
            }

            # Naming and saving the record
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            func_identifier = f"{class_name + '.' if class_name else ''}{func.__name__}"
            filename = f"record_{func_identifier}_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(record, f, default=str)

            if not success:
                raise

            return result

        return wrapper

