from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.widgets import TextArea

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
    "help": {
        "name": "help",
        "aliases": ["h"],
        "help": "Commands for helpful info on the CLI.",
        "commands": {}
    }
}

# Create text areas (widgets) for input and output
input_text_area = TextArea(focusable=True, prompt='Input: ')
output_text_area = TextArea(focusable=False)

# Define a key binding to process input and display output
kb = KeyBindings()

@kb.add('enter')
def _(event):
    # Get input text, process it, and update the output area
    input_text = input_text_area.text
    sub_cmds = {}
    tokens = input_text.split()
    if not len(tokens):
        return print("Type 'help' for a list of commands.")

    while tokens:
        # Imagine processing input_text here and generating output
        if tokens[0] in COMMANDS:
            sub_cmds = COMMANDS[tokens.pop()]['commands']

        if tokens[0] in sub_cmds:
            sub_cmds[tokens.pop()]()

        output_text = "Processed: " + input_text
        output_text_area.text = output_text
        input_text_area.text = ''  # Clear input area

# Define layout: Split horizontally, input on top, output on bottom
layout = Layout(HSplit([output_text_area, input_text_area]))

# Create the application instance with layout and key bindings
app = Application(layout=layout, key_bindings=kb, full_screen=True)

if __name__ == '__main__':
    app.run()
