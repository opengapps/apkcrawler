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
Global.report      = None
Global.dlFiles     = []
Global.dlFilesBeta = []

# logging
logFile   = '{0}.log'.format(os.path.basename(__file__))
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
                                         and return it as an ApkVersionInfo object
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
            avi = ApkVersionInfo(name    = data['apk']['package'],
                                 arch    = data['apk'].get('cpu', 'all'),
                                 sdk     = data['apk']['minSdk'],
                                 dpi     = doDpiStuff(data['apk'].get('screenCompat', 'nodpi')),
                                 ver     = data['apk']['vername'].split(' ')[0],  # Look at only the true version number
                                 vercode = data['apk']['vercode'],
                                 #scrape_url=''
                                 )
            avi.download_url = data['apk']['path']
            return avi
        else:
            logging.error(file_name)
    except:
        logging.exception('!!! Invalid JSON from: "{0}"'.format(url))

    return None
# END: def getApkInfo


def downloadApk(avi, isBeta=False):
    """
    downloadApk(avi): Download the specified URL to APK file name
    """
    url = avi.download_url

    cpu = '({0})'.format(avi.arch)

    dpi = avi.dpi if avi.dpi != 'nodpi' else 'no'
    dpi = '({0}dpi)'.format(dpi)

    apkname = '{0}_{1}-{2}_minAPI{3}{4}{5}.apk'.format(avi.name.replace('.beta', ''),
                                                       avi.realver.replace(' ', '_'),
                                                       avi.vercode,
                                                       avi.sdk,
                                                       cpu, dpi)

    logging.info('Downloading "{0}" from: {1}'.format(apkname,url))

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

                # If the version name contains 'beta' append '.beta' to the apkid
                extra  = ''
                if 'beta' in item['ver']:
                    extra = '.beta'

                apkid    = item['apkid']
                apkextra = apkid + extra
                ver      = item['ver'].split(' ')[0]

                avi = ApkVersionInfo(name=apkid,
                                     #arch='',
                                     #sdk='',
                                     #dpi='',
                                     ver=ver,  # Look at only the true version number
                                     vercode=item['vercode'],
                                     #scrape_url=''
                                     )

                # Check for beta support
                bCheckMore = False
                if Global.report.needsBetaSupport(avi):
                    import copy
                    avibeta = copy.deepcopy(avi)
                    avibeta.name += '.beta'
                    needBeta = Global.report.isThisApkNeeded(avibeta)

                # Do we already have it
                if Global.report.isThisApkNeeded(avi):
                    # Get additional info
                    avi = getApkInfo(repo, apkid, ver,
                                     options='vercode=' + str(item['vercode']))
                    if avi:
                        # Still need it after additional info?
                        if Global.report.isThisApkNeeded(avi):
                            downloadApk(avi)
                    # END: if avi:
                # END: if isThisApkNeeded
            # END: for item
        # END: if data
        offset += 100
    # END: while
# END: def checkOneStore:


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
             'dalon',
             'darkkiller',
             'datawind-apps',
             'denis86',
             'donvito2021',
             'draconius666',
             'eearl',
             'eltremendo02',
             'epsil',
             'ezam-akmar',
             'gonzalo-rodriguez',
             'grungo2407',
             'gs3passion',
             'gyjano',
             'hampoo',
             'hfk217',
             'hoser98',
             'hot105',
             'iosefirina22',
             'irishandroid',
             'jaslibertas',
             'jdquila',
             'jodean',
             'kcprophet',
             'kryss974',
             'kvanzuijlen',
             'leighakat',
             'letechest',
             'lonerfox2013',
             'ludock96',
             'mark8',
             'matandroid',
             'megas0ra',
             'mestruque',
             'metin2ventor',
             'michael-belisle',
             'migatronic',
             'milaupv',
             'msi8',
             'mys3',
             'new-day-apps',
             'nowkin',
             'orgia82',
             'pentacore',
             'perfect-electronic',
             'pocketappz',
             'poulpe',
             'prozac4me',
             'rahullah',
             'rodrivergara',
             'ryoma3ch1z3n',
             'sandro797',
             'scratchn63',
             'shotaro',
             'slapchop',
             'snah',
             'sommydany',
             'speny',
             'sprithansi',
             'stein-gmg',
             'story89998',
             'sunnygnutz',
             'tim-we',
             'tutu75',
             'vip-apk',
             'wanky',
             'westcoastandroid',
             'xerodox',
             'yelbana2']

    # Start checking all stores ...
    p = multiprocessing.Pool(5)
    p.map(checkOneStore, repos)

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
