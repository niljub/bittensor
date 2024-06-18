import asyncio
import sys
import uuid

import pytest

import bittensor
from bittensor.commands import (
    RegisterCommand,
    RegisterSubnetworkCommand,
    SwapHotkeyCommand,
    StakeCommand,
    RootRegisterCommand,
    NewHotkeyCommand,
)
from tests.e2e_tests.utils import (
    setup_wallet,
    template_path,
    repo_name,
)

"""
Test the swap_hotkey mechanism with multiple hotkeys.

Verify that:
* Alice - neuron is registered on network as a validator
* Bob - neuron is registered on network as a miner
* Create three new hotkeys for Bob
* Swap each hotkey of Bob via BTCLI
* Verify that each hotkey is swapped
* Verify that stake hotkey, delegates hotkey, UIDS, and prometheus hotkey are swapped
* Ensure that the coldkey remains the same and is correctly associated with the new hotkeys
"""

@pytest.mark.asyncio
async def test_swap_hotkey_validator_owner(local_chain):
    # Register root as Alice - the subnet owner and validator
    alice_keypair, alice_exec_command, alice_wallet = setup_wallet("//Alice")
    alice_exec_command(RegisterSubnetworkCommand, ["s", "create"])
    # Verify subnet 1 created successfully
    assert local_chain.query("SubtensorModule", "NetworksAdded", [1]).serialize()

    # Register Bob as miner
    bob_keypair, bob_exec_command, bob_wallet = setup_wallet("//Bob")

    bob_old_hotkey_address = bob_wallet.hotkey.ss58_address

    # Register Alice as neuron to the subnet
    alice_exec_command(
        RegisterCommand,
        [
            "s",
            "register",
            "--netuid",
            "1",
        ],
    )

    # Register Bob as neuron to the subnet
    bob_exec_command(
        RegisterCommand,
        [
            "s",
            "register",
            "--netuid",
            "1",
        ],
    )

    subtensor = bittensor.subtensor(network="ws://localhost:9945")
    # assert two neurons are in network
    assert len(subtensor.neurons(netuid=1)) == 2

    # register Bob as miner
    cmd = " ".join(
        [
            f"{sys.executable}",
            f'"{template_path}{repo_name}/neurons/miner.py"',
            "--no_prompt",
            "--netuid",
            "1",
            "--subtensor.network",
            "local",
            "--subtensor.chain_endpoint",
            "ws://localhost:9945",
            "--wallet.path",
            bob_wallet.path,
            "--wallet.name",
            bob_wallet.name,
            "--wallet.hotkey",
            "default",
            "--logging.trace",
        ]
    )

    miner_process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    await asyncio.sleep(
        5
    )  # wait for 5 seconds for the metagraph to refresh with latest data

    # register Alice as validator
    cmd = " ".join(
        [
            f"{sys.executable}",
            f'"{template_path}{repo_name}/neurons/validator.py"',
            "--no_prompt",
            "--netuid",
            "1",
            "--subtensor.network",
            "local",
            "--subtensor.chain_endpoint",
            "ws://localhost:9945",
            "--wallet.path",
            alice_wallet.path,
            "--wallet.name",
            alice_wallet.name,
            "--wallet.hotkey",
            "default",
            "--logging.trace",
        ]
    )
    # run validator in the background

    validator_process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    await asyncio.sleep(
        5
    )  # wait for 5 seconds for the metagraph and subtensor to refresh with latest data

    # register validator with root network
    alice_exec_command(
        RootRegisterCommand,
        [
            "root",
            "register",
            "--netuid",
            "1",
            "--wallet.name",
            "default",
            "--wallet.hotkey",
            "default",
            "--subtensor.chain_endpoint",
            "ws://localhost:9945",
        ],
    )

    # Alice to stake to become to top neuron after the first epoch
    alice_exec_command(
        StakeCommand,
        [
            "stake",
            "add",
            "--amount",
            "10000",
        ],
    )

    # get latest metagraph
    metagraph = bittensor.metagraph(netuid=1, network="ws://localhost:9945")
    subtensor = bittensor.subtensor(network="ws://localhost:9945")
    # assert bob has old hotkey
    bob_neuron = metagraph.neurons[1]

    assert bob_neuron.coldkey == "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
    assert bob_neuron.hotkey == bob_old_hotkey_address
    assert bob_neuron.hotkey == bob_neuron.coldkey
    assert bob_neuron.coldkey == subtensor.get_hotkey_owner(bob_old_hotkey_address)
    assert subtensor.is_hotkey_delegate(bob_neuron.hotkey) is False
    assert (
        subtensor.is_hotkey_registered_on_subnet(
            hotkey_ss58=bob_neuron.hotkey, netuid=1
        )
        is True
    )
    assert (
        subtensor.get_uid_for_hotkey_on_subnet(hotkey_ss58=bob_neuron.hotkey, netuid=1)
        == bob_neuron.uid
    )
    # TODO: assert bob only has one hotkey

    # generate new guid names for hotkeys
    new_hotkey_names = [str(uuid.uuid4()) for _ in range(3)]

    # create and register new hotkeys
    for new_hotkey_name in new_hotkey_names:
        bob_exec_command(
            NewHotkeyCommand,
            [
                "w",
                "new_hotkey",
                "--wallet.name",
                bob_wallet.name,
                "--wallet.hotkey",
                new_hotkey_name,
                "--wait_for_inclusion",
                "True",
                "--wait_for_finalization",
                "True",
            ],
        )
        # Register the new hotkey to the subnet
        bob_exec_command(
            RegisterCommand,
            [
                "s",
                "register",
                "--netuid",
                "1",
                "--wallet.hotkey",
                new_hotkey_name,
            ],
        )

    # swap hotkeys
    for new_hotkey_name in new_hotkey_names:
        bob_exec_command(
            SwapHotkeyCommand,
            [
                "w",
                "swap_hotkey",
                "--wallet.name",
                bob_wallet.name,
                "--wallet.hotkey",
                bob_wallet.hotkey_str,
                "--wallet.hotkey_b",
                new_hotkey_name,
                "--wait_for_inclusion",
                "True",
                "--wait_for_finalization",
                "True",
            ],
        )

        # get latest metagraph
        metagraph = bittensor.metagraph(netuid=1, network="ws://localhost:9945")
        subtensor = bittensor.subtensor(network="ws://localhost:9945")

        # assert bob has new hotkey
        bob_neuron = metagraph.neurons[1]

        assert (
            bob_neuron.coldkey == "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
        )  # cold key didn't change
        assert bob_neuron.hotkey != bob_old_hotkey_address
        assert bob_neuron.hotkey != bob_neuron.coldkey
        assert bob_neuron.coldkey == subtensor.get_hotkey_owner(
            bob_neuron.hotkey
        )  # new key is owner
        assert (
            subtensor.is_hotkey_delegate(bob_neuron.hotkey) is False
        )  # new key is not a delegate
        assert (
            subtensor.is_hotkey_registered_on_subnet(
                hotkey_ss58=bob_neuron.hotkey, netuid=1
            )
            is True
        )
        assert (
            subtensor.get_uid_for_hotkey_on_subnet(
                hotkey_ss58=bob_neuron.hotkey, netuid=1
            )
            == bob_neuron.uid
        )
        # update old hotkey address
        bob_old_hotkey_address = bob_neuron.hotkey

    # kill processes
    miner_process.terminate()
    validator_process.terminate()
