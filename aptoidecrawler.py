#!/usr/bin/env python

#
# Required Modules
# - beautifulsoup4
# - html5lib
# - requests
#

import sys
import os
import logging

import json
import requests
import codecs

###################
# DEBUG VARS      #
###################

DEBUG        = True
READFROMFILE = False  # Read from file for debugging
SAVELASTFILE = False  # Write to file upon each request

###################
# END: DEBUG VARS #
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
    DEBUG_readFromFile():
    """
    if READFROMFILE and os.path.exists(file_name):
        with open(file_name, 'rb') as debug_file:
            return debug_file.read()
    else:
        return ''
# END: def DEBUG_readFromFile():


def DEBUG_writeToFile(file_name, debug, encoding):
    """
    DEBUG_writeToFile():
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
    listRepo(repo):
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
# END: def listRepo(repo):


def getApkInfo(repo, apkid, apkversion, options=None, doVersion1=False):
    """
    getApkInfo(repo, apkid, apkversion):
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
# END: def getApkInfo(repo, apkid, apkversion):


def doDpiStuff(screenCompat):
    """
    doDpiStuff(screenCompat):
    """
    if screenCompat == 'nodpi':
        return screenCompat

    dpis = {}
    splits = screenCompat.split(',')
    for split in splits:
        splits2 = split.split('/')
        dpis[str(splits2[1])] = ''

    return '-'.join(sorted(dpis.keys()))
# END: def doDpiStuff(screenCompat):


def doCpuStuff(cpu):
    """
    doCpuStuff(cpu):
    """
    return {
        'armeabi-v7a': 'arm',
        'arm64-v8a'  : 'arm64',
        'x86'        : 'x86',
    }.get(cpu, 'all')
# END: def doCpuStuff(cpu):


def main(param_list):
    """
    main():
    """

    repos = ['albrtkmxxo',
             'android777',
             'aplicaciones-ceibal',
             'apk-s',
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
             'rahullah'
             'rodrivergara',
             'ryoma3ch1z3n',
             'sandro797',
             'shotaro'
             'slapchop',
             'snah',
             'speny',
             'stein-gmg',
             'tim-we',
             'tutu75',
             'vip-apk',
             'westcoastandroid']

    apps = {'com.android.chrome'                          : '46.0.2490.76',
            'com.google.android.apps.docs'                : '2.3.414.25',
            'com.google.android.apps.docs.editors.docs'   : '1.4.432.07',
            'com.google.android.apps.docs.editors.sheets' : '1.4.432.09',
            'com.google.android.apps.docs.editors.slides' : '1.2.432.11',
            'com.google.android.apps.maps'                : '9.16.2',
            'com.google.android.apps.photos'              : '1.8.0.106438466',
            'com.google.android.apps.plus'                : '6.6.0.105800701',
            'com.google.android.gms.leanback'             : '8.3.00',
            'com.google.android.play.games'               : '3.4.12',
            'com.google.android.play.games.leanback'      : '3.4.12',
            'com.google.android.talk'                     : '5.1.105976615',
            'com.google.android.youtube'                  : '10.42.52'}

    appsneeded = ["com.android.chrome|arm64|21|nodpi|46.0.2490.76",
                  "com.google.android.apps.docs|arm|14|160|2.3.414.25.32",
                  "com.google.android.apps.docs|arm|14|640|2.3.414.25.36",
                  "com.google.android.apps.docs|arm64|14|240|2.3.414.25.43",
                  "com.google.android.apps.docs|arm64|14|320|2.3.414.25.44",
                  "com.google.android.apps.docs|arm64|14|480|2.3.414.25.45",
                  "com.google.android.apps.docs|arm64|14|640|2.3.414.25.46",
                  "com.google.android.apps.docs|arm64|14|nodpi|2.3.414.25.40",
                  "com.google.android.apps.docs|x86|14|160|2.3.414.25.72",
                  "com.google.android.apps.docs|x86|14|240|2.3.414.25.73",
                  "com.google.android.apps.docs|x86|14|320|2.3.414.25.74",
                  "com.google.android.apps.docs|x86|14|480|2.3.414.25.75",
                  "com.google.android.apps.docs|x86|14|nodpi|2.3.414.25.70",
                  "com.google.android.apps.docs.editors.docs|arm|16|160|1.4.432.07.32",
                  "com.google.android.apps.docs.editors.docs|arm64|16|240|1.4.432.07.43",
                  "com.google.android.apps.docs.editors.docs|arm64|16|640|1.4.432.07.46",
                  "com.google.android.apps.docs.editors.docs|arm64|16|nodpi|1.4.432.07.40",
                  "com.google.android.apps.docs.editors.docs|x86|16|160|1.4.432.07.72",
                  "com.google.android.apps.docs.editors.docs|x86|16|320|1.4.432.07.74",
                  "com.google.android.apps.docs.editors.docs|x86|16|nodpi|1.4.432.07.70",
                  "com.google.android.apps.docs.editors.sheets|arm|16|160|1.4.432.09.32",
                  "com.google.android.apps.docs.editors.sheets|arm|16|240|1.4.432.09.33",
                  "com.google.android.apps.docs.editors.sheets|arm|16|640|1.4.432.09.36",
                  "com.google.android.apps.docs.editors.sheets|arm64|16|240|1.4.432.09.43",
                  "com.google.android.apps.docs.editors.sheets|x86|16|160|1.4.432.09.72",
                  "com.google.android.apps.docs.editors.sheets|x86|16|320|1.4.432.09.74",
                  "com.google.android.apps.docs.editors.sheets|x86|16|nodpi|1.4.432.09.70",
                  "com.google.android.apps.docs.editors.slides|arm64|16|nodpi|1.2.432.11.40",
                  "com.google.android.apps.docs.editors.slides|x86|16|160|1.2.432.11.72",
                  "com.google.android.apps.docs.editors.slides|x86|16|320|1.2.432.11.74",
                  "com.google.android.apps.docs.editors.slides|x86|16|nodpi|1.2.432.11.70",
                  "com.google.android.apps.maps|arm|18|nodpi|9.16.2",
                  "com.google.android.apps.maps|arm64|18|nodpi|9.16.2",
                  "com.google.android.apps.maps|x86|18|nodpi|9.16.2",
                  "com.google.android.apps.maps|x86_64|18|nodpi|9.16.2",
                  "com.google.android.apps.photos|x86|14|nodpi|1.8.0.106438466",
                  "com.google.android.apps.plus|x86|19|213-240|6.6.0.105800701",
                  "com.google.android.apps.plus|x86|19|nodpi|6.6.0.105800701",
                  "com.google.android.gms.leanback|arm|19|nodpi|8.3.00",
                  "com.google.android.gms.leanback|arm64|19|nodpi|8.3.00",
                  "com.google.android.play.games|arm|9|240|3.4.12",
                  "com.google.android.play.games|arm|9|nodpi|3.4.12",
                  "com.google.android.play.games|arm64|9|480|3.4.12",
                  "com.google.android.play.games|x86|9|nodpi|3.4.12",
                  "com.google.android.play.games.leanback|arm|21|nodpi|3.4.12",
                  "com.google.android.play.games.leanback|arm64|21|nodpi|3.4.12",
                  "com.google.android.play.games.leanback|x86|21|nodpi|3.4.12",
                  "com.google.android.talk|arm|15|160|5.1.105976615",
                  "com.google.android.talk|arm|15|240|5.1.105976615",
                  "com.google.android.talk|arm|15|320|5.1.105976615",
                  "com.google.android.talk|arm|15|480|5.1.105976615",
                  "com.google.android.talk|arm|15|640|5.1.105976615",
                  "com.google.android.talk|arm|15|nodpi|5.1.105976615",
                  "com.google.android.talk|x86|15|160|5.1.105976615",
                  "com.google.android.talk|x86|15|320|5.1.105976615",
                  "com.google.android.talk|x86|15|480|5.1.105976615",
                  "com.google.android.talk|x86|15|nodpi|5.1.105976615",
                  "com.google.android.youtube|arm|15|160|10.42.52",
                  "com.google.android.youtube|arm|15|240|10.42.52",
                  "com.google.android.youtube|arm|15|320|10.42.52",
                  "com.google.android.youtube|arm|15|480|10.42.52",
                  "com.google.android.youtube|arm|15|nodpi|10.42.52",
                  "com.google.android.youtube|arm64|23|nodpi|10.42.52",
                  "com.google.android.youtube|arm64|15|240|10.42.52",
                  "com.google.android.youtube|arm64|15|320|10.42.52",
                  "com.google.android.youtube|arm64|15|480|10.42.52",
                  "com.google.android.youtube|arm64|15|nodpi|10.42.52",
                  "com.google.android.youtube|x86|15|160|10.42.52",
                  "com.google.android.youtube|x86|15|240|10.42.52",
                  "com.google.android.youtube|x86|15|320|10.42.52",
                  "com.google.android.youtube|x86|15|480|10.42.52",
                  "com.google.android.youtube|x86|15|nodpi|10.42.52"]

    for repo in repos:
        offset = 0
        while offset < 500:
            data   = listRepo(repo, ('recent', '100', str(offset)))
            if data:
                for item in data['listing']:
                    if item['apkid'] in apps.keys() and apps[item['apkid']] in item['ver']:
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
