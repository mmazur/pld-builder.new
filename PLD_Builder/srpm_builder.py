import email
import string
import time
import os
import os.path
import StringIO
import sys
import re

import gpg
import request
import log
import path
from acl import acl
from lock import lock
from bqueue import B_Queue
from config import config, init_conf
import chroot
import buildlogs

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

def collect_files(log):
  f = open(log)
  rx = re.compile(r"^Wrote: (/home.*\.rpm)$")
  files = []
  for l in f.xreadlines():
    m = rx.search(l)
    if m:
      files.append(m.group(1))
  return files

def append_to(log, msg):
  f = open(log, "a")
  f.write("%s\n" % msg)
  f.close()

def clean_tmp(dir):
  # FIXME: use python
  os.system("rm -f %s/*; rmdir %s" % (dir, dir))

def handle_request(r):
  def build_srpm(b):
    b.src_rpm = ""
    builder_opts = "-nu --clean --nodeps"
    cmd = "cd rpm/SPECS; ./builder %s -bs %s -r %s %s 2>&1" % \
                 (builder_opts, b.bconds_string(), b.branch, b.spec)
    spec_log = tmp + b.spec + ".log"
    append_to(spec_log, "Building SRPM using: %s\n" % cmd)
    res = chroot.run(cmd, logfile = spec_log)
    files = collect_files(spec_log)
    if len(files) > 0:
      if len(files) > 1:
        append_to(spec_log, "error: More then one file produced: %s" % files)
        res = 1
      last = files[len(files) - 1]
      b.src_rpm_file = last
      b.src_rpm = os.path.basename(last)
      all_files.extend(files)
    else:
      append_to(spec_log, "error: No files produced.")
      res = 1
    buildlogs.add(logfile = spec_log, failed = res)
    return res

  tmp = path.spool_dir + r.id + "/"
  os.mkdir(tmp)
  user = acl.user(r.requester)
  log.notice("started processing %s" % r.id)
  all_files = []
  for batch in r.batches:
    log.notice("building %s" % batch.spec)
    if build_srpm(batch):
      # clean up
      log.notice("building %s failed" % batch.spec)
      chroot.run("rm -f %s" % string.join(all_files))
      m = user.message_to()
      m.set_headers(subject = "SRPMS: %s failed" % batch.spec)
      # FIXME: write about other specs from group
      m.write("Building SRPM failed for %s.\nAttached log:\n" % batch.spec)
      m.append_log(tmp + batch.spec + ".log")
      m.send()
      buildlogs.flush()
      clean_tmp(tmp)
      return
    log.notice("building %s finished" % batch.spec)
  os.mkdir(path.srpms_dir + r.id)
  for batch in r.batches:
    # export files from chroot
    local = path.srpms_dir + r.id + "/" + batch.src_rpm
    f = batch.src_rpm_file
    chroot.run("cat %s; rm -f %s" % (f, f), logfile = local)
    # FIXME: copy files to ftp

  # store new queue and counter for binary builders
  cnt_f = open(path.counter_file, "r+")
  num = int(string.strip(cnt_f.read()))
  r.no = num
  q = B_Queue(path.req_queue_file)
  q.lock(0)
  q.read()
  q.add(r)
  q.write()
  q.unlock()
  q.write_signed(path.req_queue_signed_file)
  num += 1
  cnt_f.seek(0)
  cnt_f.write("%d\n" % num)
  cnt_f.close()
  # FIXME: send notification?

def main():
  init_conf("src")
  lock("building-srpm")
  q = B_Queue(path.queue_file)
  if not q.lock(1): return
  q.read()
  if q.requests == []: return
  r = pick_request(q)
  q.write()
  q.unlock()
  handle_request(r)

main()