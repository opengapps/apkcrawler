#!/usr/bin/env python3

import logging
import multiprocessing
import os
import random
import re
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
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)  # suppress certificate matching warnings

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
                                         download_src=playstore,
                                         crawler_name=self.__class__.__name__
                                         )
                    logging.debug('Found Play Store entry {0} {1}-{2}'.format(avi.name, avi.ver, avi.vercode))
                    return avi
                else:
                    logging.info('{0} is incompatible for {1}'.format(playstore.androidId, apkid))
            elif res.status_code == http.client.NOT_FOUND:
                logging.debug('{0} cannot find {1}'.format(playstore.androidId, apkid))
            elif res.status_code == http.client.SERVICE_UNAVAILABLE:
                wait = delay * x
                logging.info('{0} too many sequential requests for {1}, paused for {2} seconds'.format(playstore.androidId, apkid, wait))
                time.sleep(wait)  # wait longer with each failed try
                continue
            else:
                logging.error('{0} unknown HTTP status for {1}: {2}'.format(playstore.androidId, apkid, res.status_code))
            return None  # Not found, return empty
        else:
            logging.error('{0} repetitive error 503 for {1}'.format(playstore.androidId, apkid))
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
        if playstore.login(authSubToken=credentials.authSubToken):
            for apkid in random.sample(list(self.report.getAllApkIds()), len(list(self.report.getAllApkIds()))):  # Shuffle the list, we want each crawler to search in a randomized order
                wait = credentials.delay + random.randint(0, credentials.delay)
                logging.info('{0} searches for {1}, paused for {2} seconds'.format(playstore.androidId, apkid, wait))
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
            # END: for apkid in report.getAllApkIds()
        else:
            logging.error('Play Store login failed for {0}'.format(credentials.androidId))
        # END: if playstore.login()
        return filenames
    # END: def checkPlayStore

    def downloadApk(self, avi, delay, isBeta=False):
        """
        downloadApk(avi, delay, isBeta): Download the specified ApkInfo from the Play Store to APK file name
        """
        apkname = ('beta.' if isBeta else '') + avi.getFilename()

        logging.info('{0} downloads "{1}"'.format(avi.download_src.androidId, apkname))

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
                    logging.debug(('beta:' if isBeta else 'reg :') + apkname)
                    return       (('beta:' if isBeta else ''     ) + apkname)
                elif res.status_code == http.client.SERVICE_UNAVAILABLE:
                    wait = delay * x
                    logging.info('Too many sequential requests on the Play Store (503) using {0} for: {1}, waiting {2} seconds'.format(avi.download_src.androidId, avi.name, wait))
                    time.sleep(wait)  # wait longer with each failed try
                    continue
                elif res.status_code == http.client.FORBIDDEN:
                    logging.error('Play Store download of {0} using {1} is forbidden (403)'.format(apkname, avi.download_src.androidId))
                    return  # Nope, won't happen
                else:
                    logging.error('Play Store download of {0} using {1} returned unknown HTTP status {2}'.format(apkname, avi.download_src.androidId, res.status_code))
            else:
                logging.error('Play Store download of {0} using {1} failed with repetitive 503 errors'.format(apkname, avi.download_src.androidId))
                return  # Kept receiving 503, return empty
            # END: for x

        except OSError:
            logging.exception('!!! Filename is not valid: "{0}"'.format(apkname))
            return
    # END: def downloadApk

    def crawl(self, threads=6):
        """
        crawl(): check all PlayStores
        """
        path = os.path.dirname(__file__)
        if path:
            path += '/'
        credentialsfile = path + os.path.splitext(os.path.basename(__file__))[0] + '.config'
        stores = getCredentials(credentialsfile)
        p = multiprocessing.Pool(processes=threads, maxtasksperchild=5)  # Run only 5 tasks before re-creating the process
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
    sReCredentials = '^\s*(?P<ANDROIDID>[^#,]*),\s*(?P<DELAY>[^#,]*),\s*(?P<EMAIL>[^#,]*),\s*(?P<PASSWORD>[^#,]*),\s*(?P<TOKEN>[^#,]*)(#.*)?$'
    reCredentials  = re.compile(sReCredentials)
    tokendelay = 0
    credentials = []
    if os.path.isfile(credentialsfile):
        with open(credentialsfile, 'r') as f:
            for line in f:
                if line:
                    try:
                        m = reCredentials.match(line)
                        if m:
                            androidId = m.group('ANDROIDID')
                            delay     = m.group('DELAY')
                            email     = m.group('EMAIL')
                            password  = m.group('PASSWORD')
                            token     = m.group('TOKEN')
                            logging.info('Found credentials for: {0}'.format(androidId))
                            if not token:
                                logging.info('{0} lacks authToken'.format(androidId))
                                if tokendelay:
                                    logging.info('Wait {0} seconds before processing anymore tokens'.format(delay))
                                    time.sleep(tokendelay)
                                token = getToken(androidId, email, password)
                                if token:
                                    logging.info('{0} writing authToken to config to {1}'.format(androidId, credentialsfile))
                                    updateTokenCredentials(credentialsfile, androidId, delay, email, password, token)
                                else:
                                    logging.error('{0} authToken retrieval failed'.format(androidId))
                                tokendelay = int(delay)  # we don't want to fetch tokens too quickly after one another
                            if token:
                                credentials.append(PlayStoreCredentials(androidId, delay, email, password, token))
                            else:
                                logging.error('{0} has no valid token and will not be crawled'.format(androidId))
                    except:
                        raise CredentialsException('Malformed line in Credentials file', credentialsfile)
    else:
        raise CredentialsException('Credentials file does not exist', credentialsfile)
    return credentials
# END: def getCredentials

def getToken(androidId, email, password, lang="en_US"):
    '''
    getToken(): Retrieve a Play Store authToken
    '''
    logging.info('{0} requests authToken'.format(androidId))
    return GooglePlayAPI(androidId, lang).login(email, password)
# END: def getToken

def updateTokenCredentials(credentialsfile, androidId, delay, email, password, token=''):
    '''
    updateTokenCredentials(): update the authToken stored in the Credentialsfile for the original line
     Quickly opens the file, changes the line and writes it. Locking is short and should be safe for intermediary changes.
    '''
    sReCredentials = '(?P<ID>\s*' + androidId + ',\s*' + delay + ',\s*' + email + ',\s*' + password + ',\s*)(?P<TOKEN>[^#,]*)(?P<COMMENT>#.*)?'
    reCredentials  = re.compile(sReCredentials)

    if os.path.isfile(credentialsfile):
        file_handle = open(credentialsfile, 'r')
        file_string = file_handle.read()
        file_handle.close()

        file_string = (reCredentials.sub('\g<ID>' + token + '\g<COMMENT>', file_string))

        file_handle = open(credentialsfile, 'w')
        file_handle.write(file_string)
        file_handle.close()
# END: def updateTokenCredentials

nonbeta = []
beta    = []


def unwrap_callback(results):
    for resultlist in results:
        if resultlist:
            for result in resultlist:
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

    if len(list(report.getAllApkIds())) == 0:
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
