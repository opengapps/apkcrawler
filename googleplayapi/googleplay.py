#!/usr/bin/env python3
from __future__ import unicode_literals

import base64
import json
import gzip
import logging
import pprint
import http.client
import requests
import time

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
        self.downloadUserAgent = "AndroidDownloadManager/6.0.1 (Linux; U; Android 6.0.1; Nexus 6P Build/MTC19T)"
        self.regionCookie = "US"
        self.defaultAgentvername="6.7.13.E-all [0] 2920566"
        self.defaultAgentvercode="80671300"
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
                          "sdk_version": "17"}  # to work around oauth issues
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
                        k, v = d.split("=")
                        params[k.strip().lower()] = v.strip()
                    if "auth" in params:
                        self.setAuthSubToken(params["auth"])
                        ret = self.authSubToken
                    elif "error" in params:
                        logging.error('{0} Play Store login error: {1}'.format(self.androidId, params["error"]))
                    else:
                        logging.error('{0} Play Store returned no auth token'.format(self.androidId))
        return ret

    def executeRequestApi2(self, path, agentvername=None, agentvercode=None, datapost=None, post_content_type="application/x-www-form-urlencoded; charset=UTF-8"):
        if not agentvername:
            agentvername = self.defaultAgentvername
        if not agentvercode:
            agentvercode = self.defaultAgentvercode
        user_agent = "Android-Finsky/" + agentvername + " (api=3,versionCode=" + agentvercode + ",sdk=23,device=angler,hardware=angler,product=angler,build=MTC19T:user)"

        if (datapost is None and path in self.preFetch):
            data = self.preFetch[path]
        else:
            headers = {"Accept-Language": self.lang,
                       "Authorization": "GoogleLogin auth=%s" % self.authSubToken,
                       "X-DFE-Enabled-Experiments": "cl:billing.select_add_instrument_by_default",
                       "X-DFE-Unsupported-Experiments": "nocache:billing.use_charging_poller,market_emails,buyer_currency,prod_baseline,checkin.set_asset_paid_app_field,shekel_test,content_ratings,buyer_currency_in_app,nocache:encrypted_apk,recent_changes",
                       "X-DFE-Device-Id": self.androidId,
                       "X-DFE-Client-Id": "am-android-google",
                       "X-DFE-Device-Config-Token": "1",
                       "X-DFE-Cookie": base64.standard_b64encode(b'\x08\xa9\x0f\x10\x01\x18\x00"\x02' + self.regionCookie.encode('utf-8')).decode('utf-8').replace('=', ''),
                       "User-Agent": user_agent,
                       "X-DFE-SmallestScreenWidthDp": "320",
                       "X-DFE-Filter-Level": "3",
                       "Accept-Encoding": "gzip, deflate",
                       "Host": "android.clients.google.com"}  # TODO make the values for versioncode, sdk, device, hardware, platformVersionRelease, model, isWidescreen, X-DFE-SmallestScreenWidthDp flexible?

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

    def bulkDetails(self, packageNames):
        """Get several apps details from a list of package names.

        This is much more efficient than calling N times details() since it
        requires only one request.

        packageNames is a list of app ID (usually starting with 'com.')."""
        path = "bulkDetails"
        req = googleplayapi.googleplay_pb2.BulkDetailsRequest()
        req.docid.extend(packageNames)
        data = req.SerializeToString()
        (status_code, message) = self.executeRequestApi2(path, datapost=data, post_content_type="application/x-protobuf")
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

    def download(self, packageName, versionCode, offerType=1, agentvername=None, agentvercode=None):
        """Download an app and return its raw data (APK file).

        packageName is the app unique ID (usually starting with 'com.').

        versionCode can be grabbed by using the details() method on the given
        app."""
        if packageName == "com.android.vending":
            (status_code, message) = self.executeRequestApi2(path="delivery?ot=%d&doc=%s&vc=%d&shh=%s" % (offerType, packageName, versionCode, "1"), agentvername=agentvername, agentvercode=agentvercode)
        else:
            (status_code, message) = self.executeRequestApi2(path="purchase", datapost="ot=%d&doc=%s&vc=%d" % (offerType, packageName, versionCode))

        if status_code == http.client.OK:
            if packageName == "com.android.vending":
                url = message.payload.deliveryResponse.appDeliveryData.downloadUrl
                cookie = message.payload.deliveryResponse.appDeliveryData.downloadAuthCookie[0]
            else:
                url = message.payload.buyResponse.purchaseStatusResponse.appDeliveryData.downloadUrl
                cookie = message.payload.buyResponse.purchaseStatusResponse.appDeliveryData.downloadAuthCookie[0]
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

    def checkinRequest(self):
        """Checkin to the playstore
        The response contains url to the voice files """

        # android build proto
        build_proto = googleplayapi.googleplay_pb2.AndroidBuildProto()
        build_proto.id = "samsung/m0xx/m0:4.0.4/IMM76D/I9300XXALF2:user/release-keys"
        build_proto.product = "smdk4x12"
        build_proto.carrier = "Google"
        build_proto.radio = "I9300XXALF2"
        build_proto.bootloader = "PRIMELA03"
        build_proto.client = "android-google"
        build_proto.timestamp =  time.time().__round__()
        build_proto.googleServices = 16
        build_proto.device = "m0"
        build_proto.sdkVersion = 21
        build_proto.model = "GT-I9300"
        build_proto.manufacturer = "Samsung"
        build_proto.buildProduct = "m0xx"
        build_proto.otaInstalled = False

        # checkin proto
        checkin_proto = googleplayapi.googleplay_pb2.AndroidCheckinProto()
        checkin_proto.build.MergeFrom(build_proto)
        checkin_proto.lastCheckinMsec = 0
        checkin_proto.cellOperator = "310260"
        checkin_proto.simOperator = "310260"
        checkin_proto.roaming = "WIFI::"
        checkin_proto.userNumber = 0


        # device configuration proto
        device_proto = googleplayapi.googleplay_pb2.DeviceConfigurationProto()
        device_proto.touchScreen = 3
        device_proto.keyboard = 1
        device_proto.navigation = 1
        device_proto.screenLayout = 2
        device_proto.hasHardKeyboard = False
        device_proto.hasFiveWayNavigation = False
        device_proto.screenDensity = 320
        device_proto.glEsVersion = 131072
        device_proto.systemSharedLibrary.extend([
            "android.test.runner", "com.android.future.usb.accessory", "com.android.location.provider",
            "com.android.media.remotedisplay", "com.android.mediadrm.signer", "com.android.nfc_extras",
            "com.google.android.camera.experimental2015", "com.google.android.dialer.support", "com.google.android.maps",
            "com.google.android.media.effects",	"com.google.widevine.software.drm", "javax.obex"
        ])
        device_proto.systemAvailableFeature.extend([
            "android.hardware.audio.low_latency", "android.hardware.audio.output", "android.hardware.audio.pro",
            "android.hardware.microphone", "android.hardware.output", "android.hardware.bluetooth", "android.hardware.bluetooth_le", "android.hardware.camera",
            "android.hardware.camera.any", "android.hardware.camera.autofocus", "android.hardware.camera.flash", "android.hardware.camera.front",
            "android.hardware.camera.level.full", "android.hardware.camera.capability.manual_sensor", "android.hardware.camera.capability.manual_post_processing", "android.hardware.camera.capability.raw",
            "android.hardware.consumerir", "android.hardware.ethernet", "android.hardware.fingerprint", "android.hardware.location",
            "android.hardware.location.network", "android.hardware.location.gps", "android.hardware.microphone", "android.hardware.nfc",
            "android.hardware.nfc.hce", "android.hardware.sensor.accelerometer", "android.hardware.sensor.barometer", "android.hardware.sensor.compass",
            "android.hardware.sensor.gyroscope", "android.hardware.sensor.hifi_sensors", "android.hardware.sensor.light", "android.hardware.sensor.proximity",
            "android.hardware.sensor.stepcounter", "android.hardware.sensor.stepdetector", "android.hardware.screen.landscape", "android.hardware.screen.portrait",
            "android.hardware.telephony", "android.hardware.telephony.cdma", "android.hardware.telephony.gsm", "android.hardware.faketouch",
            "android.hardware.touchscreen", "android.hardware.touchscreen.multitouch", "android.hardware.touchscreen.multitouch.distinct", "android.hardware.touchscreen.multitouch.jazzhand",
            "android.hardware.usb.host", "android.hardware.usb.accessory", "android.hardware.wifi", "android.hardware.wifi.direct",
            "android.software.app_widgets", "android.software.backup", "android.software.connectionservice", "android.software.device_admin",
            "android.software.home_screen", "android.software.input_methods", "android.software.live_wallpaper", "android.software.managed_users",
            "android.software.midi", "android.software.print", "android.software.sip", "android.software.sip.voip",
            "android.software.verified_boot", "android.software.voice_recognizers", "android.software.webview", "com.google.android.feature.GOOGLE_BUILD",
            "com.google.android.feature.GOOGLE_EXPERIENCE", "com.google.android.feature.EXCHANGE_6_2", "com.nxp.mifare"
        ])
        device_proto.nativePlatform.extend(["x86_64", "x86", "arm64-v8a", "armeabi-v7a", "armeabi"])
        device_proto.screenWidth = 720
        device_proto.screenHeight = 1184
        device_proto.systemSupportedLocale.extend([
            "af", "af_ZA", "am", "am_ET", "ar", "ar_EG", "bg", "bg_BG", "ca", "ca_ES", "cs", "cs_CZ",
            "da", "da_DK", "de", "de_AT", "de_CH", "de_DE", "de_LI", "el", "el_GR", "en", "en_AU", "en_CA",
            "en_GB", "en_NZ", "en_SG", "en_US", "es", "es_ES", "es_US", "fa", "fa_IR", "fi", "fi_FI", "fr",
            "fr_BE", "fr_CA", "fr_CH", "fr_FR", "hi", "hi_IN", "hr", "hr_HR", "hu", "hu_HU", "in", "in_ID",
            "it", "it_CH", "it_IT", "iw", "iw_IL", "ja", "ja_JP", "ko", "ko_KR", "lt", "lt_LT", "lv",
            "lv_LV", "ms", "ms_MY", "nb", "nb_NO", "nl", "nl_BE", "nl_NL", "pl", "pl_PL", "pt", "pt_BR",
            "pt_PT", "rm", "rm_CH", "ro", "ro_RO", "ru", "ru_RU", "sk", "sk_SK", "sl", "sl_SI", "sr",
            "sr_RS", "sv", "sv_SE", "sw", "sw_TZ", "th", "th_TH", "tl", "tl_PH", "tr", "tr_TR", "ug",
            "ug_CN", "uk", "uk_UA", "vi", "vi_VN", "zh_CN", "zh_TW", "zu", "zu_ZA"
        ])
        device_proto.glExtension.extend([
            "GL_EXT_debug_marker", "GL_EXT_discard_framebuffer", "GL_EXT_multi_draw_arrays",
            "GL_EXT_shader_texture_lod", "GL_EXT_texture_format_BGRA8888",
            "GL_IMG_multisampled_render_to_texture", "GL_IMG_program_binary", "GL_IMG_read_format",
            "GL_IMG_shader_binary", "GL_IMG_texture_compression_pvrtc", "GL_IMG_texture_format_BGRA8888",
            "GL_IMG_texture_npot", "GL_IMG_vertex_array_object", "GL_OES_EGL_image",
            "GL_OES_EGL_image_external", "GL_OES_blend_equation_separate", "GL_OES_blend_func_separate",
            "GL_OES_blend_subtract", "GL_OES_byte_coordinates", "GL_OES_compressed_ETC1_RGB8_texture",
            "GL_OES_compressed_paletted_texture", "GL_OES_depth24", "GL_OES_depth_texture",
            "GL_OES_draw_texture", "GL_OES_egl_sync", "GL_OES_element_index_uint",
            "GL_OES_extended_matrix_palette", "GL_OES_fixed_point", "GL_OES_fragment_precision_high",
            "GL_OES_framebuffer_object", "GL_OES_get_program_binary", "GL_OES_mapbuffer",
            "GL_OES_matrix_get", "GL_OES_matrix_palette", "GL_OES_packed_depth_stencil",
            "GL_OES_point_size_array", "GL_OES_point_sprite", "GL_OES_query_matrix", "GL_OES_read_format",
            "GL_OES_required_internalformat", "GL_OES_rgb8_rgba8", "GL_OES_single_precision",
            "GL_OES_standard_derivatives", "GL_OES_stencil8", "GL_OES_stencil_wrap",
            "GL_OES_texture_cube_map", "GL_OES_texture_env_crossbar", "GL_OES_texture_float",
            "GL_OES_texture_half_float", "GL_OES_texture_mirrored_repeat", "GL_OES_vertex_array_object",
            "GL_OES_vertex_half_float"
        ])


        # checkin request
        req = googleplayapi.googleplay_pb2.AndroidCheckinRequest()
        req.id = 0
        req.digest = "1-da39a3ee5e6b4b0d3255bfef95601890afd80709"
        req.checkin.MergeFrom(checkin_proto)
        req.locale = "en_US"
        req.timeZone = "America/Los_Angeles" # random
        req.macAddr.extend(["000000000001"])
        req.macAddrType.extend(["wifi"])
        req.version = 3
        req.deviceConfiguration.MergeFrom(device_proto)
        req.fragment = 0

        data = req.SerializeToString()
        return data

    def checkinResponse(self, proxy=None):
        self.proxy_dict = proxy
        checkinRequest = self.checkinRequest()
        headers = {
            "User-Agent": "Android-Checkin/2.0 (generic JRO03E); gzip",
            "Host": "android.clients.google.com",
            "Content-Type": "application/x-protobuffer"
        }
        response = requests.post('https://android.clients.google.com/checkin', data=checkinRequest, headers=headers, proxies=self.proxy_dict, verify=False)
        if response.status_code != http.client.OK:
            return (response.status_code, None)
        data = response.content
        message = googleplayapi.googleplay_pb2.AndroidCheckinResponse.FromString(data)

        return (response.status_code, message)

    def getVoiceUrl(self):
        (status_code, message) = self.checkinResponse()
        voice_url = [x for x in message.setting if x.name == b'voice_search:gstatic_url']
        return voice_url[0].value.decode('utf-8')
