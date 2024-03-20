import os
import argparse
import bittensor
from typing import *
from bittensor.command.parser import CommandParser


class SubtensorInterface:

    def __init__(
        self,
        network: Optional[str] = None,
        config: Optional[bittensor.config] = None,
        _mock: bool = False,
        log_verbose: bool = True,
    ) -> None:
        """
        Initializes a Subtensor interface for interacting with the Bittensor blockchain.

        NOTE:
            Currently subtensor defaults to the ``finney`` network. This will change in a future release.

        We strongly encourage users to run their own local subtensor node whenever possible. This increases
        decentralization and resilience of the network. In a future release, local subtensor will become the
        default and the fallback to ``finney`` removed. Please plan ahead for this change. We will provide detailed
        instructions on how to run a local subtensor node in the documentation in a subsequent release.

        Args:
            network (str, optional): The network name to connect to (e.g., ``finney``, ``local``). This can also be the chain endpoint (e.g., ``wss://entrypoint-finney.opentensor.ai:443``) and will be correctly parsed into the network and chain endpoint. If not specified, defaults to the main Bittensor network.
            config (bittensor.config, optional): Configuration object for the subtensor. If not provided, a default configuration is used.
            _mock (bool, optional): If set to ``True``, uses a mocked connection for testing purposes.

        This initialization sets up the connection to the specified Bittensor network, allowing for various
        blockchain operations such as neuron registration, stake management, and setting weights.

        """
        # Determine config.subtensor.chain_endpoint and config.subtensor.network config.
        # If chain_endpoint is set, we override the network flag, otherwise, the chain_endpoint is assigned by the network.
        # Argument importance: network > chain_endpoint > config.subtensor.chain_endpoint > config.subtensor.network

        # Check if network is a config object. (Single argument passed as first positional)
        if isinstance(network, bittensor.config):
            if network.subtensor is None:
                bittensor.logging.warning(
                    "If passing a bittensor config object, it must not be empty. Using default subtensor config."
                )
                config = None
            else:
                config = network
            network = None

        if config is None:
            config = SubtensorInterface.config()
        self.config = copy.deepcopy(config)  # type: ignore

        # Setup config.subtensor.network and config.subtensor.chain_endpoint
        self.chain_endpoint, self.network = subtensor.setup_config(network, config)  # type: ignore

        if (
            self.network == "finney"
            or self.chain_endpoint == bittensor.__finney_entrypoint__
        ) and log_verbose:
            bittensor.logging.info(
                f"You are connecting to {self.network} network with endpoint {self.chain_endpoint}."
            )
            bittensor.logging.warning(
                "We strongly encourage running a local subtensor node whenever possible. "
                "This increases decentralization and resilience of the network."
            )
            bittensor.logging.warning(
                "In a future release, local subtensor will become the default endpoint. "
                "To get ahead of this change, please run a local subtensor node and point to it."
            )

        # Returns a mocked connection with a background chain connection.
        self.config.subtensor._mock = (
            _mock
            if _mock != None
            else self.config.subtensor.get("_mock", bittensor.defaults.subtensor._mock)
        )
        if (
            self.config.subtensor._mock
        ):  # TODO: review this doesn't appear to be used anywhere.
            config.subtensor._mock = True
            return bittensor.MockSubtensor()  # type: ignore




    @staticmethod
    def config() -> "bittensor.config":
        parser = argparse.ArgumentParser()
        SubtensorInterface.add_args(parser)
        return bittensor.config(parser, args=[])

    @classmethod
    def help(cls):
        """Print help to stdout"""
        parser = argparse.ArgumentParser()
        cls.add_args(parser)
        print(cls.__new__.__doc__)
        parser.print_help()

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser, prefix: Optional[str] = None):
        prefix_str = "" if prefix is None else f"{prefix}."
        try:
            default_network = os.getenv("BT_SUBTENSOR_NETWORK") or "finney"
            default_chain_endpoint = (
                os.getenv("BT_SUBTENSOR_CHAIN_ENDPOINT")
                or bittensor.__finney_entrypoint__
            )
            parser.add_argument(
                "--" + prefix_str + "subtensor.network",
                default=default_network,
                type=str,
                help="""The subtensor network flag. The likely choices are:
                                        -- finney (main network)
                                        -- test (test network)
                                        -- archive (archive network +300 blocks)
                                        -- local (local running network)
                                    If this option is set it overloads subtensor.chain_endpoint with
                                    an entry point node from that network.
                                    """,
            )
            parser.add_argument(
                "--" + prefix_str + "subtensor.chain_endpoint",
                default=default_chain_endpoint,
                type=str,
                help="""The subtensor endpoint flag. If set, overrides the --network flag.
                                    """,
            )
            parser.add_argument(
                "--" + prefix_str + "subtensor._mock",
                default=False,
                type=bool,
                help="""If true, uses a mocked connection to the chain.
                                    """,
            )

        except argparse.ArgumentError:
            # re-parsing arguments.
            pass

    @staticmethod
    def determine_chain_endpoint_and_network(network: str):
        """Determines the chain endpoint and network from the passed network or chain_endpoint.

        Args:
            network (str): The network flag. The choices are: ``-- finney`` (main network), ``-- archive`` (archive network +300 blocks), ``-- local`` (local running network), ``-- test`` (test network).
            chain_endpoint (str): The chain endpoint flag. If set, overrides the network argument.
        Returns:
            network (str): The network flag.
            chain_endpoint (str): The chain endpoint flag. If set, overrides the ``network`` argument.
        """
        if network is None:
            return None, None
        if network in ["finney", "local", "test", "archive"]:
            if network == "finney":
                # Kiru Finney stagin network.
                return network, bittensor.__finney_entrypoint__
            elif network == "local":
                return network, bittensor.__local_entrypoint__
            elif network == "test":
                return network, bittensor.__finney_test_entrypoint__
            elif network == "archive":
                return network, bittensor.__archive_entrypoint__
        else:
            if (
                network == bittensor.__finney_entrypoint__
                or "entrypoint-finney.opentensor.ai" in network
            ):
                return "finney", bittensor.__finney_entrypoint__
            elif (
                network == bittensor.__finney_test_entrypoint__
                or "test.finney.opentensor.ai" in network
            ):
                return "test", bittensor.__finney_test_entrypoint__
            elif (
                network == bittensor.__archive_entrypoint__
                or "archive.chain.opentensor.ai" in network
            ):
                return "archive", bittensor.__archive_entrypoint__
            elif "127.0.0.1" in network or "localhost" in network:
                return "local", network
            else:
                return "unknown", network

    @staticmethod
    def setup_config(network: str, config: bittensor.config):
        if network != None:
            (
                evaluated_network,
                evaluated_endpoint,
            ) = SubtensorInterface.determine_chain_endpoint_and_network(network)
        else:
            if config.get("__is_set", {}).get("subtensor.chain_endpoint"):
                (
                    evaluated_network,
                    evaluated_endpoint,
                ) = SubtensorInterface.determine_chain_endpoint_and_network(
                    config.subtensor.chain_endpoint
                )

            elif config.get("__is_set", {}).get("subtensor.network"):
                (
                    evaluated_network,
                    evaluated_endpoint,
                ) = SubtensorInterface.determine_chain_endpoint_and_network(
                    config.subtensor.network
                )

            elif config.subtensor.get("chain_endpoint"):
                (
                    evaluated_network,
                    evaluated_endpoint,
                ) = SubtensorInterface.determine_chain_endpoint_and_network(
                    config.subtensor.chain_endpoint
                )

            elif config.subtensor.get("network"):
                (
                    evaluated_network,
                    evaluated_endpoint,
                ) = SubtensorInterface.determine_chain_endpoint_and_network(
                    config.subtensor.network
                )

            else:
                (
                    evaluated_network,
                    evaluated_endpoint,
                ) = SubtensorInterface.determine_chain_endpoint_and_network(
                    bittensor.defaults.subtensor.network
                )

        return (
            bittensor.utils.networking.get_formatted_ws_endpoint_url(
                evaluated_endpoint
            ),
            evaluated_network,
        )



