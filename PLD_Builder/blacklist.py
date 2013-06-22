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
        self.blacklist = {}
        status.push("reading package-blacklist")
        with open(path.blacklist_file) as f:
            for l in f:
                p = l.rstrip()
                if re.match(r"^#.*", p):
                    continue
                self.blacklist[p] = 1
                log.notice("blacklist added: %s (%d)" % (l, self.blacklist.has_key(p)))
        status.pop()

    def package(self, p):
#       log.notice("blacklist check: %s (%d)" % (p, self.blacklist.has_key(p)))
        if self.blacklist.has_key(p):
            return True
        return False

    def packages(self):
        return self.blacklist

blacklist = Blacklist_File()
