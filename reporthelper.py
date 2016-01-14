import re
import logging
from apkhelper import ApkVersionInfo


class ReportHelper(object):
    """ReportHelper"""
    def __init__(self, lines):
        self.dAllApks      = self.processReportSourcesOutput(lines)
        self.maxVerEachApk = self.getMaxVersionDict()
        self.minSdkEachApk = self.getMinSdkDict()
        self.appsNeeded    = self.showMissingApks()
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

                # Check if supported and add if it is
                if name not in self.dAllApks.keys():
                    self.dAllApks[name] = []

                arch = m.group('arch').strip()
                sdk  = m.group('sdk').strip()
                dpi  = m.group('dpi').strip()
                ver  = m.group('ver').strip()
                code = m.group('code').strip()
                avi  = ApkVersionInfo(name, arch, sdk, dpi, ver, code)

                self.dAllApks[name].append(avi)
            # END: if m:
        # END: for line
    # END: def processReportSourcesOutput

    def getMaxVersionDict(self):
        """
        getMaxVersionDict(): Populate a dictionary of the max version of each APK
        """
        self.maxVerEachApk = {}

        for k in sorted(self.dAllApks.keys()):
            k2 = self.dAllApks[k][0].maxname
            if k not in self.maxVerEachApk:
                max1 = max(apk for apk in self.dAllApks[k]).ver
                max2 = max1

                # Check for "non-leanback" versions for max comparison
                if k2 in self.dAllApks:
                    max2 = max(apk for apk in self.dAllApks[k2]).ver

                self.maxVerEachApk[k] = max(max1, max2)

                # Special case for Drive, Docs, Sheets and Slides
                # Remove the last '.XX' since it is CPU/DPI specific
                if 'com.google.android.apps.docs' in k:
                    self.maxVerEachApk[k] = self.maxVerEachApk[k][0:-3]
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
                minSdk = min(minSdk, 19)  # We suport down to 19
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

        for k in self.dAllApks.keys():
            thisappsneeded = []
            for a in self.dAllApks[k]:
                maxApk = ApkVersionInfo(ver = self.maxVerEachApk[k])
                if '2280749' in maxApk.ver:  # This excludes 'from factor image' apks
                    maxApk.ver = '0'
                    thisappsneeded = []
                if a.ver < maxApk.ver:
                    logging.debug('{0}: {1} < maxApk.ver: {2}'.format(k, a.ver, maxApk.ver))
                    thisappsneeded.append(a.fullString(self.maxVerEachApk[k]))
            if len(thisappsneeded) != 0:
                self.appsNeeded.extend(thisappsneeded)
        # END: for k in

        for a in sorted(self.appsNeeded):
            logging.info(a)
    # END: def showMissingApks

    def isThisApkNeeded(self):
        """
        def isThisApkNeeded(): Return true if this information passed in is needed per the report data
                               that this class was initialized with
        """
        return True
    # END: def isThisApkNeeded():
# END: class ReportHelper
