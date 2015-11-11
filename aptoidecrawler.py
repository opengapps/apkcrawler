#!/usr/bin/env python

#
# Required Modules
# - requests
#

import sys
import os
import datetime
import re
import logging
import multiprocessing

import json
import requests

from debug import Debug

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
# CLASSES         #
###################


class ApkVersionInfo(object):
    """ApkVersionInfo"""
    def __init__(self, name='', arch='', sdk='', dpi='', ver='', vercode=''):
        super(ApkVersionInfo, self).__init__()

        sName  = '^(?P<name>.*)\.leanback$'
        reName = re.compile(sName)

        sVer = '^(?P<ver>.*)(?P<extra>[-.](leanback|tv|arm|arm\.arm_neon|armeabi-v7a|arm64|arm64-v8a|x86|large|small))$'
        reVer = re.compile(sVer)

        self.name     = name
        self.maxname  = name  # used for max versions
        self.arch     = arch
        self.sdk      = sdk
        self.dpi      = dpi
        self.ver      = ver
        self.realver  = None  # used for full versions
        self.vercode  = vercode

        m = reName.match(self.maxname)
        if m:
            self.maxname = m.group('name')

        if 'com.google.android.apps.docs' in self.name:
            self.realver = self.ver[-3:]

        m = reVer.match(self.ver)
        if m:
            self.ver     = m.group('ver')
            self.realver = m.group('extra')

    def fullString(self, max):
        return '{0}|{1}|{2}|{3}|{4}{5}|{6}'.format(self.name,
                                                   self.arch,
                                                   self.sdk,
                                                   self.dpi,
                                                   max,
                                                   self.realver if self.realver else '',
                                                   self.vercode )

    def __lt__(self, other):
        return self.__cmp__(other) == -1

    def __cmp__(self, other):
        if self.ver == '' or other.ver == '':
            logging.error('AVI.cmp(): self.ver or other.ver is empty [{0},{1}]'.format(self.ver, other.ver))
            return cmp(self.name, other.name)
        else:
            import re

            # Make blank-->'0', replace - with . and split into parts
            p1 = [int(x if x != '' else '0') for x in re.sub('[A-Za-z]+', '',  self.ver.replace('-', '.')).split('.')]
            p2 = [int(x if x != '' else '0') for x in re.sub('[A-Za-z]+', '', other.ver.replace('-', '.')).split('.')]

            # fill up the shorter version with zeros ...
            lendiff = len(p1) - len(p2)
            if lendiff > 0:
                p2.extend([0] * lendiff)
            elif lendiff < 0:
                p1.extend([0] * (-lendiff))

            for i, p in enumerate(p1):
                ret = cmp(p, p2[i])
                if ret:
                    return ret
            return 0
    # END: def cmp:

    def __str__(self):
        return str(self.__dict__)
# END: class ApkVersionInfo()

###################
# END: CLASSES    #
###################

###################
# Globals         #
###################

dAllApks      = {}
maxVerEachApk = {}
minSdkEachApk = {}

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

    if data == '':
        session = requests.Session()
        logging.debug('Requesting1: ' + url)
        resp    = session.get(url)
        data    = resp.json()
        Debug.writeToFile(file_name, json.dumps(data, sort_keys=True,
                          indent=4, separators=(',', ': ')), resp.encoding)

    if data['status'] == 'OK':
        return data
    else:
        logging.error(file_name)
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

    if data == '':
        session = requests.Session()
        logging.debug('Requesting2: ' + url)
        resp    = session.get(url)
        data    = resp.json()
        Debug.writeToFile(file_name, json.dumps(data, sort_keys=True,
                          indent=4, separators=(',', ': ')), resp.encoding)

    if data['status'] == 'OK':
        return data
    else:
        logging.error(file_name)
        return None
# END: def getApkInfo


def downloadApk(apkInfo):
    """
    downloadApk(apkInfo): Download the specified URL to APK file name
    """
    url     = apkInfo['path']
    apkname = '{0}-{1}-{2}-minAPI{3}.apk'.format(apkInfo['package'],
                                                 apkInfo['vername'],
                                                 apkInfo['vercode'],
                                                 apkInfo['minSdk'])

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
        r = session.get(url)

        with open(apkname, 'wb') as local_file:
            local_file.write(r.content)
        print('{0} '.format(apkname)),
        sys.stdout.flush()
    except OSError:
        logging.exception('!!! Filename is not valid: "{0}"'.format(apkname))
# END: def downloadApk


def doDpiStuff(screenCompat):
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

    return '-'.join(sorted(dpis.keys()))
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


def processReportSourcesOutput(lines):
    """
    processReportSourcesOutput(lines): Return a dictionary of all APKs and versions in report
                                       created by report_sources.sh
    """
    global dAllApks

    dAllApks = {}

    sColumns = ['(?P<name>com\.[^|]*)', '(?P<arch>[^|]*)', '(?P<sdk>[^|]*)', '(?P<dpi>[^|]*)',
                '(?P<ver>[^|]*)',       '(?P<code>[^|]*)', '(?P<sig>[^|]*)']
    pattern  = '^\s+' + '\|'.join(sColumns) + '$'
    reLine   = re.compile(pattern)

    for line in lines:
        m = reLine.match(line)
        if m:
            name = m.group('name').strip()

            # Check if supported and add if it is
            if name not in dAllApks.keys():
                dAllApks[name] = []

            arch = m.group('arch').strip()
            sdk  = m.group('sdk').strip()
            dpi  = m.group('dpi').strip()
            ver  = m.group('ver').strip()
            code = m.group('code').strip()
            avi  = ApkVersionInfo(name, arch, sdk, dpi, ver, code)

            dAllApks[name].append(avi)
        # END: if m:
    # END: for line
# END: def processReportSourcesOutput


def getMaxVersionDict():
    """
    getMaxVersionDict():
    """
    global dAllApks
    global maxVerEachApk
    global minSdkEachApk

    maxVerEachApk = {}
    minSdkEachApk = {}

    for k in sorted(dAllApks.keys()):
        k2 = dAllApks[k][0].maxname
        if not k in maxVerEachApk:
            max1 = max(apk for apk in dAllApks[k]).ver
            max2 = max1

            # Check for "non-leanback" versions for max comparison
            if k2 in dAllApks:
                max2 = max(apk for apk in dAllApks[k2]).ver

            maxVerEachApk[k] = max(max1, max2)

            # Special case for Drive, Docs, Sheets and Slides
            # Remove the last '.XX' since it is CPU/DPI specific
            if 'com.google.android.apps.docs' in k:
                maxVerEachApk[k] = maxVerEachApk[k][0:-3]
        # END: if not k

        if not k in minSdkEachApk:
            minSdk = min(int(apk.sdk) for apk in dAllApks[k])
            minSdk = min(minSdk, 19)  # We suport down to 19
            minSdkEachApk[k] = minSdk
        # END: if not k in minSdkEachApk:

        logging.debug('{0} - maxVer: {1}, minSdk: {2}'.format(k, maxVerEachApk[k], minSdkEachApk[k]))
    # END: for k
# END: def getMaxVersionDict


def checkOneStore(repo):
    """
    checkOneStore(repo):
    """
    global dAllApks
    global maxVerEachApk
    global minSdkEachApk

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
    global dAllApks

    lines = ''
    if len(param_list) == 1:
        with open(param_list[0]) as report:
            lines = report.readlines()
    else:
        lines = sys.stdin.readlines()

    processReportSourcesOutput(lines)
    getMaxVersionDict()

    if len(dAllApks.keys()) == 0:
        print('ERROR: expecting:')
        print(' - 1 parameter (report file from output of report_sources.sh)')
        print(' or ')
        print(' - stdin from report_sources.sh')
        return

    repos = ['albrtkmxxo',
             'android777',
             'apk-s',
             'aplicaciones-ceibal',
             'apps',
             'austroid',
             'bazar-canaima',
             'benny09',
             'brainyideas',
             'darkkiller',
             'denis86',
             'donvito2021',
             'draconius666',
             'eltremendo02',
             'grungo2407',
             'gyjano',
             'hampoo',
             'hfk217',
             'hot105',
             'iosefirina22',
             'irishandroid',
             'kcprophet',
             'kryss974',
             'leighakat',
             'letechest',
             'lonerfox2013',
             'ludock96',
             'mark8',
             'matandroid',
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
             'tim-we',
             'tutu75',
             'vip-apk',
             'westcoastandroid',
             'yelbana2']

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

    main(sys.argv[1:])
