# Just a draft, not accounting yet for classes we need to do when getting to implemenation level; might need to be split out to different files per class

# example usage:
# angler = AndroidBuild-object of e.g. a Nexus 6P
# AndroidCheckin(angler) to register and get a GSF
# playstore = angler.associate(dummy@google.com, secret)
# storeourtokenforlateruse = angler.get_authToken()
# playstore.search(com.google.android.app)

class AndroidBuild:
    def __init__(self, fingerprint, board, etc):
        # field that are not provided but are obligatory should probably be set to some dummy values like 000000000001 for mac addr

# use Python's pickle to e.g. serialize this object for later (re)-usage
class AndroidCheckin:
    def __init__(self, androidBuild=None):  # either you give an build that should be checked in during the init-fuction
        # run the _register method

    def _register(self):  # private function
        # do the checkin procedure using AndroidBuild
        # save all the stuff, including our super secret securityToken that can be used to associate

    def associate(self, username, password):
        # IF we have a securityToken
            # run the association stuff that connects this device it to a google account, return a PlayStore-object that can be used
        # IF we don't have a securityToken in AndroidCheckin (which means this build is not in the GSF-register phase) or association failed return a None-object

    def get_gsf(self):
        return self.gsfId

    def get_voicesearch(self):
        return self.voicesearch


# This object we use to access the playstore as a specific device
class PlayStore:
    def __init__(self, gsfId, authToken=None, username=None, password=None):
        # either you give a token, or a username and password that will be used to directly make a token using _login()

    # private method that we can use to download a file using a cookie
    def _get_file(self, path, cookie):

    # private method that we can use to communicate with the Play Store
    def _play_request(self, path, useragent, postData=None, postContentType="application/x-www-form-urlencoded; charset=UTF-8"):
        if postData:
            # do post()
        else:
            # do get()
        # parse the results to something useable for the return

    # check for selfUpdate results
    def check_playstore_update(self, curVerName, curVerCode):

    def download(self, packageName, versionCode, offerType=1):

    def download_playstore_update(self, versionCode, curVerName, curVerCode):
        # do a 'delivery' instead of a 'purchase' method and use the appropiate useragent

    def get_authToken(self):
        retun self.authToken
