import os
from typing import List, Tuple, Union
import yaml
import importlib.util
import inspect
import ast
from abc import ABC, abstractmethod


class PluginSpecificationChecker:
    """
    A class to check if a plugin under the plugins directory matches a specified
    structure and content requirements including the existence of specific files,
    classes, and inheritance, with added security checks for code obfuscation,
    forbidden imports and forbidden function calls.

    Attributes:
        feature (str): The feature category of the plugin.
        plugin_name (str): The name of the plugin.
    """

    def __init__(self, feature: str, plugin_name: str) -> None:
        self.feature = feature
        self.plugin_name = plugin_name
        self.plugin_path = f"plugins/{self.feature}/{self.plugin_name}_plugin"
        self.system_plugins_path = "system_plugins"

    def check_plugin(self) -> Tuple[bool, List[str]]:
        """
        Performs a series of checks to verify the plugin's compliance with the
        specified requirements.

        Returns:
            Tuple[bool, List[str]]: A tuple containing a boolean indicating the
            success of the checks, and a list of strings detailing any issues found.
        """
        issues = []

        # Check for conflicts with system plugins
        if self._plugin_name_conflict():
            issues.append(
                f"Plugin name '{self.plugin_name}' conflicts with a system plugin."
            )

        # Check for required files
        required_files_checks = [
            self._check_file_exists("defaults.yml"),
            self._check_file_exists("__init__.py"),
            self._check_file_exists("plugin.py"),
            self._check_file_exists("config.py"),
            self._check_for_obfuscated_code("plugin.py"),
            self._check_for_obfuscated_code("config.py"),
        ]
        for check_result, msg in required_files_checks:
            if not check_result:
                issues.append(msg)

        # Dynamic checks on plugin.py and config.py for class existence,
        # inheritance, and abstract methods implementation
        dynamic_checks = [
            self._check_dynamic_class_file(
                "plugin.py",
                f"{self.plugin_name.capitalize()}{self.feature.capitalize()}Plugin",
                f"{self.feature.capitalize()}BasePlugin",
            ),
            self._check_dynamic_class_file(
                "config.py",
                f"{self.plugin_name.capitalize()}PluginConfig",
                f"{self.feature.capitalize()}BaseConfig",
            ),
        ]
        for check_result, msg in dynamic_checks:
            if not check_result:
                issues.append(msg)

        return len(issues) == 0, issues

    def _plugin_name_conflict(self) -> bool:
        """
        Checks if the plugin name conflicts with any existing system plugin.

        Returns:
            bool: True if there is a conflict, False otherwise.
        """
        system_plugin_path = os.path.join(self.system_plugins_path, self.feature)
        return self.plugin_name in os.listdir(system_plugin_path)

    def _check_file_exists(self, filename: str) -> Tuple[bool, str]:
        """
        Checks if a specified file exists within the plugin directory.

        Args:
            filename (str): The name of the file to check.

        Returns:
            Tuple[bool, str]: A tuple containing a boolean indicating if the file
            exists, and a string with a message if it doesn't.
        """
        file_path = os.path.join(self.plugin_path, filename)
        if not os.path.exists(file_path):
            return False, f"Required file '{filename}' is missing."
        return True, ""

    def _check_dynamic_class_file(
        self, filename: str, class_name: str, base_class_name: str
    ) -> Tuple[bool, Union[str, None]]:
        """
        Dynamically loads a Python file and checks for the existence of a specified
        class, its inheritance, and the implementation of all abstract methods.

        Args:
            filename (str): The name of the Python file to load.
            class_name (str): The name of the class to check for.
            base_class_name (str): The name of the base class that the class should inherit from.

        Returns:
            Tuple[bool, Union[str, None]]: A tuple containing a boolean indicating
            the success of the checks, and an optional string with details if a check fails.
        """
        file_path = os.path.join(self.plugin_path, filename)
        module_name = file_path.replace("/", ".").rstrip(".py")

        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            return False, f"Unable to load module for file '{filename}'."
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Check for class existence
        if not hasattr(module, class_name):
            return False, f"Required class '{class_name}' is missing in '{filename}'."

        cls = getattr(module, class_name)

        # Check for correct inheritance
        if not issubclass(cls, getattr(module, base_class_name, ABC)):
            return (
                False,
                f"Class '{class_name}' does not inherit from '{base_class_name}'.",
            )

        # Check for abstract methods implementation
        if inspect.isabstract(cls):
            return (
                False,
                f"Class '{class_name}' does not implement all abstract methods.",
            )

        return True, None

    def check_config_imports(self) -> Tuple[bool, str]:
        """
        Checks the config.py of the plugin for forbidden imports.

        Returns:
            Tuple[bool, str]: A tuple containing a boolean indicating if the config
            passes the check, and a string with a message if it doesn't.
        """
        forbidden_imports = [
            "subtensor",
            "axon",
            "metagraph",
            "wallet",
            "keyfile",
            "subnets",
            "synapse",
            "stream",
            "dendrite",
            "cli",
            "chain_data",
        ]
        return self._check_forbidden_imports("config.py", forbidden_imports)

    def check_plugin_security(self) -> Tuple[bool, str]:
        """
        Checks the plugin.py for forbidden imports and specific function calls.

        Returns:
            Tuple[bool, str]: A tuple containing a boolean indicating if the plugin
            passes the security checks, and a string with a message if it doesn't.
        """
        forbidden_imports = ["wallet", "keyfile"]
        forbidden_calls = ["subtensor.transfer"]
        import_issues, import_msg = self._check_forbidden_imports(
            "plugin.py", forbidden_imports
        )
        call_issues, call_msg = self._check_forbidden_calls(
            "plugin.py", forbidden_calls
        )

        if not import_issues and not call_issues:
            return True, ""
        messages = []
        if import_msg:
            messages.append(import_msg)
        if call_msg:
            messages.append(call_msg)
        return (
            False,
            " WARNING: Security issue found. "
            + " ".join(messages)
            + " Use --accept-risk to override.",
        )

    def _check_forbidden_imports(
        self, filename: str, forbidden_imports: List[str]
    ) -> Tuple[bool, str]:
        """
        Checks a Python file for forbidden imports.

        Args:
            filename (str): The name of the file to check.
            forbidden_imports (List[str]): A list of forbidden imports.

        Returns:
            Tuple[bool, str]: A tuple indicating whether the file is free of forbidden
            imports, and a message if it's not.
        """
        with open(os.path.join(self.plugin_path, filename), "r") as file:
            tree = ast.parse(file.read(), filename=filename)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in forbidden_imports:
                        return (
                            False,
                            f"Forbidden import '{alias.name}' found in {filename}.",
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module in forbidden_imports:
                    return (
                        False,
                        f"Forbidden import '{node.module}' found in {filename}.",
                    )

        return True, ""

    def _check_forbidden_calls(
        self, filename: str, forbidden_calls: List[str]
    ) -> Tuple[bool, str]:
        """
        Checks a Python file for forbidden function calls.

        Args:
            filename (str): The name of the file to check.
            forbidden_calls (List[str]): A list of strings representing forbidden function calls.

        Returns:
            Tuple[bool, str]: A tuple indicating whether the file is free of forbidden
            calls, and a message if it's not.
        """
        with open(os.path.join(self.plugin_path, filename), "r") as file:
            tree = ast.parse(file.read(), filename=filename)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if (
                    hasattr(node.func, "attr")
                    and f"{node.func.value.id}.{node.func.attr}" in forbidden_calls
                ):
                    return (
                        False,
                        f"Forbidden call '{node.func.value.id}.{node.func.attr}' found in {filename}.",
                    )
                elif hasattr(node.func, "id") and node.func.id in forbidden_calls:
                    return (
                        False,
                        f"Forbidden call '{node.func.id}' found in {filename}.",
                    )

        return True, ""

    def _check_for_obfuscated_code(self, file_path: str) -> Tuple[bool, List[str]]:
        """
        Checks a Python file for obfuscated code, such as base64 encoded strings that are
        executed, among other potentially obfuscating techniques.

        Args:
            file_path (str): The path to the file to be checked.

        Returns:
            Tuple[bool, List[str]]: A tuple containing a boolean indicating if obfuscation
            was detected and a list of strings describing each instance of obfuscation found.
        """
        with open(file_path, "r", encoding="utf-8") as file:
            tree = ast.parse(file.read(), filename=file_path)

        issues = []

        class ObfuscationDetector(ast.NodeVisitor):
            def visit_Call(self, node):
                if isinstance(node.func, ast.Name) and node.func.id in ["exec", "eval"]:
                    issues.append(
                        " WARNING: Security issue found. " +
                        f"Usage of {node.func.id}() which can execute dynamic code."
                    )
                self.generic_visit(node)

            def visit_Str(self, string):
                if "base64" in string.s:
                    issues.append(
                        " WARNING: Security issue found. " +
                        "Potential base64 encoded string found which could be obfuscated code."
                    )
                self.generic_visit(string)

            def visit_Bytes(self, bytes):
                try:
                    if "base64" in bytes.s.decode():
                        issues.append(
                            " WARNING: Security issue found. " +
                            "Potential base64 encoded bytes found which could be obfuscated code."
                        )
                except Exception:
                    pass
                self.generic_visit(bytes)

        ObfuscationDetector().visit(tree)

        return len(issues) == 0, issues

# Example usage:
# checker = PluginSpecificationChecker("feature_name", "plugin_name")
# is_valid, issues = checker.check_plugin()
# if is_valid:
#     print("Plugin is valid.")
# else:
#     print("Plugin issues:", issues)
