#!/usr/bin/env python

import logging
import telnetlib

log = logging.getLogger(__name__)

import telnetlib
import re
import logging


class Controller(object):
	"""
	Control multiple VLC instances via RC interface.
	"""
	def __init__(self, ports, timeout=2):
		self.timeout = timeout
		self.workers = [telnetlib.Telnet('127.0.0.1', port, timeout)
										for port in ports]

	def _prepare_str(self, string):
		return bytes(string.encode('ascii'))
	
	def command(self, cmd):
		output = []		
		cmd_end = '{cmd}: returned '.format(cmd=cmd)
		
		for index, worker in enumerate(self.workers):
			log.debug('Sending command "{cmd}" to worker {num}'.format(
				cmd=cmd, num=index))
			worker.read_eager()
			worker.write(self._prepare_str(cmd + '\r\n'))
			output.append(worker.read_until(self._prepare_str(cmd_end), self.timeout))
			worker.read_eager()
		
		output_dbg = '\n'.join('{num}: {msg}'.format(num=index, msg=msg)
													 for index, msg in enumerate(output))
		log.debug('Got workers\' output:\n {}'.format(output_dbg))
		return output