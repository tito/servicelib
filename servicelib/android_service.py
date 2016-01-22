# coding=utf-8

__all__ = ["AndroidService"]

from servicelib.base_service import BaseService
from jnius import autoclass


class AndroidService(BaseService):
    context = autoclass("org.kivy.android.PythonActivity").mActivity

    def __init__(self, name, entrypoint, **options):
        super(AndroidService, self).__init__(name, entrypoint, **options)
        self.package = self.context.getApplicationContext().getPackageName()
        self.java_class = "{}.Service{}".format(self.package,
                                                name.capitalize())
        self.service = autoclass(self.java_class)

    def start(self, arg=""):
        self.service.start(self.context, arg)

    def stop(self):
        self.service.stop(self.context)

    def is_running(self):
        # no idea how to check it right now.
        return False


Service = AndroidService
