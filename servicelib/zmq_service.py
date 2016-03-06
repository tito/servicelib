# coding=utf-8
"""
Local service using ZMQ
=======================

"""

import zmq
import os
from time import time
from threading import Thread, Event, current_thread
from servicelib import Service
import pickle


class TimeoutException(Exception):
    pass


class ZmqService(Service):
    def __init__(self, name, entrypoint, on_message=None, **options):
        self._channel = None
        self.socket = None
        self.service_port = None
        self._is_ready = Event()
        self._is_stopped = Event()
        self._can_bind = Event()
        self.on_message = on_message
        super(ZmqService, self).__init__(name, entrypoint, **options)

    def start(self, *args):
        # print("{}: start".format(self.__class__.__name__))
        self._is_ready.clear()
        self._is_stopped.clear()
        self._can_bind.clear()
        self.setup_zmq_channel()
        super(ZmqService, self).start(str(self._channel_port))

    def soft_quit(self):
        self.send("QUIT")

    def stop(self, *args):
        # print("{}: stop".format(self.__class__.__name__))
        super(ZmqService, self).stop()
        self._quit = True
        self._channel = None

    def restart(self, *args):
        self.stop()
        self.start()

    @property
    def is_ready(self):
        return self._is_ready.is_set()

    def wait_ready(self, timeout=None):
        # print("{}: waiting service to be ready".format(self.__class__.__name__))
        start = time()
        while True:
            self.poll()
            if timeout is not None and timeout > 0:
                if time() - start > timeout:
                    raise TimeoutException()
            if self._is_ready.wait(0.1):
                break
        # print("{}: service is ready".format(self.__class__.__name__))

    def wait_stopped(self, timeout=None):
        print("{}: waiting service to be stopped".format(self.__class__.__name__))
        start = time()
        while True:
            self.poll()
            if timeout is not None and timeout > 0:
                if time() - start > timeout:
                    return False
            if self._is_stopped.wait(0.1):
                break
        return True
        print("{}: service is stopped".format(self.__class__.__name__))

    def setup_zmq_channel(self):
        if self._channel is not None:
            return
        # print("{}: setup zmq channel".format(self.__class__.__name__))
        self._quit = False
        self._event = Event()
        self._channel = Thread(target=self._zmq_channel_run)
        self._channel.daemon = True
        self._channel.start()
        # print("{}: waiting zmq channel to be up".format(self.__class__.__name__))
        self._event.wait()
        # print("{}: zmq channel ready".format(self.__class__.__name__))

    def setup_zmq_service(self):
        # print("{}: connect to service".format(self.__class__.__name__))
        context = zmq.Context()
        self.socket = context.socket(zmq.PAIR)
        self.socket.connect("tcp://127.0.0.1:{}".format(self.service_port))
        # print("{}: sending READY".format(self.__class__.__name__))
        self.dispatch_message("READY")
        # print("{}: waiting READY".format(self.__class__.__name__))
        self._is_ready.set()
        # print("{}: READY done".format(self.__class__.__name__))

    def poll(self, *args):
        # print("{}: poll".format(self.__class__.__name__))
        if self.socket is None and self._can_bind.is_set():
            self.setup_zmq_service()

    def _zmq_channel_run(self):
        try:
            self._zmq_channel_run_handle()
        except:
            import traceback
            traceback.print_exc()

    def _zmq_channel_run_handle(self):
        from kivy.clock import Clock
        context = zmq.Context()
        socket = context.socket(zmq.PULL)
        port = socket.bind_to_random_port("tcp://127.0.0.1")
        self._channel_port = port
        self._event.set()
        while not self._quit:
            if not socket.poll(10):
                continue
            command, args = socket.recv_multipart()
            args = pickle.loads(args)
            if command == "READY":
                self.service_port = args[0]
                self._can_bind.set()
                Clock.schedule_once(self.poll, 0)
            elif command == "STOPPED":
                self._is_stopped.set()
            else:
                self.dispatch_message(command, *args)
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

    def send(self, command, *args):
        args = pickle.dumps(args)
        self.socket.send_multipart([command, args])


class ZmqServiceImpl(object):
    socket_in = None
    socket_out = None
    quit = False
    port = None
    ident = None

    def run(self):
        self.ident = current_thread().ident
        self.port = port = int(os.getenv("PYTHON_SERVICE_ARGUMENT"))
        context = zmq.Context()

        # in communication
        self.socket_in = context.socket(zmq.PAIR)
        service_port = self.socket_in.bind_to_random_port("tcp://127.0.0.1")

        # app communication
        self.socket_out = context.socket(zmq.PUSH)
        self.socket_out.connect("tcp://127.0.0.1:{}".format(port))
        self.send("READY", service_port)

        # wait for commands
        while not self.quit:
            command, args = self.socket_in.recv_multipart()
            args = pickle.loads(args)
            self.dispatch_message(command, *args)

    def dispatch_message(self, command, *args):
        handle = "on_{}".format(command)
        if hasattr(self, handle):
            getattr(self, handle)(*args)

    def send(self, command, *args):
        args = pickle.dumps(args)
        self.socket_out.send_multipart([command, args])

    def on_QUIT(self):
        self.send("STOPPED")
        self.quit = True

    def on_PING(self, timestamp):
        self.send("PONG", timestamp)

    def get_context(self):
        return ZmqServiceImplContext(self)


class ZmqServiceImplContext(object):
    def __init__(self, impl):
        self.impl = impl
        self.ident = current_thread().ident
        self.context = None
        if self.ident == impl.ident:
            # same thread, reuse socket
            self.socket = impl.socket_out
        else:
            # new thread, new context
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.PUSH)
            self.socket.connect("tcp://127.0.0.1:{}".format(impl.port))
        super(ZmqServiceImplContext, self).__init__()

    def send(self, command, *args):
        args = pickle.dumps(args)
        self.socket.send_multipart([command, args])

    def release(self):
        if self.context is not None:
            self.context.destroy()
            self.context = None
