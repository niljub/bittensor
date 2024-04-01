#!/usr/bin/env python
import asyncio
from bittensor.staging.import_hooks import install_lazy_loader

import sys
import shtab
from bittensor.cli import cli as btcli
from bittensor.btlogging import logging as bt_logging
from bittensor.staging.exceptions import RetriesExceededException, NetworkUnavailable, NetworkUnreachable


async def sub_main():
    # Create the parser with shtab support
    parser = btcli.__create_parser__()
    args, unknown = parser.parse_known_args()

    if args.print_completion:  # Check for print-completion argument
        print(shtab.complete(parser, args.print_completion))
        return

    try:
        cli_instance = btcli(args=sys.argv[1:])
        cli_instance.run()
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
    except RuntimeError as e:
        bt_logging.error(f'RuntimeError: {e}')
    except (NetworkUnreachable, NetworkUnavailable, RetriesExceededException) as e:
        bt_logging.error(f'Network error. {e}')


if __name__ == '__main__':
    install_lazy_loader(
        [
            "websocket",
            "substrateinterface",
            "bittensor.subtensor.subtensor",
        ]
    )
    import cProfile
    import pstats
    with cProfile.Profile() as pr:
        asyncio.run(sub_main())

    stats = pstats.Stats(pr)
    stats.sort_stats(pstats.SortKey.TIME)
    stats.print_stats()


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
