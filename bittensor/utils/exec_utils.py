"""
Utility functions for execution of tasks using multiprocessing.
"""

# The MIT License (MIT)
# Copyright © 2021 Yuma Rao

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import bittensor
import multiprocessing
import time

def exec_after(interval: int, func: callable, *args, **kwargs) -> tuple[bool, str]:
    """
    Starts a background process to execute a function after a given time interval.

    Parameters:
    - interval (int): Number of seconds to wait before executing the function.
    - func (callable): The function to be executed.
    - args: Argument list for the function.
    - kwargs: Keyword arguments for the function.
    """

    def run_in_background(func: callable, *args, **kwargs) -> None:
        """Helper function to delay the execution and run in a separate process."""
        time.sleep(interval)
        func(*args, **kwargs)

    try:
        process_args = [func] + list(args)
        p = multiprocessing.Process(target=run_in_background, args=process_args, kwargs=kwargs)
        p.start()
        return True, "Background process started succesfully"
    except Exception as e:
        bittensor.logging.error(f"Failed to start background process: {e}")
        return False, f"Failed to start a new process: {str(e)}"