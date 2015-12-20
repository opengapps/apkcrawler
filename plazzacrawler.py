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
Global.dAllApks      = {}
Global.maxVerEachApk = {}
Global.minSdkEachApk = {}

# logging
logFile   = '{0}.log'.format(os.path.basename(sys.argv[0]))
logLevel  = (logging.DEBUG if Debug.DEBUG else logging.INFO)
logFormat = '%(asctime)s %(levelname)s/%(funcName)s(%(process)-5d): %(message)s'


def downloadApk(url,package,vercode):
    """
    downloadApk(apkInfo): Download the specified URL to APK file name
    """
    apkname = '{0}-{1}.apk'.format(package,
                                   vercode)

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

        r = session.get(url,stream=True)
        with open(apkname, 'wb') as local_file:
            for chunk in r.iter_content(1024):
                local_file.write(chunk)

        print('{0} '.format(apkname)),
        sys.stdout.flush()
    except OSError:
        logging.exception('!!! Filename is not valid: "{0}"'.format(apkname))
# END: def downloadApk


def checkOneApp(apkid):
    """
    checkOneApp(apkid):
    """
    dAllApks      = Global.dAllApks
    maxVerEachApk = Global.maxVerEachApk
    minSdkEachApk = Global.minSdkEachApk

    logging.info('Checking app: {0}'.format(apkid))

    html_name = '{0}.html'.format(apkid)
    url       = 'http://www.plazza.ir/app/' + apkid + '?hl=en'
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
        latestapk = dom.findAll('a', {'itemprop': 'downloadUrl'})[0]
        appid     = re.search('(^\/dl\/)([0-9]+)(\/1$)', latestapk['href']).group(2)
        latesturl = session.head('http://www.plazza.ir' + latestapk['href'],allow_redirects=True).url
        latestver = re.search('(_)([0-9]+)(\.apk)$', latesturl).group(2)

        #We still miss versioncode comparison here
        downloadApk(latesturl,apkid,latestver)

        #Fetching of older versions is not completed, because it requires VIP accounts
        #olderapks = dom.findAll('div', {'style': 'direction: rtl'})[0].findAll('a', {'target': '_blank'})
        #for apk in olderapks:
        #    apkver = re.search('(\/)([0-9]+)(\?.*$|$)', apk['href']).group(2) #number is either end of string or there can be an ? for extra GET parameters
        #    apkurl = session.head('http://www.plazza.ir/dl_version/' + appid + '/' + apkver + '/1',allow_redirects=True).url

    except AttributeError:
        logging.info('{0} has an invalid version in the download URL ...'.format(apkid))
    except IndexError:
        logging.info('{0} not supported by plazza.ir ...'.format(apkid))
    except:
        logging.exception('!!! Error parsing html from: "{0}"'.format(url))

# END: def checkOneApp:


def main(param_list):
    """
    main(): single parameter for report_sources.sh output
    """
    dAllApks      = Global.dAllApks
    maxVerEachApk = Global.maxVerEachApk
    minSdkEachApk = Global.minSdkEachApk

    lines = ''
    if len(param_list) == 1:
        with open(param_list[0]) as report:
            lines = report.readlines()
    else:
        lines = sys.stdin.readlines()

    dAllApks = ReportHelper.processReportSourcesOutput(lines)

    if len(dAllApks.keys()) == 0:
        print('ERROR: expecting:')
        print(' - 1 parameter (report file from output of report_sources.sh)')
        print(' or ')
        print(' - stdin from report_sources.sh')
        return

    maxVerEachApk = ReportHelper.getMaxVersionDict(dAllApks)
    minSdkEachApk = ReportHelper.getMinSdkDict(dAllApks)

    ReportHelper.showMissingApks(dAllApks, maxVerEachApk)

    keys = dAllApks.keys()

    Global.dAllApks      = dAllApks
    Global.maxVerEachApk = maxVerEachApk
    Global.minSdkEachApk = minSdkEachApk

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
