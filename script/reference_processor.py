#!/usr/bin/python
# -*- coding: utf-8 -*-
from reporter import Reporter
import csv
from reference_storer import BibliographicReferenceStorer
import os


class ReferenceProcessor(object):
    def __init__(self,
                 stored_file,
                 reference_dir,
                 error_dir,
                 stopper,
                 headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; "
                                        "rv:33.0) Gecko/20100101 Firefox/33.0"},
                 sec_to_wait=10,
                 max_iteration=6,
                 timeout=30):
        self.headers = headers
        self.sec_to_wait = sec_to_wait
        self.max_iteration = max_iteration
        self.timeout = timeout
        self.stopper = stopper
        self.name = "BEE " + self.__class__.__name__
        self.repok = Reporter(prefix="[%s - INFO] " % self.name)
        self.repok.new_article()
        self.reper = Reporter(prefix="[%s - ERROR] " % self.name)
        self.reper.new_article()
        self.rs = BibliographicReferenceStorer(stored_file, reference_dir, error_dir)

    def process(self):
        pass  # To implement in subclasses