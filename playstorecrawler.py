#!/usr/bin/env python

import sys
import os
import logging
import multiprocessing

from googleplay import GooglePlayAPI

from apkhelper import ApkVersionInfo
from reporthelper import ReportHelper

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
    def __init__(self, androidId, email=None, password=None, authSubToken=None):
        super(PlayStoreCredentials, self).__init__()
        self.androidId = androidId.strip()
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
# Globals         #
###################
manager = multiprocessing.Manager()
Global  = manager.Namespace()
Global.report      = None
Global.offerType = 1 #safe to assume for all our downloads
Global.dlFiles     = []
Global.dlFilesBeta = []

###################
# END: Globals    #
###################

###################
# Functions       #
###################

def getApkInfo(playstore, apkid):
    """
    getApkInfo(playstore, apkid): Get APK specific information from the Play Store
                                         and return it as an ApkVersionInfo object
    """
    res = playstore.details(apkid)
    avi = ApkVersionInfo(name    = apkid,
                         ver     = res.docV2.details.appDetails.versionString.split(' ')[0],  # not sure if we need the split here
                         vercode = res.docV2.details.appDetails.versionCode
                         #we might want to add the playstore hanlder to version information too ?
                         )
    return avi
# END: def getApkInfo

def checkPlayStore(credentials, lang="en_US", debug=False):
    """
    checkPlayStore(androidId):
    """
    print(credentials.__dict__)
    playstore = GooglePlayAPI(credentials.androidId,lang,debug)
    playstore.login(credentials.email,credentials.password,credentials.authSubToken)
    #youtube = getApkInfo(playstore, "com.google.android.youtube")
    #downloadApk(playstore, youtube)

# END: def checkPlayStore

def downloadApk(playstore, avi, isBeta=False):
    """
    downloadApk(avi): Download the specified URL to APK file name
    """
    print(avi.__dict__)
    apkname = '{0}_{1}-{2}.apk'.format(avi.name.replace('.beta', ''),
                                                       avi.realver.replace(' ', '_'),
                                                       avi.vercode)

    logging.info('Downloading "{0}"'.format(apkname)) #maybe add here a human readable playstore api handler we are using (token or username?)

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

        with open(apkname, 'wb') as local_file:
            local_file.write(playstore.download(avi.name, avi.vercode, Global.offerType))
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
    credentialsfile = os.path.dirname(__file__)+'/'+os.path.splitext(os.path.basename(__file__))[0] + '.config'

    credentials = []
    if os.path.isfile(credentialsfile):
        with open(credentialsfile, 'r') as f:
            for line in f:
                line = line.partition('#')[0]
                if line:
                    try:
                        (androidId, email, password, authSubToken) = line.strip().split(',')
                        credentials.append(PlayStoreCredentials(androidId, email, password, authSubToken))
                    except:
                        exit('Malformed line in Credentials file')
    else:
        exit('Credentials file does not exist ({0})'.format(credentialsfile))
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
    keys = Global.report.dAllApks.keys()

    Global.dlFiles     = []
    Global.dlFilesBeta = []

    if len(keys) == 0:
        print('ERROR: expecting:')
        print(' - 1 parameter (report file from output of report_sources.sh)')
        print(' or ')
        print(' - stdin from report_sources.sh')
        return

    allCredentials = getCredentials()
    # Start checking with allCredentials
    p = multiprocessing.Pool(1)
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
#    logging.basicConfig(filename = logFile, filemode = 'w', level = logLevel, format = logFormat)
#    logging.getLogger("requests").setLevel(logging.WARNING)
#    logging.getLogger("requesocks").setLevel(logging.WARNING)

    main(sys.argv[1:])
