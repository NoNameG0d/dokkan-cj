import base64
import hashlib
import hmac
import time
import uuid
from typing import Dict, Tuple, Any

import aiofiles
import aiohttp
import mitmproxy.http
from multidict import CIMultiDictProxy

from .database import load_db, db_loaded

"""
    Async-based Dokkan server request class
"""


class DokkanAPI:

    def __init__(self, http: mitmproxy.http.HTTPFlow):
        self.user_agent = http.request.headers["User-Agent"]
        self.region = http.metadata["region"]
        self.platform = http.metadata["platform"]
        self.cf_host = http.metadata["cf_host"]
        self.host = http.metadata["host"]
        self.port = http.metadata["port"]
        self.port_str = http.metadata["port_str"]
        self.client_version = http.metadata["client_version"]
        self.basic_auth = http.metadata["basic_auth"]
        self.unique_id = http.metadata["unique_id"]
        self.access_token = http.metadata["access_token"]
        self.access_secret = http.metadata["access_secret"]
        self.asset_version = http.metadata["asset_version"]
        self.database_version = http.metadata["database_version"]

    def make_auth_headers(self, auth: str, extra_headers=None) -> Dict[str, str]:
        if extra_headers is None:
            extra_headers = {}
        return {
            'User-Agent': self.user_agent,
            'Authorization': auth,
            'Content-type': 'application/json',
            'X-Platform': self.platform,
            'X-AssetVersion': self.asset_version,
            'X-DatabaseVersion': self.database_version,
            'X-ClientVersion': self.client_version,
            **extra_headers
        }

    def make_mac_auth(self, method: str, action: str) -> str:
        ts = int(round(time.time(), 0))
        nonce = f'{ts}:{uuid.uuid4().hex}'
        value = f'{ts}\n{nonce}\n{method}\n{action}\n{self.host}\n{self.port_str}\n\n'
        hmac_hex_bin = hmac.new(self.access_secret.encode('utf-8'), value.encode('utf-8'), hashlib.sha256).digest()
        mac = base64.b64encode(hmac_hex_bin).decode()
        return f'MAC id="{self.access_token}" nonce="{nonce}" ts="{ts}" mac="{mac}"'

    async def request(self, method: str, url: str, is_mac: bool = True, **kwargs) -> Tuple[int, 'CIMultiDictProxy[str]', Any]:
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        if is_mac:
            kwargs['headers'] = {**self.make_auth_headers(self.make_mac_auth(method, url)), **kwargs['headers']}
        async with aiohttp.ClientSession() as session:
            async with session.request(method, f'https://{self.host}{url}', **kwargs) as resp:
                return resp.status, resp.headers, await resp.json()

    async def get(self, url: str, is_mac: bool = True, **kwargs) -> Tuple[int, 'CIMultiDictProxy[str]', Any]:
        return await self.request('GET', url, is_mac, **kwargs)

    async def post(self, url: str, is_mac: bool = True, **kwargs) -> Tuple[int, 'CIMultiDictProxy[str]', Any]:
        return await self.request('POST', url, is_mac, **kwargs)

    async def put(self, url: str, is_mac: bool = True, **kwargs) -> Tuple[int, 'CIMultiDictProxy[str]', Any]:
        return await self.request('PUT', url, is_mac, **kwargs)

    @staticmethod
    async def download_file(url: str, save_path: str, **kwargs) -> bool:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, **kwargs) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(save_path, mode='wb')
                    await f.write(await resp.read())
                    await f.close()
                    return True
                else:
                    return False
