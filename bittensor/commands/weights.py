# The MIT License (MIT)
# Copyright © 2021 Yuma Rao
# Copyright © 2023 Opentensor Foundation

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

"""Module that encapsulates the SetWeightCommand.
NB: within the extrinsic layer a commit and reveal weights feature is included.
"""

import argparse
import datetime

from rich.prompt import Prompt, Confirm

import bittensor
from bittensor.extrinsics import set_weights
from bittensor.utils import commit_reveal_utils
from . import defaults  # type: ignore


class SetWeightCommand:
    """
    Executes the `set_weights` command to set weights for specific neurons on the Bittensor network.

    Usage:
        The command allows setting weights for specific neurons within a subnet. Users need to specify the netuid (network unique identifier), corresponding UIDs, and weights they wish to set.

    Optional arguments:
        - `--netuid` (int): The netuid of the subnet for which weights are to be set.
        - `--uids` (str): Corresponding UIDs for the specified netuid, in comma-separated format.
        - `--weights` (str): Corresponding weights for the specified UIDs, in comma-separated format.
        - ``--reveal-using-salt`` (str): This is useful when a commit-reveal process fails after a commit and before revealing the weights hash.
                            Here you can specify the same salt that was used in a failed commit-reveal process to retry the reveal operation.

    Example usage:
        $ btcli wt set_weights --netuid 1 --uids 1,2,3,4 --weights 0.1,0.2,0.3,0.4
        
        For reveal-using-salt with all values:
        $ btcli wt set_weights --netuid 1 --uids 1,2,3,4 --weights 0.1,0.2,0.3,0.4 --reveal-using-salt 163,241,217,11,161,142,147,189

    Note:
        This command is used to set weights for specific neurons and requires the user to have the necessary permissions.
    """

    @staticmethod
    def run(cli: "bittensor.cli"):
        r"""Set weights for specific neurons."""
        try:
            subtensor: "bittensor.subtensor" = bittensor.subtensor(
                config=cli.config, log_verbose=False
            )
            SetWeightCommand._run(cli, subtensor)
        finally:
            if "subtensor" in locals():
                subtensor.close()
                bittensor.logging.debug("closing subtensor connection")


    @staticmethod
    def _run(cli: "bittensor.cli", subtensor: "bittensor.subtensor"):
        r"""Set weights for specific neurons"""

        if cli.config.reveal_using_salt:
            SetWeightCommand._do_reveal_from_cli(cli, subtensor)
        else:
            reveal_data = commit_reveal_utils.read_last_reveal_data()
            if reveal_data and datetime.datetime.now(datetime.timezone.utc) < datetime.datetime.fromisoformat(reveal_data.reveal_time):
                SetWeightCommand._do_reveal_from_cache(cli, subtensor, reveal_data)
            else:
                SetWeightCommand._do_set_weights(cli, subtensor)


    @staticmethod
    def _do_set_weights(cli, subtensor):
        wallet = bittensor.wallet(config=cli.config)

        # Get values if not set
        if not cli.config.is_set("netuid"):
            cli.config.netuid = int(Prompt.ask(f"Enter netuid"))

        if not cli.config.is_set("uids"):
            cli.config.uids = Prompt.ask(f"Enter UIDs (comma-separated)")

        if not cli.config.is_set("weights"):
            cli.config.weights = Prompt.ask(f"Enter weights (comma-separated)")

        # Convert comma-separated strings to appropriate lists
        uids = list(map(int, cli.config.uids.split(',')))
        weights = list(map(float, cli.config.weights.split(',')))

        # Call the set_weights_extrinsic function in the module set_weights from extrinsics package
        success, message = set_weights.set_weights_extrinsic(
                    subtensor=subtensor,
                    wallet=wallet,
                    netuid=cli.config.netuid,
                    uids=uids,
                    weights=weights,
                    wait_for_inclusion=True,
                    wait_for_finalization=False,
                    prompt=True
                )
        
        return success,message


    @staticmethod
    def _do_reveal_from_cache(cli, subtensor, reveal_data):
        bittensor.__console__.print(
                    f"[red]A previously issued set_weights command partially failed.[/red]\n"
                    f"[red]This partial failure means your weights were committed as a hash but were not revealed (unhashed)[/red]\n"
                    "[red]The following values for set_weights were cached:[/red]\n"
                    f"[red]  wallet_name: {reveal_data.wallet_name}[/red]\n"
                    f"[red]  wallet_hotkey: {reveal_data.wallet_hotkey}[/red]\n"
                    f"[red]  wallet_path: {reveal_data.wallet_path}[/red]\n"
                    f"[red]  netuid: {reveal_data.netuid}[/red]\n"
                    f"[red]  uids: {reveal_data.weight_uids}[/red]\n"
                    f"[red]  weights: {reveal_data.weight_vals}[/red]\n"
                    f"[red]  salt: {reveal_data.salt}[/red]\n"
                    f"[red]  wait_for_inclusion: {reveal_data.wait_for_inclusion}[/red]\n"
                    f"[red]  wait_for_finalization: {reveal_data.wait_for_finalization}[/red]"
                )

        if Confirm.ask("Retry reveal of weights hash using these values?"):
            cli.config.netuid = reveal_data.netuid
            cli.config.uids = reveal_data.weight_uids
            cli.config.weights = reveal_data.weight_vals
            cli.config.reveal_using_salt = reveal_data.salt
            cli.config.wallet.name = reveal_data.wallet_name
            cli.config.wallet.hotkey = reveal_data.wallet_hotkey
            cli.config.wallet.path = reveal_data.wallet_path
            cli.config.wait_for_inclusion = reveal_data.wait_for_inclusion
            cli.config.wait_for_finalization = reveal_data.wait_for_finalization
            SetWeightCommand._do_reveal_from_cli(cli, subtensor)

        else:
            if Confirm.ask("Do you want to clear these values from the cache (enter N if you want to retry later)?"):
                if commit_reveal_utils._clear_last_reveal_data():
                    bittensor.__console__.print("Values cleared from cache.")
                else:
                    bittensor.__console__.print("Values could not be cleared due to an unexpected error.")


    @staticmethod
    def _do_reveal_from_cli(cli, subtensor):
        wallet = bittensor.wallet(config=cli.config)
            # Convert comma-separated strings to appropriate lists
        uids = list(map(int, cli.config.uids.split(',')))
        weights = list(map(float, cli.config.weights.split(',')))

            # Call the set_weights_extrinsic function in the module set_weights from extrinsics package
        success, message = set_weights.reveal(
                subtensor=subtensor,
                wallet=wallet,
                netuid=cli.config.netuid,
                weight_uids=uids,
                weight_vals=weights,
                salt=cli.config.reveal_using_salt,
                wait_for_inclusion=True,
                wait_for_finalization=False
            )
        if success:
            bittensor.logging.info("Successfully set weights.")
        else:
            bittensor.logging.error(f"Failed to set weights: {message}")


    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        parser = parser.add_parser("set_weights", help="Set weights for a specific subnet.")
        parser.add_argument("--netuid", dest="netuid", type=int, required=False)
        parser.add_argument("--uids", dest="uids", type=str, required=False)
        parser.add_argument("--weights", dest="weights", type=str, required=False)
        parser.add_argument("--reveal-using-salt", dest="reveal_using_salt", type=str, required=False)
        parser.add_argument("--wait-for-inclusion", dest="wait_for_inclusion", action="store_true", default=False)
        parser.add_argument("--wait-for-finalization", dest="wait_for_finalization", action="store_true", default=True)
        parser.add_argument("--prompt", dest="prompt", action="store_true", default=False)

        bittensor.wallet.add_args(parser)
        bittensor.subtensor.add_args(parser)

    @staticmethod
    def check_config(config: "bittensor.config"):
        if not config.no_prompt and not config.is_set("wallet.name"):
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)
        if not config.no_prompt and not config.is_set("wallet.hotkey"):
            hotkey = Prompt.ask("Enter hotkey name", default=defaults.wallet.hotkey)
            config.wallet.hotkey = str(hotkey)

