"""
Conversion for weight between chain representation and np.array or torch.Tensor
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

import os
import ast
from datetime import datetime
from dataclasses import dataclass
from typing import Tuple, List, Union
import numpy as np
from numpy.typing import NDArray
from scalecodec import ScaleBytes, U16, Vec
from substrateinterface import Keypair
import hashlib
import bittensor

CACHE_DIR = os.path.expanduser("~/.bittensor/cache")
REVEAL_WEIGHTS_QUEUE = os.path.join(CACHE_DIR, "reveal_weights.queue")



def generate_weight_hash(
    address: str,
    netuid: int,
    uids: List[int],
    values: List[int],
    version_key: int,
    salt: List[int],
) -> str:
    """
    Generate a valid commit hash from the provided weights.

    Args:
        address (str): The account identifier. Wallet ss58_address.
        netuid (int): The network unique identifier.
        uids (List[int]): The list of UIDs.
        salt (List[int]): The salt to add to hash.
        values (List[int]): The list of weight values.
        version_key (int): The version key.

    Returns:
        str: The generated commit hash.
    """
    # Encode data using SCALE codec
    wallet_address = ScaleBytes(Keypair(ss58_address=address).public_key)
    netuid = ScaleBytes(netuid.to_bytes(2, "little"))

    vec_uids = Vec(data=None, sub_type="U16")
    vec_uids.value = [U16(ScaleBytes(uid.to_bytes(2, "little"))) for uid in uids]
    uids = ScaleBytes(vec_uids.encode().data)

    vec_values = Vec(data=None, sub_type="U16")
    vec_values.value = [
        U16(ScaleBytes(value.to_bytes(2, "little"))) for value in values
    ]
    values = ScaleBytes(vec_values.encode().data)

    version_key = ScaleBytes(version_key.to_bytes(8, "little"))

    vec_salt = Vec(data=None, sub_type="U16")
    vec_salt.value = [U16(ScaleBytes(salts.to_bytes(2, "little"))) for salts in salt]
    salt = ScaleBytes(vec_salt.encode().data)

    data = wallet_address + netuid + uids + values + salt + version_key

    # Generate Blake2b hash of the data tuple
    blake2b_hash = hashlib.blake2b(data.data, digest_size=32)

    # Convert the hash to hex string and add "0x" prefix
    commit_hash = "0x" + blake2b_hash.hexdigest()

    return commit_hash

@dataclass
class RevealData:
    """
    A container for values from a set weights operation where a commit-reveal failure occurred, 
    and a retry is necessary. This dataclass captures all the relevant fields that can be persisted 
    to a file with the intention to retry the operation at a later time.

    Attributes:
        interval (str): The interval for the reveal process.
        commit_time (str): The commit time in ISO 8601 format.
        reveal_time (str): The reveal time in ISO 8601 format.
        wallet_name (str): The name of the wallet.
        wallet_hotkey (str): The hotkey of the wallet.
        wallet_path (str): The path to the wallet.
        subtensor_network (str): The network identifier.
        subtensor_chain_endpoint (str): The chain endpoint.
        netuid (int): The network unique identifier.
        weight_uids (str): A comma-separated string of UIDs.
        weight_vals (str): A comma-separated string of weight values.
        salt (str): The salt used in the commit-reveal process.
        wait_for_inclusion (bool): Whether to wait for inclusion in the block.
        wait_for_finalization (bool): Whether to wait for finalization of the block.
    """
    interval: str = None
    commit_time: str = None
    reveal_time: str = None
    wallet_name: str = None
    wallet_hotkey: str = None
    wallet_path: str = None
    subtensor_network: str = None
    subtensor_chain_endpoint: str = None
    netuid: int = None
    weight_uids: str = None
    weight_vals: str = None
    salt: str = None
    wait_for_inclusion: bool = False
    wait_for_finalization: bool = False

    @classmethod
    def cli_retry_cmd(cls):
        return (
            f"btcli weights set_weights "
            f"--netuid {cls.netuid} --uids {cls.weight_uids} --weights {cls.weight_vals} "
            f"--reveal-using-salt {cls.salt} "
            f"--wallet.name {cls.wallet_name} --wallet.hotkey {cls.wallet_hotkey} --wallet.path {cls.wallet_path}"
        )

    @staticmethod
    def create(
        wallet: "bittensor.wallet",
        subtensor: "bittensor.subtensor",
        netuid: int,
        weight_uids: NDArray[np.int64],
        weight_vals: NDArray[np.float32],
        salt: list[int],
        wait_for_inclusion: bool,
        wait_for_finalization: bool,
        interval: int
    ) -> "RevealData":
        """
        Creates an instance of RevealData by converting some of the values into strings.

        Args:
            wallet (bittensor.wallet): The wallet object containing wallet details.
            subtensor (bittensor.subtensor): The subtensor object containing network information.
            netuid (int): The network unique identifier.
            weight_uids (NDArray[np.int64]): Array of UIDs.
            weight_vals (NDArray[np.float32]): Array of weight values.
            salt (list[int]): The salt used in the commit-reveal process.
            wait_for_inclusion (bool): Whether to wait for inclusion in the block.
            wait_for_finalization (bool): Whether to wait for finalization of the block.
            interval (int): The interval in seconds for the reveal process.

        Returns:
            RevealData: An instance of RevealData with the provided values.
        """

        current_time = datetime.now().astimezone().replace(microsecond=0)
        return RevealData(
            interval=interval,
            commit_time = current_time.isoformat(),
            reveal_time = (current_time + datetime.timedelta(seconds=interval)).isoformat(),
            wallet_name = wallet.name,
            wallet_hotkey = wallet.hotkey,
            wallet_path = wallet.path,
            subtensor_network=subtensor.network,
            subtensor_chain_endpoint=subtensor.chain_endpoint,
            netuid=netuid,
            weight_uids=",".join(map(str, weight_uids)),
            weight_vals=",".join(map(str, weight_vals)),
            salt=str(salt),
            wait_for_inclusion=wait_for_inclusion,
            wait_for_finalization=wait_for_finalization
        )
    @staticmethod
    def from_dict(data: dict) -> "RevealData":
        """
        Creates an instance of RevealData from a dictionary.

        Args:
            data (dict): A dictionary containing the values.

        Returns:
            RevealData: An instance of RevealData with the provided values.
        """
        if not data:
            return None
        return RevealData(
            interval=data.get("interval"),
            commit_time=data.get("commit_time"),
            reveal_time=data.get("reveal_time"),
            wallet_name=data.get("wallet_name"),
            wallet_hotkey=data.get("wallet_hotkey"),
            wallet_path=data.get("wallet_path"),
            subtensor_network=data.get("subtensor_network"),
            subtensor_chain_endpoint=data.get("subtensor_chain_endpoint"),
            netuid=data.get("netuid"),
            weight_uids=data.get("weight_uids"),
            weight_vals=data.get("weight_vals"),
            salt=data.get("salt"),
            wait_for_inclusion=data.get("wait_for_inclusion", False),
            wait_for_finalization=data.get("wait_for_finalization", False),
        )

def write_reveal_data(reveal_data: "RevealData") -> bool:
    """
    Writes the provided reveal data to the cache file.

    This function attempts to create the cache directory if it does not exist,
    and then writes the reveal data to the cache file in a dictionary format.

    Args:
        reveal_data (RevealData): The reveal data to be written to the cache file.

    Returns:
        bool: True if the operation was successful, False otherwise.
    """
    success = False
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(REVEAL_WEIGHTS_QUEUE, "w") as f:
            f.write(str(reveal_data.__dict__))
        success = True
    except Exception as e:
        bittensor.logging.error(f"Failed to write reveal data: {e}")
    return success


def read_last_reveal_data() -> RevealData:
    """
    Reads the set weights commit reveal failure cache file for the last set of values that failed.

    Returns:
        FailureData: An instance of FailureData with the last failure data.
    """
    try:
        if os.path.exists(REVEAL_WEIGHTS_QUEUE):
            with open(REVEAL_WEIGHTS_QUEUE, "r") as f:
                lines = f.readlines()
                if lines:
                    data = ast.literal_eval(lines[-1])  # Safely evaluate the string as a Python literal
                    return RevealData.from_dict(data)
    except Exception as e:
        bittensor.logging.error(f"Failed to read last failure data: {e}")
    return None

def remove_last_reveal_data() -> bool:
    """
    Removes the last set weights commit reveal failure data from the cache file.

    This function attempts to remove the last entry of failure data from the cache file.
    If there is only one entry, it deletes the cache file entirely.

    Returns:
        bool: True if the operation was successful, False otherwise.
    """
    success = False
    try:
        if os.path.exists(REVEAL_WEIGHTS_QUEUE):
            with open(REVEAL_WEIGHTS_QUEUE, "r") as f:
                lines = f.readlines()
            if len(lines) > 1:
                with open(REVEAL_WEIGHTS_QUEUE, "w") as f:
                    f.writelines(lines[:-1])
            else:
                os.remove(REVEAL_WEIGHTS_QUEUE)
        success = True
    except Exception as e:
        bittensor.logging.error(f"Failed to remove last reveal data: {e}")
    return success