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


class ApkPureCrawler(object):
    def __init__(self, report, dlFiles=[], dlFilesBeta=[]):
        self.report      = report
        self.dlFiles     = dlFiles
        self.dlFilesBeta = dlFilesBeta

        self.sReVerInfo = 'Version:\s(?P<VERNAME>.*)\s\((?P<VERCODE>[0-9]*)\)(\sfor\sAndroid.+API\s(?P<SDK>[0-9]+)\))?'
        self.reVersion  = re.compile(self.sReVerInfo)

    def downloadApk(self, avi, isBeta=False):
        """
        downloadApk(apkInfo): Download the specified URL to APK file name
        """
        apkname = ('beta.' if isBeta else '') + avi.getFilename()

        logging.info('Downloading "{0}" from: {1}'.format(apkname, avi.download_src))

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
            r = session.get(avi.download_src)

            with open(apkname, 'wb') as local_file:
                local_file.write(r.content)

            logging.debug(('beta:' if isBeta else 'reg :') + apkname)
            return       (('beta:' if isBeta else ''     ) + apkname)
        except OSError:
            logging.exception('!!! Filename is not valid: "{0}"'.format(apkname))
    # END: def downloadApk

    def parseRedirectPage(self, apkid):
        url = apkid.scrape_src

        session = requests.Session()
        logging.debug('Requesting2: ' + url)
        resp    = session.get(url)
        html    = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'ignore')

        if resp.status_code == http.client.OK:
            try:
                dom                = BeautifulSoup(html, 'html5lib')
                apkid.download_src = dom.find('a', {'id': 'download_link', 'class': 'ga'})['href']
            except:
                logging.exception('!!! Error parsing html from: "{0}"'.format(url))

            return apkid
    # END: def parseRedirectPage

    def checkOneApp(self, apkid):
        """
        checkOneApp(apkid):
        """
        logging.info('Checking app: {0}'.format(apkid))

        filenames = []

        url       = 'https://apkpure.com/apkpure/' + apkid  # the /apkpure/ part just needs to be an arbitrary string

        session = requests.Session()
        logging.debug('Requesting1: ' + url)
        resp    = session.get(url)
        html    = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'ignore')

        if resp.status_code == http.client.OK:
            try:
                dom     = BeautifulSoup(html, 'html5lib')
                apklist = dom.find('div', {'class': 'faq_cat'})
                apks    = apklist.findAll('dd', {'style': ''}) + apklist.findAll('dd', {'style': 'display:none;'})

                for apk in apks:
                    m = self.reVersion.search(apk.find('p').get_text())
                    if m:
                        vername = m.group('VERNAME')
                        vercode = m.group('VERCODE')
                        sdk     = m.group('SDK')
                    href = 'https://apkpure.com' + apk.find('a', {'class': 'down'})['href']

                    if href:
                        avi = ApkVersionInfo(name=apkid,
                                             sdk=(sdk if sdk else 0),
                                             ver=vername,
                                             vercode=vercode,
                                             scrape_src=href,
                                             crawler_name=self.__class__.__name__
                                             )

                        if self.report.isThisApkNeeded(avi):
                            avi = self.parseRedirectPage(avi)
                            filenames.append(self.downloadApk(avi))

            except IndexError:
                logging.info('{0} not supported by apk-dl.com ...'.format(apkid))
            except:
                logging.exception('!!! Error parsing html from: "{0}"'.format(url))

        return filenames
    # END: def checkOneApp:

    def crawl(self, threads=5):
        """
        crawl(): check all apk-dl apps
        """
        # Start checking all apkids ...
        p = multiprocessing.Pool(processes=threads, maxtasksperchild=5)  # Run only 5 tasks before re-placing the process
        r = p.map_async(unwrap_self_checkOneApp, list(zip([self] * len(list(self.report.getAllApkIds())), list(self.report.getAllApkIds()))), callback=unwrap_callback)
        r.wait()
        (self.dlFiles, self.dlFilesBeta) = unwrap_getresults()
    # END: crawl():
# END: class ApkPureCrawler

nonbeta = []
beta    = []


def unwrap_callback(results):
    for resultlist in results:
        for result in resultlist:
            if result:
                if result.startswith('beta:'):
                    beta.append(result[5:])
                else:
                    nonbeta.append(result)


def unwrap_getresults():
    return (nonbeta, beta)


def unwrap_self_checkOneApp(arg, **kwarg):
    return ApkPureCrawler.checkOneApp(*arg, **kwarg)


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

    crawler = ApkPureCrawler(report)
    crawler.crawl()

    outputString = ' '.join(crawler.dlFiles)
    if crawler.dlFilesBeta:
        outputString += ' beta ' + ' '.join(crawler.dlFilesBeta)

    if outputString:
        print(outputString)
        sys.stdout.flush()

    logging.debug('Done ...')
