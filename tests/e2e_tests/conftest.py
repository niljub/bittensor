from bittensor import logging
import os
import re
import select
import shlex
import signal
import subprocess
import time

import pytest
from substrateinterface import SubstrateInterface

from tests.e2e_tests.utils import (
    clone_or_update_templates,
    install_templates,
    uninstall_templates,
)



# Fixture for setting up and tearing down a localnet.sh chain between tests
@pytest.fixture(scope="function")
def local_chain(request):
    param = request.param if hasattr(request, "param") else None
    # Get the environment variable for the script path
    script_path = os.getenv("LOCALNET_SH_PATH")

    if not script_path:
        # Skip the test if the localhost.sh path is not set
        logging.warning("LOCALNET_SH_PATH env variable is not set, e2e test skipped.")
        pytest.skip("LOCALNET_SH_PATH environment variable is not set.")

    # Check if param is None, and handle it accordingly
    args = "" if param is None else f"{param}"

    # compile commands to send to process
    cmds = shlex.split(f"{script_path} {args}")
    # Start new node process
    process = subprocess.Popen(
        cmds,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid,
    )

    # Install neuron templates
    logging.info("downloading and installing neuron templates from github")
    templates_dir = clone_or_update_templates()
    install_templates(templates_dir)

    # Pattern match indicates node is compiled and ready
    pattern = re.compile(r"Imported #1")

    # Time out of 15 minutes
    def wait_for_node_start(process, pattern, timeout=900):
        start_time = time.time()
        while True:
            # Check if we've exceeded the timeout
            if time.time() - start_time > timeout:
                logging.error("Subtensor not started in time")
                return False

            # Check if ready for output every 1 second
            ready, _, _ = select.select([process.stdout], [], [], 2.0)

            if ready:
                line = process.stdout.readline()
                if not line:  # EOF
                    logging.error("Process ended unexpectedly")
                    return False
                logging.info(line.strip())
                if pattern.search(line):
                    logging.info("Node started!")
                    return True
            else:
                # No output within 1 second, continue the loop
                continue

    if not wait_for_node_start(process, pattern):
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        pytest.fail("Node failed to start within the timeout period.")

    # Run the test, passing in substrate interface
    yield SubstrateInterface(url="ws://127.0.0.1:9945")

    # Terminate the process group (includes all child processes)
    os.killpg(os.getpgid(process.pid), signal.SIGTERM)

    # Give some time for the process to terminate
    time.sleep(1)

    # If the process is not terminated, send SIGKILL
    if process.poll() is None:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)

    # Ensure the process has terminated
    process.wait()

    # uninstall templates
    logging.info("uninstalling neuron templates")
    uninstall_templates(templates_dir)
