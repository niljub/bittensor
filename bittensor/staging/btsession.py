import asyncio
import logging
import typing as t
import time
from asyncio import Event, Queue, Task
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type, Union
from contextlib import asynccontextmanager
from injector import inject, Injector, provider, Module, singleton
import websockets
from bittensor.staging.exceptions import (
    NetworkUnavailable,
    NetworkUnreachable,
    MessagesExceededException,
    RetriesExceededException,
)
from bittensor.staging.transport import WebSocketTransport


@dataclass
class NetworkStats:
    """Dataclass to keep track of Network connection statistics.

    Attributes:
        n_recv (int): Number of messages received.
        n_recv_format_errors (int): Number of received messages with format errors.
        n_sent (int): Number of messages sent.
        n_send_format_errors (int): Number of sent messages with format errors.
        n_ignored (int): Number of messages ignored.
    """

    n_recv: int = 0
    n_recv_format_errors: int = 0
    n_sent: int = 0
    n_send_format_errors: int = 0
    n_ignored: int = 0


class NetworkMessageHandler:
    """Handles sending and receiving Network messages in an async manner.

    This class manages Network messges. It handles message sending and receiving
    through asyncio queues, tracks connection statistics, and manages
    connection lifecycle events such as close requests.

    Attributes:
        network_response (Union[ClientWebSocketResponse, web.WebSocketResponse]): The Network response object.
        receive_queue (asyncio.Queue): Queue for incoming messages.
        send_queue (asyncio.Queue): Queue for outgoing messages.
        stats (Stats): Connection statistics.
        socket_errors (List[Any]): List to track socket errors.

    """

    @inject
    def __init__(
        self,
        send_queue: Queue,
        recv_queue: Queue,
        network_response,
    ):
        self.send_queue = send_queue
        self.recv_queue = recv_queue
        self.websocket = None
        self._close_requested = Event()
        self._sender_task: t.Optional[Task] = None
        self._stop_watcher_task: t.Optional[Task] = None
        self.logger = logging.getLogger()
        self.send_queue = send_queue
        self.socket_errors: t.List[t.Any] = []
        self.stats = NetworkStats()

    async def handler(websocket):
        consumer_task = asyncio.create_task(consumer_handler(websocket))
        producer_task = asyncio.create_task(producer_handler(websocket))
        done, pending = await asyncio.wait(
            [consumer_task, producer_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()

    async def consume(self):
        # Handle incoming messages
        async for msg in self.websocket:
            await self.recv_queue.put(msg.data)

    async def produce(self):
        # Handle outgoing messages
        while True:
            message = await self.send_queue.get()
            await self.websocket.send_str(message)

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
                await self.network_response.send_str(message)
                self.stats.n_sent += 1
        except Exception as e:
            self.socket_errors.append(e)
        finally:
            await self._close()

    async def _receive_loop(self) -> None:
        """Coroutine to handle receiving messages from the WebSocket and putting them into the receive queue."""
        try:
            async for msg in self.network_response:
                await self.receive_queue.put(msg.data)
                self.stats.n_recv += 1
        except Exception as e:
            self.socket_errors.append(e)
        finally:
            await self._close()

    async def _watch_for_stop(self) -> None:
        """Coroutine to monitor for a stop event, triggering cleanup when received."""
        await self._close_requested.wait()
        await self._close()

    async def _close(self) -> None:
        """Cleans up tasks and the WebSocket connection, preparing for shutdown."""
        if not self.network_response.closed:
            await self.network_response.close()
        if self._sender_task and not self._sender_task.done():
            self._sender_task.cancel()
        if self._stop_watcher_task and not self._stop_watcher_task.done():
            self._stop_watcher_task.cancel()


class ClientSessionModule(Module):
    @provider
    def provide_message_handler(self) -> NetworkMessageHandler:
        return NetworkMessageHandler()

    @provider
    def provide_send_queue(self) -> Queue:
        return asyncio.Queue()

    @provider
    def provide_recv_queue(self) -> Queue:
        return asyncio.Queue()


class NetworkManager:
    task: asyncio.Task = None
    init_done_event: asyncio.Event
    msg_handler: t.Optional[NetworkMessageHandler]
    errors: list

    @inject
    def __init__(
        self,
        network: str,
        send_queue: Queue,
        recv_queue: Queue,
        msg_handler: NetworkMessageHandler,
        retry_delay: int = 4,
    ):
        self.network = network
        self.recv_queue = recv_queue
        self.send_queue = send_queue
        self.msg_handler = msg_handler
        self.errors = []
        self.init_done_event = asyncio.Event()
        self.callbacks = {}
        self.transport = None
        self._is_running = False
        self._retry_delay = retry_delay or 4

    async def connect(self):
        if not self._is_running:
            self._is_running = True

    async def send_rpc(self, message):
        await self.send_queue.put(message)

    async def register_callback(
        self, event: str, callback: Callable[[Dict[str, Any]], None]
    ):
        self.callbacks[event] = callback

    async def _on_message(self, ws, message):
        await self.send_queue.put(message)

    async def _process_queues(self):
        while self._is_running:
            try:
                while not self.send_queue.empty():
                    message = self.send_queue.get_nowait()
                    self._ws.send(message)
                while not self.recv_queue.empty():
                    message = self.recv_queue.get_nowait()
                    event = message.get("method")
                    if event in self.callbacks:
                        self.callbacks[event](message)
            except asyncio.QueueFull as exc:
                raise MessagesExceededException from exc
            await asyncio.sleep(self._retry_delay)

    def _shutdown_websocket(self):
        self._is_running = False
        self._ws.close()
        self.recv_queue.join()
        self.send_queue.join()


class NetworkModule(Module):
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
    def provide_network_response(self) -> Callable:
        """Provides the network_response handler."""

        def network_response_handler(message):
            print(f"Received message: {message}")

        return network_response_handler

    @provider
    def provide_network_message_handler(
        self,
        send_queue: Queue,
        recv_queue: Queue,
        network_response_handler: Callable,
    ) -> NetworkMessageHandler:
        """Provides an instance of NetworkMessageHandler with all required dependencies."""
        return NetworkMessageHandler(send_queue, recv_queue, network_response_handler)

    @provider
    def provide_network_manager_factory(
        self,
        send_queue: Queue,
        recv_queue: Queue,
        network_message_handler: NetworkMessageHandler,
    ) -> Callable[[str], NetworkManager]:
        """
        Provides a factory function for creating NetworkManager instances.
        """

        def factory(network: str) -> NetworkManager:
            return NetworkManager(
                network, send_queue, recv_queue, network_message_handler
            )

        return factory


@inject
@asynccontextmanager
async def managed_network(injector: Injector, url: str, *args, **kwargs):
    # Use the factory function to get a NetworkManager with the given URL
    factory = injector.get(Callable[[str], NetworkManager])
    network_manager = factory(url)
    # TODO: implement logic to determine whether or not btcli session is stateless
    try:
        await network_manager.connect()
        yield network_manager
    finally:
        await network_manager.disconnect()
