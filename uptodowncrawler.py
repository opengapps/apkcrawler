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
Global.report = None

# logging
logFile   = '{0}.log'.format(os.path.basename(sys.argv[0]))
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

def downloadApk(url,package):
    """
    downloadApk(apkInfo): Download the specified URL to APK file name
    """
    apkname = '{0}.apk'.format(package)

    logging.info('Downloading "{0}" from: {1}'.format(apkname,url))

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
        r = session.get(url, headers = user_agent)

        with open(apkname, 'wb') as local_file:
            local_file.write(r.content)
        print('{0} '.format(apkname)),
        sys.stdout.flush()
    except OSError:
        logging.exception('!!! Filename is not valid: "{0}"'.format(apkname))
# END: def downloadApk


def checkOneApp(apkid):
    """
    checkOneApp(apkid):
    """
    logging.info('Checking app: {0}'.format(apkid))

    try:
        upToDownName = allUpToDownNames[apkid]
        html_name = '{0}.html'.format(upToDownName)
        url       = 'http://' + upToDownName + '.en.uptodown.com/android/download'
        html      = Debug.readFromFile(html_name)

        if html == '':
            session = requests.Session()
            session.proxies = Debug.getProxy()
            logging.debug('Requesting: ' + url)
            resp    = session.get(url)
            html    = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'ignore')
            Debug.writeToFile(html_name, html, resp.encoding)

        try:
            dom       = BeautifulSoup(html, 'html5lib')
            latestapk = dom.findAll('iframe', {'id': 'iframe_download'})[0]['src'] #note that this url will still result in a redirect 302

            #We still miss versioncode comparison here
            downloadApk(latestapk,apkid)

            #We still miss fetching older versions

        except IndexError:
            logging.info('{0} not supported by uptodown.com ...'.format(apkid))
        except:
            logging.exception('!!! Error parsing html from: "{0}"'.format(url))
    except KeyError:
        logging.info('{0} not in uptodown.com dictionary...'.format(apkid))
# END: def checkOneApp:


def main(param_list):
    """
    main(): single parameter for report_sources.sh output
    """
    lines = ''
    if len(param_list) == 1:
        with open(param_list[0]) as report:
            lines = report.readlines()
    else:
        lines = sys.stdin.readlines()

    Global.report = ReportHelper(lines)
    keys = Global.report.dAllApks.keys()

    if len(keys) == 0:
        print('ERROR: expecting:')
        print(' - 1 parameter (report file from output of report_sources.sh)')
        print(' or ')
        print(' - stdin from report_sources.sh')
        return

    # Start checking all apkids ...
    p = multiprocessing.Pool(5)
    p.map(checkOneApp, keys)

# END: main():

###################
# END: Functions  #
###################

if __name__ == "__main__":
    logging.basicConfig(filename = logFile, filemode = 'w', level = logLevel, format = logFormat)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("requesocks").setLevel(logging.WARNING)

    main(sys.argv[1:])
