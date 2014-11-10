#!/usr/bin/python

import socket
import string
import cgi
import time
import log
import ssl
import sys
import traceback
import os
from config import config, init_conf

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

import request_handler
import path

class MyHandler(BaseHTTPRequestHandler):

	def do_GET(self):
		self.send_error(401);

	def do_POST(self):
		global rootnode
		filename = "(unknown)"
		try:
			length = int(self.headers.getheader('content-length'))
			ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
			if ctype != 'application/x-www-form-urlencoded':
				log.error("request_handler_server: [%s]: 401 Unauthorized" % self.client_address[0])
				self.send_error(401)
				self.end_headers()
				return

			query = self.rfile.read(length)

			filename = self.headers.getheader('x-filename')

			if not request_handler.handle_request_main(query, filename = filename):
				error = log.last_log();
				log.error("request_handler_server: [%s]: handle_request_main(..., %s) failed" % (self.client_address[0], filename))
				self.send_error(500, "%s: request failed. %s" % (filename, error))
				self.end_headers()
				return

			self.send_response(200)
			self.end_headers()

		except Exception, e:
			self.send_error(500, "%s: %s" % (filename, e))
			self.end_headers()
			log.error("request_handler_server: [%s]: exception: %s\n%s" % (self.client_address[0], e, traceback.format_exc()))
			raise
			pass

def write_css():
	css_src = os.path.join(os.path.dirname(__file__), 'style.css')
	css_file = path.www_dir + "/style.css"
	# skip if file exists and code is not newer
	if os.path.exists(css_file) and os.stat(css_src).st_mtime < os.stat(css_file).st_mtime:
		return

	old_umask = os.umask(0022)
	r = open(css_src, 'r')
	f = open(css_file, "w")
	f.write(r.read())
	f.close()
	r.close()
	os.umask(old_umask)

def write_js():
	js_src = os.path.join(os.path.dirname(__file__), 'script.js')
	js_file = path.www_dir + '/script.js'
	# skip if file exists and code is not newer
	if os.path.exists(js_file) and os.stat(js_src).st_mtime < os.stat(js_file).st_mtime:
		return

	old_umask = os.umask(0022)
	r = open(js_src, 'r')
	f = open(js_file, 'w')
	f.write(r.read())
	f.close()
	r.close()
	os.umask(old_umask)

def main(srv_ssl=False):
	write_css();
	write_js();
	socket.setdefaulttimeout(30)
	try:
		init_conf()
		host = ""
		port = config.request_handler_server_port
		if srv_ssl:
			port = config.request_handler_server_ssl_port

		try:
			server = HTTPServer((host, port), MyHandler)
			if srv_ssl:
				server.socket = ssl.wrap_socket (server.socket,
						keyfile = config.request_handler_server_ssl_key,
						certfile = config.request_handler_server_ssl_cert,
						ca_certs = "/etc/certs/ca-certificates.crt",
						server_side=True)
		except Exception, e:
			log.notice("request_handler_server: can't start server on [%s:%d], ssl=%s: %s" % (host, port, str(srv_ssl), e))
			print >> sys.stderr, "ERROR: Can't start server on [%s:%d], ssl=%s: %s" % (host, port, str(srv_ssl), e)
			sys.exit(1)

		log.notice('request_handler_server: started on [%s:%d], ssl=%s...' % (host, port, str(srv_ssl)))
		server.serve_forever()
	except KeyboardInterrupt:
		log.notice('request_handler_server: ^C received, shutting down server')
		server.socket.close()

if __name__ == '__main__':
	srv_ssl = False
	if len(sys.argv) == 2 and sys.argv[1] == "ssl":
		srv_ssl = True

	main(srv_ssl)

