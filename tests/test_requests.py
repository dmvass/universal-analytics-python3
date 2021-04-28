import math
from unittest import mock

import asynctest
import pytest

from universal_analytics import requests


class TestHTTPRequest:

    @pytest.fixture
    def session(self):
        return mock.Mock()

    def test_http_request(self, session):
        payload = {"foo": "bar"}
        with requests.HTTPRequest(session=session) as http:
            http.send(payload)
        session.post.assert_called_with(requests.HTTPRequest.endpoint,
                                        data=requests.encode_payload(payload))

    def test_http_request_close_session(self, session):
        with requests.HTTPRequest(session=session):
            pass
        session.close.assert_called()

    def test_http_batch_request(self, session):
        payload_1 = {"foo": "bar"}
        payload_2 = {"bar": "foo"}
        with requests.HTTPBatchRequest(session=session) as http:
            http.send(payload_1)
            http.send(payload_2)

        session.post.assert_called_with(
            requests.HTTPBatchRequest.endpoint,
            data=requests.encode_payload([payload_1, payload_2]))

    def test_http_batch_request_max_batch_size(self, session):
        call_count = 50
        with requests.HTTPBatchRequest(session=session) as http:
            for _ in range(call_count):
                http.send({"foo": "bar"})

        max_batch_size = requests.HTTPBatchRequest.max_batch_size
        expected_call_count = math.ceil(call_count / max_batch_size)
        assert session.post.call_count == expected_call_count

    def test_http_batch_request_close_session(self, session):
        mocked__send = mock.Mock()
        http = requests.HTTPBatchRequest(session=session)
        http._send = mocked__send
        http.close()

        session.close.assert_called()
        mocked__send.assert_called()


class TestAsyncHTTPRequest:

    @pytest.fixture
    def session(self):
        return mock.Mock(post=asynctest.CoroutineMock(),
                         aclose=asynctest.CoroutineMock())

    @pytest.mark.asyncio
    async def test_http_request(self, session):
        payload = {"foo": "bar"}
        async with requests.AsyncHTTPRequest(session=session) as http:
            await http.send(payload)

        session.post.assert_called_with(requests.AsyncHTTPRequest.endpoint,
                                        data=requests.encode_payload(payload))

    @pytest.mark.asyncio
    async def test_http_request_close_session(self, session):
        async with requests.AsyncHTTPRequest(session=session):
            pass
        session.aclose.assert_called()

    @pytest.mark.asyncio
    async def test_http_batch_request(self, session):
        payload_1 = {"foo": "bar"}
        payload_2 = {"bar": "foo"}
        async with requests.AsyncHTTPBatchRequest(session=session) as http:
            await http.send(payload_1)
            await http.send(payload_2)

        session.post.assert_called_with(
            requests.AsyncHTTPBatchRequest.endpoint,
            data=requests.encode_payload([payload_1, payload_2]))

    @pytest.mark.asyncio
    async def test_http_batch_request_max_batch_size(self, session):
        call_count = 50
        async with requests.AsyncHTTPBatchRequest(session=session) as http:
            for _ in range(call_count):
                await http.send({"foo": "bar"})

        max_batch_size = requests.AsyncHTTPBatchRequest.max_batch_size
        expected_call_count = math.ceil(call_count / max_batch_size)
        assert session.post.call_count == expected_call_count

    @pytest.mark.asyncio
    async def test_http_batch_request_close_session(self, session):
        mocked__send = asynctest.CoroutineMock()
        http = requests.AsyncHTTPBatchRequest(session=session)
        http._send = mocked__send
        await http.close()

        session.aclose.assert_called()
        mocked__send.assert_called()
