#!/usr/bin/env python

#
# Required Modules
# - requests
#

import sys
import os
import datetime
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
Global.dAllApks      = {}
Global.maxVerEachApk = {}
Global.minSdkEachApk = {}

# logging
logFile   = '{0}.log'.format(os.path.basename(sys.argv[0]))
logLevel  = (logging.DEBUG if Debug.DEBUG else logging.INFO)
logFormat = '%(asctime)s %(levelname)s/%(funcName)s(%(process)-5d): %(message)s'


def listRepo(repo, orderby=None):
    """
    listRepo(repo): Get list of all APKs in a specific store from the Aptoide API
                    and return it in JSON form
    """
    file_name = '{0}{1}.json'.format(repo, '' if not orderby else '-' + '-'.join(orderby))
    orderby   = '' if not orderby else '/orderby/' + '/'.join(orderby)
    url       = 'http://webservices.aptoide.com/webservices/listRepository/{0}{1}/json'.format(repo, orderby)
    data      = Debug.readFromFile(file_name)

    try:
        if data == '':
            session = requests.Session()
            # session.proxies = Debug.getProxy()
            logging.debug('Requesting1: ' + url)
            resp    = session.get(url)
            data    = json.loads(resp.text)
            Debug.writeToFile(file_name, json.dumps(data, sort_keys=True,
                              indent=4, separators=(',', ': ')), resp.encoding)

        if data['status'] == 'OK':
            return data
        else:
            logging.error(file_name)
    except:
        logging.exception('!!! Invalid JSON from: "{0}"'.format(url))

    return None
# END: def listRepo


def getApkInfo(repo, apkid, apkversion, options=None, doVersion1=False):
    """
    getApkInfo(repo, apkid, apkversion): Get APK specific information from the Aptoide API
                                         and return it in JSON form
    """
    version   = '1' if doVersion1 else '2'
    file_name = '{0}-{1}-{2}_{3}.json'.format(repo, apkid, apkversion, version)
    options   = '' if not options else '/options=({0})'.format(options)
    url       = 'http://webservices.aptoide.com/webservices/{0}/getApkInfo/{1}/{2}/{3}{4}/json'.format(
                version, repo, apkid, apkversion, options)
    data      = Debug.readFromFile(file_name)

    try:
        if data == '':
            session = requests.Session()
            # session.proxies = Debug.getProxy()
            logging.debug('Requesting2: ' + url)
            resp    = session.get(url)
            data    = json.loads(resp.text)
            Debug.writeToFile(file_name, json.dumps(data, sort_keys=True,
                              indent=4, separators=(',', ': ')), resp.encoding)

        if data['status'] == 'OK':
            return data
        else:
            logging.error(file_name)
    except:
        logging.exception('!!! Invalid JSON from: "{0}"'.format(url))

    return None
# END: def getApkInfo


def downloadApk(apkInfo):
    """
    downloadApk(apkInfo): Download the specified URL to APK file name
    """
    url     = apkInfo['path']

    cpu     = apkInfo.get('cpu', '')
    if cpu != '':
        cpu = '({0})'.format(cpu)

    dpi     = apkInfo.get('screenCompat', '(nodpi)')
    if dpi != '(nodpi)':
        dpi = '({0}dpi)'.format(doDpiStuff(dpi))

    apkname = '{0}_{1}-{2}_minAPI{3}{4}{5}.apk'.format(apkInfo['package'],
                                                       apkInfo['vername'].replace(' ', '_'),
                                                       apkInfo['vercode'],
                                                       apkInfo['minSdk'],
                                                       cpu, dpi)

    logging.info('Downloading "{0}" from: {1}'.format(url, apkname))

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


def doDpiStuff(screenCompat, delim='-'):
    """
    doDpiStuff(screenCompat): Convert screenCompat to a single DPI or a range of DPIs
    """
    if screenCompat == 'nodpi':
        return screenCompat

    dpis = {}
    splits = screenCompat.split(',')
    for split in splits:
        splits2 = split.split('/')
        dpis[str(splits2[1])] = ''

    return delim.join(sorted(dpis.keys()))
# END: def doDpiStuff


def doCpuStuff(cpu):
    """
    doCpuStuff(cpu): Convert CPU type to that used by OpenGApps
    """
    return {
        'armeabi'              : 'arm',
        'armeabi-v7a'          : 'arm',
        'arm64-v8a'            : 'arm64',
        'arm64-v8a,armeabi-v7a': 'arm64',
        'x86'                  : 'x86',
    }.get(cpu, 'all')
# END: def doCpuStuff


def checkOneStore(repo):
    """
    checkOneStore(repo):
    """
    dAllApks      = Global.dAllApks
    maxVerEachApk = Global.maxVerEachApk
    minSdkEachApk = Global.minSdkEachApk

    logging.info('Checking store: {0}'.format(repo))

    # Date to look back until
    today       = datetime.date.today()
    search_stop = today - datetime.timedelta(days=3)

    search_date = today
    offset = 0
    while search_date > search_stop:
        data = listRepo(repo, ('recent', '100', str(offset)))
        if data:
            # Check each apk ...
            for item in data['listing']:
                search_date = datetime.datetime.strptime(item['date'], '%Y-%m-%d').date()

                # Against the list we are looking for
                if item['apkid'] not in dAllApks.keys():
                    continue

                # Do we already have it
                if filter(lambda version: version.vercode == item['vercode'], dAllApks[item['apkid']]):
                    continue

                v = item['ver'].split(' ')[0]
                maxApkInfo = ApkVersionInfo(name=item['apkid'], ver=maxVerEachApk[item['apkid']])
                tmpApkInfo = ApkVersionInfo(name=item['apkid'], ver=v)
                # Is it >= maxVersion
                if maxApkInfo <= tmpApkInfo:
                    apkInfo = getApkInfo(repo, item['apkid'], item['ver'],
                                         options='vercode=' + str(item['vercode']))
                    if apkInfo:
                        thisSdk = int(apkInfo['apk']['minSdk'])
                        if thisSdk < minSdkEachApk[item['apkid']]:
                            logging.debug('SdkTooLow: {0}({1})'.format(item['apkid'], thisSdk))
                            continue

                        this = '{0}|{1}|{2}|{3}|{4}|{5}'.format(item['apkid'],
                                                                doCpuStuff(apkInfo['apk'].get('cpu', 'all')),
                                                                apkInfo['apk']['minSdk'],
                                                                doDpiStuff(apkInfo['apk'].get('screenCompat', 'nodpi')),
                                                                v,
                                                                item['vercode'])
                        if not filter(lambda version: version.fullString(maxVerEachApk[item['apkid']]) == this,
                                      dAllApks[item['apkid']]):
                            logging.debug(this)
                            downloadApk(apkInfo['apk'])
                    # END: if apkInfo
                # END: if item
            # END: for item
        # END: if data
        offset += 100
    # END: while
# END: def checkOneStore:


def main(param_list):
    """
    main(): single parameter for report_sources.sh output
    """
    dAllApks      = Global.dAllApks
    maxVerEachApk = Global.maxVerEachApk
    minSdkEachApk = Global.minSdkEachApk

    lines = ''
    if len(param_list) == 1:
        with open(param_list[0]) as report:
            lines = report.readlines()
    else:
        lines = sys.stdin.readlines()

    dAllApks = ReportHelper.processReportSourcesOutput(lines)

    if len(dAllApks.keys()) == 0:
        print('ERROR: expecting:')
        print(' - 1 parameter (report file from output of report_sources.sh)')
        print(' or ')
        print(' - stdin from report_sources.sh')
        return

    maxVerEachApk = ReportHelper.getMaxVersionDict(dAllApks)
    minSdkEachApk = ReportHelper.getMinSdkDict(dAllApks)

    ReportHelper.showMissingApks(dAllApks, maxVerEachApk)

    repos = ['albrtkmxxo',
             'android777',
             'apk-s',
             'aplicaciones-ceibal',
             'apps',
             'appstv',
             'austroid',
             'bazar-canaima',
             'benny09',
             'brainyideas',
             'catnamiw',
             'cesang7',
             'darkkiller',
             'denis86',
             'donvito2021',
             'draconius666',
             'eltremendo02',
             'epsil',
             'ezam-akmar',
             'grungo2407',
             'gs3passion',
             'gyjano',
             'hampoo',
             'hfk217',
             'hot105',
             'iosefirina22',
             'irishandroid',
             'jaslibertas',
             'jodean',
             'kcprophet',
             'kryss974',
             'leighakat',
             'letechest',
             'lonerfox2013',
             'ludock96',
             'mark8',
             'matandroid',
             'megas0ra',
             'metin2ventor',
             'migatronic',
             'milaupv',
             'msi8',
             'mys3',
             'new-day-apps',
             'orgia82',
             'pentacore',
             'poulpe',
             'rahullah',
             'rodrivergara',
             'ryoma3ch1z3n',
             'sandro797',
             'shotaro',
             'slapchop',
             'snah',
             'sommydany',
             'speny',
             'stein-gmg',
             'story89998',
             'tim-we',
             'tutu75',
             'vip-apk',
             'westcoastandroid',
             'yelbana2']

    Global.dAllApks      = dAllApks
    Global.maxVerEachApk = maxVerEachApk
    Global.minSdkEachApk = minSdkEachApk

    # Start checking all stores ...
    p = multiprocessing.Pool(5)
    p.map(checkOneStore, repos)

# END: main():

###################
# END: Functions  #
###################

if __name__ == "__main__":
    logging.basicConfig(filename = logFile, filemode = 'w', level = logLevel, format = logFormat)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("requesocks").setLevel(logging.WARNING)

    main(sys.argv[1:])
