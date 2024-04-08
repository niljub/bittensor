import asyncio
import json
import os
import shutil
import tempfile
import socket
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

DEFAULT_NETWORK = "finney.opentensor.ai"
logger = getLogger(__name__)


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
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self.network = network or DEFAULT_NETWORK
        self.accept_data: bool = True
        self.send_task: Optional[Task] = None
        self.receive_task: Optional[Task] = None

    def register_transport(self, transport: Transport) -> None:
        """Register a new transport mechanism."""
        self.transport = transport(self.network)

    def start(self) -> None:
        """Start background tasks for sending and receiving data."""
        self.send_task = self.loop.create_task(self._process_send_queue())
        self.receive_task = self.loop.create_task(self._process_receive_queue())

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
        callback: Optional[Callable[[Any], None]] = None,
    ) -> None:
        """
        Enqueue data for sending along with a topic for pub/sub, and optionally register a callback
        to be triggered upon receiving a response for the generated request UUID.

        Args:
            data: The data to be sent.
            topic: The topic under which the data should be published.
            callback: An optional callback function that will be called with the response.

        Raises:
            Exception: If the method encounters an unhandled exception.
        """
        if not self.accept_data:
            await self._persist_data({"data": data, "topic": topic}, "send")
            return

        # Generate a unique request identifier (UUID)
        request_id = str(uuid4())

        # Structure the message for queuing
        message = {
            "request_id": request_id,
            "data": data,
            "topic": topic,
            "callback": callback.__name__
            if callback
            else None,  # Store callback by name if possible
        }

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
            # Assuming logger is defined and configured elsewhere
            logger.error(
                f"An unhandled error occurred while sending: {exc}", exc_info=True
            )
            raise

    async def _process_receive_queue(self) -> Any:
        """Receive data, pulling from persistent storage if necessary."""
        try:
            if self.receive_queue.empty():
                await self._process_persistent_data("receive")
            return await self.receive_queue.get()
        except Exception as exc:
            logger.error(
                f"An unhandled error occurred while processing receive queue: {exc}",
                exc_info=True,
            )

    async def _process_send_queue(self) -> None:
        """Continuously process the send queue, sending data through the transport."""
        while True:
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
            else:
                await asyncio.sleep(
                    0.1
                )  # Sleep to prevent a tight loop when the queue is empty

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
