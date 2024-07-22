import bittensor
from bittensor.commands import SetWeightCommand, RegisterSubnetworkCommand
from tests.e2e_tests.utils import setup_wallet


def test_set_weights_with_commit_reveal(local_chain):
    """
    This test verifies the functionality of the SetWeightCommand under two scenarios:
    1. When the commit reveal mechanism is enabled.
    2. When the commit reveal mechanism is disabled.
    
    Args:
        local_chain: A fixture that provides access to a simulated blockchain environment.
    """
    # Setup wallet and command execution utility
    keypair, exec_command, wallet_path = setup_wallet("//Alice")
    alice_wallet = bittensor.wallet(path=wallet_path)

    # Register a subnet to test with
    exec_command(RegisterSubnetworkCommand, ["s", "create"])

    # Verify subnet 1 created successfully
    assert local_chain.query("SubtensorModule", "NetworksAdded", [1]).serialize()

    # Define test parameters
    netuid = 1
    uids = "0"
    weights = "0.1"
    
    # Enable commit reveal mechanism
    subtensor = bittensor.subtensor(network="ws://localhost:9945")
    subtensor.set_hyperparameter(
        wallet=alice_wallet,
        netuid=netuid,
        parameter="commit_reveal_weights_enabled",
        value=True,
        wait_for_inclusion=True,
        wait_for_finalization=True,
        prompt=False
    )
    
    # Test SetWeightCommand with commit reveal enabled
    exec_command(
        SetWeightCommand,
        [
            "wt",
            "set_weights",
            "--netuid",
            str(netuid),
            "--uids",
            uids,
            "--weights",
            weights,
            "--subtensor.network",
            "local",
            "--subtensor.chain_endpoint",
            "ws://localhost:9945",
            "--wallet.path",
            wallet_path,
        ],
    )
    
    # Verify weights are set correctly
    set_weights = subtensor.query_module(
        module="SubtensorModule",
        name="Weights",
        params=[netuid, int(uids)]
    )
    assert set_weights.value is not None, "Set weights not found in storage"
    assert set_weights.value[0][1] == float(weights), "Incorrect weight set"
    
    # Disable commit reveal mechanism
    subtensor.set_hyperparameter(
        wallet=alice_wallet,
        netuid=netuid,
        parameter="commit_reveal_weights_enabled",
        value=False,
        wait_for_inclusion=True,
        wait_for_finalization=True,
        prompt=False
    )
    
    # Test SetWeightCommand with commit reveal disabled
    exec_command(
        SetWeightCommand,
        [
            "wt",
            "set_weights",
            "--netuid",
            str(netuid),
            "--uids",
            uids,
            "--weights",
            weights,
            "--subtensor.network",
            "local",
            "--subtensor.chain_endpoint",
            "ws://localhost:9945",
            "--wallet.path",
            wallet_path,
        ],
    )
    
    # Verify weights are set correctly
    set_weights = subtensor.query_module(
        module="SubtensorModule",
        name="Weights",
        params=[netuid, int(uids)]
    )
    assert set_weights.value is not None, "Set weights not found in storage"
    assert set_weights.value[0][1] == float(weights), "Incorrect weight set"

