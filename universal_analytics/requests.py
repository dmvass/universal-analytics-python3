from abc import ABCMeta, abstractmethod
from urllib.parse import urlencode
import logging

import httpx


__all__ = ["HTTPRequest", "HTTPBatchRequest", "AsyncHTTPRequest",
           "AsyncHTTPBatchRequest"]


logger = logging.getLogger(__name__)


def encode_payload(payload):
    if not isinstance(payload, (list, tuple)):
        payload = [payload]
    return "\n".join(map(urlencode, payload))


class BaseHTTPRequest(metaclass=ABCMeta):
    default_user_agent = "Universal Analytics"
    http_client_cls = None

    def __init__(self, session=None, user_agent=None):
        self.user_agent = user_agent or self.default_user_agent
        self.session = session or self.http_client_cls(headers=self.headers)

    @property
    def headers(self):
        return {"User-Agent": self.user_agent}

    @abstractmethod
    def send(self, data):
        pass

    @abstractmethod
    def close(self):
        pass


class HTTPRequest(BaseHTTPRequest):
    """Send data using the Measurement Protocol by making HTTP POST requests
    to the collect endpoint.

    :param aiohttp.ClientSession session: http session
    :param str user_agent: client user_agent

    """
    endpoint = "https://www.google-analytics.com/collect"
    http_client_cls = httpx.Client

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def send(self, data):
        """Apply stored properties to the given dataset and POST to the
        configured endpoint.
        """
        payload = encode_payload(data)
        logger.debug("Request: POST %s; payload=%s", self.endpoint, payload)
        self.session.post(self.endpoint, data=payload)

    def close(self):
        self.session.close()


class HTTPBatchRequest(HTTPRequest):
    """Send data using the Measurement Protocol by making HTTP POST requests
    to the batch endpoint.

    :param aiohttp.ClientSession session: http session
    :param str user_agent: client user_agent

    """
    endpoint = "https://www.google-analytics.com/batch"
    max_batch_size = 20

    def __init__(self, session=None, user_agent=None):
        super().__init__(session=session, user_agent=user_agent)
        self.reset()

    def reset(self):
        self._batch_data = []

    def _send(self):
        if self._batch_data:
            super().send(self._batch_data)
        self.reset()

    def send(self, data):
        self._batch_data.append(data)
        if len(self._batch_data) >= self.max_batch_size:
            self._send()

    def close(self):
        self._send()
        super().close()


class AsyncHTTPRequest(BaseHTTPRequest):
    """Send data using the Measurement Protocol by making asynchronous
    HTTP POST requests to the collect endpoint.

    :param aiohttp.ClientSession session: http session
    :param str user_agent: client user_agent

    """
    endpoint = "https://www.google-analytics.com/collect"
    http_client_cls = httpx.AsyncClient

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def send(self, data):
        """Apply stored properties to the given dataset and POST to the
        configured endpoint async.
        """
        payload = encode_payload(data)
        logger.debug("Request: POST %s; payload=%s", self.endpoint, payload)
        await self.session.post(self.endpoint, data=payload)

    async def close(self):
        await self.session.aclose()


class AsyncHTTPBatchRequest(AsyncHTTPRequest):
    """Send data using the Measurement Protocol by making asynchronous
    HTTP POST requests to the batch endpoint.

    :param aiohttp.ClientSession session: http session
    :param str user_agent: client user_agent

    """
    endpoint = "https://www.google-analytics.com/batch"
    max_batch_size = 20

    def __init__(self, session=None, user_agent=None):
        super().__init__(session=session, user_agent=user_agent)
        self.reset()

    def reset(self):
        self._batch_data = []

    async def _send(self):
        if self._batch_data:
            await super().send(self._batch_data)
        self.reset()

    async def send(self, data):
        self._batch_data.append(data)
        if len(self._batch_data) >= self.max_batch_size:
            await self._send()

    async def close(self):
        await self._send()
        await super().close()
