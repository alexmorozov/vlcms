#!/usr/bin/env python

import os.path
import cherrypy


class Server(object):
	def __init__(self, controller):
		self.controller = controller
		self.base_dir = os.path.dirname(__file__)
		with open(os.path.join(self.base_dir, 'index.html')) as f:
			self.index_page = f.read()
		
	@cherrypy.expose
	def index(self):
		with open(os.path.join(self.base_dir, 'index.html')) as f:
			index_page = f.read()
		return index_page
		
	@cherrypy.expose
	def cmd(self, command):
		self.controller.command(command)
		return '{}'


def start_webserver(controller):
	config = {
		'global': {
			'engine.autoreload.on': False,
			'server.socket_host': '0.0.0.0',
   	},
	}
	
	cherrypy.quickstart(Server(controller), '/', config)