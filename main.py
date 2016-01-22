from kivy.app import App
from kivy.utils import platform
from kivy.uix.button import Button
from kivy.logger import Logger
from kivy.lang import Builder
from threading import Thread, Event
from kivy.clock import Clock
import zmq

kv = """
BoxLayout:
    orientation: "vertical"
    BoxLayout:
        ToggleButton:
            text: "Service 1"
            on_state: app.toggle_service1(self.state == "down")
            state: "down" if app.is_service1_running() else "normal"
        Button:
            text: "Compute"
            on_release: app.s1.socket.send_multipart(["COMPUTE", "6684", "6513"])
        Button:
            text: "Echo"
            on_release: app.s1.socket.send_multipart(["ECHO", "Hello world"])
    ToggleButton:
        text: "Service 2"
        on_state: app.toggle_service2(self.state == "down")
        state: "down" if app.is_service2_running() else "normal"
    ToggleButton:
        text: "Service 3"
        on_state: app.toggle_service3(self.state == "down")
        state: "down" if app.is_service3_running() else "normal"
"""


class BaseService(object):
    def __init__(self, name, entrypoint, **options):
        self.name = name
        self.entrypoint = entrypoint
        self.options = options
        super(BaseService, self).__init__()

    def start(self, arg):
        pass

    def stop(self):
        pass


if platform == "android":
    from jnius import autoclass

    class AndroidService(BaseService):
        context = autoclass("org.kivy.android.PythonActivity").mActivity
        def __init__(self, name, entrypoint, **options):
            super(AndroidService, self).__init__(name, entrypoint, **options)
            self.package = self.context.getApplicationContext().getPackageName()
            self.java_class = "{}.Service{}".format(
                self.package, name.capitalize())
            self.service = autoclass(self.java_class)

        def start(self, arg):
            self.service.start(context, arg)

        def stop(self):
            self.service.stop(context)

        def is_running(self):
            # no idea how to check it right now.
            return False


    Service = AndroidService
else:

    import sys
    import os
    import subprocess
    import signal
    class SubprocessService(BaseService):
        def __init__(self, name, entrypoint, **options):
            super(SubprocessService, self).__init__(name, entrypoint, **options)
            self.entrypoint_dir = os.getcwd()
            self.process = None
            self.pid = None

            # check if a pid is already present
            try:
                with open(self.pid_filename) as fd:
                    self.pid = int(fd.read())
                try:
                    os.kill(self.pid, 0)
                except OSError:
                    # process is gone
                    print "Service {} was gone, removing pid file".format(self.name)
                    try:
                        os.unlink(self.pid_filename)
                    except:
                        pass
                    self.pid = None
                print "Service {} is already running (pid={})".format(self.name, self.pid)
            except:
                pass

        @property
        def pid_filename(self):
            pid_fn = "{}.pid".format(self.entrypoint.rsplit(".", 1)[0])
            return os.path.join(self.entrypoint_dir, pid_fn)

        def start(self, arg):
            env = os.environ.copy()
            env["PYTHON_SERVICE_ARGUMENT"] = arg
            if self.pid is not None:
                return
            self.process = subprocess.Popen([
                sys.executable, os.path.join(self.entrypoint_dir, self.entrypoint)
            ], cwd=os.getcwd(), env=env)
            self.pid = self.process.pid
            with open(self.pid_filename, "w") as fd:
                fd.write(str(self.pid))

        def stop(self):
            if self.process is not None:
                self.process.terminate()
                self.process = None
            else:
                try:
                    os.kill(self.pid, signal.SIGTERM)
                except OSError:
                    pass
            self.pid = None
            try:
                os.unlink(self.pid_filename)
            except:
                pass

        def is_running(self):
            return self.pid is not None

    Service = SubprocessService


class ZmqService(Service):
    def __init__(self, name, entrypoint, on_message, **options):
        self._channel = None
        self.on_message = on_message
        super(ZmqService, self).__init__(name, entrypoint, **options)

    def start(self, arg):
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
        print "app: setup zmq service"
        context = zmq.Context()
        self.socket = context.socket(zmq.PAIR)
        print "app: connecting"
        self.socket.connect("tcp://127.0.0.1:{}".format(port))
        print "app: connected"
        self.on_message(["READY"])

    def _zmq_channel_run(self):
        context = zmq.Context()
        socket = context.socket(zmq.PAIR)
        port = socket.bind_to_random_port("tcp://127.0.0.1")
        self._channel_port = port
        self._event.set()
        while not self._quit:
            print "wait", socket.poll()
            if not socket.poll(10):
                continue
            message = socket.recv_multipart()
            if message[0] == "READY":
                Clock.schedule_once(
                    lambda dt: self.setup_zmq_service(message[1]), 0)
            else:
                self.on_message(message)
        self._event.set()


class TestPause(App):
    def build(self):
        self.t_server = self.t_client = None
        self.s1 = ZmqService("s1", "service_1.py", self.on_s1_message)
        self.s2 = Service("s2", "service_2.py")
        self.s3 = Service("s3", "service_3.py")
        return Builder.load_string(kv)

    def on_pause(self):
        Logger.info("App: GO PAUSE")
        return True

    def on_resume(self):
        Logger.info("App: GO RESUME")
        return True

    def run_server(self):
        print "server: create zmq context"
        context = zmq.Context()
        print "server: create socket"
        socket = context.socket(zmq.PAIR)
        print "server: bind"
        socket.bind("tcp://*:12345")
        while True:
            print "server: wait message"
            message = socket.recv()
            print "server: received", message
            socket.send("START" + message + "END")

    def run_client(self):
        print "client: create zmq context"
        context = zmq.Context()
        print "client: create socket"
        socket = context.socket(zmq.PAIR)
        print "client: connect to server"
        socket.connect("tcp://localhost:12345")
        for req in range(3):
            print "client: send message", req
            socket.send("hello{}".format(req))
            print "client: get message"
            message = socket.recv()
            print "client: received", message

    def toggle_service1(self, should_start):
        if should_start:
            self.s1.start("")
        else:
            self.s1.stop()

    def on_s1_message(self, message):
        print "Service1 received message", message

    def toggle_service2(self, should_start):
        if should_start:
            self.s2.start("")
        else:
            self.s2.stop()

    def toggle_service3(self, should_start):
        if should_start:
            self.s3.start("")
        else:
            self.s3.stop()

    def is_service1_running(self):
        return self.s1.is_running()

    def is_service2_running(self):
        return self.s2.is_running()

    def is_service3_running(self):
        return self.s3.is_running()


if __name__ == "__main__":
    TestPause().run()
