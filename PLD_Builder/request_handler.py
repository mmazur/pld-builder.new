import email
import string
import time
import os
import StringIO
import sys
import fnmatch

import gpg
import request
import log
import path
import util
import wrap
import status
from acl import acl
from lock import lock
from bqueue import B_Queue
from config import config, init_conf

def check_double_id(id):
  id_nl = id + "\n"
  
  ids = open(path.processed_ids_file)
  for i in ids.xreadlines():
    if i == id_nl:
      # FIXME: security email here?
      log.alert("request %s already processed" % id)
      return 1
  ids.close()
  
  ids = open(path.processed_ids_file, "a")
  ids.write(id_nl)
  ids.close()

  return 0

def handle_group(r, user):
  def fail_mail(msg):
    if len(r.batches) >= 1:
      spec = r.batches[0].spec
    else:
      spec = "None.spec"
    log.error("%s: %s" % (spec, msg))
    m = user.message_to()
    m.set_headers(subject = "building %s failed" % spec)
    m.write_line(msg)
    m.send()
  
  lock("request")
  if check_double_id(r.id):
    return
    
  if not user.can_do("src", config.builder):
    fail_mail("user %s is not allowed to src:%s" \
                % (user.get_login(), config.builder))
    return

  for batch in r.batches:
    batch.expand_builders(config.binary_builders)
    if not batch.is_command() and config.builder in batch.builders:
      batch.builders.remove(config.builder)
    for bld in batch.builders:
      batch.builders_status[bld] = '?'
      if bld not in config.binary_builders and bld != config.builder:
        fail_mail("I (src rpm builder '%s') do not handle binary builder '%s', only '%s'" % \
                        (config.builder, bld, string.join(config.binary_builders)))
        return
      if batch.is_command():
        if not user.can_do("command", bld):
          fail_mail("user %s is not allowed to command:%s" \
                        % (user.get_login(), bld))
          return
      elif not user.can_do("binary", bld):
        pkg = batch.spec
        if pkg.endswith(".spec"):
          pkg = pkg[:-5]
        if not user.can_do("binary-" + pkg, bld):
          fail_mail("user %s is not allowed to binary-%s:%s" \
                        % (user.get_login(), pkg, bld))
          return

  r.requester = user.get_login()
  r.requester_email = user.mail_to()
  r.time = time.time()
  log.notice("queued %s from %s" % (r.id, user.get_login()))
  q = B_Queue(path.queue_file)
  q.lock(0)
  q.read()
  q.add(r)
  q.write()
  q.unlock()

def handle_notification(r, user):
  if not user.can_do("notify", r.builder):
    log.alert("user %s is not allowed to notify:%s" % (user.login, r.builder))
  q = B_Queue(path.req_queue_file)
  q.lock(0)
  q.read()
  not_fin = filter(lambda (r): not r.is_done(), q.requests)
  r.apply_to(q)
  for r in not_fin:
    if r.is_done():
      util.clean_tmp(path.srpms_dir + r.id)
  now = time.time()
  def leave_it(r):
    # for ,,done'' set timeout to 4d
    if r.is_done() and r.time + 4 * 24 * 60 * 60 < now:
      return False
    # and for not ,,done'' set it to 20d
    if r.time + 20 * 24 * 60 * 60 < now:
      util.clean_tmp(path.srpms_dir + r.id)
      return False
    return True
  q.requests = filter(leave_it, q.requests)
  q.write()
  q.dump(open(path.queue_stats_file, "w"))
  q.dump_html(open(path.queue_html_stats_file, "w"))
  os.chmod(path.queue_html_stats_file, 0644)
  os.chmod(path.queue_stats_file, 0644)
  q.unlock()

def handle_request(f):
  sio = StringIO.StringIO()
  util.sendfile(f, sio)
  sio.seek(0)
  (em, body) = gpg.verify_sig(sio)
  user = acl.user_by_email(em)
  if user == None:
    # FIXME: security email here
    log.alert("invalid signature, or not in acl %s" % em)
    return
  acl.set_current_user(user)
  status.push("email from %s" % user.login)
  r = request.parse_request(body)
  if r.kind == 'group':
    handle_group(r, user)
  elif r.kind == 'notification':
    handle_notification(r, user)
  else:
    msg = "%s: don't know how to handle requests of this kind '%s'" \
                % (user.get_login(), r.kind)
    log.alert(msg)
    m = user.message_to()
    m.set_headers(subject = "unknown request")
    m.write_line(msg)
    m.send()
  status.pop()

def main():
  init_conf("src")
  status.push("handling email request")
  handle_request(sys.stdin)
  status.pop()
  sys.exit(0)

if __name__ == '__main__':
  wrap.wrap(main)
