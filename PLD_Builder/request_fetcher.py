import ConfigParser
import string
import os
import urllib
import StringIO
import sys

import gzip

import path
import log
import status
import lock
import util
import gpg
import request
from acl import acl
from bqueue import B_Queue

last_count = 0

def has_new(control_url):
  global last_count
  cnt_f = open(path.last_req_no_file)
  last_count = int(string.strip(cnt_f.readline()))
  cnt_f.close()
  f = urllib.urlopen(control_url + "/max_req_no")
  res = 0
  if int(string.strip(f.readline())) != last_count:
    res = 1
  f.close()
  return res

def fetch_queue(control_url, queue_signed_by):
  f = urllib.urlopen(control_url + "/queue.gz")
  sio = StringIO.StringIO()
  util.sendfile(f, sio)
  f.close()
  sio.seek(0)
  f = gzip.GzipFile(fileobj = sio)
  (signers, body) = gpg.verify_sig(f)
  u = acl.user_by_email(signers)
  if u == None:
    log.alert("queue.gz not signed with signature of valid user: %s" % signers)
    sys.exit(1)
  if u.login != queue_signed_by:
    log.alert("queue.gz should be signed by %s not by %s" \
        % (queue_signed_by, u.login))
    sys.exit(1)
  body.seek(0)
  return request.parse_requests(body)

def handle_reqs(builder, reqs):
  qpath = path.queue_file + "-" + builder
  if not os.access(qpath, os.F_OK):
    util.append_to(qpath, "<queue/>\n")
  q = B_Queue(qpath)
  q.lock(0)
  q.read()
  for r in reqs:
    if r.kind != 'group': 
      raise 'handle_reqs: fatal: huh? %s' % r.kind
    need_it = 0
    for b in r.batches:
      if builder in b.builders:
        need_it = 1
    if need_it:
      log.notice("queued %s (%d) for %s" % (r.id, r.no, builder))
      q.add(r)
  q.write()
  q.unlock()

def main():
  os.environ['LC_ALL'] = "C"
  lock.lock("request_fetcher")
  
  status.push("reading builder config")
  p = ConfigParser.ConfigParser()
  p.readfp(open(path.builder_conf))
  builders = string.split(p.get("all", "builders"))
  control_url = p.get("all", "control_url")
  queue_signed_by = p.get("all", "queue_signed_by")
  status.pop()
  
  status.push("fetching requests")
  if has_new(control_url):
    q = fetch_queue(control_url, queue_signed_by)
    max_no = 0
    q_new = []
    for r in q:
      if r.no > max_no: 
        max_no = r.no
      if r.no > last_count:
        q_new.append(r)
    for b in builders:
      handle_reqs(b, q_new)
    f = open(path.last_req_no_file, "w")
    f.write("%d\n" % max_no)
    f.close()
  status.pop()

util.wrap(main)