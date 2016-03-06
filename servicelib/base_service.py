# coding=utf-8


class BaseService(object):
    def __init__(self, name, entrypoint, **options):
        self.name = name
        self.entrypoint = entrypoint
        self.options = options
        super(BaseService, self).__init__()

    def start(self, arg=""):
        pass

    def stop(self):
        pass

    @property
    def module(self):
        mod = self.entrypoint.replace("/", ".")
        if mod.endswith(".py"):
            mod = mod[:-3]
        elif mod.endswith(".pyo"):
            mod = mod[:-4]
        elif mod.endswith(".pyc"):
            mod = mod[:-4]
        return mod
