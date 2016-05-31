#!/usr/bin/env python3

#
# Required Modules
# - requests
#

import json
import http.client
import logging
import multiprocessing
import os
import re
import requests
import sys

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
            r = session.get(avi.download_src)

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

        file_name = '{0}.json'.format(apkid)
        url       = 'http://helper.mgccw.com/nclient/sjson/detail/detailInfo.htm?apkId=' + apkid
        data      = Debug.readFromFile(file_name)

        try:
            if data == '':
                session = requests.Session()
                logging.debug('Requesting: ' + url)
                resp    = session.get(url, allow_redirects=False)
                if (resp.status_code) == http.client.FOUND:
                    raise ValueError
                data    = json.loads(resp.text)
                Debug.writeToFile(file_name, json.dumps(data, sort_keys=True,
                                  indent=4, separators=(',', ': ')), resp.encoding)

            item = data['data']['appInfo']
            avi = ApkVersionInfo(name=item['apkId'],
                                 sdk=item['sdkVersion'],
                                 ver=item['version'].split(' ')[0],
                                 vercode=item['versionCode'],
                                 download_src='http://download.mgccw.com/' + item['apkPath'],
                                 crawler_name=self.__class__.__name__
                                 )

            if self.report.isThisApkNeeded(avi):
                return self.downloadApk(avi)

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
        p = multiprocessing.Pool(processes=threads, maxtasksperchild=5)  # Run only 5 tasks before re-placing the process
        r = p.map_async(unwrap_self_checkOneApp, list(zip([self] * len(list(self.report.getAllApkIds())), list(self.report.getAllApkIds()))), callback=unwrap_callback)
        r.wait()
        (self.dlFiles, self.dlFilesBeta) = unwrap_getresults()
    # END: crawl():
# END: class MobogenieCrawler

nonbeta = []
beta    = []


def unwrap_callback(results):
    for result in results:
        if result:
            if result.startswith('beta:'):
                beta.append(result[5:])
            else:
                nonbeta.append(result)


def unwrap_getresults():
    return (nonbeta, beta)


def unwrap_self_checkOneApp(arg, **kwarg):
    return MobogenieCrawler.checkOneApp(*arg, **kwarg)


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

    crawler = MobogenieCrawler(report)
    crawler.crawl()

    outputString = ' '.join(crawler.dlFiles)
    if crawler.dlFilesBeta:
        outputString += ' beta ' + ' '.join(crawler.dlFilesBeta)

    if outputString:
        print(outputString)
        sys.stdout.flush()

    logging.debug('Done ...')
