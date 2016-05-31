#!/usr/bin/env python3

#
# Required Modules
# - beautifulsoup4
# - html5lib
# - requests
#

import sys
import os
import re
import logging
import multiprocessing
import requests

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


class ApkdlCrawler(object):
    def __init__(self, report, dlFiles=[], dlFilesBeta=[]):
        self.report      = report
        self.dlFiles     = dlFiles
        self.dlFilesBeta = dlFilesBeta

    def getUrlFromRedirect(self, apkname, url):
        """
        getUrlFromRedirect(url):
        """
        link      = ''

        session = requests.Session()
        logging.debug('Requesting2: ' + url)
        resp    = session.get(url)
        html    = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'ignore')

        try:
            dom  = BeautifulSoup(html, 'html5lib')
            link = dom.find('span', {'class': 'glyphicon glyphicon-cloud-download'}).parent['href']
        except:
            logging.exception('!!! Error parsing html from: "{0}"'.format(url))

        return link
    # END: def getUrlFromRedirect:

    def downloadApk(self, apkInfo, isBeta=False):
        """
        downloadApk(apkInfo): Download the specified URL to APK file name
        """
        apkname = ('beta.' if isBeta else '') + avi.getFilename()

        url     = self.getUrlFromRedirect(apkname, apkInfo.download_src)
        if url == '':
            logging.error('Unable to determine redirect url for ' + apkname)
            return

        logging.info('Downloading "{0}" from: {1}'.format(apkname, url))

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

        filenames = []

        url       = 'http://apk-dl.com/' + apkid

        session = requests.Session()
        logging.debug('Requesting: ' + url)
        resp    = session.get(url)
        html    = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'ignore')

        try:
            dom     = BeautifulSoup(html, 'html5lib')
            apklist = dom.findAll('ul', {'class': 'apks dlist'})[0]
            apks    = apklist.findAll('div', {'class': 'details'})

            for apk in apks:
                items = apk.findAll('div')
                dApk = {}
                for item in items:
                    itext = '{0}'.format(item.get_text().encode('ascii', 'ignore'))
                    itext = re.sub('\s', '', itext)
                    itextsp = itext.split(':', 1)
                    if len(itextsp) == 2:
                        dApk[str(itextsp[0])] = str(itextsp[1])
                apkurl = apk.find('a', {'class': 'btn btn-success'})
                if apkurl:
                    dApk['url'] = 'http:' + apkurl['href']

                    Debug.printDictionary(dApk)

                    if 'Version' in dApk and 'RequiresAndroid' in dApk:
                        (trash, sdk) = dApk['RequiresAndroid'].split('API:', 1)
                        sdk = sdk[0:-1]
                        (ver, vercode) = dApk['Version'].split('(Code:', 1)
                        ver     = ver.split('(', 1)[0].strip()
                        vercode = vercode[0:-1].strip()

                        avi = ApkVersionInfo(name=apkid,
                                             sdk=sdk,
                                             ver=ver,
                                             vercode=vercode,
                                             download_src=dApk['url'],
                                             crawler_name=self.__class__.__name__
                                             )

                        if self.report.isThisApkNeeded(avi):
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
# END: class ApkdlCrawler

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
    return ApkdlCrawler.checkOneApp(*arg, **kwarg)


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

    crawler = ApkdlCrawler(report)
    crawler.crawl()

    outputString = ' '.join(crawler.dlFiles)
    if crawler.dlFilesBeta:
        outputString += ' beta ' + ' '.join(crawler.dlFilesBeta)

    if outputString:
        print(outputString)
        sys.stdout.flush()

    logging.debug('Done ...')
