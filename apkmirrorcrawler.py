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

allApkMirrorNames = {
    'com.android.chrome'                          : 'chrome',
    'com.android.facelock'                        : 'trusted-face',
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
    'com.google.android.apps.nexuslauncher'       : 'pixel-launcher',
    'com.google.android.apps.photos'              : 'photos',
    'com.google.android.apps.plus'                : 'google',
    'com.google.android.apps.translate'           : 'translate',
    'com.google.android.apps.fireball'            : 'allo-by-google',
    'com.google.android.apps.tachyon'             : 'duo-by-google',
    'com.google.android.apps.tycho'               : 'project-fi',
    'com.google.android.apps.walletnfcrel'        : 'android-pay',
    'com.google.android.apps.wallpaper'           : 'google-wallpaper-picker',
    'com.google.android.backdrop'                 : 'backdrop-daydream',
    'com.google.android.backuptransport'          : 'google-backup-transport',
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
    'com.google.android.gsf'                      : 'google-services-framework',
    'com.google.android.gsf.login'                : 'google-account-manager',
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
    'com.google.android.nexusicons'               : 'pixel-launcher-icons',
    'com.google.android.onetimeinitializer'       : 'google-one-time-init',
    'com.google.android.partnersetup'             : 'google-partner-setup',
    'com.google.android.play.games'               : 'google-play-games',
    'com.google.android.setupwizard'              : 'setup-wizard',
    'com.google.android.street'                   : 'street-view',
    'com.google.android.syncadapters.contacts'    : 'google-contacts-sync',
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

        self.sReVerInfo = 'Version:\s(?P<VERNAME>.*)\s\((?P<VERCODE>\d*)\)'
        self.reVersion  = re.compile(self.sReVerInfo)

        self.sReSdkInfo = 'Min:\s[^)]*API\s(?P<SDK>\w*)\)'
        self.reSdk      = re.compile(self.sReSdkInfo)

        self.sReTargetInfo = 'Target:\s.*API\s(?P<Target>\w*)\)'
        self.reTarget      = re.compile(self.sReTargetInfo)

    def downloadApk(self, avi, isBeta=False):
        """
        downloadApk(avi): downloads the give APK
        """
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
            r = session.get(avi.download_src)

            with open(apkname, 'wb') as local_file:
                local_file.write(r.content)

            logging.debug(('beta:' if isBeta else 'reg :') + apkname)
            return (('beta:' if isBeta else '') + apkname)
        except OSError:
            logging.exception('!!! Filename is not valid: "{0}"'.format(apkname))
    # END: def downloadApk(avi):

    def getMultipleVersionInfo(self, avi):
        """
        getMultipleVersionInfo(avi): Determines each version information for multiple
                                     arch/dpi variants
        """
        try:
            url = 'http://www.apkmirror.com' + avi.scrape_src

            session = requests.Session()
            logging.debug('Requesting3: ' + url)

            resp    = session.get(url)
            html    = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'ignore')

            dom          = BeautifulSoup(html, 'html5lib')
            downloadArea = dom.findAll('div', {'class': 'listWidget'})[0]
            tablerows    = downloadArea.findAll('div', {'class': 'table-row'})

            avis = []

            bOnce = True  # Skip header row
            for tr in tablerows:
                if bOnce:
                    bOnce = False
                    continue

                cells = tr.findAll('div', {'class': 'table-cell'})
                avi.scrape_src = cells[0].find('a')['href']
                avi.arch = cells[1].get_text()

                tmp = self.getOneVersionInfo(avi)
                if tmp:
                    avis.append(tmp)

            return avis
        except:
            try:
                return [self.getOneVersionInfo(avi)]
            except:
                logging.exception('!!! Error parsing html from: "{0}"'.format(url))
    # END: def getMultipleVersionInfo(avi):

    def getOneVersionInfo(self, avi):
        """
        getOneVersionInfo(avi): Determines each versions information
        """
        try:
            url = 'http://www.apkmirror.com' + avi.scrape_src

            session = requests.Session()
            logging.debug('Requesting2: ' + url)

            resp    = session.get(url)
            html    = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'ignore')

            dom         = BeautifulSoup(html, 'html5lib')
            contentArea = dom.findAll('div', {'class': 'tab-content'})[0]
            dl_button   = contentArea.findAll('a', {'type': 'button'})[0]
            appspecs    = contentArea.findAll('div', {'class': 'appspec-row'})

            avivername = ''
            avivercode = ''
            avisdk     = ''
            avitarget  = ''
            avidpi     = ''
            for appspec in appspecs:
                # Version
                if appspec.find('svg', {'class': 'apkm-icon-file'}):
                    m = self.reVersion.search(appspec.find('div', {'class': 'appspec-value'}).get_text())
                    if m:
                        avivername = m.group('VERNAME')
                        avivercode = m.group('VERCODE')
                # SDK & Target
                if appspec.find('svg', {'class': 'apkm-icon-sdk'}):
                    m = self.reSdk.search(appspec.find('div', {'class': 'appspec-value'}).get_text())
                    if m:
                        avisdk = m.group('SDK')
                    m = self.reTarget.search(appspec.find('div', {'class': 'appspec-value'}).get_text())
                    if m:
                        avitarget = m.group('Target')
                # DPI
                if appspec.find('svg', {'class': 'apkm-icon-dpi'}):
                    avidpi = appspec.find('div', {'class': 'appspec-value'}).get_text().replace(', ', '-')

            return ApkVersionInfo(name=avi.name,
                                  ver=avivername,
                                  vercode=avivercode,
                                  sdk=avisdk,
                                  target=avitarget,
                                  dpi=avidpi,
                                  arch=avi.arch,
                                  scrape_src=avi.scrape_src,
                                  download_src='http://www.apkmirror.com' + dl_button['href'],
                                  crawler_name=self.__class__.__name__)

        except:
            logging.exception('!!! Error parsing html from: "{0}"'.format(url))
    # END: def getOneVersionInfo(avi):

    def checkOneApp(self, apkid):
        """
        checkOneApp(apkid): Collect all versions for an application
        """
        logging.info('Checking app: {0}'.format(apkid))

        filenames = []

        try:
            apkMirrorName = allApkMirrorNames[apkid]

            # Using the "uploads/?q=" page sorts newest first but is slower
            # Using the "apk/google-inc/" page is faster loading
            # For now favor slow load and skip checking all versions (below)
            url = 'http://www.apkmirror.com/uploads/?q={0}'.format(apkMirrorName)

            session = requests.Session()
            logging.debug('Requesting1: ' + url)
            try:
                resp = session.get(url)
                html = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'ignore')

                dom      = BeautifulSoup(html, 'html5lib')
                versions = dom.findAll('div', {'class': 'infoSlide'})

                hasVariants = dom.find('svg', {'class': 'tag-icon'})

                avis = []

                # Skip all version since it is sorted (above)
                # for version in versions:
                version = versions[0]

                verName = version.findAll('span', {'class': 'infoslide-value'})
                verName = verName[0].get_text()

                appNameRow  = version.find_previous_sibling('div', {'class': 'appRow'})
                appNameLink = appNameRow.find('a', {'class': 'fontBlack'})
                appName     = appNameLink.get_text()
                appUrl      = appNameLink['href']

                if 'preview' in appName.lower():
                    logging.info('!!! Preview Found: ' + appName)
                else:
                    isBeta = 'beta' in appName.lower()

                    avi = ApkVersionInfo(name=apkid + ('.beta' if isBeta else ''),
                                         ver=verName,
                                         scrape_src=appUrl)

                    if self.report.isThisApkNeeded(avi):
                        if hasVariants:
                            avis.extend(self.getMultipleVersionInfo(avi))
                        else:
                            tmp = self.getOneVersionInfo(avi)
                            if tmp:
                                avis.append(tmp)
                # END: for version in versions:

                # Determine which versions to download
                for avi in avis:
                    if self.report.isThisApkNeeded(avi):
                        logging.info('Downloading: "{0}"'.format(avi.getFilename()))
                        filenames.append(self.downloadApk(avi, avi.name.endswith('.beta')))
                    else:
                        logging.debug('Skipping: "{0}" ({1})'.format(avi.name, avi.scrape_src))
                # END: for avi in avis:
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
        p = multiprocessing.Pool(processes=threads, maxtasksperchild=5)  # Run only 5 tasks before re-placing the process
        r = p.map_async(unwrap_self_checkOneApp,
                        list(zip([self] * len(list(self.report.getAllApkIds())), list(self.report.getAllApkIds()))),
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

    crawler = ApkMirrorCrawler(report)
    crawler.crawl()

    outputString = ' '.join(crawler.dlFiles)
    if crawler.dlFilesBeta:
        outputString += ' beta ' + ' '.join(crawler.dlFilesBeta)

    if outputString:
        print(outputString)
        sys.stdout.flush()

    logging.debug('Done ...')
