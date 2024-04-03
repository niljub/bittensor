# sub_subtensor.py
import asyncio
import dataclasses
import importlib.abc
import inspect
import logging
import queue
import sys
import threading
import time
import typing as t
from asyncio import Event, Queue, Task
from dataclasses import dataclass
from logging import getLogger
from typing import Any, Callable, Dict, List, Optional, Type, Union

import aiohttp
import bittensor
import orjson as json
import substrateinterface
from aiohttp import ClientWebSocketResponse, WSMsgType, web
from scalecodec.base import RuntimeConfigurationObject, ScaleBytes, ScaleType
from substrateinterface.exceptions import (
    BlockNotFound,
    ConfigurationError,
    ExtrinsicNotFound,
    ExtensionCallNotFound,
    StorageFunctionNotFound,
    SubstrateRequestException,
)
from substrateinterface.interfaces import ExtensionInterface
from websocket import WebSocketConnectionClosedException, create_connection

logger = getLogger(__name__)
from functools import wraps
from typing import Any, Callable

from .event_hooks import publish_before, publish_after, injector
from .utils import no_operation, NOOP






class JSONRPCProxyClient:
    """
    An asynchronous JSON RPC proxy client that communicates via websockets,
    supporting both call/response and publish/subscribe mechanisms. It reads
    requests from an input asyncio queue, sends them to the server, and writes
    responses or subscriptions data to an output asyncio queue.

    Attributes:
        uri (str): The websocket URI to connect to.
        input_queue (asyncio.Queue): Queue for incoming messages to be sent.
        output_queue (asyncio.Queue): Queue for outgoing messages received from the server.
    """
    task: asyncio.Task = None
    init_done_event: asyncio.Event
    ws_handler: t.Optional[WSConnectionHandler]
    errors: list

    def __init__(
        self,
        url: str,
        *,
        logger: Optional[logging.Logger] = None,
        session_kwargs: Optional[dict[str, t.Any]] = None,
        connection_kwargs: Optional[dict[str, t.Any]] = None,
        ws_msg_type=aiohttp.WSMsgType.TEXT,
        receive_queue: Optional[asyncio.Queue] = None,
        send_queue: Optional[asyncio.Queue] = None,
    ) -> None:
        self.url = url
        self.receive_queue = receive_queue
        self.send_queue = send_queue
        self.session_kwargs = session_kwargs or {}
        self.conn_kwargs = connection_kwargs or {}
        self.ws_msg_type = ws_msg_type
        self.logger = logger
        self.session = aiohttp.ClientSession(session_kwargs)
        self.ws_handler = None
        self.errors = []
        self.init_done_event = asyncio.Event()

    async def connect(self, connect_cb=NOOP) -> None:
        """
        Connects to the websocket and starts listening for incoming and outgoing messages.
        """
        try:
            async with aiohttp.ClientSession(**self.session_kwargs) as session:
                async with session.ws_connect(self.url, **self.conn_kwargs) as ws:
                    ws_handler = WSConnectionHandler(
                        ws,
                        logger=logger,
                        ws_msg_type=self.ws_msg_type,
                        receive_queue=self.receive_queue,
                        send_queue=self.send_queue,
                    )
                    if callable(connect_cb):
                        connect_cb(ws_handler)
                    await ws_handler.run_loop()
        except aiohttp.ClientError as e:
            self.errors.append(e)


    async def _read_from_queue_and_send(self) -> None:
        """
        Reads JSON RPC requests from the input queue and sends them to the server.
        """
        while True:
            message = await self.send_queue.get()
            if message is None:
                break
            await self.ws.send_json(message)

    async def _receive_and_write_to_queue(self) -> None:
        """
        Receives messages from the server and writes them to the output queue.
        """
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await self.output_queue.put(json.loads(msg.data))
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                break
            elif msg.type == aiohttp.WSMsgType.ERROR:
                break

    async def close(self) -> None:
        """
        Closes the websocket connection and the aiohttp client session.
        """
        await self.ws.close()
        await self.session.close()

    async def __aenter__(self) -> 'JSONRPCProxyClient':
        """
        Enables use of the client using async with statement.
        """
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """
        Ensures resources are released when exiting the async with context.
        """
        # await self.close()


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


class ProxyMeta(type):
    """
    Metaclass for creating a proxy that can dynamically intercept and manage
    method calls, property accesses, and attribute accesses.
    """

    def __call__(cls, *args, **kwargs):
        obj = cls.__new__(cls, __name="Generic Proxy", __namespace="bittensor", __module__="bittensor.sub_subtensor", __qualname__="")
        obj.__init__(*args, **kwargs)
        return obj


class GenericProxy(metaclass=ProxyMeta):
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


class SubstrateProxyInterface:

    def __init__(self, url=None, websocket=None, ss58_format=None, type_registry=None, type_registry_preset=None,
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
            method_overloads={"__init__": self.__init__, "__enter__": self.__enter__, "__exit__": NOOP, "close": NOOP, }
        )

        if not url:
            raise ValueError("'url' must be provided")

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

        self.cache_region = cache_region

        if ss58_format is not None:
            self._proxy.ss58_format = ss58_format

        self._proxy.type_registry_preset = type_registry_preset
        self._proxy.type_registry = type_registry

        self._proxy.request_id = 1
        self._proxy.url = url
        self._proxy.websocket = None
        self._proxy.ws_options = ws_options or {}

        if 'max_size' not in self._proxy.ws_options:
            self._proxy.ws_options['max_size'] = 2 ** 32
        if 'read_limit' not in self._proxy.ws_options:
            self._proxy.ws_options['read_limit'] = 2 ** 32
        if 'write_limit' not in self._proxy.ws_options:
            self._proxy.ws_options['write_limit'] = 2 ** 32

        self._proxy.__rpc_message_queue = []
        self._proxy.mock_extrinsics = None
        self._proxy.default_headers = {
            'content-type': "application/json",
            'cache-control': "no-cache"
        }

        self._proxy.metadata = None

        self._proxy.runtime_version = None
        self._proxy.transaction_version = None

        self._proxy.block_hash = None
        self._proxy.block_id = None

        self._proxy.__metadata_cache = {}

        self._proxy.config = {
            'use_remote_preset': use_remote_preset,
            'auto_discover': auto_discover,
            'auto_reconnect': auto_reconnect,
            'rpc_methods': None,
            'strict_scale_decode': True
        }

        if type(config) is dict:
            self._proxy.config.update(config)

        # Initialize extension interface
        self._proxy.extensions = ExtensionInterface(self)

        self._proxy.session = aiohttp.ClientSession()

        self._proxy.reload_type_registry(use_remote_preset=use_remote_preset, auto_discover=auto_discover)

    def connect_websocket(self):
        """
        Checks if an existing websocket exists, creates if not.
        Checks if the websocket is connected to the server, connects if not.
        """

        if not self.websocket:


        if self._proxy.url and (self._proxy.url[0:6] == 'wss://' or self._proxy.url[0:5] == 'ws://'):
            self.debug_message("Connecting to {} ...".format(self._proxy.url))
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

    @injector.inject
    @publish_after(topic="after_substrate_request")
    @publish_before(topic="before_substrate_request")
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
                for message, remove_message in list_remove_iter(self._proxy.__rpc_message_queue):

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
                for message, remove_message in list_remove_iter(self._proxy.__rpc_message_queue):
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
                    self._proxy.__rpc_message_queue.append(json.loads(self.websocket.recv()))

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

