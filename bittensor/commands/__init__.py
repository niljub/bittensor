# The MIT License (MIT)
# Copyright © 2023 Opentensor Technologies Inc

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

from dataclasses import dataclass

from bittensor.btlogging.loggingmachine import LoggingConfig
from bittensor.futures.subtensor.config import SubtensorConfig

@dataclass
class PowRegisterConfig:
    num_processes: int
    update_interval: int
    output_in_place: bool
    verbose: bool
    cuda: dict

@dataclass
class AxonConfig:
    port: int
    ip: str
    external_port: int
    external_ip: str
    max_workers: int
    maximum_concurrent_rpcs: int

@dataclass
class PriorityConfig:
    max_workers: int
    maxsize: int

@dataclass
class PrometheusConfig:
    port: int
    level: str

@dataclass
class WalletConfig:
    name: str
    hotkey: str
    path: str

@dataclass
class DatasetConfig:
    batch_size: int
    block_size: int
    num_workers: int
    dataset_names: str
    data_dir: str
    save_dataset: bool
    max_datasets: int
    num_batches: int

@dataclass
class BittensorConfig:
    netuid: int
    subtensor: SubtensorConfig
    pow_register: PowRegisterConfig
    axon: AxonConfig
    priority: PriorityConfig
    prometheus: PrometheusConfig
    wallet: WalletConfig
    dataset: DatasetConfig
    logging: LoggingConfig


defaults = BittensorConfig(
    netuid=1,
    subtensor=SubtensorConfig(
        network="finney",
        chain_endpoint=None,
        mock=False
    ),
    pow_register=PowRegisterConfig(
        num_processes=None,
        update_interval=50000,
        output_in_place=True,
        verbose=False,
        cuda={"dev_id": [0], "use_cuda": False, "tpb": 256},
    ),
    axon=AxonConfig(
        port=8091,
        ip="[::]",
        external_port=None,
        external_ip=None,
        max_workers=10,
        maximum_concurrent_rpcs=400,
    ),
    priority=PriorityConfig(
        max_workers=5,
        maxsize=10
    ),
    prometheus=PrometheusConfig(
        port=7091,
        level="INFO"
    ),
    wallet=WalletConfig(
        name="default",
        hotkey="default",
        path="~/.bittensor/wallets/"
    ),
    dataset=DatasetConfig(
        batch_size=10,
        block_size=20,
        num_workers=0,
        dataset_names="default",
        data_dir="~/.bittensor/data/",
        save_dataset=False,
        max_datasets=3,
        num_batches=100
    ),
    logging=LoggingConfig(
        debug=False,
        trace=False,
        record_log=False,
        logging_dir="~/.bittensor/miners"
    )
)

from .stake import StakeCommand, StakeShow
from .unstake import UnStakeCommand
from .overview import OverviewCommand
from .register import (
    PowRegisterCommand,
    RegisterCommand,
    RunFaucetCommand,
    SwapHotkeyCommand,
)
from .delegates import (
    NominateCommand,
    ListDelegatesCommand,
    DelegateStakeCommand,
    DelegateUnstakeCommand,
    MyDelegatesCommand,
)
from .wallets import (
    NewColdkeyCommand,
    NewHotkeyCommand,
    RegenColdkeyCommand,
    RegenColdkeypubCommand,
    RegenHotkeyCommand,
    UpdateWalletCommand,
    WalletCreateCommand,
    WalletBalanceCommand,
    GetWalletHistoryCommand,
)
from .transfer import TransferCommand
from .inspect import InspectCommand
from .metagraph import MetagraphCommand
from .list import ListCommand
from .misc import UpdateCommand, AutocompleteCommand
from .senate import (
    SenateCommand,
    ProposalsCommand,
    ShowVotesCommand,
    SenateRegisterCommand,
    SenateLeaveCommand,
    VoteCommand,
)
from .network import (
    RegisterSubnetworkCommand,
    SubnetLockCostCommand,
    SubnetListCommand,
    SubnetSudoCommand,
    SubnetHyperparamsCommand,
    SubnetGetHyperparamsCommand,
)
from .root import (
    RootRegisterCommand,
    RootList,
    RootSetWeightsCommand,
    RootGetWeightsCommand,
    RootSetBoostCommand,
    RootSetSlashCommand,
)
from .identity import GetIdentityCommand, SetIdentityCommand
