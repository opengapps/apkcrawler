#!/usr/bin/env python3

#
# Required Modules
# - beautifulsoup4
# - html5lib
# - requests
#

import http.client
import logging
import multiprocessing
import os
import re
import requests
import sys

from bs4 import BeautifulSoup
import unicodedata

from debug import Debug
from apkhelper import ApkVersionInfo
from reporthelper import ReportHelper

###################
# DEBUG VARS      #
###################

# Debug.DEBUG        = True
# Debug.READFROMFILE = True  # Read from file for debugging
# Debug.SAVELASTFILE = True  # Write to file upon each request

###################
# END: DEBUG VARS #
###################

###################
# Globals         #
###################

# logging
logFile   = '{0}.log'.format(os.path.basename(__file__))
logLevel  = (logging.DEBUG if Debug.DEBUG else logging.INFO)
logFormat = '%(asctime)s %(levelname)s/%(funcName)s(%(process)-5d): %(message)s'


class ApkBeastCrawler(object):
    def __init__(self, report, dlFiles=[], dlFilesBeta=[]):
        self.report      = report
        self.dlFiles     = dlFiles
        self.dlFilesBeta = dlFilesBeta

        self.sReDownloadUrl = "var url = '(?P<URL>.*)';"
        self.reDownloadUrl  = re.compile(self.sReDownloadUrl)

    def getUrlFromRedirect(self, url):
        """
        getUrlFromRedirect(url):
        """
        link      = ''

        session = requests.Session()
        logging.debug('Requesting2: ' + url)
        resp    = session.get(url)
        if resp.status_code == http.client.OK:
            html    = unicodedata.normalize('NFKD', resp.text)

            try:
                m = self.reDownloadUrl.search(html)
                if m:
                    link = m.group('URL')
            except:
                logging.exception('!!! Error parsing html from: "{0}"'.format(url))

            return link
        else:
            logging.error('HTTPStatus2: {0}, when fetching redirect at {1}'.format(resp.status_code, url))
    # END: def getUrlFromRedirect:

    def downloadApk(self, avi, isBeta=False):
        """
        downloadApk(avi, isBeta): Download the specified URL to APK file name
        """
        if avi.download_src:
            url = avi.download_src
        else:
            url = self.getUrlFromRedirect(avi.scrape_src)
        if not url or url == '':
            logging.error('Unable to determine redirect url for ' + avi.getFilename())
            return

        logging.info('Downloading "{0}" from: {1}'.format(avi.getFilename(), url))

        apkname = ('beta.' if isBeta else '') + avi.getFilename()
        try:
            if os.path.exists(apkname):
                logging.info('{0} already exists'.format(apkname))
                return

            if os.path.exists(os.path.join('.', 'apkcrawler', apkname)):
                logging.info('{0} already exists (in ./apkcrawler/)'.format(apkname))
                return

            if os.path.exists(os.path.join('..', 'apkcrawler', apkname)):
                logging.info('{0} already exists (in ../apkcrawler/)'.format(apkname))
                return

            # Open the url
            session = requests.Session()
            r = session.get(url)

            with open(apkname, 'wb') as local_file:
                local_file.write(r.content)

            logging.debug(('beta:' if isBeta else 'reg :') + apkname)
            return       (('beta:' if isBeta else ''     ) + apkname)
        except OSError:
            logging.exception('!!! Filename is not valid: "{0}"'.format(apkname))
    # END: def downloadApk

    def checkOneApp(self, apkid):
        """
        checkOneApp(apkid):
        """
        logging.info('Checking app: {0}'.format(apkid))

        url       = 'http://apkbeast.com/' + apkid

        session = requests.Session()
        logging.debug('Requesting1: ' + url)
        resp    = session.get(url)
        if resp.status_code == http.client.OK:
            html    = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'ignore')

            try:
                dom        = BeautifulSoup(html, 'html5lib')
                apkversion = dom.find('p', {'itemprop': 'softwareVersion'}).get_text()
                apkurl     = dom.find('a', {'class': 'da'})['href']

                if apkurl:
                    apkversion = apkversion.strip()
                    avi = ApkVersionInfo(name=apkid,
                                         ver=apkversion,
                                         crawler_name=self.__class__.__name__
                                         )
                    if apkurl[0] == '/':  # a relative URL; takes us to an intermediate screen
                        avi.scrape_src = 'http://apkbeast.com' + apkurl
                    else:  # direct download
                        avi.download_src = apkurl

                    if self.report.isThisApkNeeded(avi):
                        return self.downloadApk(avi)

            except IndexError:
                logging.info('{0} not supported by apk-dl.com ...'.format(apkid))
            except:
                logging.exception('!!! Error parsing html from: "{0}"'.format(url))
        else:
            logging.info('{0} not supported by APKBeast ...'.format(apkid))
    # END: def checkOneApp:

    def crawl(self, threads=3):  # APKBeast kills the connection if too many threads
        """
        crawl(): check all apk-dl apps
        """
        # Start checking all apkids ...
        p = multiprocessing.Pool(processes=threads, maxtasksperchild=5)  # Run only 5 tasks before re-placing the process
        r = p.map_async(unwrap_self_checkOneApp, list(zip([self] * len(list(self.report.getAllApkIds())), list(self.report.getAllApkIds()))), callback=unwrap_callback)
        r.wait()
        (self.dlFiles, self.dlFilesBeta) = unwrap_getresults()
    # END: crawl():
# END: class ApkBeastCrawler

nonbeta = []
beta    = []


def unwrap_callback(results):
    for result in results:
        if result:
            if result.startswith('beta:'):
                beta.append(result[5:])
            else:
                nonbeta.append(result)


def unwrap_getresults():
    return (nonbeta, beta)


def unwrap_self_checkOneApp(arg, **kwarg):
    return ApkBeastCrawler.checkOneApp(*arg, **kwarg)


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

    if len(list(report.getAllApkIds())) == 0:
        print('ERROR: expecting:')
        print(' - 1 parameter (report file from output of report_sources.sh)')
        print(' or ')
        print(' - stdin from report_sources.sh')
        exit(1)

    crawler = ApkBeastCrawler(report)
    crawler.crawl()

    outputString = ' '.join(crawler.dlFiles)
    if crawler.dlFilesBeta:
        outputString += ' beta ' + ' '.join(crawler.dlFilesBeta)

    if outputString:
        print(outputString)
        sys.stdout.flush()

    logging.debug('Done ...')
