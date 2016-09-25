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


def run(filename, config):
    shutdown = mp.Event()
    start_port = config['vlc']['start_port']
    binary = config['vlc']['binary']
    host = config['vlc']['listen']
    control_queues = []
    web_queue = mp.Queue()
    sync_queue = mp.Queue()

    for index, args in enumerate(config['instances']):
        port = start_port + index
        Worker(binary, args, filename, host, port, shutdown).start()

        queue = mp.Queue()
        master = True if index == 0 else False
        Controller(host, port, queue, shutdown,
                   sync_queue, master=master).start()
        control_queues.append(queue)

    WebServer(web_queue, shutdown).start()

    try:
        while True:
            try:
                cmd = web_queue.get(True, 0.05)
                for q in control_queues:
                    q.put(cmd)
            except Empty:
                pass

            try:
                timestamp = sync_queue.get(False)
                for queue in control_queues:
                    queue.put('seek {}'.format(timestamp))
            except Empty:
                pass

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

    run(args.filename, config)
