#!/usr/bin/env python3
from __future__ import unicode_literals

import base64
import json
import gzip
import logging
import pprint
import http.client
import requests

import hashlib
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

from google.protobuf import descriptor
from google.protobuf.internal.containers import RepeatedCompositeFieldContainer
from google.protobuf import text_format
from google.protobuf.message import Message, DecodeError

import googleplayapi.googleplay_pb2


class LoginError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class RequestError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class RequestResult(object):
    """RequestResult"""

    def __init__(self, status_code=None, body=None):
        self.status_code = status_code
        self.body = body


class GooglePlayApplication:
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)


class GooglePlayPassword:
    """
    Python implementation of the java class to encrypt the login password.

    initialization: email and password of target account.

    getEncryptedPassword() can be used to directly get the encrypted password string.

    encryptString() can be used to encrypt any string.
    """
    KEY = "AAAAgMom/1a/v0lblO2Ubrt60J2gcuXSljGFQXgcyZWveWLEwo6prwgi3iJIZdodyhKZQrNWp5nKJ3srRXcUW+F1BD3baEVGcmEgqaLZUNBjm057pKRI16kB0YppeGx5qIQ5QjKzsR8ETQbKLNWgRY0QRNVz34kMJR3P/LgHax/6rmf5AAAAAwEAAQ=="

    def __init__(self, email=None, password=None):
        self.password_string = email + '\u0000' + password

    def getEncryptedPassword(self):
        return self.encryptString(self.password_string)

    def readInt(self, bArr, i):
        return (((((bArr[i]&255) << 24)|0)|((bArr[i + 1]&255) << 16))|(
            (bArr[i + 2]&255) << 8))|(bArr[i + 3]&255)

    def createKeyFromString(self, str, bArr):
        decode = base64.standard_b64decode(str)
        keyint = self.readInt(decode, 0)
        obj = decode[4:(4 + keyint)]
        bigInt = int.from_bytes(obj, byteorder='big')
        keyInt2 = self.readInt(decode, keyint + 4)
        obj2 = decode[keyint + 8:keyint + 8 + keyInt2]
        bigInt2 = int.from_bytes(obj2, byteorder='big')
        decode = hashlib.sha1(decode).digest()
        bArr[1:] = decode[:4]
        rsaKey = RSA.construct((bigInt, bigInt2))
        return rsaKey, bArr

    def encryptString(self, inputstr):
        i = 0
        obj = bytearray(5)
        rsaKey, obj = self.createKeyFromString(self.KEY, obj)
        if rsaKey is None:
            return ""

        try:
            bytes = inputstr.encode('utf-8')
            bLen = int(((len(bytes) - 1) / 86)) + 1
            obj2 = bytearray(bLen * 133)
            encryptor = PKCS1_OAEP.new(rsaKey)
            while i < bLen:
                offset = i * 86
                strlen = (len(bytes) - offset if i == (
                bLen - 1) else 86) + offset

                encstr = encryptor.encrypt(bytes[offset:strlen])
                obj2[i * 133:i * 133 + len(obj)] = obj
                obj2[
                i * 133 + len(obj):i * 133 + len(obj) + len(encstr)] = encstr
                i += 1

            return base64.urlsafe_b64encode(obj2)
        except Exception as e:
            print(e)
            return ""


class GooglePlayAPI(object):
    """Google Play Unofficial API Class

    Usual APIs methods are login(), search(), details(), bulkDetails(),
    download(), browse(), reviews() and list().

    toStr() can be used to pretty print the result (protobuf object) of the
    previous methods.

    toDict() converts the result into a dict, for easier introspection."""

    SERVICE = "androidmarket"
    URL_LOGIN = "https://android.clients.google.com/auth"  # "https://www.google.com/accounts/ClientLogin"
    ACCOUNT_TYPE_GOOGLE = "GOOGLE"
    ACCOUNT_TYPE_HOSTED = "HOSTED"
    ACCOUNT_TYPE_HOSTED_OR_GOOGLE = "HOSTED_OR_GOOGLE"
    authSubToken = None
    # HTTP_PROXY = "http://81.137.100.158"

    def __init__(self, androidId, lang):  # you must use a device-associated androidId value
        self.preFetch = {}
        self.androidId = androidId
        self.lang = lang
        # Finsky is the nickname of the old Android Market app
        # The number is a string of the Play Store app Version Name
        # The api is the play store protocol api (probably)
        # The versionCode is the vercode of the Play Store app
        self.downloadUserAgent = "AndroidDownloadManager/7.1 (Linux; U; Android 7.1; Pixel Build/NZZ99Z)"
        self.regionCookie = "US"
        self.defaultAgentvername = "7.0.12.H-all [0]"
        self.defaultAgentvercode = "80701200"
        # self.proxy_dict = {
        #         "http"  : "http://81.137.100.158:8080",
        #         "https" : "http://81.137.100.158:8080",
        #         "ftp"   : "http://81.137.100.158:8080"
        #         }

    def toDict(self, protoObj):
        """Converts the (protobuf) result from an API call into a dict, for
        easier introspection."""
        iterable = False
        if isinstance(protoObj, RepeatedCompositeFieldContainer):
            iterable = True
        else:
            protoObj = [protoObj]
        retlist = []

        for po in protoObj:
            msg = dict()
            for fielddesc, value in po.ListFields():
                if fielddesc.type == descriptor.FieldDescriptor.TYPE_GROUP or isinstance(value, RepeatedCompositeFieldContainer) or isinstance(value, Message):
                    msg[fielddesc.name] = self.toDict(value)
                else:
                    msg[fielddesc.name] = value
            retlist.append(msg)
        if not iterable:
            if len(retlist) > 0:
                return retlist[0]
            else:
                return None
        return retlist

    def toStr(self, protoObj):
        """Used for pretty printing a result from the API."""
        return text_format.MessageToString(protoObj)

    def _try_register_preFetch(self, protoObj):
        fields = [i.name for (i, _) in protoObj.ListFields()]
        if ("preFetch" in fields):
            for p in protoObj.preFetch:
                self.preFetch[p.url] = p.response

    def setAuthSubToken(self, authSubToken):
        self.authSubToken = authSubToken

    def login(self, email=None, password=None, authSubToken=None, proxy=None):
        """Login to your Google Account. You must provide either:
        - an email and password
        - a valid Google authSubToken"""
        ret = None
        self.proxy_dict = proxy
        if (authSubToken is not None):
            self.setAuthSubToken(authSubToken)
            logging.debug('{0} uses authSubToken: {1}'.format(self.androidId, self.authSubToken))
            ret = self.authSubToken  # silent assumption
        else:
            if (email is None or password is None):
                logging.error('{0} Needs a authSubToken or (email and password)'.format(self.androidId))
            else:
                params = {
                    "Email": email,
                    "EncryptedPasswd": GooglePlayPassword(email, password).getEncryptedPassword(),
                    "service": "androidmarket",
                    "accountType": self.ACCOUNT_TYPE_HOSTED_OR_GOOGLE,
                    "has_permission": "1",
                    "source": "android",
                    "androidId": self.androidId,
                    "app": "com.android.vending",
                    # "client_sig": self.client_sig,
                    "device_country": "us",
                    "operatorCountry": "us",
                    "lang": "us",
                    "sdk_version": "17"
                    }  # to work around oauth issues
                headers = {
                    "Accept-Encoding": "gzip, deflate",
                }
                response = requests.post(self.URL_LOGIN, data=params, headers=headers, proxies=proxy, verify=False)

                if response.status_code != http.client.OK:
                    logging.error('{0} Play Store login failed, statuscode {1}: {2}'.format(self.androidId, response.status_code, response.content))
                else:
                    data = response.text.split()
                    params = {}
                    for d in data:
                        if "=" not in d:
                            continue

                        k, v = d.split("=", 1) # Do a single split as the token is padded with `==` at the end
                        params[k.strip().lower()] = v.strip()
                    if "auth" in params:
                        self.setAuthSubToken(params["auth"])
                        ret = self.authSubToken
                    elif "error" in params:
                        logging.error('{0} Play Store login error: {1}'.format(self.androidId, params["error"]))
                    else:
                        logging.error('{0} Play Store returned no auth token'.format(self.androidId))
        return ret

    def executeRequestApi2(self, path, sdk=23, agentvername=None, agentvercode=None, devicename="sailfish", datapost=None, post_content_type="application/x-www-form-urlencoded; charset=UTF-8"):
        if not agentvername:
            agentvername = self.defaultAgentvername
        if not agentvercode:
            agentvercode = self.defaultAgentvercode
        user_agent = "Android-Finsky/" + agentvername + " (api=3,versionCode=" + agentvercode + ",sdk=" + str(sdk) + ",device=" + devicename + ",hardware=" + devicename + ",product=" + devicename + ",build=NZZ99Z:user)"

        if (datapost is None and path in self.preFetch):
            data = self.preFetch[path]
        else:
            headers = {
                "Accept-Language": self.lang,
                "Authorization": "GoogleLogin auth=%s" % self.authSubToken,
                "X-DFE-Enabled-Experiments": "cl:billing.select_add_instrument_by_default",
                "X-DFE-Unsupported-Experiments": "nocache:billing.use_charging_poller,market_emails,buyer_currency,prod_baseline,checkin.set_asset_paid_app_field,shekel_test,content_ratings,buyer_currency_in_app,nocache:encrypted_apk,recent_changes",
                "X-DFE-Device-Id": self.androidId,
                "X-DFE-Client-Id": "am-android-google",
                "X-DFE-Device-Config-Token": "1",
                "X-DFE-Cookie": base64.standard_b64encode(b'\x08\xa9\x0f\x10\x01\x18\x00"\x02' + self.regionCookie.encode('utf-8') + '(\x012<CisaKQoTMzcxNzUwNjQ2MzkzMzkzMjA1NBISChAxNTEwMTM0ODU0NTE4MDU2'.encode('utf-8')).decode('utf-8').replace('=', ''),
                "User-Agent": user_agent,
                "X-DFE-SmallestScreenWidthDp": "320",
                "X-DFE-Filter-Level": "3",
                "Accept-Encoding": "gzip, deflate",
                "Host": "android.clients.google.com"
                }  # TODO make the values for versioncode, sdk, device, hardware, platformVersionRelease, model, isWidescreen, X-DFE-SmallestScreenWidthDp flexible?

            url = "https://android.clients.google.com/fdfe/%s" % path
            if datapost is not None:
                headers["Content-Type"] = post_content_type
                response = requests.post(url, data=datapost, headers=headers, proxies=self.proxy_dict, verify=False)
            else:
                response = requests.get(url, headers=headers, proxies=self.proxy_dict, verify=False)
            if response.status_code != http.client.OK:
                return (response.status_code, None)
            data = response.content

        message = googleplayapi.googleplay_pb2.ResponseWrapper.FromString(data)
        self._try_register_preFetch(message)

        return (response.status_code, message)

    #####################################
    # Google Play API Methods
    #####################################

    def search(self, query, nb_results=None, offset=None):
        """Search for apps."""
        path = "search?c=3&q=%s" % requests.utils.quote(query)  # TODO handle categories
        if (nb_results is not None):
            path += "&n=%d" % int(nb_results)
        if (offset is not None):
            path += "&o=%d" % int(offset)

        (status_code, message) = self.executeRequestApi2(path)
        if status_code == http.client.OK:
            return RequestResult(status_code, message.payload.searchResponse)
        return RequestResult(status_code, None)

    def details(self, packageName):
        """Get app details from a package name.
        packageName is the app unique ID (usually starting with 'com.')."""
        path = "details?doc=%s" % requests.utils.quote(packageName)
        (status_code, message) = self.executeRequestApi2(path)
        if status_code == http.client.OK:
            return RequestResult(status_code, message.payload.detailsResponse)
        return RequestResult(status_code, None)

    def bulkDetails(self, packageNames, sdk):
        """Get several apps details from a list of package names.

        This is much more efficient than calling N times details() since it
        requires only one request.

        packageNames is a list of app ID (usually starting with 'com.')."""
        path = "bulkDetails"
        req = googleplayapi.googleplay_pb2.BulkDetailsRequest()
        req.docid.extend(packageNames)
        data = req.SerializeToString()
        (status_code, message) = self.executeRequestApi2(path, sdk=sdk, datapost=data, post_content_type="application/x-protobuf")
        if status_code == http.client.OK:
            return RequestResult(status_code, message.payload.bulkDetailsResponse)
        return RequestResult(status_code, None)

    def browse(self, cat=None, ctr=None):
        """Browse categories.
        cat (category ID) and ctr (subcategory ID) are used as filters."""
        path = "browse?c=3"
        if cat is not None:
            path += "&cat=%s" % requests.utils.quote(cat)
        if ctr is not None:
            path += "&ctr=%s" % requests.utils.quote(ctr)
        (status_code, message) = self.executeRequestApi2(path)
        if status_code == http.client.OK:
            return RequestResult(status_code, message.payload.browseResponse)
        return RequestResult(status_code, None)

    def list(self, cat, ctr=None, nb_results=None, offset=None):
        """List apps.

        If ctr (subcategory ID) is None, returns a list of valid subcategories.

        If ctr is provided, list apps within this subcategory."""
        path = "list?c=3&cat=%s" % requests.utils.quote(cat)
        if ctr is not None:
            path += "&ctr=%s" % requests.utils.quote(ctr)
        if nb_results is not None:
            path += "&n=%s" % int(nb_results)
        if offset is not None:
            path += "&o=%s" % int(offset)
        (status_code, message) = self.executeRequestApi2(path)
        if status_code == http.client.OK:
            return RequestResult(status_code, message.payload.listResponse)
        return RequestResult(status_code, None)

    def reviews(self, packageName, filterByDevice=False, sort=2, nb_results=None, offset=None):
        """Browse reviews.
        packageName is the app unique ID.
        If filterByDevice is True, return only reviews for your device."""
        path = "rev?doc=%s&sort=%d" % (requests.utils.quote(packageName), sort)
        if (nb_results is not None):
            path += "&n=%d" % int(nb_results)
        if (offset is not None):
            path += "&o=%d" % int(offset)
        if (filterByDevice):
            path += "&dfil=1"
        (status_code, message) = self.executeRequestApi2(path)
        if status_code == http.client.OK:
            return RequestResult(status_code, message.payload.reviewResponse)
        return RequestResult(status_code, None)

    def recommend(self, packageName, nb_results=None, offset=None):
        path = "rec?c=3&doc=%s&rt=1" % (packageName,)
        if (nb_results is not None):
            path += "&n=%d" % int(nb_results)
        if (offset is not None):
            path += "&o=%d" % int(offset)
        (status_code, message) = self.executeRequestApi2(path)
        if status_code == http.client.OK:
            return RequestResult(status_code, message.payload.listResponse)
        return RequestResult(status_code, None)

    def download(self, packageName, versionCode, offerType=1, agentvername=None, agentvercode=None, devicename="sailfish"):
        """Download an app and return its raw data (APK file).

        packageName is the app unique ID (usually starting with 'com.').

        versionCode can be grabbed by using the details() method on the given
        app."""
        (status_code, message) = self.executeRequestApi2(path="delivery?ot=%d&doc=%s&vc=%d&shh=%s" % (offerType, packageName, versionCode, "1"), agentvername=agentvername, agentvercode=agentvercode, devicename=devicename)

        if status_code == http.client.OK:
            # app is not in user library
            if message.payload.deliveryResponse.status == 3:
                (status_code, message) = self.executeRequestApi2(path="purchase", datapost="ot=%d&doc=%s&vc=%d" % (offerType, packageName, versionCode))
                if status_code != http.client.OK:
                    return RequestResult(status_code, None)

            # wrong version code
            if message.payload.deliveryResponse.status == 5:
                logging.warning(" Wrong version code {0} for app {1}".format(versionCode, packageName))
                return RequestResult(status_code, None)

            url = message.payload.deliveryResponse.appDeliveryData.downloadUrl
            cookie = message.payload.deliveryResponse.appDeliveryData.downloadAuthCookie[0]

            cookies = {
                str(cookie.name): str(cookie.value)  # python-requests #459 fixes this
            }

            headers = {
                "User-Agent": self.downloadUserAgent,
                "Accept-Encoding": "",  # TODO try adding gzip and deflate here too
            }

            response = requests.get(url, headers=headers, cookies=cookies, proxies=self.proxy_dict, verify=False)
            if response.status_code != http.client.OK:
                return (response.status_code, None)  # returns the reponse-status_code of the 2nd request
            else:
                return RequestResult(response.status_code, response.content)  # take care that this response is different from the other return functions, it concerns the APK content itself (of the 2nd request)
        return RequestResult(status_code, None)  # returns the reponse-status_code of the initial request

    def playUpdate(self, agentvername, agentvercode):
        """Check for Play Store update
        You need to provide the current vername and vercode which are evaluated from the user agent
        to check if there is an eligable upgrade
        A versioncode will be returned if an update is available, otherwise None"""
        path = "selfUpdate"
        (status_code, message) = self.executeRequestApi2(path, agentvername=agentvername, agentvercode=agentvercode)
        try:
            if status_code == http.client.OK and message.payload.selfUpdate and message.payload.selfUpdate.versionCode != 0:
                return message.payload.selfUpdate.versionCode
        except:
            pass
        return None
