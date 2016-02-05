import logging
import re


class ApkVersionInfo(object):
    """ApkVersionInfo"""
    def __init__(self, name='', arch='', sdk='', dpi='', ver='', vercode='', scrape_src='', download_src=''):
        super(ApkVersionInfo, self).__init__()

        sName  = '^(?P<name>.*)(?P<extra>\.(leanback|beta))$'
        reName = re.compile(sName)

        sVer   = '^(?P<ver>.*)(?P<extra>(-.*)|(\.(arm|arm\.arm_neon|arm64|x86|large|small)))$'  # .release?
        reVer  = re.compile(sVer)

        self.name         = name
        self.extraname    = None  # used for beta/leanback versions
        self.arch         = arch
        self.sdk          = 0 if sdk == '' else int(sdk)
        self.dpi          = dpi
        self.ver          = ver   # used for comparing (could be shortened later)
        self.realver      = ver   # used for full/original versions
        self.vercode      = 0 if vercode == '' else  int(vercode)

        self.scrape_src   = scrape_src
        self.apk_name     = ''
        self.download_src = download_src

        m = reName.match(self.name)
        if m:
            self.extraname = self.name
            self.name      = m.group('name')

            # Let's keep .beta its own package for now
            if m.group('extra') == '.beta':
                self.name = self.extraname

        if 'com.google.android.apps.docs' in self.name:
            self.ver = self.ver[0:-3]

        m = reVer.match(self.ver)
        if m:
            self.ver = m.group('ver')

    def fullString(self, max):
        mymax = max
        if self.realver != self.ver:
            mymax += self.realver[len(self.ver):]

        return '{0}|{1}|{2}|{3}|{4}|{5}'.format(self.name,
                                                self.arch,
                                                self.sdk,
                                                self.dpi,
                                                mymax,
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
