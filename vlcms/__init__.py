#!/usr/bin/env python

import argparse
import logging
import multiprocessing as mp
from multiprocessing.queues import Empty
import time

import yaml

from web import WebServer
from vlc import Worker, Controller


LOG_FORMAT = '[%(levelname)s/%(name)s] %(message)s'
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
log = logging.getLogger(__name__)


def split_due(cmds):
    """
    Returns commands due now and those which are not yet.
    """
    due, notyet = [], []
    now = int(time.time())

    for timestamp, cmd in cmds:
        if now >= timestamp:
            due.append(cmd)
        else:
            notyet.append((timestamp, cmd))

    return due, notyet


def split_delayed(cmds):
    """
    Determine which commands are due and which are should be kept in queue.
    """
    immediate, delayed = [], []
    offset = 0
    now = int(time.time())

    for cmd in cmds:
        if 'sleep' in cmd:
            offset += int(cmd.split(' ')[-1])
            continue
        if offset:
            delayed.append((now + offset, cmd))
        else:
            immediate.append(cmd)

    return immediate, delayed


def run(host, start_port, binary, instances):
    shutdown = mp.Event()
    control_queues = []
    sync_queue = mp.Queue()

    for index, args in enumerate(instances):
        port = start_port + index
        Worker(binary, args, host, port, shutdown).start()

        queue = mp.Queue()
        master = True if index == 0 else False
        Controller(host, port, queue, shutdown,
                   sync_queue, master=master).start()
        control_queues.append(queue)

    web_queue = mp.Queue()
    WebServer(web_queue, shutdown).start()

    delayed_cmds = []
    try:
        while True:
            immediate_cmds, delayed_cmds = split_due(delayed_cmds)

            try:
                web_cmds = web_queue.get(True, 0.05).split(', ')
                immediate, delayed = split_delayed(web_cmds)
                delayed_cmds.extend(delayed)
                immediate_cmds.extend(immediate)
            except Empty:
                pass

            try:
                timestamp = sync_queue.get(False)
                immediate_cmds.append('seek {}'.format(timestamp))
            except Empty:
                pass

            for cmd in immediate_cmds:
                for q in control_queues:
                    q.put(cmd)

    except KeyboardInterrupt:
        log.info('Caught SIGINT, stopping the workers gracefully...')
        shutdown.set()
        time.sleep(3)


def parse_config(filename):
    with open(filename) as f:
        return yaml.load(f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', type=str)
    parser.add_argument('--config', type=str)
    args = parser.parse_args()

    config = parse_config(args.config)
    instances = [i.format(filename=args.filename) for i in config['instances']]

    run(
        host=config['vlc']['listen'],
        start_port=config['vlc']['start_port'],
        binary=config['vlc']['binary'],
        instances=instances,
    )
