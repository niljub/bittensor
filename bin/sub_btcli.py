#!/usr/bin/env python
import asyncio
from bittensor.staging.import_hooks import install_lazy_loader
import shtab
from bittensor.cli import cli as btcli
from bittensor.btlogging import logging as bt_logging
from bittensor.staging.exceptions import RetriesExceededException, NetworkUnavailable, NetworkUnreachable
from bittensor.staging.btsession import NetworkManager
from aiohttp import ClientSession, WSMsgType
from injector import inject, Injector, provider, Module
import asyncio
import sys
import asyncio
from aiohttp import ClientSession
from asyncio import Queue
from contextlib import asynccontextmanager
from injector import inject, Injector, provider, Module, singleton
from bittensor.staging.btsession import NetworkModule, NetworkManager, managed_network, ClientSessionModule


class WebSocketManager:
    def __init__(self, session: ClientSession, url: str):
        self.session = session
        self.url = url
        self.websocket = None

    async def connect(self):
        self.websocket = await self.session.ws_connect(self.url)

    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
            self.websocket = None


async def main():
    inj = Injector([NetworkModule()])

    # Create the parser with shtab support
    parser = btcli.__create_parser__()
    args, unknown = parser.parse_known_args()

    if args.print_completion:  # Check for print-completion argument
        print(shtab.complete(parser, args.print_completion))
        return

    # network = btcli.create_config(sys.argv[1:]).subtensor.chain_endpoint

    try:
        cli_instance = btcli(args=sys.argv[1:])
        await cli_instance.run()
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
    except RuntimeError as e:
        bt_logging.error(f'RuntimeError: {e}')

if __name__ == "__main__":
    install_lazy_loader(
        [
            "websocket",
            "substrateinterface",
            "bittensor.subtensor.subtensor",
        ]
    )
    asyncio.run(main(), debug=True)


# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
# Copyright © 2022 Opentensor Foundation

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
