import logging
import re
from apkhelper import ApkVersionInfo


class ReportHelper(object):
    """ReportHelper"""
    def __init__(self, lines):
        self.dAllApks      = {}
        self.maxVerEachApk = {}
        self.minSdkEachApk = {}
        self.appsNeeded    = []

        # Fill member dict and lists
        self.processReportSourcesOutput(lines)
        self.getMaxVersionDict()
        self.getMinSdkDict()
        self.showMissingApks()
    # END: __init__

    def processReportSourcesOutput(self, lines):
        """
        processReportSourcesOutput(lines): Populate a dictionary of all APKs and versions in report
                                           created by report_sources.sh
        """
        self.dAllApks = {}

        sColumns = ['(?P<name>[a-z][^|]*)', '(?P<arch>[^|]*)', '(?P<sdk>[^|]*)', '(?P<dpi>[^|]*)',
                    '(?P<ver>[^|]*)',       '(?P<code>[^|]*)', '(?P<mib>[^|]*)', '(?P<sig>[^|]*)']
        pattern  = '^\s+' + '\|'.join(sColumns) + '$'
        reLine   = re.compile(pattern)

        for line in lines:
            m = reLine.match(line)
            if m:
                name = m.group('name').strip()
                arch = m.group('arch').strip()
                sdk  = m.group('sdk').strip()
                dpi  = m.group('dpi').strip()
                ver  = m.group('ver').strip()
                code = m.group('code').strip()
                avi  = ApkVersionInfo(name=name,
                                      arch=arch,
                                      sdk=sdk,
                                      dpi=dpi,
                                      ver=ver,
                                      vercode=code)

                # Check if supported and add if it is
                if avi.vercode in [1, 19, 21, 22, 23, 24, 25, 26, 27, 28, 29]:  # Ignore factory image files
                    continue

                if avi.name not in list(self.dAllApks.keys()):
                    self.dAllApks[avi.name] = []

                self.dAllApks[avi.name].append(avi)
            # END: if m:
        # END: for line
    # END: def processReportSourcesOutput

    def getAllApkIds(self, beta=False, playstoreCaps=False):
        apkIds = self.dAllApks.keys()
        regexStr = '^.*$'
        if not beta:
            regexStr = '^.*\.beta$'
        reBeta = re.compile(regexStr)
        if playstoreCaps:
            apkIds = [apkid.replace('googlecamera', 'GoogleCamera') for apkid in apkIds]
        return list(filter(lambda x: not reBeta.match(x), apkIds))
    # END: def getAllApkIds

    def getMaxVersionDict(self):
        """
        getMaxVersionDict(): Populate a dictionary of the max version of each APK
        """
        self.maxVerEachApk = {}

        for k in sorted(self.dAllApks.keys()):
            k2 = self.dAllApks[k][0].name
            if k not in self.maxVerEachApk:
                max1 = max(apk for apk in self.dAllApks[k]).ver
                max2 = max1

                # Check for "non-leanback" versions for max comparison
                if k2 in self.dAllApks:
                    max2 = max(apk for apk in self.dAllApks[k2]).ver

                self.maxVerEachApk[k] = max(max1, max2)
            # END: if not k
            logging.debug('{0} - maxVer: {1}'.format(k, self.maxVerEachApk[k]))
        # END: for k
    # END: def getMaxVersionDict

    def getMinSdkDict(self):
        """
        getMinSdkDict(): Populate a dictionary of the minimum sdk for each APK
        """
        self.minSdkEachApk = {}

        for k in sorted(self.dAllApks.keys()):
            if k not in self.minSdkEachApk:
                minSdk = min(int(apk.sdk) for apk in self.dAllApks[k])
                minSdk = min(minSdk, 19)  # We support down to 19
                self.minSdkEachApk[k] = minSdk
            # END: if not k

            logging.debug('{0} - minSdk: {1}'.format(k, self.minSdkEachApk[k]))
        # END: for k
    # END: def getMinSdkDict

    def showMissingApks(self):
        """
        showMissingApks(): Populate a list of the needed APKs
        """
        self.appsNeeded = []

        # NOTE: This code currently only shows older apks (that need updating).
        #       @mfonville has another scheme based up vercode rules for each
        #       apkid that would be more complete
        for k in list(self.dAllApks.keys()):
            thisappsneeded = []
            for a in self.dAllApks[k]:
                maxApk = ApkVersionInfo(ver=self.maxVerEachApk[k])
                if a.ver < maxApk.ver:
                    logging.debug('{0}: {1} < maxApk.ver: {2}'.format(k, a.ver, maxApk.ver))
                    thisappsneeded.append(a.fullString(self.maxVerEachApk[k]))
            if len(thisappsneeded) != 0:
                self.appsNeeded.extend(thisappsneeded)
        # END: for k in

        for a in sorted(self.appsNeeded):
            logging.info(a)
    # END: def showMissingApks

    def isThisApkNeeded(self, avi):
        """
        def isThisApkNeeded(): Return true if this information passed in is needed per the report data
                               that this class was initialized with
        """
        # Against the list we are looking for
        if avi.lowername not in list(self.dAllApks.keys()):
            return False

        logging.debug(avi.fullString(avi.ver))
        logging.debug('Do we have already vercode?')
        # Do we have the requested vercode already? Or do we have a higher vercode while there is only one variant of these apps?
        if avi.vercode != 0:
            if ([apk for apk in self.dAllApks[avi.lowername] if apk.vercode == avi.vercode]) or (avi.isVercodeAbsolute() and ([apk for apk in self.dAllApks[avi.lowername] if apk.vercode >= avi.vercode])):
                logging.debug('    DON\'T NEED')
                return False
        else:  # We only need to run the realvername match if we could not compare the vercode itself
            logging.debug('Can we use an absolute realvername match?')
            if avi.isRealverAbsolute():
                logging.debug('Do we have already a matching absolute realvername?')
                # Do we have the requested realver already?
                if avi.realver != '':
                    if [apk for apk in self.dAllApks[avi.lowername] if apk.realver == avi.realver]:
                        logging.debug('    DON\'T NEED')
                        return False

        logging.debug('Is it less than maxVersion?')
        # Is it < maxVersion?
        if avi.ver != '':
            maxApkInfo = ApkVersionInfo(name=avi.lowername, ver=self.maxVerEachApk[avi.lowername])
            if avi < maxApkInfo:
                logging.debug('    DON\'T NEED')
                return False

        logging.debug('Is SDK a number?')  # If it is not a number, but a letter it is a preview and undesired by Open GApps
        if avi.sdk and not isinstance(avi.sdk, int):
            logging.debug('SdkNotNumber: {0}({1})'.format(avi.name, avi.sdk))
            return False

        logging.debug('Is Target a number?')  # If it is not a number, but a letter it is a preview and undesired by Open GApps
        if avi.target and not isinstance(avi.target, int):
            logging.debug('TargetNotNumber: {0}({1})'.format(avi.name, avi.target))
            return False

        logging.debug('Is it less than minSdk?')
        # Is it < minSdk?
        if avi.sdk != 0:
            if avi.sdk < self.minSdkEachApk[avi.lowername]:
                logging.debug('SdkTooLow: {0}({1})'.format(avi.name, avi.sdk))
                return False

        # Are we dealing with a app that has beta support?
        #   Examples: WebView, GoogleApp
        if self.needsBetaSupport(avi):
            logging.debug('beta support ...')
            # TODO: Needs more thought (?)
            if not avi.lowername.endswith('.beta'):  # Make sure we don't promote a beta app to non-beta
                logging.debug('Do we have already vercode? (beta)')
                # Do we have the requested vercode (in beta) already?
                if avi.vercode != 0:
                    if [apk for apk in self.dAllApks[avi.lowername + '.beta'] if apk.vercode == avi.vercode]:
                        logging.debug('    DON\'T NEED')
                        return False

                logging.debug('Is it greater than or equal to maxVersion?')
                # Is it >= maxVersion (for beta)?
                if avi.ver != '':
                    maxApkInfo = ApkVersionInfo(name=avi.lowername, ver=self.maxVerEachApk[avi.lowername + '.beta'])
                    if avi >= maxApkInfo:
                        logging.debug('    DON\'T NEED')
                        return False
                logging.debug('++++ NEED IT ... (beta)')

        # END: if self.needsBetaSupport(avi):
        logging.debug('++++ NEED IT ...')
        return True
    # END: def isThisApkNeeded():

    def needsBetaSupport(self, avi):
        """
        def needsBetaSupport(): Returns True if beta support is needed, else False
        """
        return (avi.lowername.endswith('.beta') or avi.lowername + '.beta' in self.dAllApks)
    # END: def needsBetaSupport(self, avi):
# END: class ReportHelper
