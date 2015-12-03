import logging
import re


class ApkVersionInfo(object):
    """ApkVersionInfo"""
    def __init__(self, name='', arch='', sdk='', dpi='', ver='', vercode='', scrape_url=''):
        super(ApkVersionInfo, self).__init__()

        sName  = '^(?P<name>.*)(?P<extra>\.(leanback|beta))$'
        reName = re.compile(sName)

        sVer   = '^(?P<ver>.*)(?P<extra>[-.](leanback|tv|arm|arm\.arm_neon|armeabi-v7a|arm64|arm64-v8a|x86|large|small|xxhdpi))$'
        reVer  = re.compile(sVer)

        self.name         = name
        self.extraname    = None  # used for beta/leanback versions
        self.arch         = arch
        self.sdk          = sdk
        self.dpi          = dpi
        self.ver          = ver
        self.realver      = None  # used for full versions
        self.vercode      = vercode

        self.scrape_url   = scrape_url
        self.apk_name     = ''
        self.download_url = ''

        m = reName.match(self.name)
        if m:
            self.extraname = self.name
            self.name      = m.group('name')

        if 'com.google.android.apps.docs' in self.name:
            self.realver = self.ver[-3:]

        m = reVer.match(self.ver)
        if m:
            self.ver     = m.group('ver')
            self.realver = m.group('extra')

    def fullString(self, max):
        return '{0}|{1}|{2}|{3}|{4}{5}|{6}'.format(self.name,
                                                   self.arch,
                                                   self.sdk,
                                                   self.dpi,
                                                   max,
                                                   self.realver if self.realver else '',
                                                   self.vercode )

    def __lt__(self, other):
        return self.__cmp__(other) == -1

    def __cmp__(self, other):
        if self.ver == '' or other.ver == '':
            logging.error('AVI.cmp(): self.ver or other.ver is empty [{0},{1}]'.format(self.ver, other.ver))
            return cmp(self.name, other.name)
        else:
            import re

            # Make blank-->'0', replace - and _ with . and split into parts
            p1 = [int(x if x != '' else '0') for x in re.sub('[A-Za-z]+', '',  self.ver.replace('-', '.').replace('_', '.')).split('.')]
            p2 = [int(x if x != '' else '0') for x in re.sub('[A-Za-z]+', '', other.ver.replace('-', '.').replace('_', '.')).split('.')]

            # fill up the shorter version with zeros ...
            lendiff = len(p1) - len(p2)
            if lendiff > 0:
                p2.extend([0] * lendiff)
            elif lendiff < 0:
                p1.extend([0] * (-lendiff))

            for i, p in enumerate(p1):
                ret = cmp(p, p2[i])
                if ret:
                    return ret
            return 0
    # END: def cmp:

    def __str__(self):
        return str(self.__dict__)
# END: class ApkVersionInfo()
