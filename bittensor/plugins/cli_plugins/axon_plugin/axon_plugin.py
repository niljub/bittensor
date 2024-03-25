from typing import Any

from bittensor.bittensor_plugin_system.core.plugins import CLIPlugin


class AxonPlugin(CLIPlugin):

    def execute(self, command: str, *args: Any, **kwargs: Any) -> None:
        pass

    def _core_execute(self, data: Any) -> Any:
        pass

    def shutdown(self) -> None:
        pass

    def initialize(self, config_path: str) -> None:
        pass


class AxonPluginConfig():


    @classmethod
    def config(cls) -> "bittensor.config":
        """
        Parses the command-line arguments to form a Bittensor configuration object.

        Returns:
            bittensor.config: Configuration object with settings from command-line arguments.
        """
        parser = argparse.ArgumentParser()
        cls.add_args(parser)  # Add specific axon-related arguments
        return bittensor.config(parser, args=[])

    @classmethod
    def help(cls):
        """
        Prints the help text (list of command-line arguments and their descriptions) to stdout.
        """
        parser = argparse.ArgumentParser()
        cls.add_args(parser)  # Add specific axon-related arguments
        print(cls.__new__.__doc__)  # Print docstring of the class
        parser.print_help()  # Print parser's help text

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser, prefix: Optional[str] = None):
        """
        Adds AxonServer-specific command-line arguments to the argument parser.

        Args:
            parser (argparse.ArgumentParser): Argument parser to which the arguments will be added.
            prefix (str, optional): Prefix to add to the argument names. Defaults to None.

        Note:
            Environment variables are used to define default values for the arguments.
        """
        prefix_str = "" if prefix is None else prefix + "."
        try:
            # Get default values from environment variables or use default values
            default_axon_port = os.getenv("BT_AXON_PORT") or 8091
            default_axon_ip = os.getenv("BT_AXON_IP") or "[::]"
            default_axon_external_port = os.getenv("BT_AXON_EXTERNAL_PORT") or None
            default_axon_external_ip = os.getenv("BT_AXON_EXTERNAL_IP") or None
            default_axon_max_workers = os.getenv("BT_AXON_MAX_WORERS") or 10

            # Add command-line arguments to the parser
            parser.add_argument(
                "--" + prefix_str + "axon.port",
                type=int,
                help="The local port this axon endpoint is bound to. i.e. 8091",
                default=default_axon_port,
            )
            parser.add_argument(
                "--" + prefix_str + "axon.ip",
                type=str,
                help="""The local ip this axon binds to. ie. [::]""",
                default=default_axon_ip,
            )
            parser.add_argument(
                "--" + prefix_str + "axon.external_port",
                type=int,
                required=False,
                help="""The public port this axon broadcasts to the network. i.e. 8091""",
                default=default_axon_external_port,
            )
            parser.add_argument(
                "--" + prefix_str + "axon.external_ip",
                type=str,
                required=False,
                help="""The external ip this axon broadcasts to the network to. ie. [::]""",
                default=default_axon_external_ip,
            )
            parser.add_argument(
                "--" + prefix_str + "axon.max_workers",
                type=int,
                help="""The maximum number connection handler threads working simultaneously on this endpoint.
                        The grpc server distributes new worker threads to service requests up to this number.""",
                default=default_axon_max_workers,
            )

        except argparse.ArgumentError:
            # Exception handling for re-parsing arguments
            pass