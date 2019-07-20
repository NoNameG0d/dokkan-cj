from abc import abstractmethod, ABC

import mitmproxy.http

"""
    Abstract class that other Dokkan addons are built on.
    
    Subclasses must implement the filter_request() method.
"""


class DokkanBaseAddon(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def filter_request(self, http: mitmproxy.http.HTTPFlow) -> bool:
        """
        Filter requests that will have the addon applied
        :param http: mitmproxy.http.HTTPFlow
        :return: bool
        """

    def intercept_request(self, http: mitmproxy.http.HTTPFlow):
        """
        Modify request before it is sent to the server
        :param http: mitmproxy.http.HTTPFlow
        :return:
        """
        pass

    def intercept_response(self, http: mitmproxy.http.HTTPFlow):
        """
        Modify response body before it get's returned to the client
        :param http: mitmproxy.http.HTTPFlow
        :return:
        """
        pass

    def inject_request_metadata(self, http: mitmproxy.http.HTTPFlow):
        """
        Add to http.metadata for addon data flow.
        Always called
        :param http: mitmproxy.http.HTTPFlow
        :return:
        """
        pass

    def inject_response_metadata(self, http: mitmproxy.http.HTTPFlow):
        """
        Add to http.metadata for addon data flow.
        Always called
        :param http: mitmproxy.http.HTTPFlow
        :return:
        """
        pass

    def request(self, http: mitmproxy.http.HTTPFlow):
        if self.filter_request(http):
            print(f'Intercepting request for {http.request.path}')
            self.intercept_request(http)
        self.inject_request_metadata(http)

    def response(self, http: mitmproxy.http.HTTPFlow):
        if self.filter_request(http):
            print(f'Intercepting response for {http.request.path}')
            self.intercept_response(http)
        self.inject_response_metadata(http)
