# vi: encoding=utf-8 ts=8 sts=4 sw=4 et

import string
import fnmatch
import os
import stat
import re

import path
import log
import status
from mailer import Message
from config import config

class Blacklist_File:
    def __init__(self):
        self.reload()

    def try_reload(self):
        mtime = os.stat(path.blacklist_file)[stat.ST_MTIME]
        if mtime != self.blacklist_file_mtime:
            log.notice("blacklist file has changed, reloading...")
            self.reload()
            return True
        return False

    def reload(self):
        self.blacklist_file_mtime = os.stat(path.blacklist_file)[stat.ST_MTIME]
        self.blacklist = set()
        status.push("reading package-blacklist")
        f = open(path.blacklist_file)
        for l in f:
            p = l.rstrip()
            if re.match(r"^#.*", p):
                continue
            self.blacklist.add(p)
            log.notice("blacklist added: %s" % l)
        f.close()
        status.pop()

    def package(self, p):
#       log.notice("blacklist check: %s (%d)" % (p, self.blacklist.has_key(p)))
        if p in self.blacklist:
            return True
        return False

    def packages(self):
        return self.blacklist

blacklist = Blacklist_File()
