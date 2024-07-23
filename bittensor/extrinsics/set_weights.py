# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
# Copyright © 2023 Opentensor Foundation

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

import datetime
import bittensor

import os
import logging
import numpy as np
from numpy.typing import NDArray
from rich.prompt import Confirm
from typing import Union, Tuple
from bittensor.utils import exec_utils, weight_utils
from bittensor.utils import commit_reveal_utils
from bittensor.utils.commit_reveal_utils import RevealData
from bittensor.btlogging.defines import BITTENSOR_LOGGER_NAME
from bittensor.utils.registration import torch, use_torch


logger = logging.getLogger(BITTENSOR_LOGGER_NAME)


def set_weights_extrinsic(
    subtensor: "bittensor.subtensor",
    wallet: "bittensor.wallet",
    netuid: int,
    uids: Union[NDArray[np.int64], "torch.LongTensor", list],
    weights: Union[NDArray[np.float32], "torch.FloatTensor", list],
    salt: list[int] = None,
    version_key: int = 0,
    wait_for_inclusion: bool = False,
    wait_for_finalization: bool = False,
    prompt: bool = False,
) -> Tuple[bool, str]:
    """
    Sets the inter-neuronal weights for the specified neuron. This process involves specifying the
    influence or trust a neuron places on other neurons in the network, which is a fundamental aspect
    of Bittensor's decentralized learning architecture.
    
    This function is crucial in shaping the network's collective intelligence, where each neuron's
    learning and contribution are influenced by the weights it sets towards others.

    Args:
        subtensor (bittensor.subtensor): 
            Subtensor endpoint to use.
        wallet (bittensor.wallet): 
            The wallet associated with the neuron setting the weights.
        netuid (int): 
            The ``netuid`` of the subnet to set weights for.
        uids (Union[NDArray[np.int64], torch.LongTensor, list]): 
            The list of neuron UIDs that the weights are being set for.
        weights (Union[NDArray[np.float32], torch.FloatTensor, list]): 
            The weights to set. These must be ``float`` s and correspond to the passed ``uid`` s.
        salt (list[int], optional): 
            A list of integers representing the salt to be used in the commit-reveal process.
        version_key (int, optional): 
            Version key for compatibility with the network.
        wait_for_inclusion (bool, optional): 
            Waits for the transaction to be included in a block.
        wait_for_finalization (bool, optional): 
            Waits for the transaction to be finalized on the blockchain.
        prompt (bool, optional): 
            If ``True``, prompts for user confirmation before proceeding.

    Returns:
        Tuple[bool, str]: 
            ``True`` if the setting of weights is successful, False otherwise. And `msg`, a string
            value describing the success or potential error.
    """

    # Reformat and normalize.
    weight_uids, weight_vals = _prepare_values(uids, weights)

    # Ask before moving on.
    formatted_weight_vals = [float(v / 65535) for v in weight_vals]
    if prompt and not Confirm.ask(f"Do you want to set weights:\n[bold white]  weights: {formatted_weight_vals}\n  uids: {weight_uids}[/bold white ]?"):
        return False, "Prompt refused."

    # Check if the commit-reveal mechanism is active for the given netuid.
    if subtensor.commit_reveal_active(netuid=netuid):
        return _commit_reveal(
            subtensor,
            wallet,
            netuid,
            weight_uids,
            weight_vals,
            formatted_weight_vals,
            salt,
            wait_for_inclusion,
            wait_for_finalization,
        )
    else:
        return _set_weights_without_commit_reveal(
            subtensor,
            wallet,
            netuid,
            weight_uids,
            weight_vals,
            version_key,
            wait_for_inclusion,
            wait_for_finalization
        )


def _prepare_values(
    uids: Union[NDArray[np.int64], "torch.LongTensor", list],
    weights: Union[NDArray[np.float32], "torch.FloatTensor", list]
) -> Tuple[NDArray[np.int64], NDArray[np.float32]]:
    # First convert types.
    if use_torch():
        if isinstance(uids, list):
            uids = torch.tensor(uids, dtype=torch.int64)
        if isinstance(weights, list):
            weights = torch.tensor(weights, dtype=torch.float32)
    else:
        if isinstance(uids, list):
            uids = np.array(uids, dtype=np.int64)
        if isinstance(weights, list):
            weights = np.array(weights, dtype=np.float32)
    return weight_utils.convert_weights_and_uids_for_emit(
        uids, weights
    )

def _commit_reveal(
    subtensor: "bittensor.subtensor",
    wallet: "bittensor.wallet",
    netuid: int,
    weight_uids: NDArray[np.int64],
    weight_vals: NDArray[np.float32],
    salt: list[int],
    wait_for_inclusion: bool,
    wait_for_finalization: bool
) -> Tuple[bool, str]:
    interval = subtensor.commit_reveal_interval(netuid=netuid)

    if not salt:
        # Generate a random salt of specified length to be used in the commit-reveal process
        salt_length = 8
        salt = list(os.urandom(salt_length))

    try:
        # Attempt to commit the weights to the blockchain.
        commit_success, commit_msg = subtensor.commit_weights(
            wallet=wallet,
            netuid=netuid,
            salt=salt,
            uids=weight_uids,
            weights=weight_vals,
            wait_for_inclusion=wait_for_inclusion,
            wait_for_finalization=wait_for_finalization,
        )
    except Exception as e:
        commit_success, commit_msg = False, str(e)

    if commit_success:
        try:
            # In case of process execution failure, first create the reveal_data and then save it to a file for recovery
            reveal_data = RevealData.create(wallet, subtensor, netuid, weight_uids, weight_vals, salt, wait_for_inclusion, wait_for_finalization, interval)
            commit_reveal_utils.write_reveal_data(reveal_data)

            # Attempt executing _reveal function after a delay of 'interval'
            schedule_success, schedule_msg = exec_utils.exec_after(
                interval,
                reveal,
                wallet,
                subtensor,
                netuid,
                weight_uids,
                weight_vals,
                salt,
                wait_for_inclusion,
                wait_for_finalization,
                reveal_data.interval,
                reveal_data.reveal_time
            )
        except Exception as e:
            schedule_success, schedule_msg = False, str(e)

        if schedule_success:
            bittensor.__console__.print(":white_heavy_check_mark: [green]Weights hash committed to chain[/green]")
            bittensor.__console__.print(f":alarm_clock: [dark_orange3]Weights hash reveal scheduled for {reveal_data.reveal_time}[/dark_orange3]")
            bittensor.__console__.print(f":alarm_clock: [red]WARNING: Turning off your computer will prevent this process from executing!!![/red]")
            bittensor.__console__.print(f"To retry in case of failure on or after {reveal_data.reveal_time} run:\n{reveal_data.cli_retry_cmd}")
            bittensor.logging.success(prefix="Weights hash committed and reveal operation scheduled", suffix=str(schedule_msg))
            return True, f"Weights committed and will be revealed at {reveal_data.reveal_time}"
        else:
            bittensor.__console__.print(f":cross_mark: [red]Failed[/red]: Weights hash committed but failed to schedule reveal: {e}")
            bittensor.__console__.print(f"On or after {reveal_data.reveal_time}, retry using:\n{reveal_data.cli_retry_cmd}")
            bittensor.logging.error(prefix="Schedule reveal weights hash", suffix=f"<red>Failed: </red>{e}")
            return False, f"Weights hash committed but failed to schedule reveal. {commit_msg}"
    else:
        bittensor.__console__.print(f":cross_mark: [red]Failed[/red]: error:{commit_msg}")
        bittensor.logging.error(msg=commit_msg, prefix="Set weights with hash commit", suffix=f"<red>Failed: {commit_msg}</red>")
        return False, f"Failed to commit weights hash. {commit_msg}"


def reveal(
    wallet: "bittensor.wallet",
    subtensor: "bittensor.subtensor",
    netuid: int,
    weight_uids: NDArray[np.int64],
    weight_vals: NDArray[np.float32],
    salt: list[int],
    wait_for_inclusion: bool,
    wait_for_finalization: bool,
) -> Tuple[bool, str]:

    try:
        # Attempt to reveal the weights using the salt.
        success, msg = subtensor.reveal_weights(
            wallet=wallet,
            netuid=netuid,
            uids=weight_uids,
            weights=weight_vals,
            salt=salt,
            wait_for_inclusion=wait_for_inclusion,
            wait_for_finalization=wait_for_finalization,
        )
    except Exception as e:
            success, msg = False, str(e)

    if success:
        reveal_data = RevealData.create(wallet, subtensor, netuid, weight_uids, weight_vals, salt, wait_for_inclusion, wait_for_finalization, interval)
        if reveal_data == commit_reveal_utils.read_last_reveal_data():
            commit_reveal_utils.remove_last_reveal_data()

        if not wait_for_finalization and not wait_for_inclusion:
            return True, "Not waiting for finalization or inclusion."

        bittensor.__console__.print(":white_heavy_check_mark: [green]Weights hash revealed on chain[/green]")
        bittensor.logging.success(prefix="Weights hash revealed", suffix=str(msg))
        
        return True, "Successfully revealed previously commited weights hash."
    else:
        bittensor.logging.error(
            msg=msg,
            prefix="Failed to reveal previously commited weights hash",
            suffix="<red>Failed: </red>",
        )
        return False, "Failed to reveal weights."


def _set_weights_without_commit_reveal(
    subtensor: "bittensor.subtensor",
    wallet: "bittensor.wallet",
    netuid: int,
    weight_uids: NDArray[np.int64],
    weight_vals: NDArray[np.float32],
    version_key: int,
    wait_for_inclusion: bool,
    wait_for_finalization: bool
) -> Tuple[bool, str]:
    with bittensor.__console__.status(":satellite: Setting weights on [white]{}[/white] ...".format(subtensor.network)):
        try:
            success, error_message = subtensor._do_set_weights(
                wallet=wallet,
                netuid=netuid,
                uids=weight_uids,
                vals=weight_vals,
                version_key=version_key,
                wait_for_finalization=wait_for_finalization,
                wait_for_inclusion=wait_for_inclusion,
            )

            if not wait_for_finalization and not wait_for_inclusion:
                return True, "Not waiting for finalization or inclusion."

            if success:
                bittensor.__console__.print(":white_heavy_check_mark: [green]Finalized[/green]")
                bittensor.logging.success(prefix="Set weights", suffix="<green>Finalized: </green>" + str(success))
                return True, "Successfully set weights and finalized."
            else:
                bittensor.logging.error(msg=error_message, prefix="Set weights", suffix="<red>Failed: </red>")
                return False, error_message

        except Exception as e:
            bittensor.__console__.print(":cross_mark: [red]Failed[/red]: error:{}".format(e))
            bittensor.logging.warning(prefix="Set weights", suffix="<red>Failed: </red>" + str(e))
            return False, str(e)
