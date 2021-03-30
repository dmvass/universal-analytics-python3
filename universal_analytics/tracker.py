# Copyright (c) 2013, Analytics Pros
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.

# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.

# * Neither the name of Analytics Pros nor the names of its contributors may be
#   used to endorse or promote products derived from this software without
#   specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import datetime
import hashlib
import time
import uuid


__all__ = ["Tracker"]


def generate_uuid(basedata=None):
    """Provides a random UUID with no input, or a UUID4-format MD5 checksum of
    any input data provided.

    :param str basedata: provided data to calculate a uuid

    """
    if basedata is None:
        return str(uuid.uuid4())
    elif isinstance(basedata, str):
        checksum = hashlib.md5(basedata.encode()).hexdigest()
        return str(uuid.UUID(checksum))
    else:
        raise TypeError("The 'basedata' must be string or None")


class Time(datetime.datetime):
    """Wrappers and convenience methods for processing various time
    representations.
    """

    @classmethod
    def from_unix(cls, seconds, milliseconds=0):
        """Produce a full datetime.datetime object from a Unix timestamp."""
        return datetime.datetime.fromtimestamp(seconds + milliseconds * .001)

    @classmethod
    def to_unix(cls, timestamp):
        """Wrapper over time module to produce Unix epoch time as a float."""
        if not isinstance(timestamp, datetime.datetime):
            raise TypeError("Time.milliseconds expects a datetime object")
        return timestamp.timestamp()

    @classmethod
    def milliseconds_offset(cls, timestamp, now=None):
        """Offset time (in milliseconds) from a datetime.datetime object
        to now.
        """
        if isinstance(timestamp, (int, float)):
            base = timestamp
        else:
            base = cls.to_unix(timestamp)
        if now is None:
            now = time.time()
        return (now - base) * 1000


class Tracker:
    """Primary tracking interface for Universal Analytics."""

    option_sequence = {
        "pageview": [(str, "dp")],
        "event": [(str, "ec"), (str, "ea"), (str, "el"), (int, "ev")],
        "social": [(str, "sn"), (str, "sa"), (str, "st")],
        "timing": [(str, "utc"), (str, "utv"), (str, "utt"), (str, "utl")]
    }
    params = None
    parameter_alias = {}
    valid_hittypes = ("pageview", "event", "social", "screenview",
                      "transaction", "item", "exception", "timing")

    def __init__(self, account, http, client_id=None,
                 hash_client_id=False, user_id=None):

        self.http = http
        self.hash_client_id = hash_client_id

        self.params = {"v": 1, "tid": account}
        self.params["cid"] = client_id or generate_uuid()
        if user_id is not None:
            self.params["uid"] = user_id

    def __getitem__(self, name):
        param, value = self.coerceParameter(name, None)
        return self.params.get(param, None)

    def __setitem__(self, name, value):
        param, value = self.coerceParameter(name, value)
        self.params[param] = value

    def __delitem__(self, name):
        param, value = self.coerceParameter(name, None)
        if param in self.params:
            del self.params[param]

    @property
    def account(self):
        return self.params.get("tid", None)

    def payload(self, data):
        for key, value in data.items():
            try:
                yield self.coerceParameter(key, value)
            except KeyError:
                continue

    def set_timestamp(self, data):
        """
        Interpret time-related options, apply queue-time parameter as needed.
        """
        if "hittime" in data:  # an absolute timestamp
            data["qt"] = self.hittime(timestamp=data.pop("hittime", None))
        if "hitage" in data:  # a relative age (in seconds)
            data["qt"] = self.hittime(age=data.pop("hitage", None))

    def send(self, hittype, *args, **data):
        """Transmit HTTP requests to Google Analytics using the measurement
        protocol.
        """
        if hittype not in self.valid_hittypes:
            message = "Unsupported Universal Analytics Hit Type: {hittype!r}"
            raise KeyError(message.format(hittype=hittype))

        self.set_timestamp(data)
        self.consume_options(data, hittype, args)

        # Process dictionary-object arguments of transcient data
        for item in args:
            if isinstance(item, dict):
                for key, val in self.payload(item):
                    data[key] = val

        # Update only absent parameters
        for k, v in self.params.items():
            if k not in data:
                data[k] = v

        data = dict(self.payload(data))

        if self.hash_client_id:
            data["cid"] = generate_uuid(data["cid"])

        # Transmit the hit to Google...
        return self.http.send(data)

    def set(self, name, value=None):
        """Setting persistent attributes of the session/hit/etc
        (inc. custom dimensions/metrics).
        """
        if isinstance(name, dict):
            for key, value in name.items():
                try:
                    param, value = self.coerceParameter(key, value)
                    self.params[param] = value
                except KeyError:
                    pass
        elif isinstance(name, str):
            try:
                param, value = self.coerceParameter(name, value)
                self.params[param] = value
            except KeyError:
                pass

    @classmethod
    def alias(cls, typemap, base, *names):
        """Declare an alternate (humane) name for a measurement protocol
        parameter.
        """
        cls.parameter_alias[base] = (typemap, base)
        for name in names:
            cls.parameter_alias[name] = (typemap, base)

    @classmethod
    def coerceParameter(cls, name, value=None):
        if isinstance(name, str) and name[0] == "&":
            return name[1:], str(value)
        elif name in cls.parameter_alias:
            typecast, param_name = cls.parameter_alias.get(name)
            return param_name, typecast(value)
        else:
            raise KeyError(f"Parameter '{name}' is not recognized")

    @classmethod
    def consume_options(cls, data, hittype, args):
        """Interpret sequential arguments related to known hittypes based on
        declared structures.
        """
        opt_position = 0
        data["t"] = hittype  # integrate hit type parameter
        if hittype in cls.option_sequence:
            for expected_type, optname in cls.option_sequence[hittype]:
                if opt_position < len(args) and isinstance(args[opt_position],
                                                           expected_type):
                    data[optname] = args[opt_position]
                opt_position += 1

    @classmethod
    def hittime(cls, timestamp=None, age=None, milliseconds=None):
        """Returns an integer represeting the milliseconds offset for a
        given hit (relative to now).
        """
        if isinstance(timestamp, (int, float)):
            return int(Time.milliseconds_offset(
                Time.from_unix(timestamp, milliseconds=milliseconds))
            )
        if isinstance(timestamp, datetime.datetime):
            return int(Time.milliseconds_offset(timestamp))
        if isinstance(age, (int, float)):
            return int(age * 1000) + (milliseconds or 0)


def safe_unicode(obj):
    """Safe conversion to the Unicode string version of the object."""
    try:
        return str(obj)
    except UnicodeDecodeError:
        return obj.decode("utf-8")


# Declaring name mappings for Measurement Protocol parameters
MAX_CUSTOM_DEFINITIONS = 200
MAX_EC_LISTS = 11       # 1-based index
MAX_EC_PRODUCTS = 11    # 1-based index
MAX_EC_PROMOTIONS = 11  # 1-based index

Tracker.alias(int, "v", "protocol-version")
Tracker.alias(safe_unicode, "cid", "client-id", "clientId", "clientid")
Tracker.alias(safe_unicode, "tid", "trackingId", "account")
Tracker.alias(safe_unicode, "uid", "user-id", "userId", "userid")
Tracker.alias(safe_unicode, "uip", "user-ip", "userIp", "ipaddr")
Tracker.alias(safe_unicode, "ua", "userAgent", "userAgentOverride",
              "user-agent")
Tracker.alias(safe_unicode, "dp", "page", "path")
Tracker.alias(safe_unicode, "dt", "title", "pagetitle", "pageTitle",
              "page-title")
Tracker.alias(safe_unicode, "dl", "location")
Tracker.alias(safe_unicode, "dh", "hostname")
Tracker.alias(safe_unicode,
              "sc",
              "sessioncontrol",
              "session-control",
              "sessionControl")
Tracker.alias(safe_unicode, "dr", "referrer", "referer")
Tracker.alias(int, "qt", "queueTime", "queue-time")
Tracker.alias(safe_unicode, "t", "hitType", "hittype")
Tracker.alias(int, "aip", "anonymizeIp", "anonIp", "anonymize-ip")

# Campaign attribution
Tracker.alias(safe_unicode, "cn", "campaign", "campaignName", "campaign-name")
Tracker.alias(safe_unicode,
              "cs",
              "source",
              "campaignSource",
              "campaign-source")
Tracker.alias(safe_unicode,
              "cm",
              "medium",
              "campaignMedium",
              "campaign-medium")
Tracker.alias(safe_unicode,
              "ck",
              "keyword",
              "campaignKeyword",
              "campaign-keyword")
Tracker.alias(safe_unicode,
              "cc",
              "content",
              "campaignContent",
              "campaign-content")
Tracker.alias(safe_unicode, "ci", "campaignId", "campaignID", "campaign-id")

# Technical specs
Tracker.alias(safe_unicode,
              "sr",
              "screenResolution",
              "screen-resolution",
              "resolution")
Tracker.alias(safe_unicode, "vp", "viewport", "viewportSize", "viewport-size")
Tracker.alias(safe_unicode,
              "de",
              "encoding",
              "documentEncoding",
              "document-encoding")
Tracker.alias(int, "sd", "colors", "screenColors", "screen-colors")
Tracker.alias(safe_unicode, "ul", "language", "user-language", "userLanguage")

# Mobile app
Tracker.alias(safe_unicode, "an", "appName", "app-name", "app")
Tracker.alias(safe_unicode,
              "cd",
              "contentDescription",
              "screenName",
              "screen-name",
              "content-description")
Tracker.alias(safe_unicode, "av", "appVersion", "app-version", "version")
Tracker.alias(safe_unicode,
              "aid",
              "appID",
              "appId",
              "application-id",
              "app-id",
              "applicationId")
Tracker.alias(safe_unicode, "aiid", "appInstallerId", "app-installer-id")

# E-commerce
Tracker.alias(safe_unicode, "ta", "affiliation", "transactionAffiliation",
              "transaction-affiliation")
Tracker.alias(safe_unicode,
              "ti",
              "transaction",
              "transactionId",
              "transaction-id")
Tracker.alias(float,
              "tr",
              "revenue",
              "transactionRevenue",
              "transaction-revenue")
Tracker.alias(float,
              "ts",
              "shipping",
              "transactionShipping",
              "transaction-shipping")
Tracker.alias(float, "tt", "tax", "transactionTax", "transaction-tax")
Tracker.alias(safe_unicode,
              "cu",
              "currency",
              "transactionCurrency",
              "transaction-currency")  # Currency, e.g. USD
Tracker.alias(safe_unicode, "in", "item-name", "itemName")
Tracker.alias(float, "ip", "item-price", "itemPrice")
Tracker.alias(float, "iq", "item-quantity", "itemQuantity")
Tracker.alias(safe_unicode, "ic", "item-code", "sku", "itemCode")
Tracker.alias(safe_unicode,
              "iv",
              "item-variation",
              "item-category",
              "itemCategory",
              "itemVariation")

# Events
Tracker.alias(safe_unicode,
              "ec",
              "event-category",
              "eventCategory",
              "category")
Tracker.alias(safe_unicode, "ea", "event-action", "eventAction", "action")
Tracker.alias(safe_unicode, "el", "event-label", "eventLabel", "label")
Tracker.alias(int, "ev", "event-value", "eventValue", "value")
Tracker.alias(int,
              "ni",
              "noninteractive",
              "nonInteractive",
              "noninteraction",
              "nonInteraction")

# Social
Tracker.alias(safe_unicode, "sa", "social-action", "socialAction")
Tracker.alias(safe_unicode, "sn", "social-network", "socialNetwork")
Tracker.alias(safe_unicode, "st", "social-target", "socialTarget")

# Exceptions
Tracker.alias(safe_unicode,
              "exd",
              "exception-description",
              "exceptionDescription",
              "exDescription")
Tracker.alias(int, "exf", "exception-fatal", "exceptionFatal", "exFatal")

# Experiments
Tracker.alias(safe_unicode, "exp", "experiment")

# User Timing
Tracker.alias(safe_unicode, "utc", "timingCategory", "timing-category")
Tracker.alias(safe_unicode, "utv", "timingVariable", "timing-variable")
Tracker.alias(int, "utt", "time", "timingTime", "timing-time")
Tracker.alias(safe_unicode, "utl", "timingLabel", "timing-label")
Tracker.alias(float, "dns", "timingDNS", "timing-dns")
Tracker.alias(float, "pdt", "timingPageLoad", "timing-page-load")
Tracker.alias(float, "rrt", "timingRedirect", "timing-redirect")
Tracker.alias(safe_unicode, "tcp", "timingTCPConnect", "timing-tcp-connect")
Tracker.alias(safe_unicode,
              "srt",
              "timingServerResponse",
              "timing-server-response")

# Custom dimensions and metrics
for i in range(0, 200):
    Tracker.alias(safe_unicode, f"cd{i}", f"dimension{i}")
    Tracker.alias(int, f"cm{i}", f"metric{i}")

# Enhanced Ecommerce
Tracker.alias(str, "pa")  # Product action
Tracker.alias(str, "tcc")  # Coupon code
Tracker.alias(str, "pal")  # Product action list
Tracker.alias(int, "cos")  # Checkout step
Tracker.alias(str, "col")  # Checkout step option

Tracker.alias(str, "promoa")  # Promotion action

for product_index in range(1, MAX_EC_PRODUCTS):
    # Product SKU
    Tracker.alias(str, f"pr{product_index}id")
    # Product name
    Tracker.alias(str, f"pr{product_index}nm")
    # Product brand
    Tracker.alias(str, f"pr{product_index}br")
    # Product category
    Tracker.alias(str, f"pr{product_index}ca")
    # Product variant
    Tracker.alias(str, f"pr{product_index}va")
    # Product price
    Tracker.alias(str, f"pr{product_index}pr")
    # Product quantity
    Tracker.alias(int, f"pr{product_index}qt")
    # Product coupon
    Tracker.alias(str, f"pr{product_index}cc")
    # Product position
    Tracker.alias(int, f"pr{product_index}ps")

    for custom_index in range(MAX_CUSTOM_DEFINITIONS):
        # Product custom dimension
        Tracker.alias(str, f"pr{product_index}cd{custom_index}")
        # Product custom metric
        Tracker.alias(int, f"pr{product_index}cm{custom_index}")

    for list_index in range(1, MAX_EC_LISTS):
        # Product impression SKU
        Tracker.alias(str, f"il{list_index}pi{product_index}id")
        # Product impression name
        Tracker.alias(str, f"il{list_index}pi{product_index}nm")
        # Product impression brand
        Tracker.alias(str, f"il{list_index}pi{product_index}br")
        # Product impression category
        Tracker.alias(str, f"il{list_index}pi{product_index}ca")
        # Product impression variant
        Tracker.alias(str, f"il{list_index}pi{product_index}va")
        # Product impression position
        Tracker.alias(int, f"il{list_index}pi{product_index}ps")
        # Product impression price
        Tracker.alias(int, f"il{list_index}pi{product_index}pr")

        for custom_index in range(MAX_CUSTOM_DEFINITIONS):
            # Product impression custom dimension
            Tracker.alias(str,
                          f"il{list_index}pi{product_index}cd{custom_index}")
            # Product impression custom metric
            Tracker.alias(int,
                          f"il{list_index}pi{product_index}cm{custom_index}")

for list_index in range(1, MAX_EC_LISTS):
    # Product impression list name
    Tracker.alias(str, f"il{list_index}nm")

for promotion_index in range(1, MAX_EC_PROMOTIONS):
    # Promotion ID
    Tracker.alias(str, f"promo{promotion_index}id")
    # Promotion name
    Tracker.alias(str, f"promo{promotion_index}nm")
    # Promotion creative
    Tracker.alias(str, f"promo{promotion_index}cr")
    # Promotion position
    Tracker.alias(str, f"promo{promotion_index}ps")
