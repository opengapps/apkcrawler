import re
import logging
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

        sColumns = ['(?P<name>com\.[^|]*)', '(?P<arch>[^|]*)', '(?P<sdk>[^|]*)', '(?P<dpi>[^|]*)',
                    '(?P<ver>[^|]*)',       '(?P<code>[^|]*)', '(?P<sig>[^|]*)']
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
                avi  = ApkVersionInfo(name, arch, sdk, dpi, ver, code)

                # Check if supported and add if it is
                if avi.vercode in [1, 19, 22, 23]:  # Ignore factory image files
                    continue

                if avi.name not in self.dAllApks.keys():
                    self.dAllApks[avi.name] = []

                self.dAllApks[avi.name].append(avi)
            # END: if m:
        # END: for line
    # END: def processReportSourcesOutput

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
        for k in self.dAllApks.keys():
            thisappsneeded = []
            for a in self.dAllApks[k]:
                maxApk = ApkVersionInfo(ver = self.maxVerEachApk[k])
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
        if avi.name not in self.dAllApks.keys():
            return False

        # Do we have the requested vercode already?
        if avi.vercode != 0:
            if filter(lambda apk: apk.vercode == avi.vercode, self.dAllApks[avi.name]):
                return False

        # Is it < maxVersion?
        if avi.ver != '':
            maxApkInfo = ApkVersionInfo(name=avi.name, ver=self.maxVerEachApk[avi.name])
            maxApkInfo.ver=self.maxVerEachApk[avi.name] #very ugly hack to FORCE the correct ver used in comparioson for docs apks
            if avi < maxApkInfo:
                return False

        # Is it < minSdk?
        if avi.sdk != 0:
            if avi.sdk < self.minSdkEachApk[avi.name]:
                logging.debug('SdkTooLow: {0}({1})'.format(avi.name, avi.sdk))
                return False

        # Are we dealing with a app that has beta support?
        #   Examples: WebView, GoogleApp
        if self.needsBetaSupport(avi):
            # TODO: Needs more thought (?)
            if not avi.name.endswith('.beta'):  # Make sure we don't promote a beta app to non-beta
                # Do we have the requested vercode (in beta) already?
                if avi.vercode != '':
                    if filter(lambda apk: apk.vercode == avi.vercode, self.dAllApks[avi.name + '.beta']):
                        return False

                # Is it >= maxVersion (for beta)?
                if avi.ver != '':
                    maxApkInfo = ApkVersionInfo(name=avi.name, ver=self.maxVerEachApk[avi.name + '.beta'])
                    if avi >= maxApkInfo:
                        return False

        # END: if self.needsBetaSupport(avi):

        return True
    # END: def isThisApkNeeded():

    def needsBetaSupport(self, avi):
        """
        def needsBetaSupport(): Returns True if beta support is needed, else False
        """
        return (avi.name.endswith('.beta') or avi.name + '.beta' in self.dAllApks)
    # END: def needsBetaSupport(self, avi):
# END: class ReportHelper
