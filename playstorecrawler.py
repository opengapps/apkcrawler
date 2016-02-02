#!/usr/bin/env python

import sys
import os
import logging
import multiprocessing

from googleplay import GooglePlayAPI

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

###################
# END: Globals    #
###################

###################
# Functions       #
###################

def checkPlayStore(credentials, lang="en_US", debug=False):
    """
    checkPlayStore(androidId):
    """
    playstore = GooglePlayAPI(credentials.androidId,lang,debug)
    playstore.login(credentials.email,credentials.password,credentials.authSubToken)
# END: def checkPlayStore

def getCredentials():
    '''
    getCredentials(): Retrieve Play Store credentials from the file
    '''
    credentialsfile = os.path.splitext(os.path.basename(sys.argv[0]))[0] + '.config'

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
    allCredentials = getCredentials()
    # Start checking with allCredentials
    p = multiprocessing.Pool(1)
    p.map(checkPlayStore, allCredentials)
# END: main():

###################
# END: Functions  #
###################

if __name__ == "__main__":
#    logging.basicConfig(filename = logFile, filemode = 'w', level = logLevel, format = logFormat)
#    logging.getLogger("requests").setLevel(logging.WARNING)
#    logging.getLogger("requesocks").setLevel(logging.WARNING)

    main(sys.argv[1:])
