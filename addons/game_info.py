import json
from enum import Enum

import mitmproxy.http

from addons.base import DokkanBaseAddon

"""
    GameInfo addon
    ==============

    Will watch the first few packets to generate info on the client to use in future addons

    Sets:
        http.metadata["region"]
        http.metadata["platform"]
        http.metadata["cf_host"]
        http.metadata["host"]
        http.metadata["port"]
        http.metadata["port_str"]
        http.metadata["client_version"]
        http.metadata["basic_auth"]
        http.metadata["unique_id"]
        http.metadata["access_token"]
        http.metadata["access_secret"]
        http.metadata["asset_version"]
        http.metadata["database_version"]
        http.metadata["account_name"]
        http.metadata["account_id"]

"""


class Region(Enum):
    JAPAN = "japan"
    GLOBAL = "global"


class GameInfo(DokkanBaseAddon):
    # /ping
    region = None  # type: Region
    platform = None  # type: str
    cf_host = None  # type: str
    host = None  # type: str
    port = None  # type: int
    port_str = None  # type: int
    # /auth/sign_in
    client_version = None  # type: str
    basic_auth = None  # type: str
    unique_id = None  # type: str
    access_token = None  # type: str
    access_secret = None  # type: str
    # /user
    asset_version = None  # type: int
    database_version = None  # type: int
    account_name = None  # type: str
    account_id = None  # type: int

    def __init__(self):
        super().__init__()

    def filter_request(self, http: mitmproxy.http.HTTPFlow) -> bool:
        return http.request.path in ["/ping", "/auth/sign_in", "/user"] and http.response is not None

    def capture_ping(self, http: mitmproxy.http.HTTPFlow):
        self.platform = http.request.headers["X-Platform"]
        if http.request.host.endswith(".jp"):
            self.region = Region.JAPAN
        else:
            self.region = Region.GLOBAL
        response_json = json.loads(http.response.text)
        self.cf_host = response_json["ping_info"]["cf_uri_prefix"]
        self.host = response_json["ping_info"]["host"]
        self.port = response_json["ping_info"]["port"]
        self.port_str = response_json["ping_info"]["port_str"]

    def capture_auth(self, http: mitmproxy.http.HTTPFlow):
        self.client_version = http.request.headers["X-ClientVersion"]
        self.basic_auth = http.request.headers["Authorization"].split(" ")[1]
        request_json = json.loads(http.request.text)
        self.unique_id = request_json["unique_id"]
        response_json = json.loads(http.response.text)
        self.access_token = response_json["access_token"]
        self.access_secret = response_json["secret"]

    def capture_user(self, http: mitmproxy.http.HTTPFlow):
        try:
            self.asset_version = int(http.request.headers["X-AssetVersion"])
        except ValueError:
            self.asset_version = 0
        try:
            self.database_version = int(http.request.headers["X-DatabaseVersion"])
        except ValueError:
            self.database_version = 0
        reponse_json = json.loads(http.response.text)
        self.account_name = reponse_json["user"]["name"]
        self.account_id = reponse_json["user"]["id"]

    def intercept_response(self, http: mitmproxy.http.HTTPFlow):
        if http.request.path == "/ping":
            self.capture_ping(http)
        elif http.request.path == "/auth/sign_in":
            self.capture_auth(http)
        elif http.request.path == "/user":
            self.capture_user(http)

    def inject_game_info(self, http: mitmproxy.http.HTTPFlow):
        http.metadata["region"] = self.region
        http.metadata["platform"] = self.platform
        http.metadata["cf_host"] = self.cf_host
        http.metadata["host"] = self.host
        http.metadata["port"] = self.port
        http.metadata["port_str"] = self.port_str
        http.metadata["client_version"] = self.client_version
        http.metadata["basic_auth"] = self.basic_auth
        http.metadata["unique_id"] = self.unique_id
        http.metadata["access_token"] = self.access_token
        http.metadata["access_secret"] = self.access_secret
        http.metadata["asset_version"] = self.asset_version
        http.metadata["database_version"] = self.database_version
        http.metadata["account_name"] = self.account_name
        http.metadata["account_id"] = self.account_id

    def inject_request_metadata(self, http: mitmproxy.http.HTTPFlow):
        self.inject_game_info(http)

    def inject_response_metadata(self, http: mitmproxy.http.HTTPFlow):
        self.inject_game_info(http)
