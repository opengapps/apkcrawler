from functools import total_ordering
import logging
import re

oneVariantPerRealver = {'com.google.android.apps.books',
                        'com.google.android.apps.cloudprint',
                        'com.google.android.apps.enterprise.dmagent',
                        'com.google.android.apps.gcs',
                        'com.google.android.apps.genie.geniewidget',
                        'com.google.android.calculator',
                        'com.google.android.calendar',
                        'com.google.android.deskclock',
                        'com.google.android.dialer',
                        'com.google.android.ears',
                        'com.google.android.gm',
                        'com.google.android.gm.exchange',
                        'com.google.android.marvin.talkback',
                        'com.google.android.music',
                        'com.google.android.tv.remote'}

oneVercodePerRealver = {'com.google.android.apps.docs',
                        'com.google.android.apps.docs.editors.docs',
                        'com.google.android.apps.docs.editors.sheets',
                        'com.google.android.apps.docs.editors.slides',
                        'com.google.android.apps.fitness',
                        'com.google.android.apps.inputmethod.hindi',
                        'com.google.android.apps.inputmethod.zhuyin',
                        'com.google.android.apps.messaging',
                        'com.google.android.apps.tycho',
                        'com.google.android.gms',
                        'com.google.android.googlecamera',
                        'com.google.android.googlequicksearchbox',
                        'com.google.android.inputmethod.japanese',
                        'com.google.android.inputmethod.korean',
                        'com.google.android.inputmethod.latin',
                        'com.google.android.inputmethod.pinyin',
                        'com.google.android.play.games',
                        'com.google.android.tv'}

@total_ordering
class ApkVersionInfo(object):
    """ApkVersionInfo"""
    def __init__(self, name='', arch='', sdk='', target='', dpi='', ver='', vercode='', scrape_src='', download_src='', malware=''):
        super(ApkVersionInfo, self).__init__()

        sName  = '^(?P<name>.*)(?P<extra>\.(leanback|beta))$'
        reName = re.compile(sName)

        sVer   = '^(?P<ver>[^\s-]*)(?P<extra>([\s-].*|(\.(arm|arm\.arm_neon|arm64|x86|large|small))))$'  # .release?
        reVer  = re.compile(sVer)

        self.name         = name
        self.extraname    = None  # used for beta/leanback versions
        self.arch         = arch
        self.sdk          = 0 if sdk == '' else sdk
        try:
            self.sdk      = int(self.sdk)
        except:
            pass
        self.target       = 0 if target == '' else target
        try:
            self.target      = int(self.target)
        except:
            pass
        self.dpi          = dpi
        self.ver          = ver   # used for comparing (could be shortened later)
        self.realver      = ver   # used for full/original versions
        self.vercode      = 0 if vercode == '' else int(vercode)

        self.scrape_src   = scrape_src
        self.apk_name     = ''
        self.download_src = download_src
        self.malware = malware

        m = reName.match(self.name)
        if m:
            self.extraname = self.name
            self.name      = m.group('name')

            # Let's keep .beta its own package for now
            if m.group('extra') == '.beta':
                self.name = self.extraname

        m = reVer.match(self.ver)
        if m:
            self.ver = m.group('ver')

        if 'com.google.android.apps.docs' in self.name:
            self.ver = '.'.join(self.ver.split('.')[0:4])
    # END: def init

    def fullString(self, max):
        mymax = max
        if self.realver != self.ver:
            mymax += self.realver[len(self.ver):]

        return '{0}|{1}|{2}|{3}|{4}|{5}'.format(self.name,
                                                self.arch,
                                                self.sdk,
                                                self.dpi,
                                                mymax,
                                                self.vercode)
    # END: def fullString

    def get_apk_name(self):
        return '{0}_{1}-{2}_minAPI{3}{4}{5}.apk'.format(self.name, '_'.join(self.realver.split(' ')),
                                                        self.vercode, self.sdk,
                                                        '' if not self.arch else '({0})'.format(self.arch),
                                                        '({0})'.format(self.dpi))
    # END: def get_apk_name

    def isRealverAbsolute(self):
        return (self.name in oneVariantPerRealver) or (self.name in oneVercodePerRealver)

    def __lt__(self, other):
        if self.ver == '':
            logging.error('AVI.cmp(): self.ver is empty [{0}]'.format(self.ver))
            return NotImplemented
        elif other.ver == '':
            logging.error('AVI.cmp(): other.ver is empty [{0}]'.format(other.ver))
            return NotImplemented
        else:

            # Make blank-->'0', replace - and _ with . and split into parts
            ps = [int(x if x != '' else '0') for x in re.sub('[A-Za-z]+', '', self.ver.replace('-', '.').replace('_', '.')).split('.')]
            po = [int(x if x != '' else '0') for x in re.sub('[A-Za-z]+', '', other.ver.replace('-', '.').replace('_', '.')).split('.')]

            # fill up the shorter version with zeros ...
            lendiff = len(ps) - len(po)
            if lendiff > 0:
                po.extend([0] * lendiff)
            elif lendiff < 0:
                ps.extend([0] * (-lendiff))

            for i, p in enumerate(ps):
                if p != po[i]:
                    return p < po[i]

            return ps < po
    # END: def __lt__

    def __eq__(self, other):
        if self.ver == '':
            logging.error('AVI.cmp(): self.ver is empty [{0}]'.format(self.ver))
            return NotImplemented
        elif other.ver == '':
            logging.error('AVI.cmp(): other.ver is empty [{0}]'.format(other.ver))
            return NotImplemented
        else:
            import re

            # Make blank-->'0', replace - and _ with . and split into parts
            ps = [int(x if x != '' else '0') for x in re.sub('[A-Za-z]+', '', self.ver.replace('-', '.').replace('_', '.')).split('.')]
            po = [int(x if x != '' else '0') for x in re.sub('[A-Za-z]+', '', other.ver.replace('-', '.').replace('_', '.')).split('.')]

            # fill up the shorter version with zeros ...
            lendiff = len(ps) - len(po)
            if lendiff > 0:
                po.extend([0] * lendiff)
            elif lendiff < 0:
                ps.extend([0] * (-lendiff))

            return ps == (po)
    # END: def __eq__

    def __str__(self):
        return str(self.__dict__)
# END: class ApkVersionInfo
