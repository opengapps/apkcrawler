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
import unicodedata

from bs4 import BeautifulSoup
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


class PlazzaCrawler(object):
    def __init__(self, report, dlFiles=[], dlFilesBeta=[]):
        self.report      = report
        self.dlFiles     = dlFiles
        self.dlFilesBeta = dlFilesBeta

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

            r = session.get(avi.download_src, stream=True)  # plazza blocks fetching it at one go, we need to stream it in chunks
            with open(apkname, 'wb') as local_file:
                for chunk in r.iter_content(1024):
                    local_file.write(chunk)

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

        url       = 'http://www.plazza.ir/app/' + apkid + '?hl=en'

        session = requests.Session()
        logging.debug('Requesting: ' + url)
        try:
            resp    = session.get(url, allow_redirects=False)  # we get a 302 if application is not found
            if resp.status_code == http.client.OK:
                html    = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'ignore')

                try:
                    dom       = BeautifulSoup(html, 'html5lib')
                    latesthref = dom.find('a', {'itemprop': 'downloadUrl'})['href']
                    latestver = dom.find('div', {'itemprop': 'softwareVersion'}).contents[0].strip()
                    appid     = re.search('(^\/dl\/)([0-9]+)(\/1$)', latesthref).group(2)
                    latesturl = session.head('http://www.plazza.ir' + latesthref, allow_redirects=True).url
                    # latestvercode = re.search('(_)([0-9]+)(\.apk)$', latesturl).group(2) #apparently this is NOT a (reliable?) versioncode
                    avi = ApkVersionInfo(name=apkid,
                                         ver=latestver,
                                         # vercode=latestvercode,
                                         download_src=latesturl,
                                         crawler_name=self.__class__.__name__
                                         )
                    if self.report.isThisApkNeeded(avi):
                        return self.downloadApk(avi)

                    # Fetching of older versions is not completed, because it requires VIP accounts
                    # olderapks = dom.find('div', {'style': 'direction: rtl'}).findAll('a', {'target': '_blank'})
                    # for apk in olderapks:
                    #     apkver = re.search('(\/)([0-9]+)(\?.*$|$)', apk['href']).group(2) #number is either end of string or there can be an ? for extra GET parameters
                    #     apkurl = session.head('http://www.plazza.ir/dl_version/' + appid + '/' + apkver + '/1',allow_redirects=True).url

                except:
                    logging.exception('!!! Error parsing html from: "{0}"'.format(url))
            else:
                logging.info('{0} not available on plazza.ir'.format(apkid))
        except:
            logging.exception('Connection error to plazza.ir when checking {0} at {1}'.format(apkid, url))

    # END: def checkOneApp:

    def crawl(self, threads=5):
        """
        crawl(): check all plazza apps
        """
        # Start checking all apkids ...
        p = multiprocessing.Pool(processes=threads, maxtasksperchild=5)  # Run only 5 tasks before re-placing the process
        r = p.map_async(unwrap_self_checkOneApp, list(zip([self] * len(list(self.report.getAllApkIds())), list(self.report.getAllApkIds()))), callback=unwrap_callback)
        r.wait()
        (self.dlFiles, self.dlFilesBeta) = unwrap_getresults()
    # END: crawl():
# END: class PlazzaCrawler

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
    return PlazzaCrawler.checkOneApp(*arg, **kwarg)


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

    crawler = PlazzaCrawler(report)
    crawler.crawl()

    outputString = ' '.join(crawler.dlFiles)
    if crawler.dlFilesBeta:
        outputString += ' beta ' + ' '.join(crawler.dlFilesBeta)

    if outputString:
        print(outputString)
        sys.stdout.flush()

    logging.debug('Done ...')
