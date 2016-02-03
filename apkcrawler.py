#!/usr/bin/env python

#
# Required Modules
# - beautifulsoup4
# - html5lib
# - requests
#

import sys
import os
import logging
import multiprocessing

import requests
from bs4 import BeautifulSoup
import unicodedata

from debug import Debug
from apkhelper import ApkVersionInfo

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
# CLASSES         #
###################


class ApkMirrorInfo(object):
    """ApkMirrorInfo"""
    def __init__(self, apkmirror_name='', opengapps_name='', url=''):
        super(ApkMirrorInfo, self).__init__()
        import re
        self.apkmirror_name = apkmirror_name
        self.opengapps_name = opengapps_name

        # Default naming convention (from application name to url)
        if url == '':
            self.url = apkmirror_name.lower()
            self.url = self.url.replace(' ',   '-')  # Space to dash (fairly common)
            self.url = self.url.replace('-&-', '-')  # Special case for News & Weather
            self.url = self.url.replace('+',   '')   # Special case for Google+
            self.url = self.url + '/'                # Trailing '/'
        else:
            self.url = url

        # Version RegEx String
        self.sReVerInfo = '(?P<VERNAME>\S*) \((?P<VERCODE>\d*)\).* API (?P<SDK>\d*)\)'
        self.reVersion  = re.compile(self.sReVerInfo)

        self.versions  = []

    def __str__(self):
        try:
            from urllib.parse import parse_qs
            from urllib.parse import urlencode
        except ImportError:
            from urlparse import parse_qs
            from urllib import urlencode
        import json
        vArr = [str(v) for v in self.versions]
        data = urlencode({'apkmirror_name': self.apkmirror_name,
                          'opengapps_name': self.opengapps_name,
                          'url':            self.url,
                          'versions':       vArr})
        return json.dumps(parse_qs(data))
# END: class ApkMirrorInfo()

###################
# END: CLASSES    #
###################

###################
# Globals         #
###################

APKMIRRORBASEURL    = 'http://www.apkmirror.com'
APKMIRRORGOOGLEURL  = '/apk/google-inc/'
APKMIRRORGOOGLEURL2 = '/uploads/?app='

# logging
logFile   = '{0}.log'.format(os.path.basename(__file__))
logLevel  = (logging.DEBUG if Debug.DEBUG else logging.INFO)
logFormat = '%(asctime)s %(levelname)s/%(funcName)s(%(process)-5d): %(message)s'

requestedApkInfo = []
allApkInfo = [
    ApkMirrorInfo('Android Pay',                  'androidpay'      ),
    ### Android for Work App (not the core included in Open GApps)
    # ApkMirrorInfo('Android for Work App',         'androidforwork'  ),
    ApkMirrorInfo('Android System WebView',       'webviewgoogle'   ),
    ApkMirrorInfo('Calculator',                   'calculator',     'google-calculator'     ),
    ApkMirrorInfo('Google Calendar',              'calendargoogle', 'calendar'              ),
    ApkMirrorInfo('Google Camera',                'cameragoogle',   'camera'                ),
    ApkMirrorInfo('Chrome',                       'chrome'          ),
    ApkMirrorInfo('Clock',                        'clockgoogle'     ),
    ApkMirrorInfo('Cloud Print',                  'cloudprint'      ),
    ApkMirrorInfo('Device Policy',                'dmagent'         ),
    ApkMirrorInfo('Docs',                         'docs'            ),
    ApkMirrorInfo('Drive',                        'drive'           ),
    ApkMirrorInfo('Earth',                        'earth'           ),
    ApkMirrorInfo('Exchange Services',            'exchangegoogle'  ),
    ApkMirrorInfo('Fitness Tracking',             'fitness',        'fit'                   ),
    ApkMirrorInfo('Gmail',                        'gmail'           ),
    ApkMirrorInfo('Google Cast Receiver',         'castreceiver'    ),
    ApkMirrorInfo('Google Contacts',              'contactsgoogle'  ),
    ApkMirrorInfo('Google Connectivity Services', 'gcs'             ),
    ApkMirrorInfo('Google Indic Keyboard',        'indic'           ),
    ApkMirrorInfo('Google Japanese Input',        'japanese'        ),
    ApkMirrorInfo('Google Keyboard',              'keyboardgoogle'  ),
    ApkMirrorInfo('Google Korean Input',          'korean'          ),
    ApkMirrorInfo('Google Now Launcher',          'googlenow'       ),
    ApkMirrorInfo('Google Pinyin Input',          'pinyin'          ),
    ApkMirrorInfo('Google Phone',                 'dialergoogle'    ),
    ApkMirrorInfo('Google Play Books',            'books'           ),
    ApkMirrorInfo('Google Play Games',            'playgames'       ),
    ApkMirrorInfo('Google Play Newsstand',        'newsstand'       ),
    ApkMirrorInfo('Google Play Movies',           'movies'          ),
    ApkMirrorInfo('Google Play Music',            'music'           ),
    ApkMirrorInfo('Google Play services',         'gmscore'         ),
    ApkMirrorInfo('Google Play Store',            'vending'         ),
    ApkMirrorInfo('Google App',                   'search',         'google-search/'        ),
    ApkMirrorInfo('Google Text-to-speech Engine', 'googletts'       ),
    ApkMirrorInfo('Google Zhuyin Input',          'zhuyin'          ),
    ApkMirrorInfo('Google+',                      'googleplus'      ),
    ApkMirrorInfo('Hangouts',                     'hangouts'        ),
    ApkMirrorInfo('Inbox',                        'inbox'           ),
    ApkMirrorInfo('Keep',                         'keep'            ),
    ApkMirrorInfo('Maps',                         'maps'            ),
    ApkMirrorInfo('Messenger',                    'messenger',      'messenger-google-inc/' ),
    ApkMirrorInfo('News & Weather',               'newswidget'      ),
    ApkMirrorInfo('Photos',                       'photos'          ),
    ApkMirrorInfo('Project Fi',                   'projectfi'       ),
    ApkMirrorInfo('Remote Control',               'remote'          ),
    ApkMirrorInfo('Sheets',                       'sheets'          ),
    ApkMirrorInfo('Slides',                       'slides'          ),
    ApkMirrorInfo('Sound Search for Google Play', 'ears'            ),
    ApkMirrorInfo('Street View',                  'street'          ),
    ApkMirrorInfo('Tags',                         'taggoogle'       ),
    ApkMirrorInfo('TalkBack',                     'talkback'        ),
    ApkMirrorInfo('Translate',                    'translate'       ),
    ### Trusted Face (facelock) is currently withheld for versioning reasons
    # ApkMirrorInfo('Trusted Face',                 'faceunlock'      ),
    ApkMirrorInfo('YouTube',                      'youtube'         )]

###################
# END: Globals    #
###################

###################
# Functions       #
###################


def downloadApkFromVersionInfo(apkVersionInfo):
    """
    downloadApkFromVersionInfo(apkVersionInfo): downloads the give APK
    """
    try:
        if os.path.exists(apkVersionInfo.apk_name):
            logging.info('Downloaded APK already exists.')
            return

        if os.path.exists(os.path.join('.', 'apkcrawler', apkVersionInfo.apk_name)):
            logging.info('Downloaded APK already exists (in ./apkcrawler/).')
            return

        if os.path.exists(os.path.join('..', 'apkcrawler', apkVersionInfo.apk_name)):
            logging.info('Downloaded APK already exists (in ../apkcrawler/).')
            return

        # Open the url
        session = requests.Session()
        r = session.get(apkVersionInfo.download_src)

        with open(apkVersionInfo.apk_name, 'wb') as local_file:
            local_file.write(r.content)
        print('{0} '.format(apkVersionInfo.apk_name)),
        sys.stdout.flush()
    except OSError:
        logging.exception('!!! Filename is not valid: "{0}"'.format(apkVersionInfo.apk_name))
# END: def downloadApkFromVersionInfo(apkVersionInfo):


def getVersionInfo(apkVersionInfo):
    """
    getVersionInfo(apkVersionInfo): Determines each versions information
    """
    html_name = apkVersionInfo.scrape_src.rsplit('/', 2)[1]
    html_name = html_name.replace('-android-apk-download', '') + '.html'
    url       = APKMIRRORBASEURL + apkVersionInfo.scrape_src
    html      = Debug.readFromFile(html_name)

    if html == '':
        session = requests.Session()
        logging.debug('Requesting3: ' + url)
        resp    = session.get(url)
        html    = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'ignore')
        Debug.writeToFile(html_name, html, resp.encoding)

    try:
        dom       = BeautifulSoup(html, 'html5lib')
        postArea  = dom.findAll('div', {'class': 'post-area'})[0]
        dl_button = postArea.findAll('a', {'type': 'button'})[1]
        blueFonts = postArea.findAll('span', {'class': 'fontBlue'})

        apkVersionInfo.download_src = dl_button['href']

        for blueFont in blueFonts:
            if blueFont.get_text() == 'File name: ':
                apkVersionInfo.apk_name = blueFont.next_sibling
            if blueFont.get_text() == 'Version: ':
                apkVersionInfo.ver = blueFont.next_sibling
    except:
        logging.exception('!!! Error parsing html from: "{0}"'.format(url))
# END: def getVersionInfo(apkVersionInfo):


def getAppVersions(apkInfo):
    """
    getAppVersions(apkInfo): Collect all versions for an applicaiton
    """
    logging.info('Fetching Information for: {0}'.format(apkInfo.apkmirror_name))

    html_name = '{0}.html'.format(apkInfo.opengapps_name)
    url       = APKMIRRORBASEURL + APKMIRRORGOOGLEURL2 + apkInfo.url
    html      = Debug.readFromFile(html_name)

    if html == '':
        session = requests.Session()
        logging.debug('Requesting2: ' + url)
        resp    = session.get(url)
        html    = resp.text
        Debug.writeToFile(html_name, html, resp.encoding)

    try:
        dom      = BeautifulSoup(html, 'html5lib')
        latest   = dom.findAll('div', {'class': 'latestWidget'})[1]
        versions = latest.findAll('div', {'class': 'latestPost'})

        dVersions = {}

        for version in versions:
            verName = version.findAll('a', {'class': 'fontBlack'})
            if verName:
                verName = verName[0]
            else:
                continue

            verText = '{0}'.format(verName.get_text().encode('ascii', 'ignore'))
            if 'beta' in verText.lower() or 'preview' in verText.lower():
                logging.info('!!! Beta or Preview Found: ' + verText)
            else:
                blues = version.findAll('span', {'class': 'fontBlue'})
                blueVer = [blue for blue in blues if 'Version' in blue.get_text()][0]
                verInfo = blueVer.findNext('strong').get_text()

                dVersions[verText] = verName['href']

                m = apkInfo.reVersion.search(verInfo)
                if m:
                    avi = ApkVersionInfo(name=verText,
                                         ver=m.group('VERNAME'),
                                         vercode=int(m.group('VERCODE')),
                                         sdk=int(m.group('SDK')),
                                         scrape_src=verName['href'])
                    apkInfo.versions.append(avi)
                else:
                    logging.info('!!! No Matchy: ' + verText)
        # END: for version in versions:

        Debug.printDictionary(dVersions)

        # Determine which versions to download
        if len(apkInfo.versions) > 0:
            maxVersionByVerCode = sorted(apkInfo.versions, key=lambda x: x.vercode)[-1]

            logging.debug('Max Version By VerCode: "{0}" ({1})'.format(maxVersionByVerCode.name, maxVersionByVerCode.ver))

            maxVersionByVerCode = maxVersionByVerCode.ver

            for v in apkInfo.versions:
                if v.ver == maxVersionByVerCode:
                    logging.info('Getting Info for: "{0}" ({1})'.format(v.name, v.scrape_src))
                    getVersionInfo(v)
                    logging.info('Downloading: "{0}"'.format(v.apk_name))
                    downloadApkFromVersionInfo(v)
                else:
                    logging.debug('Skipping: "{0}" ({1})'.format(v.name, v.scrape_src))
            # END: for v in apkInfo.versions:
        else:
            logging.info('No matching APKs found for: {0}'.format(apkInfo.apkmirror_name))
    except:
        logging.exception('!!! Error parsing html from: "{0}"'.format(url))

    logging.debug('-'*80)

# END: def getAppVersions(apkInfo):


def processCommandLine(param_list):
    """
    processCommandLine(param_list):
    """
    global requestedApkInfo

    # Check for OpenGApps from commandline
    for param in param_list:
        # Find matches
        requestedApkInfo.extend([ai for ai in allApkInfo
                                 if (ai.opengapps_name == param
                                 and ai not in requestedApkInfo)])
# END: def processCommandLine(param_list):


def main(param_list):
    """
    main():
    """
    global requestedApkInfo

    # Handle user input
    processCommandLine(param_list)

    # Do everything if no user input
    if not requestedApkInfo:
        requestedApkInfo.extend(allApkInfo)

    logging.debug([str(ai.apkmirror_name) for ai in requestedApkInfo])

    p = multiprocessing.Pool(5)
    p.map(getAppVersions, requestedApkInfo)
# END: main():

###################
# END: Functions  #
###################

if __name__ == "__main__":
    logging.basicConfig(filename = logFile, filemode = 'w', level = logLevel, format = logFormat)
    logging.getLogger("requests").setLevel(logging.WARNING)

    main(sys.argv[1:])
