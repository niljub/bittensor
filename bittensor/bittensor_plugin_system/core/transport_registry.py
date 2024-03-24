




class PluginRegistry:
    def __init__(self):
        self.plugins = {}

    def register(self, plugin):
        self.plugins[plugin.name] = plugin

    def get_plugin(self, name):
        return self.plugins.get(name)

    def initialize_plugins(self):
        for plugin in self.plugins.values():
            plugin.initialize()