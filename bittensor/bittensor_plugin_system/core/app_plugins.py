


class MessagingTransportPlugin(BasePlugin):
    def __init__(self, name, protocol):
        super().__init__(name)
        self.protocol = protocol

    def send_message(self, message):
        pass  # Implementation specifi