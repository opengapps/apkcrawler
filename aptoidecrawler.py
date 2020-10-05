#!/usr/bin/env python3

#
# Required Modules
# - requests
#

from datetime import datetime, timedelta
import pytz
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
    def __init__(self, report, dlFiles=[], dlFilesBeta=[], runInfo={}):
        self.report      = report
        self.dlFiles     = dlFiles
        self.dlFilesBeta = dlFilesBeta
        self.runInfo     = runInfo

    def logIdAndDate(self, itemApk):
        if itemApk['package'] == 'org.opengapps.app':
            logging.info('*** HEY IT IS OPENGAPPS ON APTOIDE *** {0}|{1}|{2}'.format(itemApk['id'], itemApk['modified'], itemApk['package']))
        elif itemApk['package'] not in list(self.report.dAllApks.keys()):
            logging.debug('{0}|{1}|{2}'.format(itemApk['id'], itemApk['modified'], itemApk['package']))
        else:
            logging.info('{0}|{1}|{2}'.format(itemApk['id'], itemApk['modified'], itemApk['package']))

    # END: def logIdAndDate(self, itemApk)

    def checkOneId(self, aptoideId):
        """
        checkOneId(aptoideId): Get APK specific information from the Aptoide API
                               and return it as an ApkVersionInfo object if it is
                               tracked by OpenGApps
        """
        file_name = '{0}.json'.format(aptoideId)
        url       = 'http://ws75.aptoide.com/api/7/app/getMeta/app_id={0}'.format(aptoideId)
        data      = Debug.readFromFile(file_name)

        run = {}
        run['id']       = aptoideId
        run['status']   = 'fail'  # 'fail', 'empty', 'good'
        run['time']     = ''
        run['filename'] = ''

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
                        run['status'] = 'empty'

                        data = resp.json()
                        if 'info' in data and 'status' in data['info'] and data['info']['status'] == 'OK':
                            # Found an APK update the Max. ID
                            run['status'] = 'good'
                            run['time']   = data['data']['modified']

                            theArchs = data['data']['file']['hardware'].get('cpus', [])
                            _arch = 'all'
                            if len(theArchs) > 0:
                                _arch = ','.join(theArchs)

                            avi = ApkVersionInfo(name        =data['data']['package'],
                                                 arch        =_arch,
                                                 sdk         =data['data']['file']['hardware']['sdk'],
                                                 dpi         =self.doDpiStuff(data['data']['file']['hardware'].get('densities', [])),
                                                 ver         =data['data']['file']['vername'].split(' ')[0],  # Look at only the true version number
                                                 vercode     =data['data']['file']['vercode'],
                                                 download_src=data['data']['file']['path'],
                                                 malware=(data['data']['file']['malware'] if 'malware' in data['data']['file'] else ''),  # We only have this key if vercode is in options
                                                 crawler_name=self.__class__.__name__
                                                 )

                            Debug.writeToFile(file_name, json.dumps(data, sort_keys=True,
                                              indent=4, separators=(',', ': ')), resp.encoding)

                            # Log AptoideID, Date, ApkID
                            self.logIdAndDate(data['data'])

                            # Check for beta support
                            bCheckMore = False
                            if self.report.needsBetaSupport(avi):
                                import copy
                                avibeta = copy.deepcopy(avi)
                                avibeta.name += '.beta'
                                needBeta = self.report.isThisApkNeeded(avibeta)

                            # Do we already have it
                            if self.report.isThisApkNeeded(avi):
                                if (avi.malware['rank'] == "warn" and
                                    avi.malware['reason']['signature_validated']['status'] == "failed" and
                                    avi.malware['reason']['signature_validated']['signature_from'] == "market"):  # signature matches market, but it does not pass verification
                                    logging.error('{0} is a corrupt or incomplete APK, ignored.'.format(avi.download_src))
                                else:
                                    # Are we sure we still need it after the additional info?
                                    if self.report.isThisApkNeeded(avi):
                                        run['filename'] = self.downloadApk(avi)
                                # END: if avi.malware

                            if avi.name == 'org.opengapps.app':
                                run['filename'] = '{0}-{1}_aptoideId-{2}.stub.apk'.format(avi.name, avi.vercode, aptoideId)
                        else:
                            pass  # logging.error('data2[\'status\']: {0}, when fetching {1}, try {2}'.format(data.get('status', 'null'), file_name, x))

                        return run
                    elif resp.status_code in [http.client.UNAUTHORIZED,  # 401
                                              http.client.FORBIDDEN,     # 403
                                              http.client.NOT_FOUND,     # 404
                                              http.client.GONE]:         # 410
                        run['status'] = 'empty'
                        return run
                    else:
                        pass  # logging.error('HTTPStatus2: {0}, when fetching {1}, try {2}'.format(resp.status_code, file_name, x))
                except:
                    logging.exception('!!! Invalid JSON from: "{0}", retry in: {1}s'.format(url, wait))
            # END: for x
        # END: if data
        return run
    # END: def checkOneId

    def downloadApk(self, avi, isBeta=False):
        """
        downloadApk(avi, isBeta): Download the specified ApkInfo from Aptoide to APK file name
        """
        url = avi.download_src
        apkname = ('beta.' if isBeta else '') + avi.getFilename()

        if ((avi.malware['rank'] in ["TRUSTED"] and
             avi.malware['reason']['signature_validated']['status'] == "passed" and
             avi.malware['reason']['signature_validated']['signature_from'] in ["market", "tester"])
            or avi.name == 'com.google.android.youtube'):
            ret = True
        else:  # IMPLIES avi.malware['reason']['signature_validated']['signature_from'] == "user"
            apkname = 'err.{0}err'.format(apkname[:-3])
            logging.error('{0} is a signed with a non-Playstore signature, be VERY careful about its authenticity.'.format(apkname))
            #print('NOTICE: {0} is a signed with a non-Playstore signature, be VERY careful about its authenticity.'.format(apkname), file=sys.stderr)
            ret = False

        logging.info('Downloading "{0}" from: {1}'.format(apkname, url))

        try:
            if os.path.exists(apkname):
                logging.info('{0} already exists'.format(apkname))
                return

            if os.path.exists(os.path.join('.', 'apkcrawler', apkname)):
                logging.info('{0} already exists (in ./apkcrawler/)'.format(apkname))
                return

            if os.path.exists(os.path.join('.', 'priv-app', apkname)):
                logging.info('{0} already exists (in ./priv-app/)'.format(apkname))
                return

            if os.path.exists(os.path.join('..', 'apkcrawler', apkname)):
                logging.info('{0} already exists (in ../apkcrawler/)'.format(apkname))
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
        if len(screenCompat) == 0:
            return 'nodpi'

        dpis = {}
        for split in screenCompat:
            dpis[str(split[1])] = ''

        return delim.join(sorted(dpis.keys()))
    # END: def doDpiStuff



    def crawl(self, threads=5):
        """
        crawl(): check all aptoideIds
        """
        path = os.path.dirname(__file__)
        if path:
            path += '/'
        configfile = path + os.path.splitext(os.path.basename(__file__))[0] + '.config'

        self.runInfo      = getStoredIds(configfile)  # Get the last runInfo from file (lastId, lastIdTime, missingIds)
        tmpEmptyResultIds = []                        # List of empty results from crawling used to create "last 500 entries"

        # Date/Time info to know when to stop crawling...
        isdst_now_in = lambda zonename: bool(datetime.now(pytz.timezone(zonename)).dst())

        # delta    = timedelta(hours=(1 if isdst_now_in('Europe/Lisbon') else 0), minutes=-3)
        delta    = timedelta(minutes=-5)
        currTime = datetime.utcnow()
        lastTime = datetime.strptime(self.runInfo['lastIdTime'], '%Y-%m-%d %H:%M:%S')
        logging.debug('currTime: {0}, lastTime: {1}, delta: {2}'.format(str(currTime), str(lastTime), str((currTime + delta) - lastTime)))

        bFoundNewMax = True  # Flag to stop crawling when we do not appear caught up based on date/time
                             # This happens when aptoide 'stops' uploading for a period of time...

        # Loop over crawler while we are not caught up and are finding new entries
        while bFoundNewMax and ((currTime + delta) > lastTime):
            maxId = self.runInfo['lastId']

            # Generate IDs missing from range
            storeIds = self.runInfo['missingIds']
            if len(storeIds) > 0:
                logging.debug('Missing IDs: {0}'.format(storeIds))

            # Clear missing
            self.runInfo['missingIds'] = []

            # Extend missing to look for new ones

            # This could be tuned, but for now a seem reasonable
            # If we are current, it will search 500 AptoideIDs (if they
            # are all empty, then no new Max. ID will be logged)
            storeIds.extend([x for x in range(maxId, maxId + 500)])

            logging.info('Looking for {0} IDs from {1}'.format(len(storeIds), maxId))

            # Start checking AptoideIDs ...
            p = multiprocessing.Pool(processes=threads, maxtasksperchild=5)  # Run only 5 tasks before re-placing the process; a lot of sequential requests from one IP still trigger 503, but the delay mechanism then kicks and in general fixes a retry
            r = p.map_async(unwrap_self_checkOneId, list(zip([self] * len(storeIds), storeIds)), callback=unwrap_callback)
            r.wait()
            p.close()

            # Proces this run's results
            localAllResults = unwrap_getresults()

            logging.debug('localAllResults: {0}'.format(len(localAllResults)))

            bFoundNewMax = False
            for r in localAllResults:
                # If we have 'good' entries, look for new maxId and update beta/non-beta file names
                if r['status'] == 'good':
                    if self.runInfo['lastId'] < int(r['id']):
                        bFoundNewMax = True
                        self.runInfo['lastId'] = int(r['id'])        # Get LastID
                        self.runInfo['lastIdTime'] = r['time']       # Get LastID's Time

                    # Update Filenames Found
                    if r['filename']:
                        tmpfn = r['filename']
                        if r['filename'].startswith('beta:'):
                            tmpfn = tmpfn[5:]  # remove 'beta:'
                            if tmpfn not in self.dlFilesBeta:
                                self.dlFilesBeta.append(tmpfn)
                        else:
                            if tmpfn not in self.dlFiles:
                                self.dlFiles.append(tmpfn)
                # Add 'fail' entries to missingIds for recrawling later (next run or next loop)
                elif r['status'] == 'fail':
                    self.runInfo['missingIds'].append(int(r['id']))  # Get Missing IDs
                # Add 'empty' entries to temp list so we can recrawl within last 500 empties next run (but not next loop)
                elif r['status'] == 'empty':
                    tmpEmptyResultIds.append(int(r['id']))
            # END: for r in localAllResults:

            # Refresh Date/Time status for loop
            currTime = datetime.utcnow()
            lastTime = datetime.strptime(self.runInfo['lastIdTime'], '%Y-%m-%d %H:%M:%S')

            logging.debug('currTime: {0}, lastTime: {1}, delta: {2}'.format(str(currTime), str(lastTime), str((currTime + delta) - lastTime)))
        # END: while bNewMaxIdFound:

        # Get Empty Entries within 500 of MaxId (search back 500 for slow adding entries???)
        for emptyId in tmpEmptyResultIds:
            if (emptyId + 500) > self.runInfo['lastId'] > emptyId:
                self.runInfo['missingIds'].append(emptyId)

        # Dedupe and sort missing list
        self.runInfo['missingIds'] = sorted(set(self.runInfo['missingIds']))

        setStoreIds(configfile, self.runInfo)  # Store the New Unique sorted list!
    # END: crawl():
# END: class AptoideCrawler


class StoresException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


def getStoredIds(configfile):
    '''
    getStoredIds(): Retrieve latest crawl information from the file
    '''
    run = {}
    run['lastId']     = 0
    run['lastIdTime'] = str(datetime.utcnow())
    run['missingIds'] = []

    if os.path.isfile(configfile):
        with open(configfile, 'r') as data_file:
            try:
                data = json.load(data_file)
                run  = data['runs'][-1]
                run['missingIds'] = data['missingIds']
            except:
                raise StoresException('Malformed Stores file', configfile)
    else:
        raise StoresException('Stores file does not exist', configfile)

    return run
# END: def getStoredIds


def setStoreIds(configfile, runInfo):
    '''
    setStoreIds(): Append Highest Aptoide ID crawled to the file
    '''
    data = {}
    data['runs'] = []

    if os.path.isfile(configfile):
        # Read current file
        with open(configfile, 'r') as data_file:
            try:
                data = json.load(data_file)
            except:
                raise StoresException('Malformed Stores file', configfile)

        # Add this run to the JSON 'runs' list
        data['missingIds'] = runInfo['missingIds']
        del runInfo['missingIds']
        runInfo['runBy'] = os.environ['LOGNAME']
        data['runs'].append(runInfo)

        # Write updated file
        with open(configfile, "w") as data_file:
            try:
                json.dump(data, data_file, sort_keys=True, indent=4, separators=(',', ': '))
            except:
                raise StoresException('Error appending line to Stores file', configfile)
    else:
        raise StoresException('Stores file does not exist', configfile)
# END: def setStoreIds

allresults = []

def unwrap_callback(results):
    for result in results:
        if result:
            allresults.append(result)


def unwrap_getresults():
    return (allresults)


def unwrap_self_checkOneId(arg, **kwarg):
    return AptoideCrawler.checkOneId(*arg, **kwarg)

if __name__ == "__main__":
    """
    main(): single parameter for report_sources.sh output
    """
    # Wait for lock file
    lockfile = logFile + '.lock'
    killfile = logFile + '.kill'
    while os.path.isfile(lockfile):
        time.sleep(60.0)
        # Check for kill file to end wait lock
        if os.path.isfile(killfile):
            os.remove(killfile)
            exit(1)

    # Grab lock file
    with open(lockfile, 'w') as lock_file:
        lock_file.write('lock')

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

    # Release lock file
    os.remove(lockfile)
