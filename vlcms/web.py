#!/usr/bin/env python

import logging
import multiprocessing as mp
import os.path

import cherrypy

from utils import ignore_sigint


log = logging.getLogger(__name__)


class Pages(object):
    def __init__(self, queue):
        self.queue = queue
        self.base_dir = os.path.dirname(__file__)

    @cherrypy.expose
    def index(self):
        with open(os.path.join(self.base_dir, 'index.html')) as f:
            return f.read()

    @cherrypy.expose
    def cmd(self, command):
        log.info('Got command "{}", sending back to master.'.format(command))
        self.queue.put(command)
        return '{result: "OK"}'


class WebServer(mp.Process):
    def __init__(self, queue, shutdown, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = queue
        self.shutdown = shutdown

    def run(self):
        cherrypy.log.error_log.propagate = False
        cherrypy.log.access_log.propagate = False
        cherrypy.tree.mount(Pages(self.queue))
        cherrypy.config.update({
            'engine.autoreload.on': False,
            'server.socket_host': '0.0.0.0',
            'environment': 'embedded',
        })
        ignore_sigint()
        log.info('Starting webserver...')
        cherrypy.engine.start()
        self.shutdown.wait()
        log.info('Stopping webserver...')
        cherrypy.engine.exit()
