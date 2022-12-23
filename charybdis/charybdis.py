from __future__ import annotations

import asyncio
import datetime
import hashlib
import os
import time
import types
import typing

import httpx


class Api:
    """Hi-Rez API wrapper."""

    SMITE_PC_URL = "https://api.smitegame.com/smiteapi.svc"
    SMITE_XBOX_URL = "https://api.xbox.smitegame.com/smiteapi.svc"
    SMITE_PS4_URL = "https://api.ps4.smitegame.com/smiteapi.svc"
    PALADINS_PC_URl = "https://api.paladins.com/paladinsapi.svc"
    PALADINS_XBOX_URL = "https://api.xbox.paladins.com/paladinsapi.svc"
    PALADINS_PS4_URL = "https://api.ps4.paladins.com/paladinsapi.svc"
    DEFAULT_TIMEOUT = httpx.Timeout(5.0, read=10.0)

    def __init__(
        self,
        base_url: str = SMITE_PC_URL,
        dev_id: str | None = os.getenv("SMITE_DEV_ID"),
        auth_key: str | None = os.getenv("SMITE_AUTH_KEY"),
        delay: datetime.timedelta | None = datetime.timedelta(milliseconds=100),
        verify: bool = True,
        client: httpx.Client | None = None,
        aclient: httpx.AsyncClient | None = None,
    ):
        if dev_id is None or auth_key is None:
            raise ValueError("dev_id and/or auth_key is None.")
        self.base_url = base_url
        self.dev_id = dev_id
        self.auth_key = auth_key
        self.delay = delay
        self.verify = verify
        self.client = client
        self.aclient = aclient
        self._session_id: str | None = None
        self._last: datetime.datetime | None = None

    def __enter__(self) -> Api:
        if self.client is not None:
            raise ValueError(
                "Cannot use a context manager and the"
                " client parameter at the same time."
            )
        self.client = httpx.Client(verify=self.verify, timeout=self.DEFAULT_TIMEOUT)
        return self

    def __exit__(
        self,
        _exc_type: typing.Type[BaseException] | None,
        _exc: BaseException | None,
        _tb: types.TracebackType | None,
    ) -> None:
        assert self.client is not None
        self.client.close()

    async def __aenter__(self) -> Api:
        if self.aclient is not None:
            raise ValueError(
                "Cannot use an async context manager and the"
                " aclient parameter at the same time."
            )
        self.aclient = httpx.AsyncClient(
            verify=self.verify, timeout=self.DEFAULT_TIMEOUT
        )
        return self

    async def __aexit__(
        self,
        _exc_type: typing.Type[BaseException] | None,
        _exc: BaseException | None,
        _tb: types.TracebackType | None,
    ) -> None:
        assert self.aclient is not None
        await self.aclient.aclose()

    def ping(self) -> str:
        """
        Calls the ping method, which seems to return a string with
        the current Smite build and patch version, and the current server date.
        """
        return self._fetch("pingjson").text

    async def aping(self) -> str:
        """Same as ping but asynchronous."""
        return (await self._afetch("pingjson")).text

    def _fetch(self, url: str) -> httpx.Response:
        url = f"{self.base_url}/{url}"
        if self.client is None:
            resp = httpx.get(url, verify=self.verify, timeout=self.DEFAULT_TIMEOUT)
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

    def call_method_dict(self, method_name: str, *args: str) -> dict[str, typing.Any]:
        """Wrapper around call_method which checks that the result is a dict."""
        return self._confirm_is_dict(self.call_method(method_name, *args))

    def call_method_list(self, method_name: str, *args: str) -> list:
        """Wrapper around call_method which checks that the result is a list."""
        return self._confirm_is_list(self.call_method(method_name, *args))

    async def acall_method_dict(
        self, method_name: str, *args: str
    ) -> dict[str, typing.Any]:
        """Same as call_method_dict but asynchronous."""
        return self._confirm_is_dict(await self.acall_method(method_name, *args))

    async def acall_method_list(self, method_name: str, *args: str) -> list:
        """Same as call_method_list but asynchronous."""
        return self._confirm_is_list(await self.acall_method(method_name, *args))

    @staticmethod
    def _confirm_is_dict(x: typing.Any) -> dict:
        if not isinstance(x, dict):
            raise RuntimeError(f"Expected dict, received type: {type(x)}, val: {x}")
        return x

    @staticmethod
    def _confirm_is_list(x: typing.Any) -> list:
        if not isinstance(x, list):
            raise RuntimeError(f"Expected list, received type: {type(x)}, val: {x}")
        return x

    def call_method(self, method_name: str, *args: str) -> typing.Any:
        """
        Calls Hi-Rez API method 'method_name' with variadic arguments 'args'.
        See the Hi-Rez API documentation for info about available methods.
        Also calls create_session if it hasn't been called yet.
        """
        if self._session_id is None:
            self.create_session()
        return self._call_method(method_name, *args)

    async def acall_method(self, method_name: str, *args: str) -> typing.Any:
        """Same as call_method but asynchronous."""
        if self._session_id is None:
            self.create_session()
        return await self._acall_method(method_name, *args)

    def create_session(self) -> None:
        """
        Creates a session with the Hi-Rez API,
        which is required for calling any other Hi-Rez API method (except ping).
        call_method automatically creates a session if it hasn't been done yet.
        Session only lasts around 15 minutes, after which it has to be created again.
        Currently, this recreation has to be done manually (TODO).
        """
        self._session_id = self._call_method("createsession")["session_id"]

    def _call_method(self, method_name: str, *args: str) -> typing.Any:
        now = datetime.datetime.now(datetime.timezone.utc)
        if (to_sleep := self._update_last(now)) is not None:
            time.sleep(to_sleep)
        url = self._create_url(now, method_name, *args)
        return self._fetch(url).json()

    async def _acall_method(self, method_name: str, *args: str) -> typing.Any:
        now = datetime.datetime.now(datetime.timezone.utc)
        if (to_sleep := self._update_last(now)) is not None:
            await asyncio.sleep(to_sleep)
        url = self._create_url(now, method_name, *args)
        return (await self._afetch(url)).json()

    def _update_last(self, now: datetime.datetime) -> float | None:
        if self.delay is None:
            return None

        if self._last is None or self._last + self.delay <= now:
            self._last = now
            return None

        self._last += self.delay
        to_sleep = self._last - now
        return to_sleep.total_seconds()

    def _create_url(self, now: datetime.datetime, method_name: str, *args: str) -> str:
        timestamp = now.strftime("%Y%m%d%H%M%S")
        signature = self._create_signature(method_name, timestamp)
        url = f"{method_name}json/{self.dev_id}/{signature}"
        if method_name != "createsession":
            assert self._session_id is not None
            url += f"/{self._session_id}"
        url += f"/{timestamp}"
        for arg in args:
            url += f"/{arg}"
        return url

    def _create_signature(self, method_name: str, timestamp: str) -> str:
        return hashlib.md5(
            f"{self.dev_id}{method_name}{self.auth_key}{timestamp}".encode("utf8")
        ).hexdigest()
