class NetworkUnavailable(Exception):
    pass


class NetworkUnreachable(Exception):
    pass


class RetriesExceededException(Exception):
    pass


class SubscribersExceededException(Exception):
    pass


class MessagesExceededException(Exception):
    pass


class ConsumersExceededException(Exception):
    pass


class ConsumersNotConnectedException(Exception):
    pass


class MessagesNotConnectedException(Exception):
    pass
