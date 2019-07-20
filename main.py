from mitmproxy import proxy, options, ctx
from mitmproxy.addons import default_addons
from mitmproxy.master import Master
from mitmproxy.utils import human

import addons

"""
    Initialize mitmproxy server and initialize addons. Server will listen on all interfaces.
    
    Addon order is important.
    
    Nox seems to use 172.17.100.2 to identify the host computer. Use 172.17.100.2:8080 as the proxy server in your phones WiFi proxy settings.
"""


def start():
    opts = options.Options(listen_host='0.0.0.0', listen_port=8080)
    pconf = proxy.config.ProxyConfig(opts)

    mitm = Master(opts)
    mitm.server = proxy.server.ProxyServer(pconf)
    mitm.addons.add(*default_addons())

    mitm.addons.add(addons.GameInfo())
    mitm.addons.add(addons.DownloadDatabase())
    mitm.addons.add(addons.CardSwapDemo())

    try:
        print("Proxy server listening at http://{}".format(human.format_address(ctx.master.server.address)))
        mitm.run()
    except KeyboardInterrupt:
        mitm.shutdown()


if __name__ == "__main__":
    start()
