import asyncio
import datetime
import hashlib
import os
import time

import httpx


class Api:
    base_url = "https://api.smitegame.com/smiteapi.svc"

    def __init__(
        self,
        dev_id: str = os.getenv("SMITE_DEV_ID"),
        auth_key: str = os.getenv("SMITE_AUTH_KEY"),
        delay: datetime.timedelta | None = datetime.timedelta(milliseconds=100),
        verify: bool = True,
        client: httpx.Client | None = None,
        aclient: httpx.AsyncClient | None = None,
    ):
        self.dev_id = dev_id
        self.auth_key = auth_key
        self.delay = delay
        self.verify = verify
        self.client = client
        self.aclient = aclient
        self._session_id: str | None = None
        self._last: datetime.datetime | None = None
        self._alock = asyncio.Lock()
        if self.dev_id is None or self.auth_key is None:
            raise ValueError("DEV_ID and/or AUTH_KEY is not set.")

    def __enter__(self):
        if self.client is not None:
            raise ValueError(
                "Cannot use a context manager and the"
                " client parameter at the same time."
            )
        self.client = httpx.Client(verify=self.verify)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    async def __aenter__(self):
        if self.aclient is not None:
            raise ValueError(
                "Cannot use an async context manager and the"
                " aclient parameter at the same time."
            )
        self.aclient = httpx.AsyncClient(verify=self.verify)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclient.aclose()

    def ping(self) -> str:
        return self._fetch("pingjson").text

    async def aping(self) -> str:
        return (await self._afetch("pingjson")).text

    def _fetch(self, url: str) -> httpx.Response:
        url = f"{self.base_url}/{url}"
        if self.client is None:
            resp = httpx.get(url, verify=self.verify)
        else:
            resp = self.client.get(url)
        resp.raise_for_status()
        return resp

    async def _afetch(self, url: str) -> httpx.Response:
        url = f"{self.base_url}/{url}"
        if self.aclient is None:
            raise NotImplementedError(
                "Making async requests without using a context manager or passing"
                " httpx.AsyncClient into the aclient parameter is not supported."
            )
        else:
            resp = await self.aclient.get(url)
        resp.raise_for_status()
        return resp

    def call_method(self, *args) -> dict | list:
        if self._session_id is None:
            self.create_session()
        return self._call_method(*args)

    async def acall_method(self, *args) -> dict | list:
        async with self._alock:
            if self._session_id is None:
                await self.acreate_session()
        return await self._acall_method(*args)

    def create_session(self) -> None:
        self._session_id = self._call_method("createsession")["session_id"]

    async def acreate_session(self) -> None:
        self._session_id = (await self._acall_method("createsession"))["session_id"]

    def _call_method(self, method_name: str, *args) -> dict | list:
        now = datetime.datetime.now(datetime.timezone.utc)
        if (to_sleep := self._update_last(now)) is not None:
            time.sleep(to_sleep)
        url = self._create_url(now, method_name, *args)
        return self._fetch(url).json()

    async def _acall_method(self, method_name: str, *args) -> dict | list:
        now = datetime.datetime.now(datetime.timezone.utc)
        if (to_sleep := self._update_last(now)) is not None:
            await asyncio.sleep(to_sleep)
        url = self._create_url(now, method_name, *args)
        return (await self._afetch(url)).json()

    def _update_last(self, now: datetime.datetime) -> float | None:
        if self.delay is not None:
            if self._last is None or self._last + self.delay <= now:
                self._last = now
            else:
                self._last += self.delay
                to_sleep = self._last - now
                return to_sleep.total_seconds()

    def _create_url(self, now: datetime.datetime, method_name: str, *args) -> str:
        timestamp = now.strftime("%Y%m%d%H%M%S")
        signature = self._create_signature(method_name, timestamp)
        url = f"{method_name}json/{self.dev_id}/{signature}"
        if self._session_id is not None:
            url += f"/{self._session_id}"
        url += f"/{timestamp}"
        for arg in args:
            url += f"/{arg}"
        return url

    def _create_signature(self, method_name: str, timestamp: str) -> str:
        return hashlib.md5(
            f"{self.dev_id}{method_name}{self.auth_key}{timestamp}".encode("utf8")
        ).hexdigest()
