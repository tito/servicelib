# coding=utf-8
"""
ZMQ communication demo
======================

Service and application can be started either way.
The solution proposed here wait the application to be ready (in case of), and
handle port binding conflict.

It also demonstrate a protocol based on recv/send multipart, first arg
as the command, etc.

The application starts a server socket for responses.
This service starts a server socket for receiving command.

The startup protocol is this:

1. the application create the response socket
2. the application start the service
3. the application wait on the response socket to know on which port
   the service is running at
4. the application can send message on the service port

"""

import zmq
import os


def run():
    print "1: started"
    # get the argument sent by the service
    arg = os.getenv("PYTHON_SERVICE_ARGUMENT")
    port = int(arg)
    context = zmq.Context()

    # in communication
    print "1: creating inbound socket"
    sin = context.socket(zmq.PAIR)
    service_port = sin.bind_to_random_port("tcp://127.0.0.1")
    print "1: listening on inbound socket at {}".format(service_port)

    # app communication
    print "1: connect to app socket at {}".format(port)
    sapp = context.socket(zmq.PAIR)
    sapp.connect("tcp://127.0.0.1:{}".format(port))
    print "1: advertise that we are ready"
    sapp.send_multipart(("READY", str(service_port)))

    # wait for commands
    while True:
        print "1: wait for a message"
        message = sin.recv_multipart()
        print "1: received", message

        if message[0] == "QUIT":
            print "1: soft-leaving"
            break

        elif message[0] == "ECHO":
            sapp.send_multipart(message)

        elif message[0] == "COMPUTE":
            arg1, arg2 = message[1:]
            import time
            time.sleep(3)
            print "1: send compute result"
            res = str(int(arg1) ** int(arg2))
            print "1", len(res)
            sapp.send_multipart(("RESULT", res))


run()
