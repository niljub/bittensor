import asyncio
import json
import os
import shutil
import inspect
import tempfile
import threading

from asyncio import Queue, Task
from pathlib import Path
from typing import (
    Any,
    Optional,
    Dict,
    List,
    Tuple,
    Union,
    Type,
    Coroutine,
    TypeVar,
    cast,
    Callable,
)
from logging import getLogger
from uuid import uuid4

from bittensor.staging.transport import (
    Transport,
    WebSocketTransport,
    AioWebSocketTransport,
    RetryableError,
    FatalError,
    TransportError,
)
from bittensor.staging.socket_overload import socket
from bittensor.staging.sub_subtensor import SubstrateInterface, SubstrateProxyInterface
from bittensor.staging.utils import generate_request_token

DEFAULT_NETWORK = "finney.opentensor.ai"
logger = getLogger(__name__)
lock = threading.Lock()


class NetworkManager:
    """
    Manages network communication with retry logic and persistent storage for overflow.
    """

    def __init__(
        self,
        transport: Transport,
        network: Optional[str] = None,
        queue_size: int = 1024,
    ) -> None:
        self.transport: Transport = transport
        self.send_queue: Queue = Queue(maxsize=queue_size)
        self.receive_queue: Queue = Queue(maxsize=queue_size)
        self.callbacks: Dict[str, Callable[[Any], None]] = {}
        self.storage_dir: Path = Path(tempfile.mkdtemp(prefix="network_manager_"))
        self.network = network or DEFAULT_NETWORK
        self.accept_data: bool = True
        self.rpc_methods: dict = {}
        self.send_task: Optional[Task] = None
        self.receive_task: Optional[Task] = None
        self.subscriptions: dict = {}
        # self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

        self.loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        t = threading.Thread(target=self.start_loop, args=(self.loop,))
        t.start()

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def register_transport(self, transport: Transport) -> None:
        """Register a new transport mechanism."""
        self.transport = transport(self.network)

    def start(self) -> None:
        """Start background tasks for sending and receiving data."""
        self.send_task = self.loop.create_task(self._process_send_queue())
        self.receive_task = self.loop.create_task(self._process_receive_queue())

    async def request_supported_rpc_methods(self):
        await self.async_rpc_request("rpc_methods", [], result_handler=self.register_supported_rpc_methods)

    async def register_supported_rpc_methods(self, rpc_methods: dict):
        self.rpc_methods = rpc_methods.get("result")

    @staticmethod
    async def check_network_connectivity(endpoints: List[Tuple[str, int]]) -> bool:
        """
        Check network connectivity to a list of endpoints.

        Args:
            endpoints: A list of tuples where each tuple contains an IP address or hostname
                       and a port number (e.g., [("8.8.8.8", 53), ("www.example.com", 80)]).

        Returns:
            bool: True if all endpoints are reachable, False otherwise.

        This method attempts to establish a socket connection to each endpoint. If any endpoint is
        not reachable, the method returns False, indicating a potential connectivity issue.
        """
        for host, port in endpoints:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)  # Set a timeout for socket operations
                try:
                    if sock.connect_ex((host, port)) != 0:
                        return False  # If the connection attempt fails, return False
                except socket.gaierror:
                    return False  # Return False if the host is not reachable/resolvable
        return True  # All endpoints are reachable



    async def send_data(
        self,
        data: Any,
        topic: Optional[str] = "general",
        callback: Union[Callable[[Any], None], Coroutine[Any, Any, None]] = None,
    ) -> None:
        """
        Enqueue data for sending along with an optional topic for pub/sub, and optionally register a callback
        to be triggered upon receiving a response for the generated request UUID.

        Args:
            data: The data to be sent.
            topic: The topic under which the data should be published.
            callback: An optional callback function that will be called with the response.

        Raises:
            Exception: If the method encounters an unhandled or unrecoverable exception.
        """
        # Generate a unique request identifier (UUID)
        request_id = generate_request_token()

        # Structure the message for queuing
        message = {
            "request_id": request_id,
            "data": data,
            "topic": topic,
            "callback": callback.__name__
            if callback
            else None,  # Store callback by name if possible
        }

        if not self.accept_data:
            await self._persist_data(message, "send")
            return

        try:
            if not self.send_queue.full():
                await self.send_queue.put(message)
                # Register the callback with the request_id if provided
                if callback:
                    self.callbacks[request_id] = callback
            else:
                # When the queue is full, flush to disk and prevent further writes
                await self._flush_queue_to_disk("send")
                await self._persist_data(message, "send")
                self.accept_data = False
        except Exception as exc:
            logger.error(
                f"An unhandled error occurred while sending: {exc}", exc_info=True
            )
            raise

    async def receive_data(self) -> None:
        """
        Processes received data which is internally obtained, handling an optional topic and/or
        an optional callback that uses the request UUID from the internally obtained data.

        The method is designed to work asynchronously, retrieving data from a queue or another data source,
        processing it, and, if applicable, triggering a registered callback with the data and topic.
        """
        try:
            # Receive next message from queue
            data = await self.receive_queue.get()

            # Extract request_id, and optionally, topic from the data
            request_id = data.get('id')
            topic = data.get('topic', None)
            called_back = False

            processed_data = {"data": data, "topic": topic}
            logger.debug(f"Data received for processing: {processed_data}")

            # If a callback is registered for this request_id, call it with the data
            if request_id and request_id in self.callbacks:
                called_back = True
                callback = self.callbacks[request_id]
                if callable(callback):
                    self._trigger_callback(callback, processed_data)
            if topic and topic in self.subscriptions:
                called_back = True
                await self._notify_subscribers(topic, processed_data)
            if not called_back:
                # Handle case where there's no callback or subscribers registered for the request_id
                logger.debug(f"No callback registered for request_id: {request_id}")

        except Exception as exc:
            logger.error(f"An unhandled error occurred while receiving data: {exc}", exc_info=True)
            raise

    def _trigger_callback(self, callback: Callable, processed_data: dict) -> None:
        if inspect.iscoroutinefunction(callback):
            # Schedule the coroutine without immediately invoking it
            self._schedule_async_task(callback, 0, **processed_data)
        else:
            # For synchronous callbacks, execute immediately in the thread-safe manner
            self.loop.call_soon_threadsafe(callback, **processed_data)

    def _schedule_async_task(self, coro_func, delay=0.1, **kwargs):
        """Helper method to schedule an asynchronous task after a delay."""
        self.loop.call_later(delay, lambda: asyncio.create_task(coro_func(**kwargs)))

    async def _process_receive_queue(self) -> Any:
        """Receive data, pulling from persistent storage if necessary."""
        try:
            if self.receive_queue.empty():
                await self._process_persistent_data("receive")
                # Schedules with a 1 second delay to prevent a tight loop
                self._schedule_async_task(self._process_receive_queue, 1)
            else:
                # Schedules with a small delay
                self._schedule_async_task(self._process_receive_queue, 0.1)
                return await self.receive_data()
        except Exception as exc:
            logger.error(
                f"An unhandled error occurred while processing receive queue: {exc}",
                exc_info=True,
            )

    async def _process_send_queue(self) -> None:
        """Continuously process the send queue, sending data through the transport."""
        if not self.send_queue.empty():
            data = await self.send_queue.get()
            try:
                await self.transport.send(data)
            except RetryableError:
                await self._persist_data(
                    data, "send"
                )  # Requeue data for later if retryable
            except FatalError as exc:
                logger.error(
                    f"An unrecoverable fatal error occurred while sending: {exc}",
                    exc_info=True,
                )
            self._schedule_async_task(self._process_send_queue, 0)
        else:
            # Schedules with a delay to prevent tight loop
            self._schedule_async_task(self._process_send_queue, 1)

    def subscribe(self, topic: str, callback: Callable[[str, Any], None]) -> None:
        """
        Subscribes a callback function to a specified topic. Whenever data associated with
        this topic is received, the callback will be triggered.

        Args:
            topic: The topic to which the callback function subscribes.
            callback: The callback function that will be called with two arguments:
                      the topic as a string and the received data.
        """
        with lock:
            if topic not in self.subscriptions:
                self.subscriptions[topic] = []

            self.subscriptions[topic].append(callback)
            logger.info(f"Subscribed to topic '{topic}'")

    def unsubscribe(self, topic: str, callback: Callable[[str, Any], None]) -> None:
        """
        UnSubscribes a callback function from a specified topic.

        Args:
            topic: The topic to which the callback function subscribes.
            callback: The callback to unsubscribe.
        """
        with lock:
            if topic not in self.subscriptions:
                logger.debug(f"No such topic to unsubscribe '{topic}'")
                return

            self.subscriptions[topic].append(callback)
            logger.info(f"Subscribed to topic '{topic}'")

    async def send_subscription_reqeust(self, topic: str, method: str) -> None:
        # Subscribe to a system event or extrinsic event
        payload = {
            "id": generate_request_token("SUB"),
            "jsonrpc": "2.0",
            "method": "rpc_customSubscribe",
            "params": {"topic": topic},
        }
        result = self.rpc_request(method, payload)

    async def _notify_subscribers(self, topic: str, processed_data: dict) -> None:
        """
        Notifies all subscribers about new data on their subscribed topic.
        """
        topic = processed_data.get("topic")
        for callback in self.subscriptions[topic]:
            try:
                if callable(callback):
                    self._trigger_callback(callback, processed_data=processed_data)
                else:
                    logger.debug(f"Ubsubscribing non-callable '{callback}' from topic '{topic}'")
                    self.unsubscribe(topic, callback)
            except Exception as exc:
                logger.error(f"Error in callback for topic '{topic}': {exc}", exc_info=True)

    async def _persist_data(self, data: Any, direction: str) -> None:
        """Persist data to disk when queues are full or in an error state."""
        file_path = self.storage_dir / f"{direction}_{int(self.loop.time())}.json"
        with open(file_path, "w") as file:
            json.dump(data, file)

    async def _flush_queue_to_disk(self, direction: str) -> None:
        """Flush the entire queue to disk."""
        while not getattr(self, f"{direction}_queue").empty():
            data = await getattr(self, f"{direction}_queue").get()
            await self._persist_data(data, direction)

    async def _process_persistent_data(self, direction: str) -> None:
        """Process data stored on disk."""
        for file in sorted(
            self.storage_dir.glob(f"{direction}_*.json"), key=os.path.getmtime
        ):
            with open(file, "r") as f:
                data = json.load(f)
            if direction == "send":
                await self.send_data(data)
            elif direction == "receive":
                await self.receive_queue.put(data)
            os.remove(file)  # Delete the file after processing

    async def cleanup(self) -> None:
        """Clean up resources, including persistent storage and closing connections."""
        if self.send_task:
            self.send_task.cancel()
        if self.receive_task:
            self.receive_task.cancel()
        try:
            if hasattr(self.transport, "close") and asyncio.iscoroutinefunction(
                self.transport.close
            ):
                await self.transport.close()
            shutil.rmtree(self.storage_dir)
        except Exception as exc:
            logger.error(
                f"An unknown exception occurred during cleanup: {exc}", exc_info=True
            )


