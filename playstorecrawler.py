#!/usr/bin/env python3

import logging
import multiprocessing
import os
import random
import requests
import sys
import time

import http.client

from googleplayapi.googleplay import GooglePlayAPI

from debug import Debug
from apkhelper import ApkVersionInfo
from reporthelper import ReportHelper

###########################
# DO NOT TRY THIS AT HOME #
###########################
import requests.packages.urllib3.exceptions
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning) #suppress certificate matching warnings

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
Global.offerType = 1  # safe to assume for all our downloads

# logging
logFile   = '{0}.log'.format(os.path.basename(__file__))
logLevel  = (logging.DEBUG if Debug.DEBUG else logging.INFO)
logFormat = '%(asctime)s %(levelname)s/%(funcName)s(%(process)-5d): %(message)s'


class PlayStoreCredentials(object):
    """PlayStoreCredentials"""
    def __init__(self, androidId, delay=60, email=None, password=None, authSubToken=None):
        super(PlayStoreCredentials, self).__init__()
        self.androidId = androidId.strip()
        if delay:
            self.delay = int(delay)
        else:
            self.delay = 60
        if email:
            self.email = email.strip()
        else:
            self.email = None
        if password:
            self.password = password.strip()
        else:
            self.password = None
        if authSubToken:
            self.authSubToken = authSubToken.strip()
        else:
            self.authSubToken = None

    def __str__(self):
        return str(self.androidId)
# END: class PlayStoreCredentials


class PlayStoreCrawler(object):
    def __init__(self, report, dlFiles=[], dlFilesBeta=[]):
        self.report      = report
        self.dlFiles     = dlFiles
        self.dlFilesBeta = dlFilesBeta

    def getApkInfo(self, playstore, apkid, delay):
        """
        getApkInfo(playstore, apkid): Get APK specific information from the Play Store
                                             and return it as an ApkVersionInfo object
        """
        for x in range(1, 4):  # up to three tries
            res = playstore.details(apkid)
            if res.body:
                if res.body.docV2.details.appDetails.versionCode:  # if the versioncode does not exist; it is not offered as a valid download for this device by the Play Store
                    avi = ApkVersionInfo(name        =res.body.docV2.docid,
                                         ver         =res.body.docV2.details.appDetails.versionString.split(' ')[0],  # not sure if we need the split here
                                         vercode     =res.body.docV2.details.appDetails.versionCode,
                                         download_src=playstore
                                         )
                    logging.debug('Found Play Store entry {0} {1}-{2}'.format(avi.name, avi.ver, avi.vercode))
                    return avi
                else:
                    logging.info('Play Store entry {0} using {1} is incompatible with the AndroidId\'s device'.format(apkid, playstore.androidId))
            elif res.status_code == http.client.NOT_FOUND:
                logging.debug('No Play Store entry {0} using {1}'.format(apkid, playstore.androidId))
            elif res.status_code == http.client.SERVICE_UNAVAILABLE:
                wait = delay * x
                logging.info('Too many sequential requests on the Play Store (503) using {0} for: {1}, waiting {2} seconds'.format(playstore.androidId, apkid, wait))
                time.sleep(wait)  # wait longer with each failed try
                continue
            else:
                logging.error('Play Store entry {0} using {1} returned unknown HTTP status {2}'.format(apkid, playstore.androidId, res.status_code))
            return None  # Not found, return empty
        else:
            logging.error('Play Store entry {0} using {1} failed with repetitive 503 errors'.format(apkid, playstore.androidId))
            return None  # Kept receiving 503, return empty
        # END: for x
    # END: def getApkInfo

    def checkPlayStore(self, credentials, lang="en_US"):
        """
        checkPlayStore(androidId):
        """
        filenames = []
        logging.debug('Logging in to Play Store with: ' + credentials.androidId)
        playstore = GooglePlayAPI(credentials.androidId, lang)
        if playstore.login(credentials.email, credentials.password, credentials.authSubToken):
            for apkid in random.sample(list(self.report.dAllApks.keys()), len(list(self.report.dAllApks.keys()))):  # Shuffle the list, we want each crawler to search in a randomized order
                wait = credentials.delay + random.randint(0, credentials.delay)
                logging.info('Pausing {0} before searching for: {1}, waiting {2} seconds'.format(playstore.androidId, apkid, wait))
                time.sleep(wait)
                avi = self.getApkInfo(playstore, apkid, credentials.delay)
                if avi:
                    if self.report.isThisApkNeeded(avi):
                        logging.debug('Update {0} {1}-{2}'.format(avi.name, avi.ver, avi.vercode))
                        filenames.append(self.downloadApk(avi, credentials.delay))
                    else:
                        logging.debug('Skip {0} {1}-{2}'.format(avi.name, avi.ver, avi.vercode))
                # else:
                    # logging.debug('No Play Store result for {0}'.format(apkid))
                # END: if avi
            # END: for apkid in report.dAllApks.keys()
        else:
            logging.error('Play Store login failed for {0}'.format(credentials.androidId))
        # END: if playstore.login()
        return filenames
    # END: def checkPlayStore

    def downloadApk(self, avi, delay, isBeta=False):
        """
        downloadApk(avi, delay, isBeta): Download the specified ApkInfo from the Play Store to APK file name
        """
        apkname = '{0}_{1}-{2}.apk'.format(avi.name.replace('.beta', ''),
                                           avi.realver.replace(' ', '_'),
                                           avi.vercode)

        logging.info('Downloading "{0}" using: {1}'.format(apkname, avi.download_src.androidId))

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

            for x in range(1, 4):  # up to three tries
                res = avi.download_src.download(avi.name, avi.vercode, Global.offerType)
                if res.body:
                    with open(apkname, 'wb') as local_file:
                        local_file.write(res.body)
                elif res.status_code == http.client.SERVICE_UNAVAILABLE:
                    wait = delay * x
                    logging.info('Too many sequential requests on the Play Store (503) using {0} for: {1}, waiting {2} seconds'.format(avi.download_src.androidId, avi.name, wait))
                    time.sleep(wait)  # wait longer with each failed try
                    continue
                elif res.status_code == http.client.FORBIDDEN:
                    logging.error('Play Store download of {0} using {1} is forbidden (403)'.format(apkname, avi.download_src.androidId))
                else:
                    logging.error('Play Store download of {0} using {1} returned unknown HTTP status {2}'.format(apkname, avi.download_src.androidId, res.status_code))
                return None  # Not downloadable, return empty
            else:
                logging.error('Play Store download of {0} using {1} failed with repetitive 503 errors'.format(apkname, avi.download_src.androidId))
                return None  # Kept receiving 503, return empty
            # END: for x

            logging.debug(('beta:' if isBeta else 'reg :') + apkname)
            return       (('beta:' if isBeta else ''     ) + apkname)
        except OSError:
            logging.exception('!!! Filename is not valid: "{0}"'.format(apkVersionInfo.apk_name))
    # END: def downloadApk

    def crawl(self, threads=5):
        """
        crawl(): check all PlayStores
        """
        path = os.path.dirname(__file__)
        if path:
            path += '/'
        credentialsfile = path + os.path.splitext(os.path.basename(__file__))[0] + '.config'

        stores = getCredentials(credentialsfile)
        p = multiprocessing.Pool(threads)
        r = p.map_async(unwrap_self_checkPlayStore, list(zip([self] * len(stores), stores)), callback=unwrap_callback)
        r.wait()
        (self.dlFiles, self.dlFilesBeta) = unwrap_getresults()
    # END: crawl():
# END: class PlayStoreCrawler


class CredentialsException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


def getCredentials(credentialsfile):
    '''
    getCredentials(): Retrieve Play Store credentials from the file
    '''
    credentials = []
    if os.path.isfile(credentialsfile):
        with open(credentialsfile, 'r') as f:
            for line in f:
                line = line.partition('#')[0]
                if line:
                    try:
                        (androidId, delay, email, password, authSubToken) = line.strip().split(',')
                        logging.info('Found credentials for: ' + androidId)
                        credentials.append(PlayStoreCredentials(androidId, delay, email, password, authSubToken))
                    except:
                        pass
                        raise CredentialsException('Malformed line in Credentials file', credentialsfile)
    else:
        pass
        raise CredentialsException('Credentials file does not exist', credentialsfile)
    return credentials
# END: def getCredentials

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


def unwrap_self_checkPlayStore(arg, **kwarg):
    return PlayStoreCrawler.checkPlayStore(*arg, **kwarg)


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

    if len(list(report.dAllApks.keys())) == 0:
        print('ERROR: expecting:')
        print(' - 1 parameter (report file from output of report_sources.sh)')
        print(' or ')
        print(' - stdin from report_sources.sh')
        exit(1)

    crawler = PlayStoreCrawler(report)
    crawler.crawl()

    outputString = ' '.join(crawler.dlFiles)
    if crawler.dlFilesBeta:
        outputString += ' beta ' + ' '.join(crawler.dlFilesBeta)

    if outputString:
        print(outputString)
        sys.stdout.flush()

    logging.debug('Done ...')
