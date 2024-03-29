#!/usr/bin/env python
"""
This is an example of how to prompt inside an application that uses the asyncio
eventloop. The ``prompt_toolkit`` library will make sure that when other
coroutines are writing to stdout, they write above the prompt, not destroying
the input line.
This example does several things:
    1. It starts a simple coroutine, printing a counter to stdout every second.
    2. It starts a simple input/echo app loop which reads from stdin.
Very important is the following patch. If you are passing stdin by reference to
other parts of the code, make sure that this patch is applied as early as
possible. ::
    sys.stdout = app.stdout_proxy()
"""
import sys
import asyncio
import random
import time
import importlib
import types
from typing import *

from injector import inject, singleton, Module
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit import Application, HTML, PromptSession
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.widgets import Box, Frame
from rich.console import Console
from overload.lazy_loader import install_lazy_loader

from injector import Injector
from injector import Module, provider, singleton
from asyncio import LifoQueue, Queue


class DIModule(Module):
    @singleton
    @provider
    def provide_console(self) -> Console:
        return Console()

    @singleton
    @provider
    def provide_queue(self) -> Queue:
        return asyncio.Queue()



ALIAS_TO_COMMAND = {
    "subnets": "subnets",
    "root": "root",
    "wallet": "wallet",
    "stake": "stake",
    "sudo": "sudo",
    "legacy": "legacy",
    "s": "subnets",
    "r": "root",
    "w": "wallet",
    "st": "stake",
    "su": "sudo",
    "l": "legacy",
    "subnet": "subnets",
    "roots": "root",
    "wallets": "wallet",
    "stakes": "stake",
    "sudos": "sudo",
    "i": "info",
    "info": "info",
}
COMMANDS = {
    "subnets": {
        "name": "subnets",
        "aliases": ["s", "subnet"],
        "help": "Commands for managing and viewing subnetworks.",
        "commands": {
            "list": "SubnetListCommand",
            "metagraph": "MetagraphCommand",
            "lock_cost": "SubnetLockCostCommand",
            "create": "RegisterSubnetworkCommand",
            "pow_register": "PowRegisterCommand",
            "register": "RegisterCommand",
            "hyperparameters": "SubnetHyperparamsCommand",
        },
    },
    "root": {
        "name": "root",
        "aliases": ["r", "roots"],
        "help": "Commands for managing and viewing the root network.",
        "commands": {
            "list": "RootList",
            "weights": "RootSetWeightsCommand",
            "get_weights": "RootGetWeightsCommand",
            "boost": "RootSetBoostCommand",
            "slash": "RootSetSlashCommand",
            "senate_vote": "VoteCommand",
            "senate": "SenateCommand",
            "register": "RootRegisterCommand",
            "proposals": "ProposalsCommand",
            "delegate": "DelegateStakeCommand",
            "undelegate": "DelegateUnstakeCommand",
            "my_delegates": "MyDelegatesCommand",
            "list_delegates": "ListDelegatesCommand",
            "nominate": "NominateCommand",
        },
    },
    "wallet": {
        "name": "wallet",
        "aliases": ["w", "wallets"],
        "help": "Commands for managing and viewing wallets.",
        "commands": {
            "list": "ListCommand",
            "overview": "OverviewCommand",
            "transfer": "TransferCommand",
            "inspect": "InspectCommand",
            "balance": "WalletBalanceCommand",
            "create": "WalletCreateCommand",
            "new_hotkey": "NewHotkeyCommand",
            "new_coldkey": "NewColdkeyCommand",
            "regen_coldkey": "RegenColdkeyCommand",
            "regen_coldkeypub": "RegenColdkeypubCommand",
            "regen_hotkey": "RegenHotkeyCommand",
            "faucet": "RunFaucetCommand",
            "update": "UpdateWalletCommand",
            "swap_hotkey": "SwapHotkeyCommand",
            "set_identity": "SetIdentityCommand",
            "get_identity": "GetIdentityCommand",
            "history": "GetWalletHistoryCommand",
        },
    },
    "stake": {
        "name": "stake",
        "aliases": ["st", "stakes"],
        "help": "Commands for staking and removing stake from hotkey accounts.",
        "commands": {
            "show": "StakeShow",
            "add": "StakeCommand",
            "remove": "UnStakeCommand",
        },
    },
    "sudo": {
        "name": "sudo",
        "aliases": ["su", "sudos"],
        "help": "Commands for subnet management",
        "commands": {
            # "dissolve": None,
            "set": "SubnetSudoCommand",
            "get": "SubnetGetHyperparamsCommand",
        },
    },
    "legacy": {
        "name": "legacy",
        "aliases": ["l"],
        "help": "Miscellaneous commands.",
        "commands": {
            "update": "UpdateCommand",
            "faucet": "RunFaucetCommand",
        },
    },
    "info": {
        "name": "info",
        "aliases": ["i"],
        "help": "Instructions for enabling autocompletion for the CLI.",
        "commands": {
            "autocomplete": "AutocompleteCommand",
        },
    },
}

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.containers import VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit import PromptSession


class CLIRepl:

    def __init__(self):
        # Create buffers and controls
        status_bar_control = FormattedTextControl(text="Bittensor")
        self.main_display_buffer = Buffer()
        self.input_buffer = Buffer()

        self.input_buffer.
        # Create containers
        self.root = HSplit([
            Window(height=1, content=status_bar_control),
            VSplit([
                Window(content=BufferControl(buffer=self.main_display_buffer)),
            ]),
            Window(height=1, content=BufferControl(buffer=self.input_buffer)),
        ])

        # Create layout
        self.layout = Layout(container=self.root)

        # Create and run the application
        self.app = Application(layout=self.layout, full_screen=True)

    async def start(self):
        producer_task = asyncio.create_task(producer())
        consumer_task = asyncio.create_task(consumer())
        try:

            await self.app.run_async()
        finally:
            producer_task.cancel()
            consumer_task.cancel()


class InputQueue:
    def __init__(self):
        self.queue = asyncio.Queue()

    async def put(self, item):
        await self.queue.put(item)

    async def get(self):
        return await self.queue.get()


class OutputQueue:
    def __init__(self):
        self.queue = asyncio.Queue()

    async def put(self, item):
        await self.queue.put(item)

    async def get(self):
        return await self.queue.get()


async def producer():
    """Simulates adding items to the queue."""
    for _ in range(100):
        await asyncio.sleep(random.uniform(0.1, 2))  # Simulate work
        item = f"Item {time.time()}"
        print(f"Producing {item}")
        await queue.put(item)
    await queue.put(None)  # Signal that the producer is done


async def consumer():
    """Coroutine that continuously reads from the queue and writes to the console."""
    session = PromptSession()
    while True:
        try:
            text = session.prompt('btcli> ')
            if text.lower() == 'quit':
                break
            # Process the command
            print('You entered:', text)
        except KeyboardInterrupt:
            continue
        except EOFError:
            break


async def main():
    injector = Injector([DIModule()])

    repl = injector.get(CLIRepl)
    await repl.start()



if __name__ == "__main__":
    install_lazy_loader(
        [
            "websocket",
            "substrateinterface",
            "bittensor.subtensor.subtensor",
            "bittensor.metagraph.metagraph",
            "bittensor.cli.cli",
            "bittensor.chain_data.chain_data",
            "bittensor.wallet.wallet",
            "bittensor.cli.COMMANDS",
            "bittensor.axon.axon",
            "bittensor.dendrite.dendrite",
            "bittensor.tensor.tensor",
            "bittensor.commands.stake.StakeCommand",
            "bittensor.commands.stake.StakeShow",
            "bittensor.commands.unstake.UnStakeCommand",
            "bittensor.commands.overview.OverviewCommand",
            "bittensor.commands.misc.UpdateCommand",
            "bittensor.commands.misc.UpdateCommand",
            "bittensor.commands.list.ListCommand",
            "bittensor.commands.metagraph.MetagraphCommand",
            "bittensor.commands.inspect.InspectCommand",
            "bittensor.commands.transfer.TransferCommand",
            "bittensor.commands.wallets.GetWalletHistoryCommand",
            "bittensor.commands.wallets.WalletBalanceCommand",
            "bittensor.commands.wallets.WalletCreateCommand",
            "bittensor.commands.wallets.UpdateWalletCommand",
            "bittensor.commands.wallets.RegenHotkeyCommand",
            "bittensor.commands.wallets.RegenColdkeypubCommand",
            "bittensor.commands.wallets.RegenColdkeyCommand",
            "bittensor.commands.wallets.NewHotkeyCommand",
            "bittensor.commands.wallets.NewColdkeyCommand",
            "bittensor.commands.delegates.MyDelegatesCommand",
            "bittensor.commands.delegates.DelegateUnstakeCommand",
            "bittensor.commands.delegates.DelegateStakeCommand",
            "bittensor.commands.delegates.ListDelegatesCommand",
            "bittensor.commands.delegates.NominateCommand",
            "bittensor.commands.register.SwapHotkeyCommand",
            "bittensor.commands.register.RunFaucetCommand",
            "bittensor.commands.register.RegisterCommand",
            "bittensor.commands.register.PowRegisterCommand",
            "bittensor.senate.SenateCommand",
            "bittensor.senate.ProposalsCommand",
            "bittensor.senate.ShowVotesCommand",
            "bittensor.senate.SenateRegisterCommand",
            "bittensor.senate.SenateLeaveCommand",
            "bittensor.senate.VoteCommand",
            "bittensor.network.RegisterSubnetworkCommand",
            "bittensor.network.SubnetLockCostCommand",
            "bittensor.network.SubnetListCommand",
            "bittensor.network.SubnetSudoCommand",
            "bittensor.network.SubnetHyperparamsCommand",
            "bittensor.network.SubnetGetHyperparamsCommand",
            "bittensor.root.RootRegisterCommand",
            "bittensor.root.RootList",
            "bittensor.root.RootSetWeightsCommand",
            "bittensor.root.RootGetWeightsCommand",
            "bittensor.root.RootSetBoostCommand",
            "bittensor.root.RootSetSlashCommand",
            "bittensor.identity.GetIdentityCommand",
            "bittensor.identity.SetIdentityCommand",
            ]
        )
    asyncio.run(main())
