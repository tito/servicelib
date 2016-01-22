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
