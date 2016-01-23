# coding=utf-8
"""
Local service using ZMQ
=======================

"""

import zmq
import os
from threading import Thread, Event
from servicelib import Service


class ZmqService(Service):
    def __init__(self, name, entrypoint, on_message=None, **options):
        self._channel = None
        self.on_message = on_message
        super(ZmqService, self).__init__(name, entrypoint, **options)

    def start(self, arg=None):
        self.setup_zmq_channel()
        super(ZmqService, self).start(str(self._channel_port))

    def stop(self):
        super(ZmqService, self).stop()
        self._quit = True
        self._channel = None

    def setup_zmq_channel(self):
        if self._channel is not None:
            return
        self._quit = False
        self._event = Event()
        self._channel = Thread(target=self._zmq_channel_run)
        self._channel.daemon = True
        self._channel.start()
        self._event.wait()

    def setup_zmq_service(self, port):
        context = zmq.Context()
        self.socket = context.socket(zmq.PAIR)
        self.socket.connect("tcp://127.0.0.1:{}".format(port))
        self.on_message("READY")

    def _zmq_channel_run(self):
        from kivy.clock import Clock
        context = zmq.Context()
        socket = context.socket(zmq.PAIR)
        port = socket.bind_to_random_port("tcp://127.0.0.1")
        self._channel_port = port
        self._event.set()
        while not self._quit:
            if not socket.poll(10):
                continue
            message = socket.recv_multipart()
            if message[0] == "READY":
                Clock.schedule_once(
                    lambda dt: self.setup_zmq_service(message[1]), 0)
            else:
                self.dispatch_message(*message)
        self._event.set()
        socket.close()

    def dispatch_message(self, command, *args):
        handle = "on_{}".format(command)
        if hasattr(self, handle):
            getattr(self, handle)(*args)
        elif self.on_message:
            self.on_message(command, *args)
        else:
            print("ZmqService: no handler for {}".format(command))

    def ping(self, on_pong):
        if not self.socket:
            return None

    def send(self, *args):
        self.socket.send_multipart(args)


class ZmqServiceImpl(object):
    socket_in = None
    socket_out = None
    quit = False

    def run(self):
        port = int(os.getenv("PYTHON_SERVICE_ARGUMENT"))
        context = zmq.Context()

        # in communication
        self.socket_in = context.socket(zmq.PAIR)
        service_port = self.socket_in.bind_to_random_port("tcp://127.0.0.1")

        # app communication
        self.socket_out = context.socket(zmq.PAIR)
        self.socket_out.connect("tcp://127.0.0.1:{}".format(port))
        self.socket_out.send_multipart(("READY", str(service_port)))

        # wait for commands
        while not self.quit:
            message = self.socket_in.recv_multipart()
            self.dispatch_message(*message)

    def dispatch_message(self, command, *args):
        handle = "on_{}".format(command)
        if hasattr(self, handle):
            getattr(self, handle)(*args)

    def send(self, *args):
        self.socket_out.send_multipart(args)

    def on_QUIT(self):
        self.send("STOPPED")
        self.quit = True

    def on_PING(self, timestamp):
        self.send("PONG", timestamp)
