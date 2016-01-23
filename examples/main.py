from kivy.app import App
from kivy.utils import platform
from kivy.uix.button import Button
from kivy.logger import Logger
from kivy.lang import Builder
from threading import Thread, Event
from kivy.clock import Clock
from servicelib import Service
from servicelib.zmq_service import ZmqService

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
            on_release: app.s1.send("COMPUTE", "6684", "6513")
        Button:
            text: "Echo"
            on_release: app.s1.send("ECHO", "Hello world")
    ToggleButton:
        text: "Service 2"
        on_state: app.toggle_service2(self.state == "down")
        state: "down" if app.is_service2_running() else "normal"
    ToggleButton:
        text: "Service 3"
        on_state: app.toggle_service3(self.state == "down")
        state: "down" if app.is_service3_running() else "normal"
"""



class TestPause(App):
    def build(self):
        self.t_server = self.t_client = None
        self.s1 = ZmqService("s1", "service_1.py", self.on_s1_message)
        self.s2 = Service("s2", "service_2.py")
        self.s3 = Service("s3", "service_3.py")
        return Builder.load_string(kv)

    def on_pause(self):
        return True

    def toggle_service1(self, should_start):
        if should_start:
            self.s1.start("")
        else:
            self.s1.stop()

    def on_s1_message(self, *message):
        print "Service1 received message", message

    def toggle_service2(self, should_start):
        if should_start:
            self.s2.start()
        else:
            self.s2.stop()

    def toggle_service3(self, should_start):
        if should_start:
            self.s3.start()
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
