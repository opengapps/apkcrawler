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
Global.report = None
Global.dlFiles     = []
Global.dlFilesBeta = []

# logging
logFile   = '{0}.log'.format(os.path.basename(__file__))
logLevel  = (logging.DEBUG if Debug.DEBUG else logging.INFO)
logFormat = '%(asctime)s %(levelname)s/%(funcName)s(%(process)-5d): %(message)s'

def downloadApk(avi, isBeta=False):
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
            Global.dlFilesBeta.append(apkname)
            logging.debug('beta: ' + ', '.join(Global.dlFilesBeta))
        else:
            tmp = Global.dlFiles
            tmp.append(apkname)
            Global.dlFiles = tmp
            # Global.dlFiles.append(apkname)
            logging.debug('reg : ' + ', '.join(Global.dlFiles))
    except OSError:
        logging.exception('!!! Filename is not valid: "{0}"'.format(apkname))
# END: def downloadApk


def checkOneApp(apkid):
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

        if Global.report.isThisApkNeeded(avi):
            downloadApk(avi)

    except ValueError:
        logging.info('{0} not supported by mobogenie ...'.format(apkid))
    except:
        logging.exception('!!! Invalid JSON from: "{0}"'.format(url))
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
