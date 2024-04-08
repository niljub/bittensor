import importlib.abc
import sys
from logging import getLogger
from typing import Any, Callable, Dict, List, Optional, Type, Union

logger = getLogger(__name__)


class LazyLoader(importlib.abc.Loader):
    """
    A loader that defers the loading of a module until an attribute is accessed.
    """

    def __init__(self, fullname: str, path: Optional[str]):
        self.module_name = fullname
        self.path = path

    def create_module(self, spec):
        # Create a new module object, but don't initialize it yet.
        return None

    def exec_module(self, module):
        # Replace the module's class with a subclass that uses __getattr__
        # to load the module upon first attribute access.
        module.__class__ = LazyModule
        module.__dict__["_lazy_name"] = self.module_name
        module.__dict__["_lazy_loaded"] = False


class LazyModule(importlib.abc.Loader):
    """
    Subclass of the module type that loads the actual module upon first attribute access.
    """

    def __getattr__(self, name):
        if "_lazy_loaded" not in self._proxy.__dict__:
            self._proxy.__dict__["_lazy_loaded"] = True
            loader = importlib.machinery.SourceFileLoader(
                self._proxy.__dict__["_lazy_name"], self._proxy.__dict__["_lazy_name"]
            )
            loader.exec_module(self)
        return getattr(self, name)


class LazyProperty(object):
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            value = self.func(instance)
            setattr(instance, self.func.__name__, value)
            return value


class LazyImportFinder(importlib.abc.MetaPathFinder):
    """
    A meta_path finder to support lazy loading of modules.
    """

    def __init__(self, to_lazy_load: List[str]):
        self.to_lazy_load = to_lazy_load

    def find_spec(self, fullname, path, target=None):
        if fullname in self.to_lazy_load:
            return importlib.machinery.ModuleSpec(fullname, LazyLoader(fullname, path))


def install_lazy_loader(to_lazy_load: List[str]):
    """
    Install the lazy loader for the specified modules.

    Args:
    to_lazy_load (List[str]): A list of fully qualified module names to lazy load.
    """
    sys.meta_path.insert(0, LazyImportFinder(to_lazy_load))
