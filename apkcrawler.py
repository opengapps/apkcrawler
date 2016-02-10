#!/usr/bin/env python

import sys
import os
import logging

from debug import Debug
from reporthelper import ReportHelper
from apkdlcrawler import ApkdlCrawler
from apkmirrorcrawler import ApkMirrorCrawler
from aptoidecrawler import AptoideCrawler
from mobogeniecrawler import MobogenieCrawler
from plazzacrawler import PlazzaCrawler
from uptodowncrawler import UptodownCrawler

# logging
logFile   = '{0}.log'.format(os.path.basename(__file__))
logLevel  = (logging.DEBUG if Debug.DEBUG else logging.INFO)
logFormat = '%(asctime)s %(levelname)s/%(funcName)s(%(process)-5d): %(message)s'

if __name__ == "__main__":
    """
    main(): single parameter for report_sources.sh output
    """
    logging.basicConfig(filename = logFile, filemode = 'w', level = logLevel, format = logFormat)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("requesocks").setLevel(logging.WARNING)

    lines = ''
    if len(sys.argv[1:]) == 1:
        with open(sys.argv[1]) as report:
            lines = report.readlines()
    else:
        lines = sys.stdin.readlines()

    report = ReportHelper(lines)

    keys = report.dAllApks.keys()

    if len(keys) == 0:
        print('ERROR: expecting:')
        print(' - 1 parameter (report file from output of report_sources.sh)')
        print(' or ')
        print(' - stdin from report_sources.sh')
        exit(1)

    nonbeta = []
    beta    = []

    crawlers = [ApkdlCrawler(report),
                ApkMirrorCrawler(report),
                AptoideCrawler(report),
                MobogenieCrawler(report),
                PlazzaCrawler(report),
                UptodownCrawler(report)]

    for crawler in crawlers:
        crawler.crawl()
        nonbeta.extend(crawler.dlFiles)
        beta.extend(crawler.dlFilesBeta)

    outputString = ' '.join(nonbeta)
    if beta:
        outputString += ' beta ' + ' '.join(beta)

    if outputString:
        print(outputString)
        sys.stdout.flush()
    logging.debug('Done ...')
