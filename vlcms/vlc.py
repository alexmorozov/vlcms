import logging
import multiprocessing as mp
from multiprocessing.queues import Empty
import subprocess
import telnetlib
import time

from utils import ignore_sigint

log = logging.getLogger(__name__)


class Worker(mp.Process):
    """
    A VLC instance running until the shutdown event is fired.
    """
    def __init__(self, binary, args_template, filename, host, port, shutdown,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.binary = binary
        self.args_template = args_template
        self.filename = filename
        self.host = host
        self.port = port
        self.shutdown = shutdown

    @property
    def control_options(self):
        return ('--intf rc --rc-quiet '
                '--rc-host {host}:{port}').format(host=self.host,
                                                  port=self.port)

    @property
    def cmdline(self):
        args = self.args_template.format(filename=self.filename)
        return '{bin} {control} {args}'.format(
            bin=self.binary, control=self.control_options, args=args)

    def run(self):
        log.info('Starting VLC on port {}...'.format(self.port))
        ignore_sigint()
        process = subprocess.Popen(self.cmdline)
        self.shutdown.wait()
        log.info('Stopping VLC instance on port {}...'.format(self.port))
        process.terminate()


class Controller(mp.Process):
    """
    A remote controller for a VLC instance
    """
    def __init__(self, host, port, queue, shutdown, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host = host
        self.port = port
        self.queue = queue
        self.shutdown = shutdown
        self.net_timeout = 3
        self.poll_timeout = 0.05
        self.conn = telnetlib.Telnet()

    def _prepare_str(self, string):
        """
        Convert a command to raw bytes.
        """
        return bytes(string.encode('ascii'))

    def send_command(self, cmd):
        if not self.conn.sock:
            self.conn.open(self.host, self.port, self.net_timeout)

        log.debug('Sending command "{cmd}"'.format(cmd=cmd))
        self.conn.read_eager()
        self.conn.write(self._prepare_str(cmd + '\r\n'))
        output = self.conn.read_eager()
        return str(output)

    def run(self):
        log.info('Starting controller for port {}...'.format(self.port))
        ignore_sigint()
        while not self.shutdown.wait(self.poll_timeout):
            try:
                raw_cmd = self.queue.get(True, self.poll_timeout)
                for cmd in raw_cmd.split(', '):
                    if 'sleep' in cmd:
                        time.sleep(int(cmd.split(' ')[-1]))
                    else:
                        self.send_command(cmd)
            except Empty:
                pass
        log.info('Closing controller for port {}...'.format(self.port))
        self.conn.close()
