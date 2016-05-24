#!/usr/bin/env python3
from __future__ import unicode_literals

import base64
import json
import gzip
import logging
import pprint
import http.client
import requests

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
        self.playUserAgent = "Android-Finsky/6.7.07.E (api=3,versionCode=80670700,sdk=23,device=angler,hardware=angler,product=angler,build=MTC19T:user)"
        self.downloadUserAgent = "AndroidDownloadManager/6.0.1 (Linux; U; Android 6.0.1; Nexus 6P Build/MTC19T)"
        self.regionCookie = "US"
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
        ret = False
        if (authSubToken is not None):
            self.setAuthSubToken(authSubToken)
            logging.debug('Logged in with {0} using authSubToken: {1}'.format(self.androidId, authSubToken))
            ret = True  # TODO is not tested if it really works, silent assumption at the moment. Needs to e.g. try to fetch the auth-page too to verify and return a valid value
        else:
            if (email is None or password is None):
                logging.error('Need a authSubToken or (email and password) for {0}'.format(self.androidId))
            else:
                params = {"Email": email,
                          "Passwd": password,
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
                          "sdk_version": "23"}  # TODO make sdk_version flexible
                headers = {
                    "Accept-Encoding": "",
                }
                self.proxy_dict = proxy
                response = requests.post(self.URL_LOGIN, data=params, headers=headers, proxies=proxy, verify=False)
                if response.status_code != http.client.OK:
                    logging.error('Play Store login failed for {0}: {1}'.format(self.androidId, response.content))
                else:
                    data = response.text.split()
                    params = {}
                    for d in data:
                        if "=" not in d:
                            continue
                        k, v = d.split("=")
                        params[k.strip().lower()] = v.strip()
                    if "auth" in params:
                        self.setAuthSubToken(params["auth"])
                        ret = True
                    elif "error" in params:
                        logging.error('Play Store login error for {0}: {1}'.format(self.androidId, params["error"]))
                    else:
                        logging.error('Play Store returned no auth token for {0}'.format(self.androidId))
        return ret

    def executeRequestApi2(self, path, datapost=None, post_content_type="application/x-www-form-urlencoded; charset=UTF-8"):
        if (datapost is None and path in self.preFetch):
            data = self.preFetch[path]
        else:
            headers = {"Accept-Language": self.lang,
                       "Authorization": "GoogleLogin auth=%s" % self.authSubToken,
                       "X-DFE-Enabled-Experiments": "cl:billing.select_add_instrument_by_default",
                       "X-DFE-Unsupported-Experiments": "nocache:billing.use_charging_poller,market_emails,buyer_currency,prod_baseline,checkin.set_asset_paid_app_field,shekel_test,content_ratings,buyer_currency_in_app,nocache:encrypted_apk,recent_changes",
                       "X-DFE-Device-Id": self.androidId,
                       "X-DFE-Client-Id": "am-android-google",
                       # "X-DFE-Logging-Id": XXXXX,  # Not necessary
                       "X-DFE-Cookie": base64.encodebytes(b'\x08\xa9\x0f\x10\x01\x18\x00"\x02' + self.regionCookie.encode('utf-8')).decode('utf-8').replace('=', ''),
                       "User-Agent": self.playUserAgent,
                       "X-DFE-SmallestScreenWidthDp": "320",
                       "X-DFE-Filter-Level": "3",
                       "Accept-Encoding": "",
                       "Host": "android.clients.google.com"}  # TODO make the values for versioncode, sdk, device, hardware, platformVersionRelease, model, isWidescreen, X-DFE-SmallestScreenWidthDp flexible?

            if datapost is not None:
                headers["Content-Type"] = post_content_type

            url = "https://android.clients.google.com/fdfe/%s" % path
            if datapost is not None:
                response = requests.post(url, data=datapost, headers=headers, proxies=self.proxy_dict, verify=False)
            else:
                response = requests.get(url, headers=headers, proxies=self.proxy_dict, verify=False)
            if response.status_code != http.client.OK:
                return (response.status_code, None)
            data = response.content
            # print data
        '''
        data = StringIO.StringIO(data)
        gzipper = gzip.GzipFile(fileobj=data)
        data = gzipper.read()
        '''
        message = googleplayapi.googleplay_pb2.ResponseWrapper.FromString(data)
        self._try_register_preFetch(message)

        # print text_format.MessageToString(message)
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

    def bulkDetails(self, packageNames):
        """Get several apps details from a list of package names.

        This is much more efficient than calling N times details() since it
        requires only one request.

        packageNames is a list of app ID (usually starting with 'com.')."""
        path = "bulkDetails"
        req = googleplayapi.googleplay_pb2.BulkDetailsRequest()
        req.docid.extend(packageNames)
        data = req.SerializeToString()
        (status_code, message) = self.executeRequestApi2(path, data, "application/x-protobuf")
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
        if(filterByDevice):
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

    def download(self, packageName, versionCode, offerType=1):
        """Download an app and return its raw data (APK file).

        packageName is the app unique ID (usually starting with 'com.').

        versionCode can be grabbed by using the details() method on the given
        app."""
        path = "purchase"
        data = "ot=%d&doc=%s&vc=%d" % (offerType, packageName, versionCode)
        (status_code, message) = self.executeRequestApi2(path, data)

        if status_code == http.client.OK:
            url = message.payload.buyResponse.purchaseStatusResponse.appDeliveryData.downloadUrl
            cookie = message.payload.buyResponse.purchaseStatusResponse.appDeliveryData.downloadAuthCookie[0]

            cookies = {
                str(cookie.name): str(cookie.value)  # python-requests #459 fixes this
            }

            headers = {
                "User-Agent": self.downloadUserAgent,
                "Accept-Encoding": "",
            }

            response = requests.get(url, headers=headers, cookies=cookies, proxies=self.proxy_dict, verify=False)
            if response.status_code != http.client.OK:
                return (response.status_code, None)  # returns the reponse-status_code of the 2nd request
            else:
                return RequestResult(response.status_code, response.content)  # take care that this response is different from the other return functions, it concerns the APK content itself (of the 2nd request)
        return RequestResult(status_code, None)  # returns the reponse-status_code of the initial request
