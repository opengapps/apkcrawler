#!/usr/bin/env python3

import logging
import os
import sys

from debug import Debug
from reporthelper import ReportHelper
from apkbeastcrawler import ApkBeastCrawler
from apkdlcrawler import ApkdlCrawler
from apkmirrorcrawler import ApkMirrorCrawler
from apkpurecrawler import ApkPureCrawler
from aptoidecrawler import AptoideCrawler
from mobogeniecrawler import MobogenieCrawler
from playstorecrawler import PlayStoreCrawler
from plazzacrawler import PlazzaCrawler
from uptodowncrawler import UptodownCrawler

from aptoidecrawler import StoresException as AptoideStoresException
from playstorecrawler import CredentialsException as PlayStoreCredentialsException

# logging
logFile   = '{0}.log'.format(os.path.basename(__file__))
logLevel  = (logging.DEBUG if Debug.DEBUG else logging.INFO)
logFormat = '%(asctime)s %(levelname)s/%(funcName)s(%(process)-5d): %(message)s'

if __name__ == "__main__":
    """
    main(): single parameter for report_sources.sh output
    """
    logging.basicConfig(filename=logFile, filemode='w', level=logLevel, format=logFormat)
    logging.getLogger("requests").setLevel(logging.WARNING)

    lines = ''
    if len(sys.argv[1:]) == 1:
        with open(sys.argv[1]) as report:
            lines = report.readlines()
    else:
        lines = sys.stdin.readlines()

    report = ReportHelper(lines)

    keys = list(report.getAllApkIds())

    if len(keys) == 0:
        print('ERROR: expecting:')
        print(' - 1 parameter (report file from output of report_sources.sh)')
        print(' or ')
        print(' - stdin from report_sources.sh')
        exit(1)

    nonbeta = []
    beta    = []

    crawlers = [ApkBeastCrawler(report),
                ApkdlCrawler(report),
                ApkMirrorCrawler(report),
                ApkPureCrawler(report),
                AptoideCrawler(report),
                MobogenieCrawler(report),
                PlayStoreCrawler(report),
                PlazzaCrawler(report),
                UptodownCrawler(report)]

    for crawler in crawlers:
        try:
            logging.debug('Crawling {0}'.format(crawler.__class__.__name__))
            crawler.crawl()
        except AptoideStoresException as e:
            pass
            logging.info('AptoideStoresException {0}'.format(e))
            print('AptoideStoresException: {0}'.format(e))
        except PlayStoreCredentialsException as e:
            pass
            logging.info('PlayStoreCredentialsException {0}'.format(e))
            print('PlayStoreCredentialsException: {0}'.format(e))
        nonbeta.extend(crawler.dlFiles)
        beta.extend(crawler.dlFilesBeta)

    outputString = ' '.join(nonbeta)
    if beta:
        outputString += ' beta ' + ' '.join(beta)

    if outputString:
        print(outputString)
        sys.stdout.flush()
    logging.debug('Done ...')
