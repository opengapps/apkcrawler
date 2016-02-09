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

manager = multiprocessing.Manager()
Global  = manager.Namespace()

# logging
logFile   = '{0}.log'.format(os.path.basename(__file__))
logLevel  = (logging.DEBUG if Debug.DEBUG else logging.INFO)
logFormat = '%(asctime)s %(levelname)s/%(funcName)s(%(process)-5d): %(message)s'

allUpToDownNames = {
    #com.android.chrome #they only have chrome beta
    'com.android.vending' : 'google-play',
    #com.google.android.androidforwork
    'com.google.android.apps.books': 'google-play-books',
    #com.google.android.apps.cloudprint
    'com.google.android.apps.docs': 'google-drive',
    'com.google.android.apps.docs.editors.docs': 'google-docs',
    'com.google.android.apps.docs.editors.sheets': 'google-sheets',
    'com.google.android.apps.docs.editors.slides': 'google-slides',
    #com.google.android.apps.enterprise.dmagent
    'com.google.android.apps.fitness': 'google-fit',
    #com.google.android.apps.gcs
    #com.google.android.apps.genie.geniewidget
    'com.google.android.apps.inbox': 'inbox-by-gmail',
    #com.google.android.apps.inputmethod.hindi
    #com.google.android.apps.inputmethod.zhuyin
    'com.google.android.apps.magazines': 'google-play-newsstand',
    'com.google.android.apps.maps': 'google-maps',
    #com.google.android.apps.mediashell
    'com.google.android.apps.messaging': 'messenger',
    #com.google.android.apps.photos
    'com.google.android.apps.plus': 'google-plus',
    'com.google.android.apps.translate': 'traductor-de-google',
    #com.google.android.apps.tycho
    #com.google.android.apps.walletnfcrel
    #com.google.android.calculator
    'com.google.android.calendar': 'google-calendar',
    #com.google.android.contacts
    'com.google.android.deskclock': 'clock',
    #com.google.android.dialer
    'com.google.android.ears': 'sound-search-for-google-play',
    'com.google.android.gm': 'gmail',
    #com.google.android.gm.exchange
    'com.google.android.gms': 'google-play-services',
    'com.google.android.googlecamera': 'google-camera',
    'com.google.android.googlequicksearchbox': 'google-search',
    'com.google.android.inputmethod.japanese': 'google-japanese-input',
    #com.google.android.inputmethod.korean
    'com.google.android.inputmethod.latin': 'google-keyboard',
    #com.google.android.inputmethod.pinyin
    #com.google.android.katniss
    'com.google.android.keep': 'google-keep',
    'com.google.android.launcher': 'google-now-launcher',
    #com.google.android.leanbacklauncher
    'com.google.android.marvin.talkback': 'google-talkback',
    'com.google.android.music': 'google-play-music',
    'com.google.android.play.games': 'google-play-games',
    'com.google.android.street': 'street-view-on-google-maps',
    'com.google.android.talk': 'hangouts',
    #com.google.android.tts
    #com.google.android.tv
    #com.google.android.tv.remote
    'com.google.android.videos': 'google-play-movies',
    'com.google.android.webview': 'android-system-webview',
    'com.google.android.youtube': 'youtube',
    #com.google.android.youtube.tv
    'com.google.earth': 'google-earth'}

class UptodownCrawler(object):
    def __init__(self, report, dlFiles=[], dlFilesBeta=[]):
        self.report      = report
        self.dlFiles     = dlFiles
        self.dlFilesBeta = dlFilesBeta

    def downloadApk(self, avi, isBeta=False):
        """
        downloadApk(apkInfo): Download the specified URL to APK file name
        """
        apkname = '{0}-{1}.apk'.format(avi.name.replace('.beta', ''),
                                       avi.realver.replace(' ', '_'))

        logging.info('Downloading "{0}" from: {1}'.format(apkname,avi.download_src))

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
            session.proxies = Debug.getProxy()
            user_agent = {'User-agent': 'Mozilla/5.0'} #they don't like scripted downloads and then offer their own app instead
            r = session.get(avi.download_src, headers = user_agent)

            with open(apkname, 'wb') as local_file:
                local_file.write(r.content)
            if isBeta:
                self.dlFilesBeta.append(apkname)
                logging.debug('beta: ' + ', '.join(self.dlFilesBeta))
            else:
                self.dlFiles.append(apkname)
                logging.debug('reg : ' + ', '.join(self.dlFiles))
        except OSError:
            logging.exception('!!! Filename is not valid: "{0}"'.format(apkname))
    # END: def downloadApk


    def checkOneApp(self, apkid):
        """
        checkOneApp(apkid):
        """
        logging.info('Checking app: {0}'.format(apkid))
        try:
            upToDownName = allUpToDownNames[apkid]
            appurl      = 'http://' + upToDownName + '.en.uptodown.com/android'
            downloadurl = 'http://' + upToDownName + '.en.uptodown.com/android/download'

            session = requests.Session()
            session.proxies = Debug.getProxy()
            logging.debug('Requesting: ' + appurl)
            try:
                appresp = session.get(appurl)
                apphtml = unicodedata.normalize('NFKD', appresp.text).encode('ascii', 'ignore')
                appdom  = BeautifulSoup(apphtml, 'html5lib')
                appver = appdom.find('span', {'itemprop': 'softwareVersion'}).contents
                if  appver: #sometimes there is no version number specified within the span
                    latestver   = appver[0].lstrip('v').strip().encode("ascii") #sometimes they set a v in front of the versionName and it presents unicode for some reason
                else:
                    latestver   = ''
                logging.debug('Requesting: ' + downloadurl)
                try:
                    downloadresp = session.get(downloadurl)
                    downloadhtml = unicodedata.normalize('NFKD', downloadresp.text).encode('ascii', 'ignore')
                    downloaddom = BeautifulSoup(downloadhtml, 'html5lib')
                    latesturl   = downloaddom.find('iframe', {'id': 'iframe_download'})['src'] #note that this url will still result in a redirect 302

                    avi = ApkVersionInfo(name=apkid,
                                         ver=latestver,
                                         download_src=latesturl
                                         )
                    if self.report.isThisApkNeeded(avi):
                        self.downloadApk(avi)

                    #We still miss fetching older versions
                except:
                    logging.exception('!!! Error parsing html from: "{0}"'.format(downloadurl))
            except:
                logging.exception('!!! Error parsing html from: "{0}"'.format(appurl))
        except KeyError:
            logging.info('{0} not in uptodown.com dictionary'.format(apkid))
    # END: def checkOneApp:


    def crawl(self, threads=5):
        """
        crawl(): check all uptodown apps
        """
        # Start checking all apkids ...
        p = multiprocessing.Pool(threads)
        p.map(unwrap_self_checkOneApp, zip([self]*len(self.report.dAllApks.keys()), self.report.dAllApks.keys()))
    # END: crawl():
# END: class UptodownCrawler

def unwrap_self_checkOneApp(arg, **kwarg):
    return UptodownCrawler.checkOneApp(*arg, **kwarg)

###################
# END: Functions  #
###################

if __name__ == "__main__":
    """
    main(): single parameter for report_sources.sh output
    """
    logging.basicConfig(filename = logFile, filemode = 'w', level = logLevel, format = logFormat)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("requesocks").setLevel(logging.WARNING)

    lines = ''
    if len(sys.argv[1:]) == 1:
        with open(sys.argv[1:]) as report:
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

    crawler = UptodownCrawler(report)
    crawler.crawl()
    logging.debug('Just before outputString creation')
    outputString = ' '.join(crawler.dlFiles)
    if crawler.dlFilesBeta:
        outputString += ' beta ' + ' '.join(crawler.dlFilesBeta)
    logging.debug('Just after outputString creation')
    if outputString:
        print(outputString)
        sys.stdout.flush()
    logging.debug('Done ...')
