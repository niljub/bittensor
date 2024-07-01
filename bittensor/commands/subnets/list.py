# The MIT License (MIT)
# Copyright © 2021 Yuma Rao

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
import argparse
import bittensor as bt
from rich.table import Table
from typing import Optional, List, Dict
from ..utils import get_delegates_details 

class ListSubnetsCommand:
    @staticmethod
    def run(cli: "bt.cli"):
        r"""List all subnet netuids in the network."""
        try:
            subtensor: "bt.subtensor" = bt.subtensor(
                config=cli.config, log_verbose=False
            )
            ListSubnetsCommand._run(cli, subtensor)
        finally:
            if "subtensor" in locals():
                subtensor.close()
                bt.logging.debug("closing subtensor connection")

    @staticmethod
    def _run(cli: "bt.cli", subtensor: "bt.subtensor"):
        r"""List all subnet netuids in the network."""
        # Fetch all subnet information
        import time
        import sys

        try:
            while True:
                subnets: List[bt.SubnetInfoV2] = subtensor.get_all_subnets_info_v2()
                
                current_block = subtensor.block
                def blocks_until_next_epoch(netuid: int, tempo: int, block_number: int) -> int:
                    # Special case: tempo = 0, the network never runs.
                    if tempo == 0:
                        return 1000
                    return tempo - ((block_number + netuid + 1) % (tempo + 1))

                # Initialize variables to store aggregated data
                rows = []
                total_neurons = 0
                total_registered = 0
                total_price = 0
                total_emission = 0
                dynamic_emission = 0
                n_dtao = 0
                n_stao = 0
                total_tao_locked = 0
                # Fetch delegate information
                delegate_info = get_delegates_details(url=bt.__delegates_details_url__)
                # Process each subnet and collect relevant data
                dynamic_rows = []
                stable_rows = []
                total_dynamic_stake = bt.Balance(0)
                total_stable_stake = bt.Balance(0)
                total_dynamic_emission = bt.Balance(0)
                total_stable_emission = bt.Balance(0)
                total_dynamic_tao = bt.Balance(0)
                total_stable_tao = bt.Balance(0)
                total_price = bt.Balance(0)
                for subnet in subnets:
                    pool = subnet.dynamic_pool
                    total_neurons += subnet.max_n
                    total_registered += subnet.subnetwork_n
                    subnet_price = pool.price if pool.is_dynamic else bt.Balance.from_rao(0)
                    total_price += subnet_price
                    subnet_emission = bt.Balance.from_rao(subnet.emission_value)
                    tao_locked = subnet.tao_locked
                    total_tao_locked += tao_locked

                    sn_symbol = f"{bt.Balance.get_unit(subnet.netuid)}\u200E"
                    alpha_out_str = (
                        f"{sn_symbol}{pool.alpha_outstanding.tao:,.4f}"
                        if pool.is_dynamic
                        else f"{sn_symbol}{tao_locked.tao:,.4f}"
                    )
                    if pool.is_dynamic:
                        n_dtao += 1
                        total_dynamic_stake += tao_locked
                        total_dynamic_emission += subnet_emission
                        total_dynamic_tao += tao_locked
                    else:
                        n_stao += 1
                        total_stable_stake += tao_locked
                        total_stable_emission += subnet_emission
                        total_stable_tao += tao_locked

                    # Prepare row data for the table
                    row_data = (
                        str(subnet.netuid),
                        f"[light_goldenrod1]{sn_symbol}[light_goldenrod1]",
                        f"{subnet.subnetwork_n}/{subnet.max_n}",
                        f"τ{subnet_emission.tao:.4f}",
                        f"τ{tao_locked.tao:,.4f}",
                        f"{(1/subnet_price.tao):.4f}{sn_symbol}/τ" if pool.is_dynamic else f"1.0{sn_symbol}/τ",
                        alpha_out_str,
                        str(blocks_until_next_epoch(subnet.netuid, subnet.hyperparameters["tempo"], current_block)),
                        f"{subnet.burn!s:8.8}",
                        f"{delegate_info[subnet.owner_ss58].name if subnet.owner_ss58 in delegate_info else subnet.owner_ss58[:5] + '...' + subnet.owner_ss58[-5:]}",
                    )

                    # Append row data to the appropriate list
                    if pool.is_dynamic:
                        dynamic_rows.append((subnet_emission.tao, row_data))
                    else:
                        stable_rows.append((subnet_emission.tao, row_data))

                # Sort rows by emission (descending order)
                dynamic_rows.sort(key=lambda x: x[0], reverse=True)
                stable_rows.sort(key=lambda x: x[0], reverse=True)

                # Define table properties
                console_width = bt.__console__.width - 5
                table_properties = {
                    "width": console_width,
                    "safe_box": True,
                    "padding": (0, 1),
                    "collapse_padding": False,
                    "pad_edge": True,
                    "expand": True,
                    "show_header": True,
                    "show_footer": True,
                    "show_edge": False,
                    "show_lines": False,
                    "leading": 0,
                    "style": "none",
                    "row_styles": None,
                    "header_style": "bold",
                    "footer_style": "bold",
                    "border_style": "rgb(7,54,66)",
                    "title_style": "bold magenta",
                    "title_justify": "center",
                    "highlight": False,
                }

                # Create combined table
                combined_table = Table(title="Subnets", **table_properties)
                combined_table.title = f"[white]Subnets - {subtensor.network} - Total Stake: τ{(total_dynamic_stake + total_stable_stake).tao:,.4f}\n"

                # Add columns to the table
                combined_table.add_column("mechanism", style="rgb(108,113,196)", no_wrap=True, justify="center")
                combined_table.add_column("netuid", style="rgb(253,246,227)", no_wrap=True, justify="center")
                combined_table.add_column("symbol", style="rgb(211,54,130)", no_wrap=True, justify="center")
                combined_table.add_column("n", style="rgb(108,113,196)", no_wrap=True, justify="center")
                combined_table.add_column("emission", style="rgb(38,139,210)", no_wrap=True, justify="center")
                combined_table.add_column(f"{bt.Balance.unit}", style="rgb(220,50,47)", no_wrap=True, justify="right")
                combined_table.add_column(f"{bt.Balance.unit} -> {bt.Balance.get_unit(1)}", style="rgb(181,137,0)", no_wrap=True, justify="center")
                combined_table.add_column(f"{bt.Balance.get_unit(1)}", style="rgb(133,153,0)", no_wrap=True, justify="right")
                combined_table.add_column("next epoch", style="rgb(38,139,210)", no_wrap=True, justify="center")
                combined_table.add_column("burn", style="rgb(220,50,47)", no_wrap=True, justify="center")
                combined_table.add_column("owner", style="rgb(108,113,196)", no_wrap=True)

                # Add rows to the table
                combined_table.add_row("[bold red]Rao[/bold red]", "", "", "", "", "", "", "", "", "", "")
                for _, row in dynamic_rows:
                    combined_table.add_row("", *row)
                price_arrow = "↓" if total_price.tao > total_dynamic_emission.tao else "↑"
                combined_table.add_row("", "", "", "", f"[white]τ{total_dynamic_emission.tao:.4f}[/white]", f"[white]τ{total_dynamic_tao.tao:,.4f}[/white]", "", "", "", "", "")
                combined_table.add_row("[bold blue]Finney[/bold blue]", "", "", "", "", "", "", "", "", "", "")
                combined_table.add_row()  # Empty row to separate dynamic and stable subnets
                for _, row in stable_rows:
                    combined_table.add_row("", *row)
                combined_table.add_row(" ", " ", " ", " ", f"[white]τ{total_stable_emission.tao:.4f}[/white]", f"[white]τ{total_stable_tao.tao:,.4f}[/white]", " ", " ", " ", " ", " ")
                
                # Print help table
                htable = Table(show_footer=False, pad_edge=False, box=None, expand=True, title="Help")
                htable.add_column("Column")
                htable.add_column("Details")
                htable.add_row(*[
                    f"[rgb(108,113,196)]mechanism",
                    "[grey89]The mechanism name"
                ])
                htable.add_row(*[
                    f"[rgb(253,246,227)]netuid",
                    "[grey89]The subnet index."
                ])
                htable.add_row(*[
                    f"[light_goldenrod1]symbol",
                    "[grey89]The subnet token symbol."
                ])
                htable.add_row(*[
                    f"[rgb(108,113,196)]n",
                    "[grey89]The number of registered neurons / max neurons."
                ])
                htable.add_row(*[
                    f"[rgb(38,139,210)]emission",
                    "[grey89]The subnet's emission rate."
                ])
                htable.add_row(*[
                    f"[rgb(220,50,47)]{bt.Balance.unit}",
                    f"[grey89]The total {bt.Balance.unit} locked in the subnet."
                ])
                htable.add_row(*[
                    f"[rgb(181,137,0)]{bt.Balance.get_unit(1)} -> {bt.Balance.unit}",
                    "[grey89]The exchange rate between stake and tao."
                ])
                htable.add_row(*[
                    f"[rgb(133,153,0)]{bt.Balance.get_unit(1)}",
                    f"[grey89]The total {bt.Balance.get_unit(1)} outstanding."
                ])
                htable.add_row(*[
                    f"[rgb(38,139,210)]next epoch",
                    "[grey89]Blocks until the next epoch."
                ])
                htable.add_row(*[
                    f"[rgb(220,50,47)]burn",
                    "[grey89]The subnet's burn rate."
                ])
                htable.add_row(*[
                    f"[rgb(108,113,196)]owner",
                    "[grey89]The subnet owner's name or address."
                ])
                # Print the table
                bt.__console__.clear()
                bt.__console__.print(combined_table)
                bt.__console__.print("")
                bt.__console__.print(htable, justify="center", width=bt.__console__.width)
                bt.__console__.print("")


                time.sleep(1)  # Wait for 1 second before updating
        except KeyboardInterrupt:
            bt.__console__.print("Stopped by user.")
            sys.exit(0)

    @staticmethod
    def check_config(config: "bt.config"):
        pass

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        list_subnets_parser = parser.add_parser(
            "list", help="""List all subnets on the network"""
        )
        bt.subtensor.add_args(list_subnets_parser)