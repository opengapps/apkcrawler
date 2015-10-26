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
import codecs

###################
# DEBUG VARS      #
###################

DEBUG        = False
READFROMHTML = False  # Read from file for debugging
SAVELASTHTML = False  # Write to file upon each request

###################
# END: DEBUG VARS #
###################

###################
# CLASSES         #
###################


class ApkVersionInfo(object):
    """ApkVersionInfo"""
    def __init__(self, name='', scrape_url=''):
        super(ApkVersionInfo, self).__init__()
        self.name         = name
        self.scrape_url   = scrape_url
        self.version      = ''
        self.apk_name     = ''
        self.download_url = ''

    def __lt__(self, other):
        from distutils.version import StrictVersion

        if self.version == '' or other.version == '':
            return self.name < other.name
        else:
            return StrictVersion(self.version) < StrictVersion(other.version)

    def __cmp__(self, other):
        from distutils.version import StrictVersion

        if self.version == '' or other.version == '':
            return cmp(self.name, other.name)
        else:
            return StrictVersion(self.version).__cmp__(other.version)

    def __str__(self):
        return str(self.__dict__)
# END: class ApkVersionInfo()


class ApkInfo(object):
    """ApkInfo"""
    def __init__(self, apkmirror_name='', opengapps_name='', num_used_ver='', url=''):
        super(ApkInfo, self).__init__()
        import re
        self.apkmirror_name = apkmirror_name
        self.opengapps_name = opengapps_name

        # Default naming convention (from application name to url)
        if url == '':
            self.url = apkmirror_name.lower()
            self.url = self.url.replace(' ',   '-')  # Space to dash (fairly common)
            self.url = self.url.replace(' & ', '-')  # Special case for News & Weather
            self.url = self.url.replace('+',   '')   # Special case for Google+
            self.url = self.url + '/'                # Trailing '/'
        else:
            self.url = url

        msRe = self.apkmirror_name.replace('+', '\+') + ' ' + sReVersionFmt.format('{1,' + str(num_used_ver) + '}')
        self.reVersion = re.compile(msRe)  # Special case for Google+
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
# END: class ApkInfo()

###################
# END: CLASSES    #
###################

###################
# Globals         #
###################

APKMIRRORBASEURL    = 'http://www.apkmirror.com'
APKMIRRORGOOGLEURL  = '/apk/google-inc/'
APKMIRRORGOOGLEURL2 = '/uploads/?app='

# Version RegEx String
sReVersionFmt = '(?P<VERSIONNAME>(([vR]?([A-Z]|\d+)[bQRS]?|arm|arm64|neon|x86|release|RELEASE|tv)[-.]?){0})'

# logging
logFile   = '{0}.log'.format(os.path.basename(sys.argv[0]))
logLevel  = (logging.DEBUG if DEBUG else logging.INFO)
logFormat = '%(asctime)s %(levelname)s/%(funcName)s(%(process)-5d): %(message)s'

requestedApkInfo = []
allApkInfo = [
    ApkInfo('Android Pay',                  'androidpay'          ),
    ### Android for Work App (not the core included in Open GApps)
    # ApkInfo('Android for Work App',         'androidforwork'      ),
    ApkInfo('Android System WebView',       'webviewgoogle'       ),
    ApkInfo('Calculator',                   'calculator',     '', 'google-calculator'            ),
    ApkInfo('Calendar',                     'calendargoogle'      ),
    ApkInfo('Camera',                       'cameragoogle'        ),
    ApkInfo('Chrome',                       'chrome'              ),
    ApkInfo('Clock',                        'clockgoogle'         ),
    ApkInfo('Cloud Print',                  'cloudprint'          ),
    ApkInfo('Device Policy',                'dmagent'             ),
    ApkInfo('Docs',                         'docs',           4   ),
    ApkInfo('Drive',                        'drive',          4   ),
    ApkInfo('Earth',                        'earth'               ),
    ApkInfo('Exchange Services',            'exchangegoogle'      ),
    ApkInfo('Fit',                          'fitness'             ),
    ApkInfo('Gmail',                        'gmail'               ),
    ApkInfo('Google Connectivity Services', 'gcs'                 ),
    ApkInfo('Google Hindi Input',           'hindi',          4   ),
    ApkInfo('Google Japanese Input',        'japanese',       4   ),
    ApkInfo('Google Keyboard',              'keyboardgoogle', 2   ),
    ApkInfo('Google Korean Input',          'korean',         4   ),
    ApkInfo('Google Now Launcher',          'googlenow'           ),
    ApkInfo('Google Pinyin Input',          'pinyin',         4   ),
    ApkInfo('Google Play Books',            'books'               ),
    ApkInfo('Google Play Games',            'playgames',      3   ),
    ApkInfo('Google Play Newsstand',        'newsstand'           ),
    ApkInfo('Google Play Movies',           'movies',         3   ),
    ApkInfo('Google Play Music',            'music'               ),
    ApkInfo('Google Play services',         'gmscore'             ),
    ApkInfo('Google Play Store',            'vending'             ),
    ApkInfo('Google App',                   'search',         4,  'google-search/'               ),
    ApkInfo('Google Text-to-speech Engine', 'googletts',      4   ),
    ApkInfo('Google Zhuyin Input',          'zhuyin',         4   ),
    ApkInfo('Google+',                      'googleplus',     4   ),  # or 3?
    ApkInfo('Hangouts',                     'hangouts'            ),
    ApkInfo('Keep',                         'keep'                ),
    ApkInfo('Maps',                         'maps'                ),
    ApkInfo('Messenger',                    'messenger',      '', 'messenger-google-inc/'        ),
    ApkInfo('News & Weather',               'newswidget'          ),
    ApkInfo('Photos',                       'photos'              ),
    ApkInfo('Project Fi',                   'projectfi'           ),
    ApkInfo('Sheets',                       'sheets',         4   ),
    ApkInfo('Slides',                       'slides',         4   ),
    ApkInfo('Sound Search for Google Play', 'ears',               ),
    ApkInfo('Street View',                  'street'              ),
    ApkInfo('Tags',                         'taggoogle'           ),
    ApkInfo('TalkBack',                     'talkback'            ),
    ApkInfo('Translate',                    'translate'           ),
    ### Trusted Face (facelock) is currently withheld for versioning reasons
    # ApkInfo('Trusted Face',                 'faceunlock'          ),
    ApkInfo('YouTube',                      'youtube'             )]

###################
# END: Globals    #
###################

###################
# Functions       #
###################


def printDictionary(d):
    """
    printDictionary(d): Prints well space key value pairs
    """
    maxKeyFmt = '{0: <' + str(len(max(d, key = len))) + '}'
    for k in sorted(d.keys()):
        logging.debug(maxKeyFmt.format(k) + ' - ' + d[k])
# END: def printDictionary(d):


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
        r = session.get(apkVersionInfo.download_url)

        with open(apkVersionInfo.apk_name, 'wb') as local_file:
            local_file.write(r.content)
        print('{0} '.format(apkVersionInfo.apk_name)),
        sys.stdout.flush()
    except OSError:
        logging.exception('!!! Filename is not valid: "{0}"'.format(apkVersionInfo.apk_name))
# END: def downloadApkFromVersionInfo(apkVersionInfo):


def DEBUG_readFromHtml(html_name):
    """
    DEBUG_readFromHtml():
    """
    if READFROMHTML and os.path.exists(html_name):
        with open(html_name, 'rb') as debug_file:
            return debug_file.read()
    else:
        return ''
# END: def DEBUG_readFromHtml():


def DEBUG_writeToHtml(html_name, html, encoding):
    """
    DEBUG_writeToHtml():
    """
    if SAVELASTHTML:
        try:
            with codecs.open(html_name, 'w', encoding) as debug_file:
                debug_file.write(html)
        except TypeError:
            with open(html_name, '+ab') as debug_file:
                debug_file.write(html)
# END: def DEBUG_writeToHtml():


def DEBUG_getApkInfoFromMainGooglePage():
    """
    DEBUG_getApkInfoFromMainGooglePage(): For debugging only. Collects each application's top
                                          level information for APKMirror
    """
    html_name = 'apkmirror-apk-google-inc.html'
    url       = APKMIRRORBASEURL + APKMIRRORGOOGLEURL
    html      = DEBUG_readFromHtml(html_name)

    if html == '':
        session = requests.Session()
        logging.debug('Requesting1: ' + url)
        resp = session.get(url)
        html = resp.text
        DEBUG_writeToHtml(html_name, html, resp.encoding)

    dom    = BeautifulSoup(html, 'html5lib')
    latest = dom.findAll('div', {'class': 'latestWidget'})[2]
    apps   = latest.findAll('a', {'class': 'fontBlack'})

    dApk = {}

    for app in apps:
        appText = unicodedata.normalize('NFKD', app.get_text()).encode('ascii', 'ignore')
        dApk[appText] = app['href']
    # END: for app in apps:

    printDictionary(dApk)
# END: def DEBUG_getApkInfoFromMainGooglePage():


def getVersionInfo(apkVersionInfo):
    """
    getVersionInfo(apkVersionInfo): Determines each versions information
    """
    html_name = apkVersionInfo.scrape_url.rsplit('/', 2)[1]
    html_name = html_name.replace('-android-apk-download', '') + '.html'
    url       = APKMIRRORBASEURL + apkVersionInfo.scrape_url
    html      = DEBUG_readFromHtml(html_name)

    if html == '':
        session = requests.Session()
        logging.debug('Requesting3: ' + url)
        resp    = session.get(url)
        html    = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'ignore')
        DEBUG_writeToHtml(html_name, html, resp.encoding)

    try:
        dom       = BeautifulSoup(html, 'html5lib')
        postArea  = dom.findAll('div', {'class': 'post-area'})[0]
        dl_button = postArea.findAll('a', {'type': 'button'})[1]
        blueFonts = postArea.findAll('span', {'class': 'fontBlue'})

        apkVersionInfo.download_url = dl_button['href']

        for blueFont in blueFonts:
            if blueFont.get_text() == 'File name: ':
                apkVersionInfo.apk_name = blueFont.next_sibling
            if blueFont.get_text() == 'Version: ':
                apkVersionInfo.version = blueFont.next_sibling
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
    html      = DEBUG_readFromHtml(html_name)

    if html == '':
        session = requests.Session()
        logging.debug('Requesting2: ' + url)
        resp    = session.get(url)
        html    = resp.text
        DEBUG_writeToHtml(html_name, html, resp.encoding)

    dom      = BeautifulSoup(html, 'html5lib')
    latest   = dom.findAll('div', {'class': 'latestWidget'})[1]
    versions = latest.findAll('a', {'class': 'fontBlack'})

    dVersions = {}

    for version in versions:
        verText = '"{0}"'.format(version.get_text().encode('ascii', 'ignore'))
        if 'beta' in verText.lower() or 'preview' in verText.lower():
            logging.info('!!! Beta or Preview Found: ' + verText)
        else:
            dVersions[verText] = version['href']

            m = apkInfo.reVersion.search(verText)
            if m:
                avi = ApkVersionInfo(m.group('VERSIONNAME').rstrip('-.'), version['href'])
                apkInfo.versions.append(avi)
            else:
                logging.info('!!! No Matchy: ' + verText)
    # END: for v in versions:

    printDictionary(dVersions)

    # Determine which versions to download
    if len(apkInfo.versions) > 0:
        maxVersionByName = sorted(apkInfo.versions)[-1]

        logging.debug('Max Version By Name: "{0}"'.format(maxVersionByName.name))

        for v in apkInfo.versions:
            if v.name == maxVersionByName.name:
                logging.info('Getting Info for: "{0}" ({1})'.format(v.name, v.scrape_url))
                getVersionInfo(v)
                logging.info('Downloading: "{0}"'.format(v.apk_name))
                downloadApkFromVersionInfo(v)
            else:
                logging.debug('Skipping: "{0}" ({1})'.format(v.name, v.scrape_url))
        # END: for v in apkInfo.versions:
    else:
        logging.info('No matching APKs found for: {0}'.format(apkInfo.apkmirror_name))
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

    # This was only used initially to identify the contents of allApkInfo
    # DEBUG_getApkInfoFromMainGooglePage()

    # Handle user input
    processCommandLine(param_list)

    # Do everything if no user input
    if not requestedApkInfo:
        requestedApkInfo.extend(allApkInfo)

    logging.debug([str(ai.apkmirror_name) for ai in requestedApkInfo])

    p = multiprocessing.Pool(10)
    p.map(getAppVersions, requestedApkInfo)
# END: main():

###################
# END: Functions  #
###################

if __name__ == "__main__":
    logging.basicConfig(filename = logFile, filemode = 'w', level = logLevel, format = logFormat)
    logging.getLogger("requests").setLevel(logging.WARNING)

    main(sys.argv[1:])
