#!/usr/bin/env python

import sys
import os
import logging
import multiprocessing
import random
import time

import httplib #renamed to http.client in python3

from googleplayapi.googleplay import GooglePlayAPI

from debug import Debug
from apkhelper import ApkVersionInfo
from reporthelper import ReportHelper

# Debug.USE_SOCKS_PROXY = True
if Debug.USE_SOCKS_PROXY:
    import requesocks as requests
else:
    import requests

###########################
# DO NOT TRY THIS AT HOME #
###########################
import requests.packages.urllib3.exceptions
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning) #suppress certificate matching warnings

###################
# CLASSES         #
###################

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
# END: class PlayStoreCredentials()

###################
# END: CLASSES    #
###################

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
Global.report      = None
Global.offerType = 1 #safe to assume for all our downloads
Global.dlFiles     = []
Global.dlFilesBeta = []

# logging
logFile   = '{0}.log'.format(os.path.basename(__file__))
logLevel  = (logging.DEBUG if Debug.DEBUG else logging.INFO)
logFormat = '%(asctime)s %(levelname)s/%(funcName)s(%(process)-5d): %(message)s'

###################
# END: Globals    #
###################

###################
# Functions       #
###################

def getApkInfo(playstore, apkid, delay):
    """
    getApkInfo(playstore, apkid): Get APK specific information from the Play Store
                                         and return it as an ApkVersionInfo object
    """
    for x in xrange(1,4): #up to three tries
        res = playstore.details(apkid)
        if res.body:
            if res.body.docV2.details.appDetails.versionCode: #if the versioncode does not exist; it is not offered as a valid download for this device by the Play Store
                avi = ApkVersionInfo(name    = res.body.docV2.docid,
                                     ver     = res.body.docV2.details.appDetails.versionString.split(' ')[0],  # not sure if we need the split here
                                     vercode = res.body.docV2.details.appDetails.versionCode,
                                     download_src = playstore
                                     )
                logging.debug('Found Play Store entry {0} {1}-{2}'.format(avi.name,avi.ver,avi.vercode))
                return avi
            else:
                logging.info('Play Store entry {0} using {1} is incompatible with the AndroidId\'s device'.format(apkid,playstore.androidId))
        elif res.status_code == httplib.NOT_FOUND:
            logging.debug('No Play Store entry {0} using {1}'.format(apkid,playstore.androidId))
        elif res.status_code == httplib.SERVICE_UNAVAILABLE:
            wait = delay*x
            logging.info('Too many sequential requests on the Play Store (503) using {0} for: {1}, waiting {2} seconds'.format(playstore.androidId,apkid,wait))
            time.sleep(wait) # wait longer with each failed try
            continue
        else:
            logging.error('Play Store entry {0} using {1} returned unknown HTTP status {2}'.format(apkid,playstore.androidId,res.status_code))
        return None #Not found, return empty
    else:
        logging.error('Play Store entry {0} using {1} failed with repetitive 503 errors'.format(apkid,playstore.androidId))
        return None #Kept receiving 503, return empty
    # END: for x
# END: def getApkInfo

def checkPlayStore(credentials, lang="en_US"):
    """
    checkPlayStore(androidId):
    """
    logging.debug('Logging in to Play Store with: ' + credentials.androidId)
    playstore = GooglePlayAPI(credentials.androidId,lang)
    if playstore.login(credentials.email,credentials.password,credentials.authSubToken):
        for apkid in Global.report.dAllApks.keys():
            wait = credentials.delay+random.randint(0, credentials.delay)
            logging.info('Pausing {0} before searching for: {1}, waiting {2} seconds'.format(playstore.androidId,apkid,wait))
            time.sleep(wait)
            avi = getApkInfo(playstore, apkid, credentials.delay)
            if avi:
                if Global.report.isThisApkNeeded(avi):
                    logging.debug('Update {0} {1}-{2}'.format(avi.name,avi.ver,avi.vercode))
                    downloadApk(avi, delay)
                else:
                    logging.debug('Skip {0} {1}-{2}'.format(avi.name,avi.ver,avi.vercode))
            #else:
                #logging.debug('No Play Store result for {0}'.format(apkid))
            # END: if avi
        # END: for apkid in Global.report.dAllApks.keys()
    else:
        logging.error('Play Store login failed for {0}'.format(credentials.androidId))
    # END: if playstore.login()
# END: def checkPlayStore

def downloadApk(avi, isBeta=False):
    """
    downloadApk(avi, isBeta): Download the specified ApkInfo from the Play Store to APK file name
    """
    apkname = '{0}_{1}-{2}.apk'.format(avi.name.replace('.beta', ''),
                                                       avi.realver.replace(' ', '_'),
                                                       avi.vercode)

    logging.info('Downloading "{0}" using: {1}'.format(apkname,avi.download_src.androidId))

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

        for x in xrange(1,4): #up to three tries
            res = avi.download_src.download(avi.name, avi.vercode, Global.offerType)
            if res.body:
                with open(apkname, 'wb') as local_file:
                    local_file.write(res.body)
            elif res.status_code == httplib.SERVICE_UNAVAILABLE:
                wait = delay*x
                logging.info('Too many sequential requests on the Play Store (503) using {0} for: {1}, waiting {2} seconds'.format(avi.download_src.androidId,avi.name,wait))
                time.sleep(wait) # wait longer with each failed try
                continue
            elif res.status_code == httplib.FORBIDDEN:
                logging.error('Play Store download of {0} using {1} is forbidden (403)'.format(apkname,avi.download_src.androidId))
            else:
                logging.error('Play Store download of {0} using {1} returned unknown HTTP status {2}'.format(apkname,avi.download_src.androidId,res.status_code))
            return None #Not downloadable, return empty
        else:
            logging.error('Play Store download of {0} using {1} failed with repetitive 503 errors'.format(apkname,avi.download_src.androidId))
        # END: for x
        return None #Kept receiving 503, return empty

        if isBeta:
            Global.dlFilesBeta.append(apkname)
            logging.debug('beta: ' + ', '.join(Global.dlFilesBeta))
        else:
            tmp = Global.dlFiles
            tmp.append(apkname)
            Global.dlFiles = tmp
            # Global.dlFiles.append(apkname)
            logging.debug('reg : ' + ', '.join(Global.dlFiles))
    except OSError:
        logging.exception('!!! Filename is not valid: "{0}"'.format(apkVersionInfo.apk_name))
# END: def downloadApk

def getCredentials():
    '''
    getCredentials(): Retrieve Play Store credentials from the file
    '''
    path = os.path.dirname(__file__)
    if path:
        path += '/'
    credentialsfile = path + os.path.splitext(os.path.basename(__file__))[0] + '.config'

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
                        raise StandardError('Malformed line in Credentials file')
    else:
        raise StandardError('Credentials file {0} does not exist'.format(credentialsfile))
    return credentials
# END: def getCredentials

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

    Global.dlFiles     = []
    Global.dlFilesBeta = []

    if len(Global.report.dAllApks.keys()) == 0:
        print('ERROR: expecting:')
        print(' - 1 parameter (report file from output of report_sources.sh)')
        print(' or ')
        print(' - stdin from report_sources.sh')
        return

    allCredentials = getCredentials()
    # Start checking with allCredentials
    p = multiprocessing.Pool(1) #TODO no multithreading activated yet
    p.map(checkPlayStore, allCredentials)

    logging.debug('Just before outputString creation')

    outputString = ' '.join(Global.dlFiles)
    if Global.dlFilesBeta:
        outputString += ' beta ' + ' '.join(Global.dlFilesBeta)

    logging.debug('Just after outputString creation')

    if outputString:
        print(outputString)
        sys.stdout.flush()

    logging.debug('Done ...')
# END: main():

###################
# END: Functions  #
###################

if __name__ == "__main__":
    logging.basicConfig(filename = logFile, filemode = 'w', level = logLevel, format = logFormat)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("requesocks").setLevel(logging.WARNING)

    main(sys.argv[1:])
