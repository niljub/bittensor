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
import typing
import argparse
from rich.table import Table
from rich.prompt import Prompt
from typing import Optional

import bittensor
from .. import defaults
from ..utils import (
    get_delegates_details,
    DelegatesDetails,
)
from substrateinterface.exceptions import SubstrateRequestException

console = bittensor.__console__

class StakeList:
    @staticmethod
    def run(cli: "bittensor.cli"):
        r"""Show all stake accounts."""
        try:
            subtensor: "bittensor.subtensor" = bittensor.subtensor(
                config=cli.config, log_verbose=False
            )
            StakeList._run(cli, subtensor)
        finally:
            if "subtensor" in locals():
                subtensor.close()
                bittensor.logging.debug("closing subtensor connection")

    @staticmethod
    def _run(cli: "bittensor.cli", subtensor: "bittensor.subtensor"):
        wallet = bittensor.wallet(config=cli.config)
        
        try:
            while True:
                
                subnets: typing.List[bittensor.SubnetInfoV2] = subtensor.get_all_subnets_info_v2()
                
                substakes = subtensor.get_substake_for_coldkey(
                    coldkey_ss58=wallet.coldkeypub.ss58_address
                )

                # Get registered delegates details.
                registered_delegate_info: Optional[DelegatesDetails] = get_delegates_details(
                    url=bittensor.__delegates_details_url__
                )
                
                # Iterate over substakes and aggregate them by hotkey.
                hotkeys_to_substakes: typing.Dict[str, typing.List[typing.Dict]] = {}
                for substake in substakes:
                    hotkey = substake["hotkey"]
                    if substake["stake"].rao == 0: continue
                    if hotkey not in hotkeys_to_substakes:
                        hotkeys_to_substakes[hotkey] = []
                    hotkeys_to_substakes[hotkey].append( substake )
                    
                
                def table_substakes( hotkey:str, substakes: typing.List[typing.Dict] ):
                    # Create table structure.
                    name = registered_delegate_info[hotkey].name + f" ({hotkey})" if hotkey in registered_delegate_info else hotkey
                    table = Table(
                        title=f"{name}",
                        width=bittensor.__console__.width - 5,
                        safe_box=True,
                        padding=(0, 1),
                        collapse_padding=False,
                        pad_edge=True,
                        expand=True,
                        show_header=True,
                        show_footer=True,
                        show_edge=False,
                        show_lines=False,
                        leading=0,
                        style="none",
                        row_styles=None,
                        header_style="bold",
                        footer_style="bold",
                        border_style="rgb(7,54,66)",
                        title_style="bold magenta",
                        title_justify="center",
                        highlight=False
                    )
                    table.add_column(f"[white]mechanism", footer_style="white", style="rgb(253,246,227)", no_wrap=True, justify="center")
                    table.add_column(f"[white]netuid", footer_style="overline white", style="rgb(253,246,227)", no_wrap=True, justify="center")
                    table.add_column(f"[white]symbol", footer_style="overline white", style="light_goldenrod1", no_wrap=True, justify="center")
                    table.add_column(f"[white]{bittensor.Balance.get_unit(1)}", footer_style="overline white", style="rgb(38,139,210)", no_wrap=True, justify="center")
                    table.add_column(f"[white]{bittensor.Balance.get_unit(1)} -> {bittensor.Balance.unit} ", footer_style="white", style="rgb(181,137,0)", no_wrap=True, justify="center")
                    table.add_column(f"[white]{bittensor.Balance.unit}", footer_style="overline white", style="rgb(220,50,47)", no_wrap=True, justify="center")
                    table.add_column(f"[white]Δ{bittensor.Balance.unit}", style="rgb(133,153,0)", no_wrap=True, justify="right")
                    
                    rao_rows = []
                    finney_rows = []
                    
                    for substake in substakes:
                        netuid = substake['netuid']
                        pool = subnets[netuid].dynamic_pool
                        symbol = f"{bittensor.Balance.get_unit(netuid)}\u200E"
                        price = "{:.4f}{}".format( pool.price.__float__(), f"τ/{bittensor.Balance.get_unit(netuid)}\u200E") if pool.is_dynamic else f"{1.0}τ/{symbol}"
                        alpha_value = bittensor.Balance.from_rao( int(substake['stake']) ).set_unit(netuid)
                        tao_value = pool.alpha_to_tao(alpha_value)
                        swapped_tao_value, slippage = pool.alpha_to_tao_with_slippage( substake['stake'] )
                        if pool.is_dynamic:
                            slippage_percentage = 100 * float(slippage) / float(slippage + swapped_tao_value) if slippage + swapped_tao_value != 0 else 0
                            slippage_percentage = f"{slippage_percentage:.4f}%"
                        else:
                            slippage_percentage = 'N/A'                
                        tao_locked = pool.tao_reserve if pool.is_dynamic else subtensor.get_total_subnet_stake(netuid).set_unit(netuid)
                        issuance = pool.alpha_outstanding if pool.is_dynamic else tao_locked
                        alpha_ownership = "{:.4f}".format((alpha_value.tao / issuance.tao) * 100)
                        tao_ownership = bittensor.Balance.from_tao((alpha_value.tao / issuance.tao) * tao_locked.tao)
                        row = [
                            "", # Mechanism
                            str(netuid), # Number
                            symbol, # Symbol
                            f"[dark_sea_green]{ alpha_value }", # Alpha value
                            price, # Price
                            f"[cadet_blue]{ swapped_tao_value }[/cadet_blue] (-[indian_red]{ slippage_percentage }[/indian_red])", # Swap amount.
                            f"[medium_purple]{tao_ownership}[/medium_purple]", # Tao ownership.
                        ]
                        if pool.is_dynamic:
                            rao_rows.append(row)
                        else:
                            finney_rows.append(row)
                    
                    # Add RAO rows first
                    table.add_row("[bold red]Rao[/bold red]", "", "", "", "", "", "" ) # f"[white]τ{total_price.tao:.4f}{price_arrow}[/white]" 
                    for row in rao_rows:
                        table.add_row(*row)
                    
                    # Add a separator row if both RAO and Finney rows exist
                    table.add_row("[bold blue]Finney[/bold blue]", "", "", "", "", "", "" ) 
                    if rao_rows and finney_rows:
                        table.add_row(*["" for _ in range(7)])
                    
                    # Add Finney rows
                    for row in finney_rows:
                        table.add_row(*row)
                    
                    bittensor.__console__.print(table, justify="center", width=bittensor.__console__.width)

                # Print help table
                htable = Table(show_footer=False, pad_edge=False, box=None, expand=True, title="Help")
                htable.add_column("Column")
                htable.add_column("Details")
                htable.add_row(*[
                    f"[rgb(108,113,196)]mechanim",
                    "[rgb(108,113,196)]The mechanism name"
                ])
                htable.add_row(*[
                    f"[dark_sea_green]netuid",
                    "[dark_sea_green]The subnet index."
                ])
                htable.add_row(*[
                    f"[light_goldenrod1]symbol",
                    "[light_goldenrod1]The subnet token symbol."
                ])
                htable.add_row(*[
                    f"[dark_sea_green]{bittensor.Balance.get_unit(1)}",
                    "[dark_sea_green]The staked token balance"
                ])
                htable.add_row(*[
                    f"[light_goldenrod2]{bittensor.Balance.get_unit(1)} -> {bittensor.Balance.unit}",
                    "[light_goldenrod2]The exchange rate between tao and the staked token."
                ])
                htable.add_row(*[
                    f"[cadet_blue]{bittensor.Balance.unit}",
                    f"[cadet_blue]{bittensor.Balance.unit} value attained after unstaking [indian_red](with slippage %)[/indian_red]"
                ])
                htable.add_row(*[
                    f"[medium_purple]Δ{bittensor.Balance.unit}",
                    f"[medium_purple]The stake's global value (Δ{bittensor.Balance.unit}) across all of Bittensor's mechanisms."
                ])

                # Iterate over each hotkey and make a table
                bittensor.__console__.clear()
                bittensor.__console__.print("")
                bittensor.__console__.print("")
                for hotkey in hotkeys_to_substakes.keys():
                    table_substakes( hotkey, hotkeys_to_substakes[hotkey] )
                bittensor.__console__.print("")
                bittensor.__console__.print(htable, justify="center", width=bittensor.__console__.width)
                bittensor.__console__.print("")
                
                # Wait for 1 second before refreshing
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            console.print("Stopped by user.")
            return


    @staticmethod
    def check_config(config: "bittensor.config"):
        if not config.is_set("wallet.name") and not config.no_prompt:
            wallet_name = Prompt.ask("Enter wallet name", default=defaults.wallet.name)
            config.wallet.name = str(wallet_name)

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        list_parser = parser.add_parser(
            "list", help="""List all stake accounts for wallet."""
        )
        bittensor.wallet.add_args(list_parser)
        bittensor.subtensor.add_args(list_parser)
