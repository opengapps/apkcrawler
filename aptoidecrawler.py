#!/usr/bin/env python

#
# Required Modules
# - beautifulsoup4
# - html5lib
# - requests
#

import sys
import os
import re
import logging

import json
import requests
import codecs

###################
# DEBUG VARS      #
###################

DEBUG        = False
READFROMFILE = False  # Read from file for debugging
SAVELASTFILE = False  # Write to file upon each request

###################
# END: DEBUG VARS #
###################

###################
# CLASSES         #
###################


class ApkVersionInfo(object):
    """ApkVersionInfo"""
    def __init__(self, name='', arch='', sdk='', dpi='', ver=''):
        super(ApkVersionInfo, self).__init__()

        sName  = '^(?P<name>.*)\.leanback$'
        reName = re.compile(sName)

        sVer  = '^(?P<ver>.*)(?P<extra>[-.](leanback|tv|arm|arm\.arm_neon|armeabi-v7a|arm64|arm64-v8a|x86|))$'
        reVer = re.compile(sVer)

        self.name     = name
        self.maxname  = name  # used for max versions
        self.arch     = arch
        self.sdk      = sdk
        self.dpi      = dpi
        self.ver      = ver
        self.realver  = None  # used for full versions

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
        return '{0}|{1}|{2}|{3}|{4}{5}'.format(self.name,
                                               self.arch,
                                               self.sdk,
                                               self.dpi,
                                               max,
                                               self.realver if self.realver else '' )

    def __lt__(self, other):
        from distutils.version import StrictVersion

        if self.ver == '' or other.ver == '':
            return self.name < other.name
        else:
            return StrictVersion(self.ver) < StrictVersion(other.ver)

    def __cmp__(self, other):
        from distutils.version import StrictVersion

        if self.version == '' or other.version == '':
            return cmp(self.name, other.name)
        else:
            return StrictVersion(self.ver).__cmp__(other.ver)

    def __str__(self):
        return str(self.__dict__)
# END: class ApkVersionInfo()

###################
# END: CLASSES    #
###################

###################
# Globals         #
###################

# logging
logFile   = '{0}.log'.format(os.path.basename(sys.argv[0]))
logLevel  = (logging.DEBUG if DEBUG else logging.INFO)
logFormat = '%(asctime)s %(levelname)s/%(funcName)s(%(process)-5d): %(message)s'


def DEBUG_readFromFile(file_name):
    """
    DEBUG_readFromFile(): Read the debug information from file if READFROMFILE is enabled
    """
    if READFROMFILE and os.path.exists(file_name):
        with open(file_name, 'rb') as debug_file:
            return debug_file.read()
    else:
        return ''
# END: def DEBUG_readFromFile():


def DEBUG_writeToFile(file_name, debug, encoding):
    """
    DEBUG_writeToFile(): Write the debug information to file if SAVELASTFILE is enabled
    """
    if SAVELASTFILE:
        try:
            with codecs.open(file_name, 'w', encoding) as debug_file:
                debug_file.write(str(debug))
        except TypeError:
            with open(file_name, 'ab') as debug_file:
                debug_file.write(str(debug))
# END: def DEBUG_writeToFile():


def listRepo(repo, orderby=None):
    """
    listRepo(repo): Get list of all APKs in a specific store from the Aptoide API
                    and return it in JSON form
    """
    file_name = '{0}{1}.json'.format(repo, '' if not orderby else '-' + '-'.join(orderby))
    orderby   = '' if not orderby else '/orderby/' + '/'.join(orderby)
    url       = 'http://webservices.aptoide.com/webservices/listRepository/{0}{1}/json'.format(repo, orderby)
    data      = DEBUG_readFromFile(file_name)

    if data == '':
        session = requests.Session()
        logging.debug('Requesting1: ' + url)
        resp    = session.get(url)
        data    = resp.json()
        DEBUG_writeToFile(file_name, json.dumps(data, sort_keys=True,
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
    data      = DEBUG_readFromFile(file_name)

    if data == '':
        session = requests.Session()
        logging.debug('Requesting2: ' + url)
        resp    = session.get(url)
        data    = resp.json()
        DEBUG_writeToFile(file_name, json.dumps(data, sort_keys=True,
                          indent=4, separators=(',', ': ')), resp.encoding)

    if data['status'] == 'OK':
        return data
    else:
        logging.error(file_name)
        return None
# END: def getApkInfo


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
        'armeabi-v7a': 'arm',
        'arm64-v8a'  : 'arm64',
        'x86'        : 'x86',
    }.get(cpu, 'all')
# END: def doCpuStuff


def processReportSourcesOutput(report_file):
    """
    processReportSourcesOutput(report_file): Return a dictionary of all APKs and versions in report
                                             created by report_sources.sh
    """
    ignoredPackageNames = [ 'android.autoinstalls.config.google.fugu',
                            'android.autoinstalls.config.google.nexus',
                            'com.android.facelock',
                            'com.google.android.androidforwork',
                            'com.google.android.apps.mediashell.leanback',
                            'com.google.android.athome.remotecontrol',
                            'com.google.android.atv.customization',
                            'com.google.android.atv.widget',
                            'com.google.android.backuptransport',
                            'com.google.android.configupdater',
                            'com.google.android.feedback',
                            'com.google.android.fugu.pairing',
                            'com.google.android.gsf',
                            'com.google.android.gsf.login',
                            'com.google.android.gsf.notouch',
                            'com.google.android.onetimeinitializer',
                            'com.google.android.packageinstaller',
                            'com.google.android.pano.packageinstaller',
                            'com.google.android.partnersetup',
                            'com.google.android.setupwizard',
                            'com.google.android.sss',
                            'com.google.android.sss.authbridge',
                            'com.google.android.syncadapters.calendar',
                            'com.google.android.syncadapters.contacts',
                            'com.google.android.tungsten.overscan',
                            'com.google.android.tungsten.setupwraith',
                            'com.google.android.tv.frameworkpackagestubs',
                            'com.google.android.tv.remote',
                            'com.google.android.tv.remotepairing',
                            'com.google.android.tv.voiceinput',
                            'com.google.tungsten.bugreportsender' ]

    dAllApks = {}

    pattern = "^\s+(?P<name>com\.[^|]*)\|(?P<arch>[^|]*)\|(?P<sdk>[^|]*)\|(?P<dpi>[^|]*)\|(?P<ver>[^|]*)\|[^|]*\|[^|]*$"
    reLine  = re.compile(pattern)
    with open(report_file) as report:
        report.readline()
        for line in report.readlines():
            m = reLine.match(line)
            if m:
                name = m.group('name').strip()

                # Check if ignored
                if name in ignoredPackageNames:
                    continue

                arch = m.group('arch').strip()
                sdk  = m.group('sdk').strip()
                dpi  = m.group('dpi').strip()
                ver  = m.group('ver').strip()
                avi  = ApkVersionInfo(name, arch, sdk, dpi, ver)

                # Init dict entry if needed
                if not name in dAllApks:
                    dAllApks[name] = []

                dAllApks[name].append(avi)
            # END: if m:
        # END: for line
    # END: with open

    return dAllApks
# END: def processReportSourcesOutput


def getMaxVersionDict(dAllApks):
    """
    getMaxVersionDict(dAllApks):
    """
    maxApps  = {}
    for k in sorted(dAllApks.keys()):
        k2 = dAllApks[k][0].maxname
        if not k in maxApps:
            max1 = max(apk.ver for apk in dAllApks[k])
            max2 = max1

            # Check for "non-leanback" versions for max comparison
            if k2 in dAllApks:
                max2 = max(apk.ver for apk in dAllApks[k2])

            maxApps[k]  = max(max1, max2)

            # Special case for Drive, Docs, Sheets and Slides
            # Remove the last '.XX' since it is CPU/DPI specific
            if 'com.google.android.apps.docs' in k:
                maxApps[k] = maxApps[k][0:-3]

            logging.debug('max({0}): {1}'.format(k, maxApps[k]))

    return maxApps
# END: def getMaxVersionDict


def main(param_list):
    """
    main(): single parameter for report_sources.sh output
    """
    if len(param_list) != 1:
        print('ERROR: expecting 1 parameter (report from output of report_sources.sh)')
        return

    dAllApks   = processReportSourcesOutput(param_list[0])
    maxApps    = getMaxVersionDict(dAllApks)

    appsneeded = []

    for k in dAllApks.keys():
        thisappsneeded = []
        for a in dAllApks[k]:
            maxApk = ApkVersionInfo(ver = maxApps[k])
            if a.ver < maxApk.ver:
                logging.debug('{0}: {1} < maxApk.ver: {2}'.format(k, a.ver, maxApk.ver))
                thisappsneeded.append(a.fullString(maxApps[k]))
        if len(thisappsneeded) == 0:
            logging.debug('deleted: ' + k)
            del maxApps[k]
        else:
            appsneeded.extend(thisappsneeded)

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
             'speny',
             'stein-gmg',
             'tim-we',
             'tutu75',
             'vip-apk',
             'westcoastandroid']

    # Log the needed versions:
    for n in appsneeded:
        logging.info(n)

    # Start checking all stores ...
    for repo in repos:
        offset = 0
        while offset < 500:
            data   = listRepo(repo, ('recent', '100', str(offset)))
            if data:
                # Check each apk ...
                for item in data['listing']:
                    # Against the list we are looking for
                    if item['apkid'] in maxApps.keys() and maxApps[item['apkid']] in item['ver']:
                        apkInfo = getApkInfo(repo, item['apkid'], item['ver'],
                                             options='vercode=' + str(item['vercode']))
                        if apkInfo:
                            this = '{0}|{1}|{2}|{3}|{4}'.format(item['apkid'],
                                                                doCpuStuff(apkInfo['apk'].get('cpu', 'all')),
                                                                apkInfo['apk']['minSdk'],
                                                                doDpiStuff(apkInfo['apk'].get('screenCompat', 'nodpi')),
                                                                item['ver'])
                            if this in appsneeded:
                                print(this + ' --- ' + item['path'])
                        # END: if apkInfo
                    # END: if item
                # END: for item
            # END: if data
            offset += 100
        # END: while offset
    # END: for repo
# END: main():

###################
# END: Functions  #
###################

if __name__ == "__main__":
    logging.basicConfig(filename = logFile, filemode = 'w', level = logLevel, format = logFormat)
    logging.getLogger("requests").setLevel(logging.WARNING)

    main(sys.argv[1:])
