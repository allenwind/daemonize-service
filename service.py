import os
import sys
import atexit
import signal
import time
from http.server import ThreadingHTTPServer
from http.server import SimpleHTTPRequestHandler

def daemonize(
    pidfile, *,
    stdin="/dev/null",
    stdout="/dev/null",
    stderr="/dev/null",
    postprocess=None):

    if os.path.exists(pidfile):
        raise RuntimeError("Already running")

    if postprocess is None:
        postprocess = []

    def execute_postprocess():
        for f in postprocess:
            f()

    postprocess.append(lambda: os.remove(pidfile))

    # 从父进程中脱离
    try:
        if os.fork() > 0:
            # 退出父进程
            raise SystemExit(0)
    except OSError as e:
        raise RuntimeError("fork #1 failed.")

    # 更改目录，让子进程不再依赖原目录
    os.chdir("/")
    # 重置文件权限掩码
    os.umask(0)
    # 子进程变成孤儿后，调用下面函数创建一个全新的进程会话，
    # 并设置子进程为新的进程组的首领，之后不会再有控制终端。
    # 于是，子进程和终端分离后信号机制对它不再起作用。
    os.setsid()

    # 让守护进程放弃它的会话首领地位并失去获取新的控制终端的能力
    # 这样守护进程再也没有权限去打开控制终端。
    try:
        if os.fork() > 0:
            # 退出父进程
            raise SystemExit(0)
    except OSError as e:
        raise RuntimeError("fork #2 failed.")

    sys.stdout.flush()
    sys.stderr.flush()

    # 替代stdin, stdout, stderr文件描述符
    with open(stdin, "rb", 0) as fp:
        os.dup2(fp.fileno(), sys.stdin.fileno())
    with open(stdout, "ab", 0) as fp:
        os.dup2(fp.fileno(), sys.stdout.fileno())
    with open(stderr, "ab", 0) as fp:
        os.dup2(fp.fileno(), sys.stderr.fileno())

    with open(pidfile,"w") as fp:
        print(os.getpid(),file=fp)

    # 进程退出前执行的操作集
    atexit.register(execute_postprocess)

    # 处理退出信号
    def sigterm_handler(signo, frame):
        raise SystemExit(1)

    signal.signal(signal.SIGTERM, sigterm_handler)

def service(directory):
    os.chdir(directory)
    sys.stdout.write("daemon started with pid {} at {}\n".format(
        os.getpid(), time.ctime()))

    handler = SimpleHTTPRequestHandler
    with ThreadingHTTPServer(("", 8080), handler) as httpd:
        httpd.serve_forever()

if __name__ == "__main__":
    PIDFILE = "/tmp/daemon.pid"

    if len(sys.argv) != 2:
        print("usage: {} [start|stop]".format(sys.argv[0]), file=sys.stderr)
        raise SystemExit(1)

    if sys.argv[1] == "start":
        try:
            daemonize(PIDFILE,
                      stdout="/tmp/daemon.log",
                      stderr="/tmp/dameon.log")
        except RuntimeError as e:
            print(e, file=sys.stderr)
            raise SystemExit(1)

        directory = "/home"
        service(directory)

    elif sys.argv[1] == "stop":
        if os.path.exists(PIDFILE):
            with open(PIDFILE) as fp:
                os.kill(int(fp.read()), signal.SIGTERM)
        else:
            print("not running", file=sys.stderr)
            raise SystemExit(1)

    else:
        print("unknown command {!r}".format(sys.argv[1]), file=sys.stderr)
        raise SystemExit(1)
