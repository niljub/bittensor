from aiohttp import ClientSession, ClientWebSocketResponse, WSMsgType, web
import asyncio
import logging
import typing as t
from asyncio import Event, Queue, Task
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type, Union
from contextlib import asynccontextmanager
from injector import inject, Injector, provider, Module, singleton


@dataclass
class SocketStats:
    """Dataclass to keep track of WebSocket connection statistics.

    Attributes:
        n_received (int): Number of messages received.
        n_receive_format_errors (int): Number of received messages with format errors.
        n_sent (int): Number of messages sent.
        n_send_format_errors (int): Number of sent messages with format errors.
        n_ignored (int): Number of messages ignored.
    """
    n_received: int = 0
    n_receive_format_errors: int = 0
    n_sent: int = 0
    n_send_format_errors: int = 0
    n_ignored: int = 0


class WSMessageHandler:
    """Handles WebSocket connections, both sending and receiving messages, in an async manner.

    This class manages WebSocket connections, supporting both server and client side operations. It handles
    message sending and receiving through asyncio queues, tracks connection statistics, and manages
    connection lifecycle events such as close requests.

    Attributes:
        ws_response (Union[ClientWebSocketResponse, web.WebSocketResponse]): The WebSocket response object.
        receive_queue (asyncio.Queue): Queue for incoming messages.
        send_queue (asyncio.Queue): Queue for outgoing messages.
        stats (Stats): Connection statistics.
        socket_errors (List[Any]): List to track socket errors.

    """
    MAX_INVALID_REQUESTS = 5

    @inject
    def __init__(self, session: ClientSession, send_queue: Queue, recv_queue: Queue, ws_response, receive_queue):
        self.session = session
        self.send_queue = send_queue
        self.recv_queue = recv_queue
        self.websocket = None
        self._close_requested = Event()
        self._sender_task: t.Optional[Task] = None
        self._stop_watcher_task: t.Optional[Task] = None
        self.logger = logging.getLogger()
        self.ws_response = ws_response
        self.receive_queue = receive_queue
        self.send_queue = send_queue
        self.socket_errors: t.List[t.Any] = []
        self.stats = SocketStats()

    async def consume(self):
        # Handle incoming messages
        async for msg in self.websocket:
            await self.recv_queue.put(msg.data)

    async def produce(self):
        # Handle outgoing messages
        while True:
            message = await self.send_queue.get()
            await self.websocket.send_str(message)

    def ws_response_repr(self) -> str:
        """Generates a string representation of the WebSocket response object.

        Returns:
            str: String representation of the WebSocket response.
        """
        if isinstance(self.ws_response, web.WebSocketResponse):
            return f"<WebSocketResponse object at {hex(id(self.ws_response))}>"
        return str(self.ws_response)

    async def run_loop(self) -> None:
        """Main loop for handling incoming and outgoing WebSocket messages.

        This coroutine sets up tasks for sending and receiving messages over the WebSocket connection,
        and monitors these tasks until a close request is made or an error occurs.
        """
        self._sender_task = asyncio.create_task(self._send_loop())
        self._stop_watcher_task = asyncio.create_task(self._watch_for_stop())

        await asyncio.gather(
            self._receive_loop(),
            self._sender_task,
            self._stop_watcher_task,
            return_exceptions=True,
        )

    async def _send_loop(self) -> None:
        """Coroutine to handle sending messages from the send queue over the WebSocket."""
        try:
            while not self._close_requested.is_set():
                message = await self.send_queue.get()
                if message is None:  # A None value is used to signal shutdown.
                    break
                await self.ws_response.send_str(message)  # Assuming messages are always strings.
                self.stats.n_sent += 1
        except Exception as e:
            self.socket_errors.append(e)
            self._logger.error(f"Send loop error: {e}")
        finally:
            await self._close()

    async def _receive_loop(self) -> None:
        """Coroutine to handle receiving messages from the WebSocket and putting them into the receive queue."""
        try:
            async for msg in self.ws_response:
                if msg.type == self._ws_msg_type:
                    await self.receive_queue.put(msg.data)
                    self.stats.n_received += 1
                else:
                    self.stats.n_ignored += 1
        except Exception as e:
            self.socket_errors.append(e)
            self._logger.error(f"Receive loop error: {e}")
        finally:
            await self._close()

    async def _watch_for_stop(self) -> None:
        """Coroutine to monitor for a stop event, triggering cleanup when received."""
        await self._close_requested.wait()
        await self._close()

    async def _close(self) -> None:
        """Cleans up tasks and the WebSocket connection, preparing for shutdown."""
        if not self.ws_response.closed:
            await self.ws_response.close()
        if self._sender_task and not self._sender_task.done():
            self._sender_task.cancel()
        if self._stop_watcher_task and not self._stop_watcher_task.done():
            self._stop_watcher_task.cancel()


class ClientSessionModule(Module):
    @provider
    def provide_client_session(self) -> ClientSession:
        return ClientSession()

    @provider
    def provide_message_handler(self) -> WSMessageHandler:
        return WSMessageHandler()

    @provider
    def provide_send_queue(self) -> Queue:
        return asyncio.Queue()

    @provider
    def provide_recv_queue(self) -> Queue:
        return asyncio.Queue()


class NetworkManager:
    task: asyncio.Task = None
    init_done_event: asyncio.Event
    ws_handler: t.Optional[WSMessageHandler]
    errors: list

    @inject
    def __init__(
            self,
            network: str,
            session: ClientSession,
            send_queue: Queue,
            recv_queue: Queue,
            ws_handler: WSMessageHandler
    ):
        self.network = network
        self.recv_queue = recv_queue
        self.send_queue = send_queue
        self.ws_handler = ws_handler
        self.errors = []
        self.init_done_event = asyncio.Event()
        self.session = session
        self.websocket = None

    async def __aenter__(self):
        self.websocket = await self.session.ws_connect(self.network)
        return self

    async def connect(self):
        self.websocket = await self.session.ws_connect(self.network)
        return self

    async def disconnect(self):
        if self.websocket is not None:
            await self.websocket.close()
        await self.session.close()

    async def __aexit__(self, exc_type, exc, tb):
        if self.websocket is not None:
            await self.websocket.close()
        await self.session.close()


class NetworkModule(Module):
    @provider
    @singleton
    def provide_client_session(self) -> ClientSession:
        """Provides a singleton ClientSession instance for WebSocket connections."""
        return ClientSession()

    @provider
    def provide_send_queue(self) -> Queue:
        """Provides an asyncio Queue for sending messages."""
        return asyncio.Queue()

    @provider
    def provide_recv_queue(self) -> Queue:
        """Provides an asyncio Queue for receiving messages."""
        return asyncio.Queue()

    @provider
    def provide_receive_queue(self) -> Queue:
        """Provides an asyncio Queue for receiving messages, separate from recv_queue if needed."""
        return asyncio.Queue()

    @provider
    def provide_ws_response(self) -> Callable:
        """Provides the ws_response handler. Adjust the implementation based on your application's needs."""
        # Placeholder implementation, replace with your actual ws_response logic
        def ws_response_handler(message):
            print(f"Received message: {message}")
        return ws_response_handler

    @provider
    def provide_ws_message_handler(
        self,
        session: ClientSession,
        send_queue: Queue,
        recv_queue: Queue,
        ws_response: Callable,
        receive_queue: Queue
    ) -> WSMessageHandler:
        """Provides an instance of WSMessageHandler with all required dependencies."""
        return WSMessageHandler(session, send_queue, recv_queue, ws_response, receive_queue)

    @provider
    def provide_network_manager_factory(
        self,
        session: ClientSession,
        send_queue: Queue,
        recv_queue: Queue,
        ws_message_handler: WSMessageHandler
    ) -> Callable[[str], NetworkManager]:
        """
        Provides a factory function for creating NetworkManager instances.
        """
        def factory(network: str) -> NetworkManager:
            return NetworkManager(network, session, send_queue, recv_queue, ws_message_handler)
        return factory


@asynccontextmanager
async def managed_network(injector: Injector, url: str, *args, **kwargs):
    # Use the factory function to get a NetworkManager with the given URL
    factory = injector.get(Callable[[str], NetworkManager])
    ws_manager = factory(url)
    try:
        await ws_manager.connect()
        yield ws_manager
    finally:
        await ws_manager.disconnect()
