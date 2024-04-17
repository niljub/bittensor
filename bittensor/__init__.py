# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
# Copyright © 2022-2023 Opentensor Foundation
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

from rich.console import Console
from rich.traceback import install

# Install and apply nest asyncio to allow the async functions
# to run in a .ipynb
import nest_asyncio

nest_asyncio.apply()

# Rich console.
__console__ = Console()
__use_console__ = True

# Remove overdue locals in debug training.
install(show_locals=False)


def turn_console_off():
    global __use_console__
    global __console__
    from io import StringIO

    __use_console__ = False
    __console__ = Console(file=StringIO(), stderr=False)


def turn_console_on():
    global __use_console__
    global __console__
    __use_console__ = True
    __console__ = Console()


turn_console_off()


# Logging helpers.
def trace(on: bool = True):
    logging.set_trace(on)


def debug(on: bool = True):
    logging.set_debug(on)


from .defines import (
    __version__,
    __version_as_int__,
    __new_signature_version__,
    __blocktime__,
    __pipaddress__,
    __delegates_details_url__,
    __ss58_format__,
    __networks__,
    __finney_entrypoint__,
    __finney_test_entrypoint__,
    __archive_entrypoint__,
    __bellagene_entrypoint__,
    __local_entrypoint__,
    __tao_symbol__,
    __rao_symbol__,
    __network_explorer_map__,
    __type_registry__
)

from .errors import (
    BlacklistedException,
    ChainConnectionError,
    ChainError,
    ChainQueryError,
    ChainTransactionError,
    IdentityError,
    InternalServerError,
    InvalidRequestNameError,
    KeyFileError,
    MetadataError,
    NominationError,
    NotDelegateError,
    NotRegisteredError,
    NotVerifiedException,
    PostProcessException,
    PriorityException,
    RegistrationError,
    RunException,
    StakeError,
    SynapseDendriteNoneException,
    SynapseParsingError,
    TransferError,
    UnknownSynapseError,
    UnstakeError,
)

from substrateinterface import Keypair as Keypair
from .config import InvalidConfigFile, DefaultConfig, config, T
from .keyfile import (
    serialized_keypair_to_keyfile_data,
    deserialize_keypair_from_keyfile_data,
    validate_password,
    ask_password_to_encrypt,
    keyfile_data_is_encrypted_nacl,
    keyfile_data_is_encrypted_ansible,
    keyfile_data_is_encrypted_legacy,
    keyfile_data_is_encrypted,
    keyfile_data_encryption_method,
    legacy_encrypt_keyfile_data,
    encrypt_keyfile_data,
    get_coldkey_password_from_environment,
    decrypt_keyfile_data,
    keyfile,
    Mockkeyfile,
)
from .wallet import display_mnemonic_msg, wallet

from .utils import (
    ss58_to_vec_u8,
    unbiased_topk,
    version_checking,
    strtobool,
    strtobool_with_default,
    get_explorer_root_url_by_network_from_map,
    get_explorer_root_url_by_network_from_map,
    get_explorer_url_for_network,
    ss58_address_to_bytes,
    U16_NORMALIZED_FLOAT,
    U64_NORMALIZED_FLOAT,
    u8_key_to_ss58,
    hash,
    wallet_utils,
)

from .utils.balance import Balance as Balance
from .chain_data import (
    AxonInfo,
    NeuronInfo,
    NeuronInfoLite,
    PrometheusInfo,
    DelegateInfo,
    StakeInfo,
    SubnetInfo,
    SubnetHyperparameters,
    IPInfo,
    ProposalCallData,
    ProposalVoteData,
)
from .subtensor import subtensor as subtensor
from .cli import cli as cli, COMMANDS as ALL_COMMANDS
from .btlogging import logging
from .metagraph import metagraph as metagraph
from .threadpool import PriorityThreadPoolExecutor as PriorityThreadPoolExecutor

from .synapse import TerminalInfo, Synapse
from .stream import StreamingSynapse
from .tensor import tensor, Tensor
from .axon import axon as axon
from .dendrite import dendrite as dendrite

from .mock.keyfile_mock import MockKeyfile as MockKeyfile
from .mock.subtensor_mock import MockSubtensor as MockSubtensor
from .mock.wallet_mock import MockWallet as MockWallet

from .subnets import SubnetsAPI as SubnetsAPI

configs = [
    axon.config(),
    subtensor.config(),
    PriorityThreadPoolExecutor.config(),
    wallet.config(),
    logging.get_config(),
]
defaults = config.merge_all(configs)
