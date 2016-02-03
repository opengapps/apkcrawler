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
logFile   = '{0}.log'.format(os.path.basename(__file__))
logLevel  = (logging.DEBUG if Debug.DEBUG else logging.INFO)
logFormat = '%(asctime)s %(levelname)s/%(funcName)s(%(process)-5d): %(message)s'


def getUrlFromRedirect(apkname, url):
    """
    getUrlFromRedirect(url):
    """
    html_name = '{0}_redirect.html'.format(apkname)
    html      = Debug.readFromFile(html_name)
    link      = ''

    if html == '':
        session = requests.Session()
        session.proxies = Debug.getProxy()
        logging.debug('Requesting2: ' + url)
        resp    = session.get(url)
        html    = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'ignore')
        Debug.writeToFile(html_name, html, resp.encoding)

    try:
        dom  = BeautifulSoup(html, 'html5lib')
        link = dom.findAll('span', {'class': 'glyphicon glyphicon-cloud-download'})[0].parent['href']
    except:
        logging.exception('!!! Error parsing html from: "{0}"'.format(url))

    return link
# END: def getUrlFromRedirect:


def downloadApk(apkInfo):
    """
    downloadApk(apkInfo): Download the specified URL to APK file name
    """
    apkname = '{0}_{1}-{2}_minAPI{3}.apk'.format(apkInfo.name,
                                                 apkInfo.ver,
                                                 apkInfo.vercode,
                                                 apkInfo.sdk)

    url     = getUrlFromRedirect(apkname, apkInfo.download_url)
    if url == '':
        logging.error('Unable to determine redirect url for ' + apkname)
        return

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
        r = session.get(url)

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

    html_name = '{0}.html'.format(apkid)
    url       = 'http://apk-dl.com/' + apkid
    html      = Debug.readFromFile(html_name)

    if html == '':
        session = requests.Session()
        session.proxies = Debug.getProxy()
        logging.debug('Requesting: ' + url)
        resp    = session.get(url)
        html    = unicodedata.normalize('NFKD', resp.text).encode('ascii', 'ignore')
        Debug.writeToFile(html_name, html, resp.encoding)

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
            dApk['url'] = 'http:' + apk.find('a', {'class': 'btn btn-success'})['href']

            Debug.printDictionary(dApk)

            if 'Version' in dApk and 'RequiresAndroid' in dApk:
                (trash, sdk) = dApk['RequiresAndroid'].split('API:', 1)
                sdk = sdk[0:-1]
                (ver, vercode) = dApk['Version'].split('(Code:', 1)
                ver     = ver.split('(', 1)[0]
                vercode = vercode[0:-1]

                avi = ApkVersionInfo(name=apkid,
                                     #arch='',
                                     sdk=sdk,
                                     #dpi='',
                                     ver=ver,
                                     vercode=vercode,
                                     #scrape_url=''
                                     )
                avi.download_url = dApk['url']

                if Global.report.isThisApkNeeded(avi):
                    downloadApk(avi)

    except IndexError:
        logging.info('{0} not supported by apk-dl.com ...'.format(apkid))
    except:
        logging.exception('!!! Error parsing html from: "{0}"'.format(url))

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
