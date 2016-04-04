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

    def getUrlFromRedirect(self, url):
        """
        getUrlFromRedirect(url):
        """
        link      = ''

        session = requests.Session()
        logging.debug('Requesting2: ' + url)
        resp    = session.get(url)
        if resp.status_code == http.client.OK:
            html    = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'ignore')

            # sLink = '.*window\.location = "(?P<Link>[^"]+)".*'
            # reLink = re.compile(sLink)
            # m = reLink.search(html)
            # if m:
            #     return m.group('Link')

            try:
                dom  = BeautifulSoup(html, 'html5lib')
                link = dom.find('a', attrs={'download': True})['href']
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
        apkname = '{0}-{1}.apk'.format(avi.name.replace('.beta', ''),
                                       avi.realver.replace(' ', '_'))

        if avi.download_src:
            url = avi.download_src
        else:
            url = self.getUrlFromRedirect(avi.scrape_src)
        if not url or url == '':
            logging.error('Unable to determine redirect url for ' + apkname)
            return

        logging.info('Downloading "{0}" from: {1}'.format(apkname, url))

        try:
            if os.path.exists(apkname):
                logging.info('Downloaded APK already exists.')
                return

            if os.path.exists(os.path.join('.', 'apkcrawler', apkname)):
                logging.info('Downloaded APK already exists (in ./apkcrawler/).')
                return

            if os.path.exists(os.path.join('..', 'apkcrawler', apkname)):
                logging.info('Downloaded APK already exists (in ../apkcrawler/).')
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
                apkversion = dom.find('div', {'class': 'details-section-contents'}).findAll('div', {'class': 'meta-info'})[2].find('div', {'class': 'content'}).contents[0]
                apkurl     = dom.find('img', {'class': 'gdrive'}).parent['href']

                if apkurl:
                    apkversion = apkversion.strip()
                    avi = ApkVersionInfo(name=apkid,
                                         ver=apkversion,
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
        r = p.map_async(unwrap_self_checkOneApp, list(zip([self] * len(list(self.report.dAllApks.keys())), list(self.report.dAllApks.keys()))), callback=unwrap_callback)
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

    if len(list(report.dAllApks.keys())) == 0:
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
