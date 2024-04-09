# sub_subtensor.py
import inspect
import json
from logging import getLogger
from typing import Any, Callable, Dict, List, Optional, Type, Union

import gorilla
import substrateinterface
from substrateinterface import SubstrateInterface, ExtensionInterface
from scalecodec.base import RuntimeConfigurationObject, ScaleBytes, ScaleType

from .event_hooks import publish_before, publish_after, injector
from .utils import no_operation, NOOP
from bittensor.staging.btsession import NetworkManager
from bittensor.staging.utils import generate_request_token


logger = getLogger(__name__)


class ProxyWrapMeta(type):
    def __new__(cls, name, bases, dct):
        # Wrap class and static methods
        for attribute, value in dct.items():
            if isinstance(value, (staticmethod, classmethod)):
                # Wrap the function inside the staticmethod or classmethod
                original_func = value.__func__
                wrapped_func = cls.wrap_method(original_func)
                dct[attribute] = type(value)(wrapped_func)
        return super().__new__(cls, name, bases, dct)

    @staticmethod
    def wrap_method(method):
        def wrapper(*args, **kwargs):
            print(f"Before static method {method.__name__}")
            result = method(*args, **kwargs)
            print(f"After static method {method.__name__}")
            return result

        return wrapper


class GenericProxy:
    def __init__(
        self,
        proxy_class: Type[Any],
        method_overloads: Optional[Dict[str, Union[Callable[..., Any], bool]]] = None,
        property_overloads: Optional[
            Union[Dict[str, Callable[..., Any]], Dict[str, property]]
        ] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self._proxy_class = proxy_class
        self._method_overloads = (
            method_overloads if method_overloads is not None else {}
        )
        self._property_overloads = (
            property_overloads if property_overloads is not None else {}
        )

        init_cb = self._method_overloads.get("__init__", self._proxy_class.__init__)
        if init_cb is True:
            self._instance = self._proxy_class(*args, **kwargs)
        elif callable(init_cb):
            if inspect.ismethod(init_cb) or inspect.isfunction(init_cb):
                self._instance = init_cb(self, *args, **kwargs)
            else:
                raise TypeError("Provided __init__ overload is not callable.")
        else:
            self._instance = None  # Handle the case where __init__ is not specified or is improperly defined

    def __enter__(self):
        enter_cb = self._method_overloads.get(
            "__enter__", self._instance.__enter__ if self._instance else None
        )
        if callable(enter_cb):
            return enter_cb()
        return self._instance

    def __exit__(self, exc_type, exc_val, exc_tb):
        exit_cb = self._method_overloads.get(
            "__exit__", self._instance.__exit__ if self._instance else None
        )
        if callable(exit_cb):
            return exit_cb(exc_type, exc_val, exc_tb)
        return None

    def __getattr__(self, item: str):
        if item in self._method_overloads:
            method = self._method_overloads[item]
            if method is False:
                return lambda *args, **kwargs: None
            elif method is True:
                return getattr(self._instance, item)
            else:
                return method.__get__(self._instance, self._proxy_class)

        if item in self._property_overloads:
            prop = self._property_overloads[item]
            if callable(prop):
                return prop(self._instance)
            else:
                return prop

        return getattr(self._instance, item)


class SubstrateProxyInterface:
    def __init__(
        self,
        url: str,
        transport: NetworkManager,
        ss58_format=None,
        type_registry=None,
        type_registry_preset=None,
        cache_region=None,
        runtime_config=None,
        use_remote_preset=False,
        ws_options=None,
        auto_discover=True,
        auto_reconnect=True,
        config=None,
    ):
        """
        A specialized class in interfacing with a Substrate node.

        Parameters
        ----------
        url: the URL to the substrate node, either in format https://127.0.0.1:9933 or wss://127.0.0.1:9944
        ss58_format: The address type which account IDs will be SS58-encoded to Substrate addresses. Defaults to 42, for Kusama the address type is 2
        type_registry: A dict containing the custom type registry in format: {'types': {'customType': 'u32'},..}
        type_registry_preset: The name of the predefined type registry shipped with the SCALE-codec, e.g. kusama
        cache_region: a Dogpile cache region as a central store for the metadata cache
        use_remote_preset: When True preset is downloaded from GitHub master, otherwise use files from local installed scalecodec package
        ws_options: dict of options to pass to the websocket-client create_connection function
        config: dict of config flags to overwrite default configuration
        """
        self._proxy = GenericProxy(
            proxy_class=SubstrateInterface,
            method_overloads={
                "__init__": self.__init__,
                "close": NOOP,
            },
        )
        self._pending_requests = {}
        if not url:
            raise ValueError("'url' must be provided")

        self._pending_requests = {}
        self._subscription_handlers = {}

        # Initialize lazy loading variables
        self._proxy.__version = None
        self._proxy.__name = None
        self._proxy.__properties = None
        self._proxy.__chain = None

        self._proxy.__token_decimals = None
        self._proxy.__token_symbol = None
        self._proxy.__ss58_format = None

        if not runtime_config:
            runtime_config = RuntimeConfigurationObject()

        self.runtime_config = runtime_config
        self.transport = transport

        self.cache_region = cache_region

        if ss58_format is not None:
            self._proxy.ss58_format = ss58_format

        self._proxy.type_registry_preset = type_registry_preset
        self._proxy.type_registry = type_registry

        self._proxy.request_id = 1
        self._proxy.url = url
        self._proxy.websocket = None
        self._proxy.ws_options = ws_options or {}

        if "max_size" not in self._proxy.ws_options:
            self._proxy.ws_options["max_size"] = 2**32
        if "read_limit" not in self._proxy.ws_options:
            self._proxy.ws_options["read_limit"] = 2**32
        if "write_limit" not in self._proxy.ws_options:
            self._proxy.ws_options["write_limit"] = 2**32

        self._proxy.__rpc_message_queue = []
        self._proxy.mock_extrinsics = None
        self._proxy.default_headers = {
            "content-type": "application/json",
            "cache-control": "no-cache",
        }

        self._proxy.metadata = None

        self._proxy.runtime_version = None
        self._proxy.transaction_version = None

        self._proxy.block_hash = None
        self._proxy.block_id = None

        self._proxy.__metadata_cache = {}

        self._proxy.config = {
            "use_remote_preset": use_remote_preset,
            "auto_discover": auto_discover,
            "auto_reconnect": auto_reconnect,
            "rpc_methods": None,
            "strict_scale_decode": True,
        }

        if type(config) is dict:
            self._proxy.config.update(config)

        # Initialize extension interface
        self._proxy.extensions = ExtensionInterface(self)

        self._proxy.reload_type_registry(
            use_remote_preset=use_remote_preset, auto_discover=auto_discover
        )

    def connect_websocket(self):
        """
        Checks if an existing websocket exists, creates if not.
        Checks if the websocket is connected to the server, connects if not.
        """
        pass

    def close(self):
        """
        Cleans up resources for this instance like active websocket connection and active extensions

        Returns
        -------

        """
        pass

    @staticmethod
    def debug_message(message: str):
        """
        Submits a message to the debug logger

        Parameters
        ----------
        message: str Debug message

        Returns
        -------

        """
        logger.debug(message)

    def supports_rpc_method(self, name: str) -> bool:
        """
        Check if substrate RPC supports given method
        Parameters
        ----------
        name: name of method to check

        Returns
        -------
        bool
        """
        if self._proxy.config.get("rpc_methods") is None:
            self._proxy.config["rpc_methods"] = []
            result = self.rpc_request("rpc_methods", []).get("result")
            if result:
                self._proxy.config["rpc_methods"] = result.get("methods", [])

        return name in self._proxy.config["rpc_methods"]


    async def _wait_for_response(self, response_event: asyncio.Event) -> None:
        """
        Waits for the response to the RPC request to be processed by the callback.

        Parameters
        ----------
        response_event : asyncio.Event
            The event to wait on until the response is received and processed.
        """
        await response_event.wait()

    def _default_result_handler(self, request_id: str) -> Callable[[Any], None]:
        """
        Generates a default result handler that logs the response.

        Parameters
        ----------
        request_id : str
            The request ID for which the handler is being generated.

        Returns
        -------
        Callable[[Any], None]
            A callback function that logs the response.
        """
        return lambda response: logger.info(f"Response for #{request_id}: {response}")

    def debug_message(self, message: str) -> None:
        """
        Logs a debug message.

        Parameters
        ----------
        message : str
            The debug message to log.
        """
        logger.debug(message)


patch = gorilla.Patch(
    substrateinterface,
    "SubstrateProxyInterface",
    SubstrateInterface,
    settings=gorilla.Settings(allow_hit=True),
)

# Step 3: Apply the patch
gorilla.apply(patch)
