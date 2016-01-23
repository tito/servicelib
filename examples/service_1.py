# coding=utf-8
"""
ZMQ communication demo
======================

"""

from servicelib.zmq_service import ZmqServiceImpl


class MyService(ZmqServiceImpl):
    def on_ECHO(self, *args):
        self.send("ECHO", *args)

    def on_COMPUTE(self, *args):
        result = sum(map(float, args))
        self.send("RESULT", str(result))


service = MyService()
service.run()
