import argparse
from enum import Enum
import logging
from typing import NamedTuple, Optional
import os

from bittensor import defines
from bittensor.utils import networking


class BittensorNetwork(Enum):
    FINNEY = defines.__finney_entrypoint__
    LOCAL = defines.__local_entrypoint__
    TEST = defines.__finney_test_entrypoint__
    ARCHIVE = defines.__archive_entrypoint__
    OTHER = ""
    
    def __str__(self):
        return self.value


class SubtensorConfig(NamedTuple):
    network: BittensorNetwork
    # If network is BittensorNetwork.OTHER, this is the endpoint used
    other_network_endpoint: Optional[str]
    mock: bool


DEFAULT_NETWORK = BittensorNetwork[os.getenv("BT_SUBTENSOR_NETWORK")] or BittensorNetwork.FINNEY
DEFAULT_CHAIN_ENDPOINT = (
    os.getenv("BT_SUBTENSOR_CHAIN_ENDPOINT")
    or defines.__finney_entrypoint__.value
)

logger = logging.getLogger(__name__)


def validate_network_config(network_name: str, chain_endpoint: Optional[str]=None) -> SubtensorConfig:
    if chain_endpoint:
        network = BittensorNetwork.OTHER
        return SubtensorConfig(
            network=network, 
            other_network_endpoint=chain_endpoint, 
            mock=False
        )
    else:
        try:
            # validate network name
            network = BittensorNetwork[network_name.upper()]
        except NameError as e:
            logger.error(f"Invalid network name: {network_name}. Valid choices are {BittensorNetwork.__members__.keys()}")
            raise
        return SubtensorConfig(
            network=network, 
            other_network_endpoint=None, 
            mock=False
        )
