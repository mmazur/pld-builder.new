import sys
import os
import atexit
import time
import urllib

from config import config, init_conf
from bqueue import B_Queue
from acl import acl
import lock
import util
import path
import status
import log
import chroot
import ftp
import buildlogs

# this code is duplicated in srpm_builder, but we
# might want to handle some cases differently here
def pick_request(q):
  def mycmp(r1, r2):
    if r1.kind != 'group' or r2.kind != 'group':
      raise "non-group requests"
    pri_diff = cmp(r1.priority, r2.priority)
    if pri_diff == 0:
      return cmp(r1.time, r2.time)
    else:
      return pri_diff
  q.requests.sort(mycmp)
  ret = q.requests[0]
  q.requests = q.requests[1:]
  return ret

def handle_request(r):
  def log_line(l):
    log.notice(l)
    util.append_to(spec_log, l)
  
  def fetch_src(b):
    src_url = config.control_url + "/srpms/" + r.id + "/" + b.src_rpm
    log_line("fetching %s" % src_url)
    start = time.time()
    f = urllib.urlopen(src_url)
    o = chroot.popen("cat > %s" % b.src_rpm, mode = "w")
    bytes = util.sendfile(f, o)
    f.close()
    o.close()
    t = time.time() - start
    if t == 0:
      log_line("fetched %d bytes" % bytes)
    else:
      log_line("fetched %d bytes, %.1f K/s" % (bytes, bytes / 1024.0 / t))

  def build_rpm(b):
    global spec_log
    spec_log = tmp + b.spec + ".log"
    status.push("building %s" % b.spec)
    fetch_src(b)
    res = chroot.run("rpm -U %s && rm -f %s" % (b.src_rpm, b.src_rpm), 
                     logfile = spec_log)
    if res:
      log_line("error: installing src rpm failed")
    else:
      cmd = "cd rpm/SPECS; rpmbuild -bb %s" % b.spec
      log_line("Building RPM using: %s" % cmd)
      res = chroot.run(cmd, logfile = spec_log)
      files = util.collect_files(spec_log)
      if len(files) > 0:
        all_files.extend(files)
      else:
        # FIXME: is it error?
        log_line("error: No files produced.")
        res = 1
    buildlogs.add(logfile = spec_log, failed = res)
    status.pop()
    return res

  tmp = path.spool_dir + r.id + "/"
  os.mkdir(tmp)
  atexit.register(util.clean_tmp, tmp)
  user = acl.user(r.requester)
  log.notice("started processing %s" % r.id)
  all_files = []
  for batch in r.batches:
    log.notice("building %s" % batch.spec)
    if build_rpm(batch):
      # clean up
      log.notice("building %s failed" % batch.spec)
      chroot.run("rm -f %s" % string.join(all_files))
      m = user.message_to()
      m.set_headers(subject = "Binary: %s failed" % batch.spec)
      # FIXME: write about other specs from group
      m.write("Building RPM failed for %s.\nAttached log:\n" % batch.spec)
      m.append_log(spec_log)
      m.send()
      buildlogs.flush()
      return
    log.notice("building %s finished" % batch.spec)
  for f in all_files:
    local = tmp + os.path.basename(f)
    chroot.run("cat %s; rm -f %s" % (f, f), logfile = local)
    ftp.add(local)

  # FIXME: send notification?
  buildlogs.flush()
  ftp.flush()

def check_load():
  try:
    f = open("/proc/loadavg")
    if float(string.split(f.readline())[2]) > config.max_load:
      sys.exit(0)
  except:
    pass

def main():
  if len(sys.argv) < 2:
    raise "fatal: need to have builder name as first arg"
  init_conf(sys.argv[1])
  # allow only one build in given builder at once
  if not lock.lock("building-rpm-for-%s" % config.builder, non_block = 1):
    return
  # don't kill server
  check_load()
  # not more then job_slots builds at once
  locked = 0
  for slot in range(config.job_slots):
    if lock.lock("building-rpm-slot-%d" % slot, non_block = 1):
      locked = 1
      break
  if not locked:
    return

  status.push("picking request for %s" % config.builder)
  q = B_Queue(path.queue_file + "-" + config.builder)
  q.lock(0)
  q.read()
  if q.requests == []:
    return
  r = pick_request(q)
  q.write()
  q.unlock()
  status.pop()

  # record fact that we got lock for this builder, load balancer
  # will use it for fair-queuing
  l = lock.lock("got-lock")
  f = open(path.got_lock_file, "a")
  f.write(config.builder + "\n")
  f.close()
  l.close()
  
  msg = "handling request %s (%d) for %s from %s" \
        % (r.id, r.no, config.builder, r.requester)
  log.notice(msg)
  status.push(msg)
  handle_request(r)
  status.pop()
  
util.wrap(main)