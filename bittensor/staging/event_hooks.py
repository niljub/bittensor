from typing import Callable, Dict, Tuple, List, TypeVar, Callable, Any
from injector import Injector, inject, singleton
from functools import wraps

T = TypeVar("T")


class EventHook:
    """A class for managing subscriptions and notifications with enhanced filtering."""

    def __init__(self) -> None:
        self._listeners: Dict[Tuple[str, str, str], List[Callable]] = {}

    def _get_listeners(
        self, topic: str, request_id: str = "*", group: str = "*"
    ) -> List[Callable]:
        """Retrieve listeners matching the specific criteria.

        Args:
            topic (str): The event topic.
            request_id (str): The request ID.
            group (str): The group name.

        Returns:
            List[Callable]: A list of matching listener functions.
        """
        listeners = []
        for (t, r_id, grp), lst in self._listeners.items():
            if (
                (t == topic or t == "*")
                and (r_id == request_id or r_id == "*")
                and (grp == group or grp == "*")
            ):
                listeners.extend(lst)
        return listeners

    def subscribe(
        self, listener: Callable, topic: str, request_id: str = "*", group: str = "*"
    ) -> None:
        """Subscribe a listener to a specific event with optional request_id and group filtering.

        Args:
            listener (Callable): The listener function to register.
            topic (str): The event topic.
            request_id (str): The request ID.
            group (str): The group name.
        """
        key = (topic, request_id, group)
        if key not in self._listeners:
            self._listeners[key] = []
        self._listeners[key].append(listener)

    def unsubscribe(
        self, listener: Callable, topic: str, request_id: str = "*", group: str = "*"
    ) -> None:
        """Unsubscribe a listener from a specific event.

        Args:
            listener (Callable): The listener function to unregister.
            topic (str): The event topic.
            request_id (str): The request ID.
            group (str): The group name.
        """
        key = (topic, request_id, group)
        if key in self._listeners:
            self._listeners[key].remove(listener)
            if not self._listeners[key]:  # Remove the key if no listeners are left
                del self._listeners[key]

    def notify(
        self, topic: str, *args, request_id: str = "*", group: str = "*", **kwargs
    ) -> None:
        """Notify all registered listeners for a topic, optionally filtering by request_id and group.

        Args:
            topic (str): The event topic.
            *args: Variable length argument list.
            request_id (str): The request ID.
            group (str): The group name.
            **kwargs: Arbitrary keyword arguments.
        """
        listeners = self._get_listeners(topic, request_id, group)
        for listener in listeners:
            listener(*args, **kwargs)


class EventPublisher:
    """A publisher class that supports advanced event subscription and notification."""

    def __init__(self) -> None:
        self.event_hook = EventHook()

    def add_listener(
        self, listener: Callable, topic: str, request_id: str = "*", group: str = "*"
    ) -> None:
        """Add a listener for a specific topic, with optional request_id and group.

        Args:
            listener (Callable): The function to subscribe as a listener.
            topic (str): The event topic.
            request_id (str): Optional; The request ID for more granular filtering.
            group (str): Optional; The group name for additional filtering.
        """
        self.event_hook.subscribe(listener, topic, request_id, group)

    def remove_listener(
        self, listener: Callable, topic: str, request_id: str = "*", group: str = "*"
    ) -> None:
        """Remove a listener for a specific topic, with optional request_id and group.

        Args:
            listener (Callable): The function to unsubscribe.
            topic (str): The event topic.
            request_id (str): Optional; The request ID for more granular filtering.
            group (str): Optional; The group name for additional filtering.
        """
        self.event_hook.unsubscribe(listener, topic, request_id, group)

    def publish_event(
        self, topic: str, *args, request_id: str = "*", group: str = "*", **kwargs
    ) -> None:
        """Publish an event for a specific topic, optionally filtering by request_id and group.

        Args:
            topic (str): The event topic.
            *args: Variable length argument list.
            request_id (str): Optional; The request ID for more granular filtering.
            group (str): Optional; The group name for additional filtering.
            **kwargs: Arbitrary keyword arguments.
        """
        self.event_hook.notify(
            topic, *args, request_id=request_id, group=group, **kwargs
        )


def before_hook(hook: Callable) -> Callable:
    """Decorator to add a before hook to a function.

    Args:
        hook (Callable): The function to execute before the decorated function.

    Returns:
        Callable: The decorated function with the before hook.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            hook()
            return func(*args, **kwargs)

        return wrapper

    return decorator


def after_hook(hook: Callable) -> Callable:
    """Decorator to add an after hook to a function.

    Args:
        hook (Callable): The function to execute after the decorated function.

    Returns:
        Callable: The decorated function with the after hook.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)
            hook()
            return result

        return wrapper

    return decorator


class PublishingModule:
    """Module for binding interfaces to implementations."""

    @singleton
    def provide_publisher(self) -> EventPublisher:
        """Provides a singleton instance of EventPublisher."""
        return EventPublisher()


class AppInjector(Injector):
    """Custom injector that includes our publishing module."""

    def __init__(self):
        super().__init__([PublishingModule()])


@inject
def publish_before(
    topic: str,
    request_id: str = "*",
    group: str = "*",
    publisher: EventPublisher = None,
) -> Callable:
    """Decorator to publish an event before function execution."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                # Optionally include arguments in the event
                publisher.publish_event(
                    topic,
                    *args,
                    request_id=request_id,
                    group=group,
                    **kwargs,
                    outcome="before_execution",
                )
            except Exception as e:
                # Handle or log the error if needed
                print(f"Error publishing before event: {e}")
            return func(*args, **kwargs)

        return wrapper

    return decorator


@inject
def publish_after(
    topic: str,
    request_id: str = "*",
    group: str = "*",
    publisher: EventPublisher = None,
) -> Callable:
    """Decorator to publish an event after function execution."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                result = func(*args, **kwargs)
                # Include function return value in the event
                publisher.publish_event(
                    topic,
                    *args,
                    request_id=request_id,
                    group=group,
                    **kwargs,
                    outcome="completed",
                    return_value=result,
                )
            except Exception as e:
                # Include exception details in the event
                publisher.publish_event(
                    topic,
                    *args,
                    request_id=request_id,
                    group=group,
                    **kwargs,
                    outcome="failed",
                    exception=str(e),
                )
                # Optionally re-raise the exception or handle it
                raise
            return result

        return wrapper

    return decorator


# Usage
injector = AppInjector()
