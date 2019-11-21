import datetime
import math
import uuid
from unittest import mock

import asynctest
import pytest

from universal_analytics import tracker
from universal_analytics.requests import AsyncHTTPRequest


class TestTracker:

    def setup_method(self, method):
        self.mocked_http = mock.Mock()
        self.account = "UA-XXXXX-Y"
        self.cid = str(uuid.uuid4())
        self.tracker = tracker.Tracker("UA-XXXXX-Y", self.mocked_http)

    @mock.patch("universal_analytics.tracker.generate_uuid")
    def test_init_default(self, mocked_generate_uuid):
        mocked_generate_uuid.return_value = self.cid
        t = tracker.Tracker(self.account, self.mocked_http)

        assert t.account == self.account
        assert t.http == self.mocked_http
        assert t.hash_client_id is False
        assert t.params == {"v": 1, "tid": self.account, "cid": self.cid}

    def test_init(self):
        expected_user_id = 2
        t = tracker.Tracker(self.account,
                            self.mocked_http,
                            hash_client_id=True,
                            client_id=self.cid,
                            user_id=expected_user_id)

        assert t.account == self.account
        assert t.http == self.mocked_http
        assert t.hash_client_id is True
        assert t.params == {"v": 1,
                            "tid": self.account,
                            "cid": self.cid,
                            "uid": expected_user_id}

    def test_persistent_campaign_settings(self):
        # Apply campaign settings
        self.tracker.set("campaignName", "testing-campaign")
        self.tracker.set("campaignMedium", "testing-medium")
        self.tracker["campaignSource"] = "test-source"

        assert self.tracker.params["cn"] == "testing-campaign"
        assert self.tracker.params["cm"] == "testing-medium"
        assert self.tracker.params["cs"] == "test-source"

    def test_send_pageview(self):
        # Send a pageview
        self.tracker.send("pageview", "/test")
        self.mocked_http.send.called_with({"t": "pageview",
                                           "dp": "/test",
                                           "v": 1,
                                           "tid": self.account,
                                           "cid": self.cid})

    def test_send_interactive_event(self):
        # Send an event
        self.tracker.send("event", "mycat", "myact", "mylbl",
                          {"noninteraction": 1, "page": "/1"})
        self.mocked_http.send.called_with({"t": "event",
                                           "ec": "mycat",
                                           "ea": "myact",
                                           "el": "mylbl",
                                           "ni": 1,
                                           "dp": "/1",
                                           "v": 1,
                                           "tid": self.account,
                                           "cid": self.cid})

    def test_send_social_hit(self):
        # Send a social hit
        self.tracker.send("social", "facebook", "share", "/test#social")
        self.mocked_http.send.called_with({"t": "social",
                                           "sn": "facebook",
                                           "sa": "share",
                                           "st": "/test#social",
                                           "v": 1,
                                           "tid": self.account,
                                           "cid": self.cid})

    def test_send_item(self):
        self.tracker.send("item", {
            "transactionId": "12345abc",
            "itemName": "pizza",
            "itemCode": "abc",
            "itemCategory": "hawaiian",
            "itemQuantity": 1
        }, hitage=7200)
        self.mocked_http.send.called_with({"t": "item",
                                           "qt": 7200000,
                                           "ti": "12345abc",
                                           "in": "pizza",
                                           "ic": "abc",
                                           "iv": "hawaiian",
                                           "iq": 1.0,
                                           "v": 1,
                                           "tid": self.account,
                                           "cid": self.cid})

    def test_send_transaction(self):
        self.tracker.send("transaction", {
            "transactionId": "12345abc",
            "transactionAffiliation": "phone order",
            "transactionRevenue": 28.00,
            "transactionTax": 3.00,
            "transactionShipping": 0.45,
            "transactionCurrency": "USD"
        }, hitage=7200)
        self.mocked_http.send.called_with({"t": "transaction",
                                           "qt": 7200000,
                                           "ti": "12345abc",
                                           "ta": "phone order",
                                           "tr": 28.00,
                                           "tt": 3.00,
                                           "ts": 0.45,
                                           "cu": "USD",
                                           "v": 1,
                                           "tid": self.account,
                                           "cid": self.cid})

    @pytest.mark.asyncio
    async def test_send_with_async_request(self):
        session = mock.Mock(post=asynctest.CoroutineMock(),
                            close=asynctest.CoroutineMock())
        async with AsyncHTTPRequest(session=session) as http:
            t = tracker.Tracker("UA-XXXXX-Y", http)
            await t.send("pageview", "/test")
            session.post.assert_called_once()


class TestTime:

    def setup_method(self, method):
        self.datetime = datetime.datetime(2019, 11, 3, 19, 30, 37, 361000)
        self.timestamp = self.datetime.timestamp()

    def test_from_unix(self):
        milliseconds, seconds = math.modf(self.timestamp)
        assert self.datetime == tracker.Time.from_unix(seconds,
                                                       milliseconds * 1000)

    def test_to_unix(self):
        assert self.timestamp == tracker.Time.to_unix(self.datetime)
        with pytest.raises(TypeError):
            tracker.Time.to_unix(1572802237.361)
