#!/usr/bin/env python

#
# Required Modules
# - requests
#

import sys
import os
import re
import logging
import multiprocessing

import json

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

class MobogenieCrawler(object):
    def __init__(self, report, dlFiles=[], dlFilesBeta=[]):
        self.report      = report
        self.dlFiles     = dlFiles
        self.dlFilesBeta = dlFilesBeta

    def downloadApk(self, avi, isBeta=False):
        """
        downloadApk(apkInfo): Download the specified URL to APK file name
        """
        apkname = '{0}_{1}-{2}_minAPI{3}.apk'.format(avi.name.replace('.beta', ''),
                                                     avi.realver.replace(' ', '_'),
                                                     avi.vercode,
                                                     avi.sdk)

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
            r = session.get(avi.download_src)

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

        file_name = '{0}.json'.format(apkid)
        url       = 'http://helper.mgccw.com/nclient/sjson/detail/detailInfo.htm?apkId=' + apkid
        data      = Debug.readFromFile(file_name)

        try:
            if data == '':
                session = requests.Session()
                # session.proxies = Debug.getProxy()
                logging.debug('Requesting: ' + url)
                resp    = session.get(url,allow_redirects=False)
                if (resp.status_code) == 302:
                    raise ValueError
                data    = json.loads(resp.text)
                Debug.writeToFile(file_name, json.dumps(data, sort_keys=True,
                                  indent=4, separators=(',', ': ')), resp.encoding)

            item=data['data']['appInfo']
            avi = ApkVersionInfo(name=item['apkId'],
                                 sdk=item['sdkVersion'],
                                 ver=item['version'].split(' ')[0],
                                 vercode=item['versionCode'],
                                 download_src='http://download.mgccw.com/'+item['apkPath']
                                 )

            if self.report.isThisApkNeeded(avi):
                self.downloadApk(avi)

        except ValueError:
            logging.info('{0} not supported by mobogenie ...'.format(apkid))
        except:
            logging.exception('!!! Invalid JSON from: "{0}"'.format(url))
    # END: def checkOneApp:


    def crawl(self, threads=5):
        """
        crawl(): check all mobogenie apps
        """
        # Start checking all apkids ...
        p = multiprocessing.Pool(threads)
        p.map(unwrap_self_checkOneApp, zip([self]*len(self.report.dAllApks.keys()), self.report.dAllApks.keys()))
    # END: crawl():
# END: class MobogenieCrawler

def unwrap_self_checkOneApp(arg, **kwarg):
    return MobogenieCrawler.checkOneApp(*arg, **kwarg)

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

    crawler = MobogenieCrawler(report)
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
