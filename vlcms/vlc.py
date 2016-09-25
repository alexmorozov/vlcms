import logging
import multiprocessing as mp
from multiprocessing.queues import Empty
import subprocess
import telnetlib

from utils import ignore_sigint

log = logging.getLogger(__name__)


class Worker(mp.Process):
    """
    A VLC instance running until the shutdown event is fired.
    """
    def __init__(self, binary, arguments, host, port, shutdown,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.binary = binary
        self.arguments = arguments
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
        return '{bin} {control} {args}'.format(
            bin=self.binary, control=self.control_options, args=self.arguments)

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
    def __init__(self, host, port, queue, shutdown, sync_queue, *args,
                 **kwargs):
        self.master = kwargs.pop('master', False)
        super().__init__(*args, **kwargs)
        self.host = host
        self.port = port
        self.queue = queue
        self.sync_queue = sync_queue
        self.shutdown = shutdown
        self.net_timeout = 3
        self.poll_timeout = 0.05
        self.conn = telnetlib.Telnet()

    def _prepare_str(self, string):
        """
        Convert a command to raw bytes.
        """
        return bytes(string.encode('ascii'))

    def send_command(self, cmd, output_re=None):
        if not self.conn.sock:
            self.conn.open(self.host, self.port, self.net_timeout)

        log.debug('Sending command "{cmd}"'.format(cmd=cmd))
        self.conn.read_eager()
        self.conn.write(self._prepare_str(cmd + '\r\n'))
        if output_re:
            _, match, _ = self.conn.expect([output_re], self.net_timeout)
            return match
        return None

    def run(self):
        log.info('Starting controller for port {}...'.format(self.port))
        ignore_sigint()
        while not self.shutdown.wait(self.poll_timeout):
            try:
                cmd = self.queue.get(False)
                if 'jump' in cmd:
                    if self.master:
                        self.send_command(cmd)
                        self.emit_sync()
                    else:
                        pass  # instead of jumping slaves will sync
                else:
                    self.send_command(cmd)
            except Empty:
                pass

        log.info('Closing controller for port {}...'.format(self.port))
        self.conn.close()

    def emit_sync(self):
        """
        Get a baseline timestamp and put it to the sync queue.
        """
        output = self.send_command('get_time', output_re=b'(?P<time>\d+)\r\n')
        timestamp = output.groupdict()['time'].decode('ascii')
        log.debug('Emitting sync timestamp {}'.format(timestamp))
        self.sync_queue.put(timestamp)
