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
    def __init__(self, androidId, sdk=24, delay=60, email=None, password=None, authSubToken=None):
        super(PlayStoreCredentials, self).__init__()
        self.androidId = androidId.strip()
        if sdk:
            self.sdk = int(sdk)
        else:
            self.sdk = 24
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

    def checkPlayStore(self, credentials, lang="en_US"):
        """
        checkPlayStore(androidId):
        """
        filenames = []
        logging.debug('Logging in to Play Store with: ' + credentials.androidId)
        playstore = GooglePlayAPI(credentials.androidId, lang)
        if playstore.login(authSubToken=credentials.authSubToken):
            logging.info('{0} searches Play in {1} seconds'.format(credentials.androidId, credentials.delay))
            time.sleep(credentials.delay)

            if 'com.android.vending' in self.report.getAllApkIds():
                for storeApk in self.report.dAllApks['com.android.vending']:
                    try:
                        if storeApk.extraname and storeApk.extraname.endswith('leanback'):
                            devicename = 'fugu'
                        else:
                            devicename = 'sailfish'
                        logging.debug('{0} VendingAPK: vername={1}, vercode={2}, devicename={3}'.format(credentials.androidId, storeApk.ver, storeApk.vercode, devicename))
                        playvercode = playstore.playUpdate(storeApk.ver, str(storeApk.vercode))
                        if playvercode:
                            logging.debug('{0} Play Store update {1}'.format(credentials.androidId, playvercode))
                            avi = ApkVersionInfo(name        ='com.android.vending',
                                                 vercode     =playvercode,
                                                 download_src=playstore,
                                                 crawler_name=self.__class__.__name__
                                                 )
                            filenames.append(self.downloadApk(avi, credentials.delay + random.randint(0, credentials.delay), agentvername=storeApk.ver, agentvercode=str(storeApk.vercode), devicename=devicename))
                            logging.info('{0} pauses {1} seconds before continuing'.format(credentials.androidId, credentials.delay))
                            time.sleep(credentials.delay)
                    except:
                        logging.exception('!!! playstore.playUpdate({0}, {1}) exception ...'.format(storeApk.ver, storeApk.vercode))
                    # END: try
                # END: for storeApk
            else:
                logging.debug('{0} vending apk not in report'.format(credentials.androidId))

            logging.debug('{0} - {1}'.format(credentials.sdk, self.report.getAllApkIds(playstoreCaps=True)))
            res = playstore.bulkDetails(self.report.getAllApkIds(playstoreCaps=True), credentials.sdk)

            if res and res.status_code == http.client.OK and res.body:
                for app in res.body.entry:
                    if app.doc and app.doc.docid:
                        avi = ApkVersionInfo(name        =app.doc.docid,
                                             vercode     =app.doc.details.appDetails.versionCode,
                                             download_src=playstore,
                                             crawler_name=self.__class__.__name__
                                             )
                        if self.report.isThisApkNeeded(avi):
                            logging.debug('{0} Update {1}-{2} (Uploaddate {3})'.format(playstore.androidId, avi.name, avi.vercode, app.doc.details.appDetails.uploadDate))
                            filenames.append(self.downloadApk(avi, credentials.delay + random.randint(0, credentials.delay)))
                        else:
                            logging.debug('{0} Skip {1}-{2} (Uploaddate {3})'.format(playstore.androidId, avi.name, avi.vercode, app.doc.details.appDetails.uploadDate))
                    else:
                        logging.debug('{0} Empty search entry'.format(playstore.androidId))
                        continue
            else:
                logging.error('{0} Error querying Play Store, status {1}: {2}'.format(playstore.androidId, credentials.sdk, res.status_code))
                return None  # Not found, return empty
        else:
            logging.error('Play Store login failed for {0}'.format(credentials.androidId))
        # END: if playstore.login()
        return filenames
    # END: def checkPlayStore

    def downloadApk(self, avi, delay, isBeta=False, agentvername=None, agentvercode=None, devicename="sailfish"):
        """
        downloadApk(avi, delay, isBeta): Download the specified ApkInfo from the Play Store to APK file name
        """
        apkname = ('beta.' if isBeta else '') + avi.getFilename()

        try:
            if os.path.exists(apkname):
                logging.info('{0} File {1} already exists'.format(avi.download_src.androidId, apkname))
                return

            if os.path.exists(os.path.join('.', 'apkcrawler', apkname)):
                logging.info('{0} File {1} already exists (in ./apkcrawler/)'.format(avi.download_src.androidId, apkname))
                return

            if os.path.exists(os.path.join('..', 'apkcrawler', apkname)):
                logging.info('{0} File {1} already exists (in ../apkcrawler/)'.format(avi.download_src.androidId, apkname))
                return

            logging.info('{0} downloads "{1}" in {2} seconds'.format(avi.download_src.androidId, apkname, delay))
            time.sleep(delay)

            # File might have been dowloaded during our wait, check again
            if os.path.exists(apkname):
                logging.info('{0} File {1} already exists'.format(avi.download_src.androidId, apkname))
                return

            if os.path.exists(os.path.join('.', 'apkcrawler', apkname)):
                logging.info('{0} File {1} already exists (in ./apkcrawler/)'.format(avi.download_src.androidId, apkname))
                return

            if os.path.exists(os.path.join('..', 'apkcrawler', apkname)):
                logging.info('{0} File {1} already exists (in ../apkcrawler/)'.format(avi.download_src.androidId, apkname))
                return

            for x in range(1, 4):  # up to three tries
                res = avi.download_src.download(avi.name, avi.vercode, Global.offerType, agentvername, agentvercode, devicename)
                if res.body:
                    with open(apkname, 'wb') as local_file:
                        local_file.write(res.body)
                    logging.debug(('beta:' if isBeta else 'reg :') + apkname)
                    return       (('beta:' if isBeta else ''     ) + apkname)
                elif res.status_code == http.client.SERVICE_UNAVAILABLE:
                    wait = delay * x
                    logging.info('{0} too many sequential requests on the Play Store (503) downloading {1}: waiting {2} seconds'.format(avi.download_src.androidId, apkname, wait))
                    time.sleep(wait)  # wait longer with each failed try
                    continue
                elif res.status_code == http.client.FORBIDDEN:
                    logging.error('{0} dowloading {1} is forbidden (403)'.format(avi.download_src.androidId, apkname))
                    return  # Nope, won't happen
                else:
                    logging.error('{0} downloading {1} returned unknown HTTP status {2}'.format(avi.download_src.androidId, apkname, res.status_code))
                    return  # Nope, won't happen
            else:
                logging.error('{0} downloading {1} failed with repetitive 503 errors'.format(avi.download_src.androidId, apkname))
                return  # Kept receiving 503, return empty
            # END: for x

        except OSError:
            logging.exception('!!! Filename is not valid: "{0}"'.format(apkname))
            return
    # END: def downloadApk

    def crawl(self, threads=4):
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
    sReCredentials = '^\s*(?P<ANDROIDID>[^#,]*),\s*(?P<SDK>[^#,]*),\s*(?P<DELAY>[^#,]*),\s*(?P<EMAIL>[^#,]*),\s*(?P<PASSWORD>[^#,]*),\s*(?P<TOKEN>[^\s]*)(\s*#.*)?$'
    reCredentials  = re.compile(sReCredentials)
    tokendelay = 0
    credentials = []
    if os.path.isfile(credentialsfile):
        with open(credentialsfile, 'r') as f:
            lines = f.readlines()
        for line in lines:
            if line:
                try:
                    m = reCredentials.match(line)
                    if m:
                        androidId = m.group('ANDROIDID')
                        sdk       = m.group('SDK')
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
                            credentials.append(PlayStoreCredentials(androidId, sdk, delay, email, password, token))
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

def updateTokenCredentials(credentialsfile, androidId, sdk, delay, email, password, token=''):
    '''
    updateTokenCredentials(): update the authToken stored in the Credentialsfile for the original line
     Quickly opens the file, changes the line and writes it. Locking is short and should be safe for intermediary changes.
    '''
    sReCredentials = '(?P<ID>\s*' + androidId + ',\s*' + sdk + ',\s*' + delay + ',\s*' + email + ',\s*' + password + ',\s*)(?P<TOKEN>[^\s#]*)(?P<COMMENT>\s*#.*)?'
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
                        if result[5:] not in beta:
                            beta.append(result[5:])
                    else:
                        if result not in nonbeta:
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
