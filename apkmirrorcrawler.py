#!/usr/bin/env python

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

from bs4 import BeautifulSoup
import unicodedata

from debug import Debug
from apkhelper import ApkVersionInfo
from reporthelper import ReportHelper

# Debug.USE_SOCKS_PROXY = True
if Debug.USE_SOCKS_PROXY:
    import requesocks as requests
else:
    import requests

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

allApkMirrorNames = {
    'com.android.chrome'                          : 'chrome',
    'com.android.vending'                         : 'google-play-store',
    # 'com.google.android.androidforwork'           : '',
    'com.google.android.apps.books'               : 'google-play-books',
    'com.google.android.apps.cloudprint'          : 'cloud-print',
    'com.google.android.apps.docs'                : 'drive',
    'com.google.android.apps.docs.editors.docs'   : 'docs',
    'com.google.android.apps.docs.editors.sheets' : 'sheets',
    'com.google.android.apps.docs.editors.slides' : 'slides',
    'com.google.android.apps.enterprise.dmagent'  : 'device-policy',
    'com.google.android.apps.fitness'             : 'fit',
    'com.google.android.apps.gcs'                 : 'google-connectivity-services',
    'com.google.android.apps.genie.geniewidget'   : 'news-weather',
    'com.google.android.apps.inbox'               : 'inbox',
    'com.google.android.apps.inputmethod.hindi'   : 'google-indic-keyboard',
    'com.google.android.apps.inputmethod.zhuyin'  : 'google-zhuyin-input',
    'com.google.android.apps.magazines'           : 'google-play-newsstand',
    'com.google.android.apps.maps'                : 'maps',
    'com.google.android.apps.mediashell'          : 'google-cast-receiver',
    'com.google.android.apps.messaging'           : 'messenger-google-inc',
    'com.google.android.apps.photos'              : 'photos',
    'com.google.android.apps.plus'                : 'google',
    'com.google.android.apps.translate'           : 'translate',
    'com.google.android.apps.tycho'               : 'project-fi',
    'com.google.android.apps.walletnfcrel'        : 'android-pay',
    'com.google.android.calculator'               : 'google-calculator',
    'com.google.android.calendar'                 : 'calendar',
    'com.google.android.contacts'                 : 'google-contacts',
    'com.google.android.deskclock'                : 'clock',
    'com.google.android.dialer'                   : 'google-phone',
    'com.google.android.ears'                     : 'sound-search-for-google-play',
    'com.google.android.gm'                       : 'gmail',
    'com.google.android.gm.exchange'              : 'exchange-services',
    'com.google.android.gms'                      : 'google-play-services',
    'com.google.android.googlecamera'             : 'camera',
    'com.google.android.googlequicksearchbox'     : 'google-search',
    'com.google.android.inputmethod.japanese'     : 'google-japanese-input',
    'com.google.android.inputmethod.korean'       : 'google-korean-input',
    'com.google.android.inputmethod.latin'        : 'google-keyboard',
    'com.google.android.inputmethod.pinyin'       : 'google-pinyin-input',
    'com.google.android.katniss'                  : 'google-app-for-android-tv',
    'com.google.android.keep'                     : 'keep',
    'com.google.android.launcher'                 : 'google-now-launcher',
    'com.google.android.leanbacklauncher'         : 'leanback-launcher',
    'com.google.android.marvin.talkback'          : 'talkback',
    'com.google.android.music'                    : 'google-play-music',
    'com.google.android.play.games'               : 'google-play-games',
    'com.google.android.street'                   : 'street-view',
    'com.google.android.tag'                      : 'tags',
    'com.google.android.talk'                     : 'hangouts',
    'com.google.android.tts'                      : 'google-text-to-speech-engine',
    'com.google.android.tv'                       : 'live-channels',
    'com.google.android.tv.remote'                : 'remote-control',
    'com.google.android.videos'                   : 'google-play-movies',
    'com.google.android.webview'                  : 'android-system-webview',
    'com.google.android.youtube'                  : 'youtube',
    'com.google.android.youtube.tv'               : 'youtube-for-android-tv',
    'com.google.earth'                            : 'earth'}


class ApkMirrorCrawler(object):
    def __init__(self, report, dlFiles=[], dlFilesBeta=[]):
        self.report      = report
        self.dlFiles     = dlFiles
        self.dlFilesBeta = dlFilesBeta

        self.sReVerInfo = '(?P<VERNAME>\S*) \((?P<VERCODE>\d*)\).* API (?P<SDK>\d*)\)'
        self.reVersion  = re.compile(self.sReVerInfo)

    def downloadApk(self, avi, isBeta=False):
        """
        downloadApk(avi): downloads the give APK
        """
        try:
            if os.path.exists(avi.apk_name):
                logging.info('Downloaded APK already exists.')
                return

            if os.path.exists(os.path.join('.', 'apkcrawler', avi.apk_name)):
                logging.info('Downloaded APK already exists (in ./apkcrawler/).')
                return

            if os.path.exists(os.path.join('..', 'apkcrawler', avi.apk_name)):
                logging.info('Downloaded APK already exists (in ../apkcrawler/).')
                return

            # Open the url
            session = requests.Session()
            session.proxies = Debug.getProxy()
            r = session.get(avi.download_src)

            with open(avi.apk_name, 'wb') as local_file:
                local_file.write(r.content)

            logging.debug(('beta:' if isBeta else 'reg :') + avi.apk_name)
            return (('beta:' if isBeta else ''     ) + avi.apk_name)
        except OSError:
            logging.exception('!!! Filename is not valid: "{0}"'.format(avi.apk_name))
    # END: def downloadApk(avi):

    def getVersionInfo(self, avi):
        """
        getVersionInfo(avi): Determines each versions information
        """
        try:
            url = 'http://www.apkmirror.com' + avi.scrape_src

            session = requests.Session()
            session.proxies = Debug.getProxy()
            logging.debug('Requesting2: ' + url)

            resp    = session.get(url)
            html    = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'ignore')

            dom       = BeautifulSoup(html, 'html5lib')
            postArea  = dom.findAll('div', {'class': 'post-area'})[0]
            dl_button = postArea.findAll('a', {'type': 'button'})[1]
            blueFonts = postArea.findAll('span', {'class': 'fontBlue'})

            avi.download_src = dl_button['href']

            for blueFont in blueFonts:
                if blueFont.get_text() == 'File name: ':
                    avi.apk_name = blueFont.next_sibling
        except:
            logging.exception('!!! Error parsing html from: "{0}"'.format(url))
    # END: def getVersionInfo(avi):

    def checkOneApp(self, apkid):
        """
        checkOneApp(apkid): Collect all versions for an application
        """
        logging.info('Checking app: {0}'.format(apkid))

        filenames = []

        try:
            apkMirrorName = allApkMirrorNames[apkid]
            url = 'http://www.apkmirror.com/uploads/?app=' + apkMirrorName

            session = requests.Session()
            session.proxies = Debug.getProxy()
            logging.debug('Requesting: ' + url)
            try:
                resp = session.get(url)
                html = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'ignore')

                dom      = BeautifulSoup(html, 'html5lib')
                latest   = dom.findAll('div', {'class': 'latestWidget'})[1]
                versions = latest.findAll('div', {'class': 'latestPost'})

                avis = []

                for version in versions:
                    verName = version.findAll('a', {'class': 'fontBlack'})
                    if verName:
                        verName = verName[0]
                    else:
                        continue

                    verText = '{0}'.format(verName.get_text().encode('ascii', 'ignore'))
                    if 'preview' in verText.lower():
                        logging.info('!!! Preview Found: ' + verText)
                    else:
                        isBeta = 'beta' in verText.lower()

                        blues = version.findAll('span', {'class': 'fontBlue'})
                        blueVer = [blue for blue in blues if 'Version' in blue.get_text()][0]
                        verInfo = blueVer.findNext('strong').get_text()

                        m = self.reVersion.search(verInfo)
                        if m:
                            avi = ApkVersionInfo(name=apkid + ('.beta' if isBeta else ''),
                                                 ver=m.group('VERNAME'),
                                                 vercode=int(m.group('VERCODE')),
                                                 sdk=int(m.group('SDK')),
                                                 scrape_src=verName['href'])
                            avis.append(avi)
                        else:
                            logging.info('!!! No Matchy: ' + verText)
                # END: for version in versions:

                # Determine which versions to download
                if len(avis) > 0:
                    for avi in avis:
                        if self.report.isThisApkNeeded(avi):
                            logging.info('Getting Info for: "{0}" ({1})'.format(avi.name, avi.scrape_src))
                            self.getVersionInfo(avi)
                            logging.info('Downloading: "{0}"'.format(avi.apk_name))
                            filenames.append(self.downloadApk(avi))
                        else:
                            logging.debug('Skipping: "{0}" ({1})'.format(avi.name, avi.scrape_src))
                    # END: for avi in avis:
                else:
                    logging.info('No matching APKs found for: {0}'.format(apkMirrorName))
            except:
                logging.exception('!!! Error parsing html from: "{0}"'.format(url))
        except KeyError:
            logging.info('{0} not in apkmirror.com dictionary'.format(apkid))

        return filenames
    # END: def checkOneApp:

    def crawl(self, threads=5):
        """
        crawl(): check all ApkMirror apps
        """
        # Start checking all apkids ...
        p = multiprocessing.Pool(threads)
        r = p.map_async(unwrap_self_checkOneApp,
                        zip([self]*len(self.report.dAllApks.keys()), self.report.dAllApks.keys()),
                        callback=unwrap_callback)
        r.wait()
        (self.dlFiles, self.dlFilesBeta) = unwrap_getresults()
    # END: crawl():
# END: class ApkMirrorCrawler

nonbeta = []
beta    = []


def unwrap_callback(results):
    for result_list in results:
        for result in result_list:
            if result:
                if result.startswith('beta:'):
                    beta.append(result[5:])
                else:
                    nonbeta.append(result)


def unwrap_getresults():
    return (nonbeta, beta)


def unwrap_self_checkOneApp(arg, **kwarg):
    return ApkMirrorCrawler.checkOneApp(*arg, **kwarg)


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

    if len(report.dAllApks.keys()) == 0:
        print('ERROR: expecting:')
        print(' - 1 parameter (report file from output of report_sources.sh)')
        print(' or ')
        print(' - stdin from report_sources.sh')
        exit(1)

    crawler = ApkMirrorCrawler(report)
    crawler.crawl()

    outputString = ' '.join(crawler.dlFiles)
    if crawler.dlFilesBeta:
        outputString += ' beta ' + ' '.join(crawler.dlFilesBeta)

    if outputString:
        print(outputString)
        sys.stdout.flush()

    logging.debug('Done ...')
