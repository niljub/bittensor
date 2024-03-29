import threading
import queue
import time
import gorilla
import websocket
import importlib.abc
import sys
import inspect
from typing import Callable, List, Optional, Any, Dict, Union, Type
import bittensor
import substrateinterface
from logging import getLogger
import aiohttp

from websocket import create_connection, WebSocketConnectionClosedException

from scalecodec.base import ScaleBytes, RuntimeConfigurationObject, ScaleType
from scalecodec.types import GenericCall, GenericExtrinsic, Extrinsic, MultiAccountId, GenericRuntimeCallDefinition
from scalecodec.type_registry import load_type_registry_preset
from scalecodec.updater import update_type_registries
from substrateinterface.extensions import Extension
from substrateinterface.interfaces import ExtensionInterface

from substrateinterface.storage import StorageKey

from substrateinterface.exceptions import SubstrateRequestException, ConfigurationError, StorageFunctionNotFound, BlockNotFound, ExtrinsicNotFound, ExtensionCallNotFound
from substrateinterface.constants import *
from substrateinterface.keypair import Keypair, KeypairType, MnemonicLanguageCode
from substrateinterface.utils.ss58 import ss58_decode, ss58_encode, is_valid_ss58_address, get_ss58_format
logger = getLogger(__name__)


class LazyProperty(object):

    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            value = self.func(instance)
            setattr(instance, self.func.__name__, value)
            return value


class LazyLoader(importlib.abc.Loader):
    """
    A loader that defers the loading of a module until an attribute is accessed.
    """

    def __init__(self, fullname: str, path: Optional[str]):
        self.module_name = fullname
        self.path = path

    def create_module(self, spec):
        # Create a new module object, but don't initialize it yet.
        return None

    def exec_module(self, module):
        # Replace the module's class with a subclass that uses __getattr__
        # to load the module upon first attribute access.
        module.__class__ = LazyModule
        module.__dict__["_lazy_name"] = self.module_name
        module.__dict__["_lazy_loaded"] = False


class LazyModule(importlib.abc.Loader):
    """
    Subclass of the module type that loads the actual module upon first attribute access.
    """

    def __getattr__(self, name):
        if "_lazy_loaded" not in self.__dict__:
            self.__dict__["_lazy_loaded"] = True
            loader = importlib.machinery.SourceFileLoader(
                self.__dict__["_lazy_name"], self.__dict__["_lazy_name"]
            )
            loader.exec_module(self)
        return getattr(self, name)


class LazyImportFinder(importlib.abc.MetaPathFinder):
    """
    A meta_path finder to support lazy loading of modules.
    """

    def __init__(self, to_lazy_load: List[str]):
        self.to_lazy_load = to_lazy_load

    def find_spec(self, fullname, path, target=None):
        if fullname in self.to_lazy_load:
            return importlib.machinery.ModuleSpec(fullname, LazyLoader(fullname, path))


def install_lazy_loader(to_lazy_load: List[str]):
    """
    Install the lazy loader for the specified modules.

    Args:
    to_lazy_load (List[str]): A list of fully qualified module names to lazy load.
    """
    sys.meta_path.insert(0, LazyImportFinder(to_lazy_load))


def NOOP(*args, **kwargs):
    """Empty callback function (no-operation)"""
    pass


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


class GenericProxy(metaclass=ProxyWrapMeta):
    def __init__(
            self,
            proxy_class: Type[Any],
            method_overloads: Optional[Dict[str, Union[Callable[..., Any], bool]]] = None,
            property_overloads: Optional[Union[Dict[str, Callable[..., Any]], Dict[str, property]]] = None,
            *args: Any,
            **kwargs: Any
    ) -> None:
        self._proxy_class = proxy_class
        self._method_overloads = method_overloads if method_overloads is not None else {}
        self._property_overloads = property_overloads if property_overloads is not None else {}

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
        enter_cb = self._method_overloads.get("__enter__", self._instance.__enter__ if self._instance else None)
        if callable(enter_cb):
            return enter_cb()
        return self._instance

    def __exit__(self, exc_type, exc_val, exc_tb):
        exit_cb = self._method_overloads.get("__exit__", self._instance.__exit__ if self._instance else None)
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




class SingletonWebSocket:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SingletonWebSocket, cls).__new__(cls)
        return cls._instance

    def __init__(self, url: str, check_interval: int = 1):
        self._url = url
        self._check_interval = check_interval
        self._ws = None
        self._input_queue = queue.Queue()
        self._output_queue = queue.Queue()
        self._callbacks = {}
        self._is_running = False
        self._start()

    def _start(self):
        if not self._is_running:
            self._ws = websocket.WebSocketApp(self._url,
                                              on_message=self._on_message)
            self._thread = threading.Thread(target=self._ws.run_forever)
            self._thread.start()
            self._process_queues_thread = threading.Thread(target=self._process_queues)
            self._process_queues_thread.start()
            self._is_running = True

    def send(self, data: str):
        self._input_queue.put(data)

    def register_callback(self, event: str, callback: Callable[[Dict[str, Any]], None]):
        self._callbacks[event] = callback

    def _on_message(self, ws, message):
        self._output_queue.put(message)

    def _process_queues(self):
        while self._is_running:
            try:
                while not self._input_queue.empty():
                    message = self._input_queue.get_nowait()
                    self._ws.send(message)
                while not self._output_queue.empty():
                    message = self._output_queue.get_nowait()
                    event = message.get('method')
                    if event in self._callbacks:
                        self._callbacks[event](message)
            except queue.Empty:
                pass
            time.sleep(self._check_interval)

    def _shutdown_websocket(self):
        self._is_running = False
        self._ws.close()
        self._thread.join()
        self._process_queues_thread.join()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def close(self):
        pass


def apply_patch():
    settings = gorilla.Settings(allow_hit=True)
    patch = gorilla.Patch(websocket, 'WebSocketApp', SingletonWebSocket, settings=settings)
    gorilla.apply(patch)

apply_patch()


class SubstrateProxyInterface():

    def __init__(self, proxy_class=None, method_overloads=None, property_overloads=None, url=None, websocket=None, ss58_format=None, type_registry=None, type_registry_preset=None,
                 cache_region=None, runtime_config=None, use_remote_preset=False, ws_options=None,
                 auto_discover=True, auto_reconnect=True, config=None):
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
            proxy_class=substrateinterface.SubstrateInterface,
            method_overloads={"__init__": self.__init__, "__enter__": self.__enter__, "__exit__": self, "close": NOOP, }
        )

        if not url:
            raise ValueError("'url' must be provided")

        # Initialize lazy loading variables
        self.__version = None
        self.__name = None
        self.__properties = None
        self.__chain = None

        self.__token_decimals = None
        self.__token_symbol = None
        self.__ss58_format = None

        if not runtime_config:
            runtime_config = RuntimeConfigurationObject()

        self.runtime_config = runtime_config

        self.cache_region = cache_region

        if ss58_format is not None:
            self.ss58_format = ss58_format

        self.type_registry_preset = type_registry_preset
        self.type_registry = type_registry

        self.request_id = 1
        self.url = url
        self.websocket = None

        # Websocket connection options
        self.ws_options = ws_options or {}

        # Websocket connection options
        self.ws_options = {}

        if 'max_size' not in self.ws_options:
            self.ws_options['max_size'] = 2 ** 32

        if 'read_limit' not in self.ws_options:
            self.ws_options['read_limit'] = 2 ** 32

        if 'write_limit' not in self.ws_options:
            self.ws_options['write_limit'] = 2 ** 32

        self.__rpc_message_queue = []

        if self.url and (self.url[0:6] == 'wss://' or self.url[0:5] == 'ws://'):
            self.connect_websocket()

        elif websocket:
            self.websocket = websocket

        self.mock_extrinsics = None
        self.default_headers = {
            'content-type': "application/json",
            'cache-control': "no-cache"
        }

        self.metadata = None

        self.runtime_version = None
        self.transaction_version = None

        self.block_hash = None
        self.block_id = None

        self.__metadata_cache = {}

        self.config = {
            'use_remote_preset': use_remote_preset,
            'auto_discover': auto_discover,
            'auto_reconnect': auto_reconnect,
            'rpc_methods': None,
            'strict_scale_decode': True
        }

        if type(config) is dict:
            self.config.update(config)


        # Initialize extension interface
        self.extensions = ExtensionInterface(self)

        self.session = requests.Session()

        self.reload_type_registry(use_remote_preset=use_remote_preset, auto_discover=auto_discover)

    def connect_websocket(self):
        """
        (Re)creates the websocket connection, if the URL contains a 'ws' or 'wss' scheme

        Returns
        -------

        """
        if self.url and (self.url[0:6] == 'wss://' or self.url[0:5] == 'ws://'):
            self.debug_message("Connecting to {} ...".format(self.url))
            self.websocket = create_connection(
                self.url,
                **self.ws_options
            )

    def close(self):
        """
        Cleans up resources for this instance like active websocket connection and active extensions

        Returns
        -------

        """
        if self.websocket:
            self.debug_message("Closing websocket connection")
            self.websocket.close()

        self.extensions.unregister_all()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

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
        if self.config.get('rpc_methods') is None:
            self.config['rpc_methods'] = []
            result = self.rpc_request("rpc_methods", []).get('result')
            if result:
                self.config['rpc_methods'] = result.get('methods', [])

        return name in self.config['rpc_methods']

    def rpc_request(self, method, params, result_handler=None):
        """
        Method that handles the actual RPC request to the Substrate node. The other implemented functions eventually
        use this method to perform the request.

        Parameters
        ----------
        result_handler: Callback function that processes the result received from the node
        method: method of the JSONRPC request
        params: a list containing the parameters of the JSONRPC request

        Returns
        -------
        a dict with the parsed result of the request.
        """

        request_id = self.request_id
        self.request_id += 1

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }

        self.debug_message('RPC request #{}: "{}"'.format(request_id, method))

        if self.websocket:
            try:
                self.websocket.send(json.dumps(payload))
            except WebSocketConnectionClosedException:
                if self.config.get('auto_reconnect') and self.url:
                    # Try to reconnect websocket and retry rpc_request
                    self.debug_message("Connection Closed; Trying to reconnecting...")
                    self.connect_websocket()

                    return self.rpc_request(method=method, params=params, result_handler=result_handler)
                else:
                    # websocket connection is externally created, re-raise exception
                    raise

            update_nr = 0
            json_body = None
            subscription_id = None

            while json_body is None:
                # Search for subscriptions
                for message, remove_message in list_remove_iter(self.__rpc_message_queue):

                    # Check if result message is matching request ID
                    if 'id' in message and message['id'] == request_id:

                        remove_message()

                        # Check if response has error
                        if 'error' in message:
                            raise SubstrateRequestException(message['error'])

                        # If result handler is set, pass result through and loop until handler return value is set
                        if callable(result_handler):

                            # Set subscription ID and only listen to messages containing this ID
                            subscription_id = message['result']
                            self.debug_message(f"Websocket subscription [{subscription_id}] created")

                        else:
                            json_body = message

                # Process subscription updates
                for message, remove_message in list_remove_iter(self.__rpc_message_queue):
                    # Check if message is meant for this subscription
                    if 'params' in message and message['params']['subscription'] == subscription_id:

                        remove_message()

                        self.debug_message(f"Websocket result [{subscription_id} #{update_nr}]: {message}")

                        # Call result_handler with message for processing
                        callback_result = result_handler(message, update_nr, subscription_id)
                        if callback_result is not None:
                            json_body = callback_result

                        update_nr += 1

                # Read one more message to queue
                if json_body is None:
                    self.__rpc_message_queue.append(json.loads(self.websocket.recv()))

        else:

            if result_handler:
                raise ConfigurationError("Result handlers only available for websockets (ws://) connections")

            response = self.session.request("POST", self.url, data=json.dumps(payload), headers=self.default_headers)

            if response.status_code != 200:
                raise SubstrateRequestException(
                    "RPC request failed with HTTP status code {}".format(response.status_code))

            json_body = response.json()

            # Check if response has error
            if 'error' in json_body:
                raise SubstrateRequestException(json_body['error'])

        return json_body




class SubstrateInterfaceWrapper:
    def __new__(cls, *args, **kwargs):
        methods = {"__init__": True, "__exit__": NOOP, "add_args": True, "config": True, "help": True}

        return GenericProxy(
            substrateinterface.SubstrateInterface,
            method_overloads=methods,
            *args,
            **kwargs
        )


class SubtensorWrapper(metaclass=ProxyMeta):
    def __new__(cls, *args, **kwargs):
        methods = {"__init__": True, "__exit__": NOOP, "add_args": True, "config": True, "help": True}

        return GenericProxy(
            substrateinterface.SubstrateInterface,
            method_overloads=methods,
            *args,
            **kwargs
        )

substrateinterface.SubstrateInterface = SubstrateInterfaceWrapper
bittensor.subtensor = SubtensorWrapper

