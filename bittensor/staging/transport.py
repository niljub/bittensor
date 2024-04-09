import asyncio
import json
import os
import shutil
import sys
import tempfile
from abc import ABC, abstractmethod
from asyncio import Queue
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from logging import getLogger

import aiohttp
from aiohttp import ClientWebSocketResponse, TCPConnector, _WSRequestContextManager
import websockets
from websockets import WebSocketClientProtocol
from websockets.exceptions import (
    WebSocketException,
    ConnectionClosedError,
    InvalidURI,
    SecurityError,
    ConnectionClosedOK,
    ConnectionClosed,
    WebSocketProtocolError,
    InvalidParameterName,
    InvalidOrigin,
    InvalidState,
    InvalidHeaderValue,
    InvalidHeaderFormat,
)

logger = getLogger(__name__)


class TransportError(Exception):
    """Custom exception class for transport-related errors."""


class RetryableError(TransportError):
    """Exception for errors where a retry operation is appropriate."""


class FatalError(TransportError):
    """Exception for errors that are considered fatal and should not be retried."""


class Transport(ABC):
    """
    Abstract base class for transport mechanisms.
    """

    def __call__(self, *args, **kwargs):
        pass

    @abstractmethod
    async def send(self, data: Any) -> None:
        """Send data using the transport mechanism."""
        pass

    @abstractmethod
    async def receive(self) -> Any:
        """Receive data using the transport mechanism."""
        pass


class WebSocketTransport(Transport):
    """
    WebSocket transport mechanism with retry logic, utilizing the 'websockets' library.
    """

    def __init__(
        self,
        url: str,
        max_retries: int = 5,
        retry_backoff: float = 1.5,
        send_timeout: float = 4.5,
        receive_timeout: float = 5.5,
        open_timeout: float = 10.0,
        **kwargs,
    ) -> None:
        self.url = url
        self.connect_options = kwargs
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.send_timeout = send_timeout
        self.receive_timeout = receive_timeout
        self.open_timeout = open_timeout
        self.connection: Optional[WebSocketClientProtocol] = None
        self.user_agent = kwargs.get(
            "user_agent", "Bittensor/6.0.10 WebSocketTransport/1.0"
        )
        self.compression = kwargs.get("compression", None)
        self.origin = kwargs.get("origin", None)
        self.headers = kwargs.get("headers", [])

    async def connect(self) -> None:
        """
        Connect to the websocket server.

        https://websockets.readthedocs.io/en/stable/reference/asyncio/client.html#websockets.client.connect
        The connection is closed automatically after each iteration of the loop.

        If an error occurs while establishing the connection, connect() retries
        with exponential backoff. The backoff delay starts at three seconds and
        increases up to one minute.

        If an error occurs in the body of the loop, you can handle the exception
        and connect() will reconnect with the next iteration; or you can let the
        exception bubble up and break out of the loop. This lets you decide which
        errors trigger a reconnection and which errors are fatal.
        """

        if self.connection is None:
            try:
                async for websocket in websockets.connect(
                    self.url,
                    user_agent_header=self.user_agent,
                    extra_headers=self.headers,
                    origin=self.origin,
                    open_timeout=self.open_timeout,
                    **self.connect_options,
                ):
                    try:
                        self.connection = websocket
                    except SecurityError as exc:
                        # Connection violated a security rule. Fatal.
                        logger.error(f"Security error: {exc}")
                        tb = sys.exception().__traceback__
                        raise FatalError(...).with_traceback(tb)

                    except (ConnectionClosedError, ConnectionClosed, InvalidState) as exc:
                        logger.warning(f"Connection closed unexpectedly: {exc}")
                        # ConnectionClosed[Error] can trigger a reconnect, handled by the loop

                    except WebSocketException as exc:
                        logger.warning(f"WebSocket error occurred: {exc}")
                        # General WebSocket exceptions can trigger a reconnect

                    except asyncio.TimeoutError as exc:
                        logger.warning(f"Timeout occurred: {exc}")
                        # Timeout can trigger a reconnect

                    except Exception as exc:
                        # All other exceptions. Fatal.
                        logger.error(f"Unhandled exception: {exc}")
                        tb = sys.exception().__traceback__
                        raise FatalError(...).with_traceback(tb)

            except InvalidURI as exc:
                logger.error(f"Invalid URI: {exc}")
                raise FatalError from exc
            except RuntimeError as exc:
                # Check if the original cause of RuntimeError was [Async]StopIteration. Reconnect.
                if isinstance(exc.__cause__, StopIteration) or isinstance(exc.__cause__, StopAsyncIteration):
                    # Runtime error caused by StopIteration - Assume websocket closed gracefully
                    logger.info("Closing websocket connection.")
                else:
                    # Runtime error not caused by [Async]StopIteration - Assume TransportError condition. Fatal.
                    logger.error(f"Runtime error occurred: {exc.__cause__}")
                    tb = sys.exception().__traceback__
                    raise TransportError(...).with_traceback(tb)
            except (WebSocketProtocolError, InvalidParameterName, InvalidOrigin, InvalidHeaderValue, InvalidHeaderFormat) as exc:
                # Raised when invalid connection parameters have been supplied. Fatal.
                logger.error(f"Invalid connection parameters: {exc}")
                tb = sys.exception().__traceback__
                raise FatalError(...).with_traceback(tb)

            except Exception as exc:
                # All other exceptions. Fatal.
                logger.error(f"Unhandled exception: {exc}")
                tb = sys.exception().__traceback__
                raise FatalError(...).with_traceback(tb)

    async def reconnect(self, reason: str = "reconnect triggered") -> None:
        if self.connection:
            logger.warning(f"Hard restarting websocket connection: {reason}")
            await self.connection.close(reason=reason)
            self.connection = None
            await self.connect()

    async def _ensure_connection(self) -> None:
        """Ensure that the WebSocket connection is established."""
        if self.connection is None or self.connection.closed:
            self.connection = await self.connect()

    async def send(self, data: Any) -> None:
        """Send data over WebSocket with retry logic."""
        await self._send_with_retries(data)

    async def _send_with_retries(self, data: Any, retries: int = 0, timeout: Optional[float] = None) -> None:
        """Attempt to send data with exponential backoff retries."""
        try:
            await self._ensure_connection()
            async with asyncio.timeout(timeout or self.send_timeout):
                await self.connection.send(json.dumps(data))
        except (WebSocketException, TimeoutError, WebSocketProtocolError) as e:
            if retries < self.max_retries:
                await asyncio.sleep(self.retry_backoff**retries)
                await self._send_with_retries(data, retries + 1)
            else:
                raise RetryableError(
                    f"Failed to send data after {self.max_retries} attempts"
                ) from e

        except Exception as e:
            raise FatalError(f"Unexpected error sending data: {e}") from e

    async def receive(self, timeout: Optional[float] = None) -> Any:
        """Receive data from WebSocket."""
        await self._ensure_connection()
        try:
            async with asyncio.timeout(timeout or self.receive_timeout):
                message = await self.connection.recv()
                return json.loads(message)
        except ConnectionClosedOK:
            logger.info("WebSocket connection closed OK.")
        except TimeoutError:
            logger.error("Websocket connection timed out while receiving.")
        except ConnectionClosedError:
            logger.warning("WebSocket connection closed unexepctedly.")
        except OSError:
            logger.warning("WebSocket connection closed unexepctedly.")

    async def close(self) -> None:
        """Close the WebSocket connection gracefully."""
        if self.connection and not self.connection.closed:
            await self.connection.close()


class AioWebSocketTransport(Transport):
    """
    WebSocket transport mechanism with retry logic.
    """

    def __init__(
        self, url: str, max_retries: int = 5, retry_backoff: float = 1.5
    ) -> None:
        self.url = url
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.session: Optional[aiohttp.ClientSession] = None
        self.connection: Optional[_WSRequestContextManager] = None

    async def _ensure_connection(self) -> None:
        """Ensure that the WebSocket connection is established."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        if (
            not hasattr(self, "connection")
            or self.connection is None
            or self.connection.closed
        ):
            self.connection = await self.session.ws_connect(self.url)

    async def send(self, data: Any) -> None:
        """Send data over WebSocket with retry logic."""
        await self._send_with_retries(data)

    async def _send_with_retries(self, data: Any, retries: int = 0) -> None:
        """Attempt to send data with exponential backoff retries."""
        try:
            await self._ensure_connection()
            await self.connection.send_json(data)
        except (aiohttp.ClientError, aiohttp.WSServerHandshakeError) as e:
            if retries < self.max_retries:
                await asyncio.sleep(self.retry_backoff**retries)
                await self._send_with_retries(data, retries + 1)
            else:
                raise RetryableError(
                    f"Failed to send data after {self.max_retries} attempts"
                ) from e
        except Exception as e:
            raise FatalError(f"Unexpected error sending data: {e}") from e

    async def receive(self) -> Any:
        """Receive data from WebSocket."""
        await self._ensure_connection()
        return await self.connection.receive_json()

    async def close(self) -> None:
        """Close the WebSocket connection gracefully."""
        if self.session:
            await self.session.close()
