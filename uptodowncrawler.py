#!/usr/bin/env python3

#
# Required Modules
# - beautifulsoup4
# - html5lib
# - requests
#

import logging
import multiprocessing
import os
import sys
import re
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

allUpToDownNames = {
    #'com.android.chrome'                         : 'n/a',  # they only have chrome beta
    'com.android.vending'                         : 'google-play',
    'com.google.android.apps.books'               : 'google-play-books',
    'com.google.android.apps.cloudprint'          : 'cloud-print',
    'com.google.android.apps.docs'                : 'google-drive',
    'com.google.android.apps.docs.editors.docs'   : 'google-docs',
    'com.google.android.apps.docs.editors.sheets' : 'google-sheets',
    'com.google.android.apps.docs.editors.slides' : 'google-slides',
    #'com.google.android.apps.enterprise.dmagent' : 'n/a',
    'com.google.android.apps.fitness'             : 'google-fit',
    #'com.google.android.apps.gcs'                : 'n/a',
    'com.google.android.apps.genie.geniewidget'   : 'google-news-and-weather',
    'com.google.android.apps.inbox'               : 'inbox-by-gmail',
    'com.google.android.apps.inputmethod.hindi'   : 'google-indic-keyboard',
    #'com.google.android.apps.inputmethod.zhuyin' : 'n/a',
    'com.google.android.apps.magazines'           : 'google-play-newsstand',
    'com.google.android.apps.maps'                : 'google-maps',
    'com.google.android.apps.mediashell'          : 'google-cast-receiver',
    'com.google.android.apps.messaging'           : 'messenger',
    'com.google.android.apps.photos'              : 'google-photos',
    'com.google.android.apps.plus'                : 'google-plus',
    'com.google.android.apps.translate'           : 'traductor-de-google',
    #'com.google.android.apps.tycho'              : 'n/a',
    #'com.google.android.apps.walletnfcrel'       : 'n/a',
    #'com.google.android.calculator'              : 'n/a',
    'com.google.android.calendar'                 : 'google-calendar',
    #'com.google.android.contacts'                : 'n/a',
    'com.google.android.deskclock'                : 'clock',
    'com.google.android.dialer'                   : 'google-phone',
    'com.google.android.ears'                     : 'sound-search-for-google-play',
    'com.google.android.gm'                       : 'gmail',
    #'com.google.android.gm.exchange'             : 'n/a',
    'com.google.android.gms'                      : 'google-play-services',
    'com.google.android.googlecamera'             : 'google-camera',
    'com.google.android.googlequicksearchbox'     : 'google-quick-search-box',
    'com.google.android.inputmethod.japanese'     : 'google-japanese-input',
    #'com.google.android.inputmethod.korean'      : 'n/a',
    'com.google.android.inputmethod.latin'        : 'google-keyboard',
    'com.google.android.inputmethod.pinyin'       : 'entrada-pinyin-de-google',
    'com.google.android.katniss'                  : 'google-search',
    'com.google.android.keep'                     : 'google-keep',
    'com.google.android.launcher'                 : 'google-now-launcher',
    #'com.google.android.leanbacklauncher'        : 'n/a',
    'com.google.android.marvin.talkback'          : 'google-talkback',
    'com.google.android.music'                    : 'google-play-music',
    'com.google.android.play.games'               : 'google-play-games',
    'com.google.android.street'                   : 'street-view-on-google-maps',
    'com.google.android.talk'                     : 'hangouts',
    'com.google.android.tts'                      : 'google-text-to-speech',
    #'com.google.android.tv'                      : 'n/a',
    #'com.google.android.tv.remote'               : 'n/a',
    'com.google.android.videos'                   : 'google-play-movies',
    'com.google.android.webview'                  : 'android-system-webview',
    'com.google.android.youtube'                  : 'youtube',
    #'com.google.android.youtube.tv'              : 'n/a',
    'com.google.earth'                            : 'google-earth'}


class UptodownCrawler(object):
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
            user_agent = {'User-agent': 'Mozilla/5.0'}  # they don't like scripted downloads and then offer their own app instead
            r = session.get(avi.download_src, headers=user_agent)

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
        avis = []
        filenames = []
        try:
            upToDownName = allUpToDownNames[apkid]
            appurl      = 'http://' + upToDownName + '.en.uptodown.com/android/old'

            session = requests.Session()
            logging.debug('Requesting1: ' + appurl)
            try:
                appresp = session.get(appurl)
                apphtml = unicodedata.normalize('NFKD', appresp.text).encode('ascii', 'ignore')
                appdom  = BeautifulSoup(apphtml, 'html5lib')

                latestver = appdom.find('span', {'itemprop': 'softwareVersion'})
                if latestver:   # sometimes there is only 1 version and no old versions, and you get the latest-version page of the app instead of the overview of old versions
                    avis.append(ApkVersionInfo(name=apkid,
                                               ver=(latestver.contents[0].lstrip('v').strip().encode("ascii") if latestver.contents else ''),  # sometimes there is no versionnumber, or they set a v in front of the versionName; it presents unicode for some reason
                                               scrape_src='http://' + upToDownName + '.en.uptodown.com/android/download',
                                               crawler_name=self.__class__.__name__
                                               ))
                else:
                    appversions = appdom.findAll('section', {'class': 'container'})
                    for apk in appversions[0:5]:    # limit ourself to only the first 5 results; the chance that there are updates beyond that point is smaller than the chance of having errors in the versionname
                        apkurl = apk.find('a')['href']
                        apkver = apk.find('span', {'class': 'app_card_version'}).contents
                        avis.append(ApkVersionInfo(name=apkid,
                                                   ver=(apkver[0].lstrip('v').strip().encode("ascii").decode('utf-8') if apkver else ''),  # sometimes there is no versionnumber, or they set a v in front of the versionName; it presents unicode for some reason
                                                   scrape_src='http:' + apkurl,
                                                   crawler_name=self.__class__.__name__
                                                   ))
                    # END: for appversions
                # END: if lastestver

                for avi in avis:
                    if self.report.isThisApkNeeded(avi):
                        logging.debug('Requesting2: ' + avi.scrape_src)
                        try:
                            downloadresp     = session.get(avi.scrape_src)
                            downloadhtml     = unicodedata.normalize('NFKD', downloadresp.text).encode('ascii', 'ignore')
                            downloaddom      = BeautifulSoup(downloadhtml, 'html5lib')
                            avi.download_src = 'http:' + downloaddom.find('iframe', {'class': 'hidden'})['src']  # note that this url will still result in a redirect 302
                            filenames.append(self.downloadApk(avi))
                        except:
                            logging.exception('!!! Error parsing html from: "{0}"'.format(avi.scrape_src))
                    # END: if isThisApkNeeded
                # END: for avis
            except:
                logging.exception('!!! Error parsing html from: "{0}"'.format(appurl))
        except KeyError:
            logging.info('{0} not in uptodown.com dictionary'.format(apkid))
        return filenames
    # END: def checkOneApp

    def crawl(self, threads=5):
        """
        crawl(): check all uptodown apps
        """
        # Start checking all apkids ...
        p = multiprocessing.Pool(processes=threads, maxtasksperchild=5)  # Run only 5 tasks before re-placing the process
        r = p.map_async(unwrap_self_checkOneApp, list(zip([self] * len(list(self.report.getAllApkIds())), list(self.report.getAllApkIds()))), callback=unwrap_callback)
        r.wait()
        (self.dlFiles, self.dlFilesBeta) = unwrap_getresults()
    # END: crawl():
# END: class UptodownCrawler

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
    return UptodownCrawler.checkOneApp(*arg, **kwarg)


if __name__ == "__main__":
    """
    main(): single parameter for report_sources.sh output
    """
    logging.basicConfig(filename=logFile, filemode='w', level=logLevel, format=logFormat)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("requesocks").setLevel(logging.WARNING)

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

    crawler = UptodownCrawler(report)
    crawler.crawl()

    outputString = ' '.join(crawler.dlFiles)
    if crawler.dlFilesBeta:
        outputString += ' beta ' + ' '.join(crawler.dlFilesBeta)

    if outputString:
        print(outputString)
        sys.stdout.flush()

    logging.debug('Done ...')
