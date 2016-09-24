#!/usr/bin/env python

import argparse
import logging
import subprocess
import time

from control import Controller
from web import start_webserver


logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


VLC_BINARY = '"C:\Program Files (x86)\VideoLAN\VLC\\vlc.exe"'
VLC_RC_START_PORT = 4212
VLC_OPTIONS = (
    '--directx-audio-device="Default" --audio-track=2 --vout none',
    '',
)


def spawn_vlcs(filename):
    ports = []
    for index, option in enumerate(VLC_OPTIONS):
        port = VLC_RC_START_PORT + index
        #  --rc-quiet
        control_option = '--intf rc --rc-host 127.0.0.1:{port}'.format(
            port=port)
        cmdline = '{bin} {opts} {control} {file}'.format(
            bin=VLC_BINARY, opts=option, control=control_option, file=filename)
        log.info('Starting VLC: {cmdline}'.format(cmdline=cmdline))
        p = subprocess.Popen(cmdline)
        ports.append(port)
        return ports


def run(filename):
    ports = spawn_vlcs(filename)
    controller = Controller(ports)
    time.sleep(2)
    controller.command('pause')
    start_webserver(controller)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', type=str)
    args = parser.parse_args()

    run(args.filename)
