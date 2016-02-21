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
import random
import socket
import time

import httplib
import json

from debug import Debug
from apkhelper import ApkVersionInfo
from reporthelper import ReportHelper

from socket import error as socket_error

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
GlobalDelay = 30

# logging
logFile   = '{0}.log'.format(os.path.basename(__file__))
logLevel  = (logging.DEBUG if Debug.DEBUG else logging.INFO)
logFormat = '%(asctime)s %(levelname)s/%(funcName)s(%(process)-5d): %(message)s'

class AptoideCrawler(object):
    def __init__(self, report, dlFiles=[], dlFilesBeta=[]):
        self.report      = report
        self.dlFiles     = dlFiles
        self.dlFilesBeta = dlFilesBeta

    def listRepo(self, repo, orderby=None):
        """
        listRepo(repo): Get list of all APKs in a specific store from the Aptoide API
                        and return it in JSON form
        """
        file_name = '{0}{1}.json'.format(repo, '' if not orderby else '-' + '-'.join(orderby))
        orderby   = '' if not orderby else '/orderby/' + '/'.join(orderby)
        url       = 'http://' + repo + '.aptoide.com/webservices/listRepository/{0}{1}/json'.format(repo, orderby)
        data      = Debug.readFromFile(file_name)

    #TODO use http://www.aptoide.com/webservices/docs/2/listRepositoryChange to find if there are any updates for a repo

        if data == '':
            session = requests.Session()
            # session.proxies = Debug.getProxy()

            for x in xrange(1,4): #up to three tries
                wait = GlobalDelay*x
                logging.info('Waiting {0} seconds before fetching {1}'.format(wait, file_name))
                time.sleep(wait)
                try:
                    logging.debug('Requesting1 ({0}): {1}'.format(x, url))
                    resp = session.get(url)

                    if resp.status_code ==httplib.OK:
                        data = resp.json()
                        if 'status' in data and data['status'] == 'OK':
                            Debug.writeToFile(file_name, json.dumps(data, sort_keys=True,
                                              indent=4, separators=(',', ': ')), resp.encoding)
                            return data
                        else:
                            logging.error('data1[\'status\']: {0}, when fetching {1}, try {2}'.format(data.get('status', 'null'), file_name, x))
                    else:
                        logging.error('HTTPStatus1: {0}, when fetching {1}, try {2}'.format(resp.status_code, file_name, x))
                except:
                    logging.exception('!!! Invalid JSON from: "{0}", retry in: {1}s'.format(url,wait))
            # END: for x
        # END: if data
        return None
    # END: def listRepo


    def getApkInfo(self, repo, apkid, apkversion, options=None, doVersion1=False):
        """
        getApkInfo(repo, apkid, apkversion): Get APK specific information from the Aptoide API
                                             and return it as an ApkVersionInfo object
        """
        version   = '1' if doVersion1 else '2'
        file_name = '{0}-{1}-{2}_{3}.json'.format(repo, apkid, apkversion, version)
        options   = '' if not options else '/options=({0})'.format(options)
        url       = 'http://' + repo + '.aptoide.com/webservices/{0}/getApkInfo/{1}/{2}/{3}{4}/json'.format( #using an arbitrary subdomain prevents rate-limiting
                    version, repo, apkid, apkversion, options)
        data      = Debug.readFromFile(file_name)

        if data == '':
            session = requests.Session()
            # session.proxies = Debug.getProxy()

            for x in xrange(1,4): #up to three tries
                wait = GlobalDelay*x
                logging.info('Waiting {0} seconds before fetching {1}'.format(wait, file_name))
                time.sleep(wait)
                try:
                    logging.debug('Requesting2 ({0}): {1}'.format(x, url))
                    resp = session.get(url)

                    if resp.status_code == httplib.OK:
                        data = resp.json()
                        if 'status' in data and data['status'] == 'OK':
                            avi = ApkVersionInfo(name    = data['apk']['package'],
                                                 arch    = data['apk'].get('cpu', 'all'),
                                                 sdk     = data['apk']['minSdk'],
                                                 dpi     = self.doDpiStuff(data['apk'].get('screenCompat', 'nodpi')),
                                                 ver     = data['apk']['vername'].split(' ')[0],  # Look at only the true version number
                                                 vercode = data['apk']['vercode'],
                                                 download_src = data['apk']['path'],
                                                 malware = (data['malware'] if 'malware' in data else '') #We only have this key if vercode is in options
                                                 )
                            Debug.writeToFile(file_name, json.dumps(data, sort_keys=True,
                                              indent=4, separators=(',', ': ')), resp.encoding)
                            return avi
                        else:
                            logging.error('data2[\'status\']: {0}, when fetching {1}, try {2}'.format(data.get('status', 'null'), file_name, x))
                    else:
                        logging.error('HTTPStatus2: {0}, when fetching {1}, try {2}'.format(resp.status_code, file_name, x))
                except:
                    logging.exception('!!! Invalid JSON from: "{0}", retry in: {1}s'.format(url,wait))
            # END: for x
        # END: if data
        return None
    # END: def getApkInfo


    def downloadApk(self, avi, isBeta=False):
        """
        downloadApk(avi, isBeta): Download the specified ApkInfo from Aptoide to APK file name
        """
        url = avi.download_src

        cpu = '({0})'.format(avi.arch)

        dpi = avi.dpi if avi.dpi != 'nodpi' else 'no'
        dpi = '({0}dpi)'.format(dpi)

        if (avi.malware['status']=="scanned" and
            avi.malware['reason']['signature_validated']['status']=="passed" and
            (avi.malware['reason']['signature_validated']['signature_from']=="market" or avi.malware['reason']['signature_validated']['signature_from']=="tester")):
            apkname = '{0}_{1}-{2}_minAPI{3}{4}{5}.apk'.format(avi.name.replace('.beta', ''),
                                                               avi.realver.replace(' ', '_'),
                                                               avi.vercode,
                                                               avi.sdk,
                                                               cpu, dpi)
            ret = True
        else: #IMPLIES avi.malware['reason']['signature_validated']['signature_from']=="user"
            apkname = 'err.{0}_{1}-{2}_minAPI{3}{4}{5}.err'.format(avi.name.replace('.beta', ''),
                                                               avi.realver.replace(' ', '_'),
                                                               avi.vercode,
                                                               avi.sdk,
                                                               cpu, dpi)
            logging.error('{0} is a signed with a non-Playstore signature, be VERY careful about its authenticity.'.format(apkname))
            print >> sys.stderr, 'NOTICE: {0} is a signed with a non-Playstore signature, be VERY careful about its authenticity.'.format(apkname) #rewrite in python3
            ret = False


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

            if r.status_code != httplib.OK:
                logging.exception('HTTP Status {0}. Failed to download: {1}'.format(r.status_code,apkname))
                return

            with open(apkname, 'wb') as local_file:
                local_file.write(r.content)

            if ret:
                logging.debug(('beta:' if isBeta else 'reg :') + apkname)
                return       (('beta:' if isBeta else ''     ) + apkname)
        except socket.error as serr:
            logging.exception('Socket error {0}. Failed to download: {1}'.format(serr,apkname))
        except OSError:
            logging.exception('!!! Filename is not valid: "{0}"'.format(apkname))
    # END: def downloadApk


    def doDpiStuff(self, screenCompat, delim='-'):
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

    def checkOneStore(self, repo):
        """
        checkOneStore(repo):
        """
        logging.info('Checking store: {0}'.format(repo))

        # Date to look back until
        today       = datetime.date.today()
        search_stop = today - datetime.timedelta(days=3)

        search_date = today
        offset = 0
        filenames = []
        while search_date > search_stop:
            data = self.listRepo(repo, ('recent', '100', str(offset)))
            if data:
                if len(data['listing']) == 0:
                    logging.error('{0} has no recent applications listed'.format(repo))
                    print >> sys.stderr, 'NOTICE: {0} has no recent applications listed'.format(repo) #rewrite in python3
                    break #empty repository

                if offset == 0: #check the most recent apk entry to find out if a repository is outdated
                    latestuploadtime = datetime.datetime.strptime(data['listing'][0]['date'], '%Y-%m-%d').date()
                    if today - datetime.timedelta(days=30) > latestuploadtime:
                        logging.error('{0} has not been updated for a month, last update: {1}'.format(repo,latestuploadtime))
                        print >> sys.stderr, 'NOTICE: {0} has not been updated for a month, last update: {1}'.format(repo,latestuploadtime) #rewrite in python3

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
                                         ver=ver,  # Look at only the true version number
                                         vercode=item['vercode'],
                                         )

                    # Check for beta support
                    bCheckMore = False
                    if self.report.needsBetaSupport(avi):
                        import copy
                        avibeta = copy.deepcopy(avi)
                        avibeta.name += '.beta'
                        needBeta = self.report.isThisApkNeeded(avibeta)

                    # Do we already have it
                    if self.report.isThisApkNeeded(avi):
                        # Get additional info
                        avi = self.getApkInfo(repo, apkid, ver,
                                         options='vercode=' + str(item['vercode']))
                        if avi:
                            if avi.malware['status'] == "warn" and avi.malware['reason']['signature_validated']['status']=="failed" and avi.malware['reason']['signature_validated']['signature_from']=="market": #signature matches market, but it does not pass verification
                                logging.error('{0} is a corrupt or incomplete APK, ignored.'.format(avi.download_src))
                            else:
                                # Are we sure we still need it after the additional info?
                                if self.report.isThisApkNeeded(avi):
                                    filenames.append(self.downloadApk(avi))
                            # END: if avi.malware
                        # END: if avi
                    # END: if isThisApkNeeded
                # END: for item
                offset += 100
            else:
                break #retrieving the list of recents apps failed, skip repository
            # END: if data
        # END: while
        return filenames
    # END: def checkOneStore:


    def crawl(self, threads=5):
        """
        crawl(): check all aptoide stores
        """
        repos = ['abdallah23',
                 'adgilapps2011',
                 #'advcfs',
                 #'albrtkmxxo',
                 'android777',
                 'apk-s',
                 'aplicaciones-ceibal',
                 'apps',
                 'appstv',
                 'arkz',
                 'ashley88',
                 'austroid',
                 'bazar-canaima',
                 #'blaccs',
                 #'benny09',
                 'brainyideas',
                 #'carefullycoosed',
                 'catnamiw',
                 #'cesang7',
                 'dagokayaker',
                 'dalon',
                 'damienkram',
                 'darkkiller',
                 'datawind-apps',
                 'ddnut',
                 'denis86',
                 'dominic-armes',
                 'donvito2021',
                 #'downapk',
                 'draconius666',
                 #'draydroid',
                 'eearl',
                 'elektron45',
                 'eltremendo02',
                 'emmanuel-prada',
                 #'epsil',
                 'erriperry',
                 'ezam-akmar',
                 'fedex-bermu',
                 'fetek',
                 'fmendes',
                 'gonzalo-rodriguez',
                 'greenraccoon23',
                 'grungo2407',
                 'gs3passion',
                 'gyjano',
                 'hamayk',
                 'hampoo',
                 #'hfk217',
                 'hoser98',
                 'hot105',
                 'iosefirina22',
                 'irishandroid',
                 #'jaslibertas',
                 'jaden-anthony',
                 'jdquila',
                 'jecabra',
                 'jodean',
                 #'kcprophet',
                 'kipidap',
                 'kryss974',
                 'kvanzuijlen',
                 'leighakat',
                 #'letechest',
                 #'lewy',
                 'lonerfox2013',
                 #'ludock96',
                 'mancmonkey',
                 'mark8',
                 #'matandroid',
                 'maxxthor',
                 'mc0',
                 #'megas0ra',
                 'mestruque',
                 #'metin2ventor',
                 'michael-belisle',
                 'migatronic',
                 'milaupv',
                 'mine-t999',
                 'mrunknownkisser',
                 'msi8',
                 'mygica',
                 #'mys3',
                 'nadmom',
                 'netogdiaz',
                 'new-day-apps',
                 'nndmt',
                 'nowkin',
                 #'orgia82',
                 'ortumatrix',
                 'pentacore',
                 'perfect-electronic',
                 'pocketappz',
                 #'poulpe',
                 'pp-apk',
                 'prozac4me',
                 'qweargs',
                 'rahullah',
                 'raypino',
                 'rehak',
                 'rodrivergara',
                 'ryoma3ch1z3n',
                 'sandro797',
                 'scratchn63',
                 'sebastiano82',
                 'shotaro',
                 #'slapchop',
                 'snah',
                 'sommydany',
                 #'speny',
                 'sprithansi',
                 #'stein-gmg',
                 #'story89998',
                 #'sunnygnutz',
                 'theaureli69',
                 'thegooch',
                 'tiendacanaima',
                 'tim-we',
                 'tironpickaxe',
                 'trotuman',
                 'tutu75',
                 'vip-apk',
                 'vitonline',
                 'wanky',
                 'westcoastandroid',
                 'wo88les',
                 'xavimetal',
                 'xerodox',
                 'yelbana2',
                 'zinavivid']
        random.shuffle(repos) #randomize the order of the repositories to improve the chance to quickly hit new apks (before aptoide starts complaining with 503s)

        # Start checking all stores ...
        p = multiprocessing.Pool(threads) #a lot of sequential requests from one IP still trigger 503, but the delay mechanism then kicks and in general fixes a retry
        r = p.map_async(unwrap_self_checkOneStore, zip([self]*len(repos), repos), callback=unwrap_callback)
        r.wait()
        (self.dlFiles, self.dlFilesBeta) = unwrap_getresults()
    # END: crawl():
# END: class AptoideCrawler

nonbeta = []
beta    = []
def unwrap_callback(results):
    for resultlist in results:
        for result in resultlist:
            if result:
                if result.startswith('beta:'):
                    beta.append(result[5:])
                else:
                    nonbeta.append(result)

def unwrap_getresults():
    return (nonbeta, beta)

def unwrap_self_checkOneStore(arg, **kwarg):
    return AptoideCrawler.checkOneStore(*arg, **kwarg)

if __name__ == "__main__":
    """
    main(): single parameter for report_sources.sh output
    """
    logging.basicConfig(filename = logFile, filemode = 'w', level = logLevel, format = logFormat)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("requesocks").setLevel(logging.WARNING)

    lines = ''
    if len(sys.argv[1:]) == 1:
        with open(sys.argv[1]) as report:
            lines = report.readlines()
    else:
        lines = sys.stdin.readlines()

    report = ReportHelper(lines)

    if len(report.dAllApks.keys()) == 0:
        print('ERROR: expecting:')
        print(' - 1 parameter (report file from output of report_sources.sh)')
        print(' or ')
        print(' - stdin from report_sources.sh')
        exit(1)

    crawler = AptoideCrawler(report)
    crawler.crawl()

    outputString = ' '.join(crawler.dlFiles)
    if crawler.dlFilesBeta:
        outputString += ' beta ' + ' '.join(crawler.dlFilesBeta)

    if outputString:
        print(outputString)
        sys.stdout.flush()

    logging.debug('Done ...')
