import socket


def settimeout():
    """
    Override default excess socket timeout of 600 seconds.
    Shorter timeouts ensure that connectivity issues are detected faster
    and can thus be resolved. NetworkManager does not rely soley on
    socket timeouts, instead, it sends regular heartbeat messages to
    confirm that the connection is available.

    Returns:
        None
    """
    settimeout_func = socket.socket.settimeout

    def wrapper(self, timeout):
        # prohibit timeout reset
        if timeout is None:
            timeout = socket.getdefaulttimeout()
        if timeout > 90:
            timeout = 90
        settimeout_func(self, timeout)

    wrapper.__doc__ = settimeout_func.__doc__
    wrapper.__name__ = settimeout_func.__name__
    return wrapper


socket.socket.settimeout = settimeout
