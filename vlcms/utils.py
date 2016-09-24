import signal


def ignore_sigint():
    signal.signal(signal.SIGINT, signal.SIG_IGN)
