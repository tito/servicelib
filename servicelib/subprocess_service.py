# coding=utf-8

from servicelib.base_service import BaseService
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
                print("Service {} was gone, removing pid file".format(
                    self.name))
                try:
                    os.unlink(self.pid_filename)
                except:
                    pass
                self.pid = None
            print("Service {} is already running (pid={})".format(self.name,
                                                                  self.pid))
        except:
            pass

    @property
    def pid_filename(self):
        pid_fn = "{}.pid".format(self.entrypoint.rsplit(".", 1)[0])
        if getattr(sys, "frozen", False):
            return os.path.join(os.getcwd(), os.path.basename(pid_fn))
        else:
            return os.path.join(self.entrypoint_dir, pid_fn)

    def start(self, arg=""):
        env = os.environ.copy()
        env["PYTHON_SERVICE_ARGUMENT"] = arg
        if self.pid is not None:
            return
        args = [sys.executable]
        if getattr(sys, "frozen", False):
            args.append("--service")
            args.append(self.module)
        else:
            args.append(os.path.join(self.entrypoint_dir, self.entrypoint))
        self.process = subprocess.Popen(args,
            cwd=os.getcwd(),
            env=env)
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
            except:
                pass
        self.pid = None
        try:
            os.unlink(self.pid_filename)
        except:
            pass

    def is_running(self):
        return self.pid is not None


Service = SubprocessService
