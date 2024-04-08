import asyncio
import websockets
import json
from collections import deque
from typing import Callable, Any
import os
import tempfile


class AsyncWebsocketClient:
    def __init__(self, uri, retry_interval=5, max_retries=10, temp_storage_path=None):
        self.uri = uri
        self.websocket = None
        self.send_queue = deque()
        self.receive_queue = deque()
        self.callbacks = {}
        self.retry_interval = retry_interval
        self.max_retries = max_retries
        self.temp_storage_path = temp_storage_path or tempfile.gettempdir()
        self.connected = False

    async def connect(self):
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                self.websocket = await websockets.connect(self.uri)
                self.connected = True
                asyncio.create_task(self.sender())
                asyncio.create_task(self.receiver())
                break
            except (OSError, websockets.exceptions.WebSocketException) as e:
                retry_count += 1
                await asyncio.sleep(self.retry_interval)
        if not self.connected:
            raise ConnectionError("Unable to connect to websocket server.")

    async def sender(self):
        while True:
            if not self.send_queue:
                await asyncio.sleep(0.1)  # Prevent tight loop when queue is empty
                continue
            topic, data, callback = self.send_queue.popleft()
            message = json.dumps({"topic": topic, "data": data})
            try:
                await self.websocket.send(message)
                if callback:
                    self.callbacks[topic] = callback
            except websockets.exceptions.ConnectionClosed:
                await self.handle_send_failure(topic, data, callback)

    async def receiver(self):
        while True:
            message = await self.websocket.recv()
            data = json.loads(message)
            topic = data["topic"]
            if topic in self.callbacks:
                callback = self.callbacks.pop(topic)
                callback(data["data"])
            else:
                self.receive_queue.append(data)

    async def handle_send_failure(self, topic, data, callback):
        self.persist_send_queue()
        self.send_queue.appendleft((topic, data, callback))
        await self.connect()  # Attempt to reconnect

    def persist_send_queue(self):
        if not self.send_queue:
            return
        with open(
            os.path.join(self.temp_storage_path, "ws_send_queue.json"), "w"
        ) as file:
            json.dump(list(self.send_queue), file)

    def load_persisted_send_queue(self):
        try:
            with open(
                os.path.join(self.temp_storage_path, "ws_send_queue.json"), "r"
            ) as file:
                self.send_queue = deque(json.load(file))
            os.remove(os.path.join(self.temp_storage_path, "ws_send_queue.json"))
        except FileNotFoundError:
            pass

    def enqueue_message(self, topic: str, data: Any, callback: Callable = None):
        self.send_queue.append((topic, data, callback))

    async def start(self):
        self.load_persisted_send_queue()
        await self.connect()


# Example usage
async def main():
    client = AsyncWebsocketClient("ws://example.com/websocket")
    await client.start()

    # Define callback function
    def callback_function(response_data):
        print("Received callback data:", response_data)

    # Enqueue a message
    client.enqueue_message("test_topic", {"key": "value"}, callback_function)


# Run the client
asyncio.run(main())
