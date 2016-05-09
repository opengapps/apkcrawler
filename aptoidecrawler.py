#!/usr/bin/env python3

#
# Required Modules
# - requests
#

import datetime
import http.client
import json
import logging
import multiprocessing
import os
import requests
import socket
import sys
import time

from debug import Debug
from apkhelper import ApkVersionInfo
from reporthelper import ReportHelper

from socket import error as socket_error

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
GlobalDelay = 1

# logging
logFile   = '{0}.log'.format(os.path.basename(__file__))
logLevel  = (logging.DEBUG if Debug.DEBUG else logging.INFO)
logFormat = '%(asctime)s %(levelname)s/%(funcName)s(%(process)-5d): %(message)s'


class AptoideCrawler(object):
    def __init__(self, report, dlFiles=[], dlFilesBeta=[], aptoideIds=[0]):
        self.report      = report
        self.dlFiles     = dlFiles
        self.dlFilesBeta = dlFilesBeta
        self.aptoideIds  = aptoideIds

    def logIdAndDate(self, itemApk):
        if itemApk['package'] not in list(self.report.dAllApks.keys()):
            logging.debug('{0}|{1}|{2}'.format(itemApk['id'], itemApk['added'], itemApk['package']))
        else:
            logging.info('{0}|{1}|{2}'.format(itemApk['id'], itemApk['added'], itemApk['package']))

    # END: def logIdAndDate(self, itemApk)

    def checkOneId(self, aptoideId):
        """
        checkOneId(aptoideId): Get APK specific information from the Aptoide API
                               and return it as an ApkVersionInfo object if it is
                               tracked by OpenGApps
        """
        file_name = '{0}.json'.format(aptoideId)
        url       = 'http://webservices.aptoide.com/webservices/2/getApkInfo/id:{0}/json'.format(aptoideId)
        data      = Debug.readFromFile(file_name)

        filenames = []
        if data == '':
            session = requests.Session()

            for x in range(1, 4):  # up to three tries
                wait = GlobalDelay * x
                # logging.info('Waiting {0} seconds before fetching {1}'.format(wait, file_name))
                time.sleep(wait)
                try:
                    logging.debug('Checking ({0}): {1}'.format(x, url))
                    resp = session.get(url)

                    if resp.status_code == http.client.OK:
                        # Append ID on good http response
                        filenames.append('id:' + str(aptoideId))

                        data = resp.json()
                        if 'status' in data and data['status'] == 'OK':
                            # Found an APK update the Max. ID
                            filenames[-1] = filenames[-1].replace('id:', 'max:')

                            avi = ApkVersionInfo(name        =data['apk']['package'],
                                                 arch        =data['apk'].get('cpu', 'all'),
                                                 sdk         =data['apk']['minSdk'],
                                                 dpi         =self.doDpiStuff(data['apk'].get('screenCompat', 'nodpi')),
                                                 ver         =data['apk']['vername'].split(' ')[0],  # Look at only the true version number
                                                 vercode     =data['apk']['vercode'],
                                                 download_src=data['apk']['path'],
                                                 malware=(data['malware'] if 'malware' in data else ''),  # We only have this key if vercode is in options
                                                 crawler_name=self.__class__.__name__
                                                 )

                            Debug.writeToFile(file_name, json.dumps(data, sort_keys=True,
                                              indent=4, separators=(',', ': ')), resp.encoding)

                            # Log AptoideID, Date, ApkID
                            self.logIdAndDate(data['apk'])

                            # Check for beta support
                            bCheckMore = False
                            if self.report.needsBetaSupport(avi):
                                import copy
                                avibeta = copy.deepcopy(avi)
                                avibeta.name += '.beta'
                                needBeta = self.report.isThisApkNeeded(avibeta)

                            # Do we already have it
                            if self.report.isThisApkNeeded(avi):
                                if (avi.malware['status'] == "warn" and
                                    avi.malware['reason']['signature_validated']['status'] == "failed" and
                                    avi.malware['reason']['signature_validated']['signature_from'] == "market"):  # signature matches market, but it does not pass verification
                                    logging.error('{0} is a corrupt or incomplete APK, ignored.'.format(avi.download_src))
                                else:
                                    # Are we sure we still need it after the additional info?
                                    if self.report.isThisApkNeeded(avi):
                                        filenames.append(self.downloadApk(avi))
                                # END: if avi.malware
                        else:
                            pass  # logging.error('data2[\'status\']: {0}, when fetching {1}, try {2}'.format(data.get('status', 'null'), file_name, x))

                        return filenames
                    else:
                        logging.error('HTTPStatus2: {0}, when fetching {1}, try {2}'.format(resp.status_code, file_name, x))
                except:
                    logging.exception('!!! Invalid JSON from: "{0}", retry in: {1}s'.format(url, wait))
            # END: for x
        # END: if data
        return filenames
    # END: def checkOneId

    def downloadApk(self, avi, isBeta=False):
        """
        downloadApk(avi, isBeta): Download the specified ApkInfo from Aptoide to APK file name
        """
        url = avi.download_src
        apkname = ('beta.' if isBeta else '') + avi.getFilename()

        if (avi.malware['status'] in ["trusted"] and
            avi.malware['reason']['signature_validated']['status'] == "passed" and
            avi.malware['reason']['signature_validated']['signature_from'] in ["market", "tester"]):
            ret = True
        else:  # IMPLIES avi.malware['reason']['signature_validated']['signature_from'] == "user"
            apkname = 'err.{0}err'.format(apkname[:-3])
            logging.error('{0} is a signed with a non-Playstore signature, be VERY careful about its authenticity.'.format(apkname))
            #print('NOTICE: {0} is a signed with a non-Playstore signature, be VERY careful about its authenticity.'.format(apkname), file=sys.stderr)
            ret = False

        logging.info('Downloading "{0}" from: {1}'.format(apkname, url))

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

            if r.status_code != http.client.OK:
                logging.exception('HTTP Status {0}. Failed to download: {1}'.format(r.status_code, apkname))
                return

            with open(apkname, 'wb') as local_file:
                local_file.write(r.content)

            if ret:
                logging.debug(('beta:' if isBeta else 'reg :') + apkname)
                return       (('beta:' if isBeta else ''     ) + apkname)
        except socket.error as serr:
            logging.exception('Socket error {0}. Failed to download: {1}'.format(serr, apkname))
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

    def crawl(self, threads=5):
        """
        crawl(): check all aptoide stores
        """
        path = os.path.dirname(__file__)
        if path:
            path += '/'
        storesfile = path + os.path.splitext(os.path.basename(__file__))[0] + '.config'

        self.aptoideIds = sorted(getStoredIds(storesfile))
        minId           = int(self.aptoideIds[0])
        maxId           = int(self.aptoideIds[-1])

        # Generate IDs missing from range
        storeIds = sorted(set(range(minId, maxId + 1)).difference(self.aptoideIds))
        logging.debug('Missing IDs: {0}'.format(storeIds))

        # Extend missing to look for new ones

        # This could be tuned, but for now a seem reasonable
        # If we are current, it will search 3000 AptoideIDs (they will all
        # be empty), then no new Max. ID will be logged
        storeIds.extend([x for x in range(maxId, maxId + 3000)])

        logging.info('Looking for {0} IDs from {1} to {2}'.format(len(storeIds), minId, maxId))

        # Start checking AptoideIDs ...
        p = multiprocessing.Pool(processes=threads, maxtasksperchild=5)  # Run only 5 tasks before re-placing the process; a lot of sequential requests from one IP still trigger 503, but the delay mechanism then kicks and in general fixes a retry
        r = p.map_async(unwrap_self_checkOneId, list(zip([self] * len(storeIds), storeIds)), callback=unwrap_callback)
        r.wait()

        localNewIds    = []
        localNewMaxIds = []
        (self.dlFiles, self.dlFilesBeta, localNewIds, localNewMaxIds) = unwrap_getresults()

        localNewMaxId = max(max(localNewMaxIds), maxId)

        # Merge original and new
        temp = [x for x in localNewIds if x <= localNewMaxId]  # Don't keep > max found
        temp.extend(self.aptoideIds)                           # Extend existing from file

        logging.info('Found for {0} IDs from {1} to {2}'.format(len(set(temp)), minId, localNewMaxId))

        setStoreIds(storesfile, sorted(set(temp)))             # Store the New Unique sorted list!
    # END: crawl():
# END: class AptoideCrawler


class StoresException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


def getStoredIds(storesfile):
    '''
    getStoredIds(): Retrieve Highest Aptoide ID crawled from the file
    '''
    aptoideIds = []  # Default start
    if os.path.isfile(storesfile):
        with open(storesfile, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        idRange = line.split('-')
                        if len(idRange) == 1:
                            aptoideIds.append(int(idRange[0]))
                        elif len(idRange) == 2:
                            aptoideIds.extend(list(range(int(idRange[0]), int(idRange[1])+1)))
                        else:
                            raise StoresException('Malformed line in Stores file', storesfile)
                    except:
                        raise StoresException('Malformed line in Stores file', storesfile)
    else:
        raise StoresException('Stores file does not exist', storesfile)

    return aptoideIds
# END: def getStoredIds


def setStoreIds(storesfile, aptoideIds):
    '''
    setStoreIds(): Append Highest Aptoide ID crawled to the file
    '''
    from itertools import groupby
    from operator import itemgetter

    idRanges = []
    for k, g in groupby(enumerate(aptoideIds), lambda x: x[0]-x[1]):
        idRanges.append(list(map(itemgetter(1), g)))

    if os.path.isfile(storesfile):
        try:
            with open(storesfile, "a") as f:
                sep  = '#- {0} ({1}) '.format(datetime.datetime.utcnow(), os.environ['LOGNAME'])
                sep += '-' * (80-len(sep))
                f.write(sep + '\n')
                for idRange in idRanges:
                    if len(idRange) == 1:
                        f.write(str(idRange[0]) + '\n')
                    else:
                        f.write(str(idRange[0]) + '-' + str(idRange[-1]) + '\n')
        except:
            raise StoresException('Error appending line to Stores file', storesfile)
    else:
        raise StoresException('Stores file does not exist', storesfile)
# END: def setStoreIds

nonbeta   = []
beta      = []
newIds    = []
newMaxIds = []

def unwrap_callback(results):
    for resultlist in results:
        if resultlist:
            for result in resultlist:
                if result:
                    if result.startswith('id:'):
                        newIds.append(int(result[3:]))
                    elif result.startswith('max:'):
                        tmpMax = int(result[4:])
                        newIds.append(tmpMax)
                        newMaxIds.append(tmpMax)
                    elif result.startswith('beta:'):
                        beta.append(result[5:])
                    else:
                        nonbeta.append(result)


def unwrap_getresults():
    return (nonbeta, beta, newIds, newMaxIds)


def unwrap_self_checkOneId(arg, **kwarg):
    return AptoideCrawler.checkOneId(*arg, **kwarg)

if __name__ == "__main__":
    """
    main(): single parameter for report_sources.sh output
    """
    logging.basicConfig(filename=logFile, filemode='w', level=logLevel, format=logFormat)
    logging.getLogger("requests").setLevel(logging.WARNING)

    lines = ''
    if len(sys.argv[1:]) == 1:
        with open(sys.argv[1]) as report:
            lines = report.readlines()
    else:
        lines = sys.stdin.readlines()

    report = ReportHelper(lines)

    if len(list(report.getAllApkIds())) == 0:
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
