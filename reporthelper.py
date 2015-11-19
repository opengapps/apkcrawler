import re
import logging
from apkhelper import ApkVersionInfo


class ReportHelper(object):
    """ReportHelper"""
    @staticmethod
    def processReportSourcesOutput(lines):
        """
        processReportSourcesOutput(lines): Return a dictionary of all APKs and versions in report
                                           created by report_sources.sh
        """
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
        return dAllApks
    # END: def processReportSourcesOutput

    @staticmethod
    def getMaxVersionDict(dAllApks):
        """
        getMaxVersionDict():
        """
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

        return (maxVerEachApk, minSdkEachApk)
    # END: def getMaxVersionDict

    @staticmethod
    def showMissingApks(dAllApks, maxVerEachApk):
        """
        showMissingApks(dAllApks):
        """
        appsneeded = []
        for k in dAllApks.keys():
            thisappsneeded = []
            for a in dAllApks[k]:
                maxApk = ApkVersionInfo(ver = maxVerEachApk[k])
                if '2280749' in maxApk.ver:
                    maxApk.ver = '0'
                    thisappsneeded = []
                if a.ver < maxApk.ver:
                    logging.debug('{0}: {1} < maxApk.ver: {2}'.format(k, a.ver, maxApk.ver))
                    thisappsneeded.append(a.fullString(maxVerEachApk[k]))
            if len(thisappsneeded) != 0:
                appsneeded.extend(thisappsneeded)
        # END: for k in

        for a in sorted(appsneeded):
            logging.info(a)
    # END: def showMissingApks
# END: class ReportHelper
