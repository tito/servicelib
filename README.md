# servicelib

Library to manage and communicate between your application and declared services.
This work is still on-going.

## Background

If you want to run something in an external process, we are used to pick multiprocess. But when it comes down to mobile platform such as Android, multiprocess can't work (as fork is strongly non-advised, and you don't have "python" binary).
Kivy's Python for android with SDL2 bootstrap is going to include a new service declaration.

Servicelib is just a python library that allow you to write code the same for both desktop and android platform.

.. note:: iOS is not yet supported.

## How does it work?

In contrary to multiprocess, servicelib require to have a python filename as an entrypoint to execute. Let's say you have this files in your directory:

    /
    /main.py
    /myservices
    /myservices/service1.py
    /myservices/service2.py

Then, in your application, you can stop/start a background service:

```python
from servicelib import Service

s1 = Service("S1", "myservices/service1.py")
s2 = Service("S2", "myservices/service2.py")
s1.start()
s2.start()
# later
s1.stop()
s2.stop()
```

Nothing more to do on desktop. For android, you need to declare them when building your application:

    p4a apk --bootstrap=sdl2 ... --name myapp --package org.test --service S1:myservices/service1.py --service S2:myservices/service2.py

## Communication

The `Service` class doesn't handle any sort of communication by default. You can either do your own, and use `ZmqService`. This class require `pyzmq` in order to be usable. This mean on android you'll need to add:

    --copy-libs --requirements=pyzmq

On the application side, the usage is similar. It embed a `send()` method to send message. And you can pass a callback in order to receive anything that the service send too. When the service starts, it will send a command "READY" to say it's ready to receive any work to do.

```python
from servicelib.zmq_service import ZmqService

def on_generic_message(command, *args):
    print("I received {}".format(args))
    if command == "READY":
        # service is up and ready to work.
        s1.send("HELLO")
    elif command == "WORLD":
        # got a response to HELLO
        pass
s1 = ZmqService("S1", "myservices/service1.py", on_generic_message)
s1.start()
```

An alternative to the callback is to extend the service class:

```python
from servicelib.zmq_service import ZmqService

class AppServiceS1(ZmqService):
    def on_READY(self):
        print("Service is ready, sending HELLO")
        self.send("HELLO")

    def on_WORLD(self, arg):
        print("Service sent WORLD with argument: {}".format(arg))

s1 = AppServiceS1("S1", "myservices/service1.py")
s1.start()
# ...
s1.stop()
```

On the service side, you can implement a new service like that:

```python
from servicelib.zmq_service import ZmqServiceImpl

class ServiceS1(ZmqServiceImpl):
    def on_HELLO(self, *args):
        self.send("WORLD", "123")

ServiceS1().run()    
```

Please note that on the application, all the responses from ZmqService is done from its running thread, not the thread you've instanciated it. It's up to you to dispatch it to your own thread.

## Desktop specific

Right now, i didn't tested on Windows. I don't think the background service will work as intented.
Anyway, when a service starts, it will create a pid at the same place a the entrypoint. If you restart your application,
it wont restart the service if the process in the pid is still running.

## Android specific

In order to make it work on Android, the toolchain will generate service class named `Service` + the name of the service capitalized, under the package you're running. Meaning, if you want to access it manually, in the first example:

```python
from jnius import autoclass
context = autoclass("org.kivy.android.PythonActivtiy").mActivity
ServiceS1 = autoclass("org.test.myapp.ServiceS1")

ServiceS1.start(context, "")
ServiceS1.stop()
```
