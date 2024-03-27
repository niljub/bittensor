# bittensor/__init__.py
import importlib
import types
# from bittensor.config import config
from bittensor.btlogging import logging


class LegacyLoader(types.ModuleType):
    """
    Lazily import a specified attribute from a module, mainly to avoid initializing it
    until it's actually used.
    """
    def __init__(self, full_path: str, alias: str):
        self.module_name, self.attribute_name = full_path.rsplit('.', 1)
        self.alias = alias
        super().__init__(alias)

    def _load(self):
        """Load the attribute and update this object's dict with it."""
        module = importlib.import_module(self.module_name)
        attr = getattr(module, self.attribute_name)
        self.__dict__.update({self.alias: attr})
        return attr

    def __getattr__(self, item):
        if item == self.alias:
            return self._load()
        raise AttributeError(f"{self.__class__.__name__} object has no attribute {item}")

    def __dir__(self):
        # Explicitly convert the result of super().__dir__() to a list
        extended_dir = list(super().__dir__())
        # Append the alias to the list of directory entries
        extended_dir.append(self.alias)
        return extended_dir


synapse = LegacyLoader("bittensor.synapse.Synapse", "synapse")
stream = LegacyLoader("bittensor.stream.Stream", "stream")
tensor = LegacyLoader("bittensor.tensor.Tensor", "tensor")
subtensor = LegacyLoader("bittensor.subtensor.Subtensor", "subtensor")
cli = LegacyLoader("bittensor.cli_legacy.Cli", "cli")
COMMANDS = LegacyLoader("bittensor.cli_legacy.COMMANDS", "ALL_COMMANDS")
metagraph = LegacyLoader("bittensor.metagraph.Metagraph", "metagraph")
PriorityThreadPoolExecutor = LegacyLoader("bittensor.threadpool.PriorityThreadPoolExecutor", "PriorityThreadPoolExecutor")
axon = LegacyLoader("bittensor.axon.Axon", "axon")
dendrite = LegacyLoader("bittensor.dendrite.Dendrite", "dendrite")
MockKeyfile = LegacyLoader("bittensor.mock.keyfile_mock.MockKeyfile", "MockKeyfile")
MockSubtensor = LegacyLoader("bittensor.mock.subtensor_mock.MockSubtensor", "MockSubtensor")
MockWallet = LegacyLoader("bittensor.mock.wallet_mock.MockWallet", "MockWallet")
SubnetsAPI = LegacyLoader("bittensor.subnets.SubnetsAPI", "SubnetsAPI")



