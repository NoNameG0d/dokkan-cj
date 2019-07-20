import asyncio
import configparser
import hashlib
import os

import mitmproxy.http
from Crypto.Cipher import AES

from addons.base import DokkanBaseAddon
from addons.dokkan_api import DokkanAPI, load_db, db_loaded
from addons.game_info import Region

"""
    DownloadDatabase addon
    ======================
    
    Will wait for user auth then startup a task to download and decrypt the database.
    
    If database is available and not yet initialized, will initialize during request phase.
    
    Sets:
        http.metadata["database_available"]
        http.metadata["database_path"]
        
    Must be loaded after GameInfo addon
"""


class DownloadDatabase(DokkanBaseAddon):
    japan_database_version = 0
    global_database_version = 0
    initalized = False

    def __init__(self):
        super().__init__()
        self.load_config()

    def load_config(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.japan_database_version = config.getint('Database', 'japan_database_version', fallback=0)
        self.global_database_version = config.getint('Database', 'global_database_version', fallback=0)

    def save_config(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        config.add_section('Database')
        config['Database'] = {
            'japan_database_version': self.japan_database_version,
            'global_database_version': self.global_database_version,
        }
        with open('config.ini', 'w') as f:
            config.write(f)

    def database_download_required(self, http: mitmproxy.http.HTTPFlow) -> bool:
        if http.metadata['region'] == Region.JAPAN and (not os.path.exists('japan.db') or self.japan_database_version < http.metadata['database_version']):
            return True
        if http.metadata['region'] == Region.GLOBAL and (not os.path.exists('global.db') or self.global_database_version < http.metadata['database_version']):
            return True
        return False

    def filter_request(self, http: mitmproxy.http.HTTPFlow) -> bool:
        return http.request.path == '/user' and http.response is not None

    async def download_database(self, http: mitmproxy.http.HTTPFlow):
        dokkan_api = DokkanAPI(http)
        print('[DATABASE] Getting database location...')
        status, resp_headers, json_data = await dokkan_api.get('/client_assets/database')
        print('[DATABASE] Downloading database...')
        enc_file_path = f'{http.metadata["region"].value}.enc.db'
        dec_file_path = f'{http.metadata["region"].value}.db'
        if await dokkan_api.download_file(json_data['url'], enc_file_path):
            print('[DATABASE] Download complete...')
            sqlcipher = SQLCipher()
            print('[DATABASE] Decrypting database...')
            if http.metadata['region'] == Region.JAPAN:
                sqlcipher.decrypt(enc_file_path, bytearray('2db857e837e0a81706e86ea66e2d1633'.encode('utf8')), dec_file_path)
                self.japan_database_version = json_data['version']
            elif http.metadata['region'] == Region.GLOBAL:
                sqlcipher.decrypt(enc_file_path, bytearray('9bf9c6ed9d537c399a6c4513e92ab24717e1a488381e3338593abd923fc8a13b'.encode('utf8')), dec_file_path)
                self.global_database_version = json_data['version']
            print('[DATABASE] Saving config...')
            self.save_config()
        print('[DATABASE] Done')
        self.initalized = True

    def inject_request_metadata(self, http: mitmproxy.http.HTTPFlow):
        if self.initalized:
            http.metadata["database_available"] = not self.database_download_required(http)
            http.metadata["database_path"] = f'{http.metadata["region"].value}.db'
            if not db_loaded and http.metadata["database_available"]:
                load_db(http.metadata["database_path"])
        else:
            http.metadata["database_available"] = False

    def intercept_response(self, http: mitmproxy.http.HTTPFlow):
        if self.database_download_required(http):
            print('[DATABASE] Database download is required...')
            loop = asyncio.get_event_loop()
            loop.create_task(self.download_database(http))
        else:
            self.initalized = True
            print('[DATABASE] Done')


"""
    Minimized SQLCipher decryption. Will probably only work for standard type 3 SQLCipher databases.
    
    Most safety checks are removed, may need to be revised.
"""


class SQLCipher:
    header = b'SQLite format 3\0'
    salt_mask = 0x3a
    key_sz = 32
    key_iter = 64000
    hmac_key_sz = 32
    hmac_key_iter = 2
    page_sz = 1024
    salt_sz = 16
    iv_sz = 16
    reserve_sz = 48
    hmac_sz = 20

    def decrypt(self, filename_in: str, password: bytearray, filename_out: str):
        with open(filename_in, 'rb') as enc, open(filename_out, 'wb', buffering=self.page_sz * 16) as dec:
            enc_size = os.path.getsize(enc.name)
            dec.write(self.header)
            first_page = enc.read(self.page_sz)
            salt = first_page[:self.salt_sz]
            key, hmac_key = self.key_derive(salt, password, self.salt_mask, self.key_sz, self.key_iter, self.hmac_key_sz, self.hmac_key_iter)

            enc.seek(0)
            for i in range(0, int(enc_size / 1024)):
                page = enc.read(self.page_sz)
                if i == 0:
                    page = page[self.salt_sz:]
                page_content = page[:-self.reserve_sz]
                reserve = page[-self.reserve_sz:]
                iv = reserve[:self.iv_sz]
                dec.write(self.decrypt_page(page_content, key, iv))
                dec.write(os.urandom(self.reserve_sz))

            dec.flush()

    @staticmethod
    def decrypt_page(raw, key, iv):
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return cipher.decrypt(raw)

    @staticmethod
    def key_derive(salt, password, salt_mask, key_sz, key_iter, hmac_key_sz, hmac_key_iter):
        key = hashlib.pbkdf2_hmac('sha1', password, salt, key_iter, key_sz)
        hmac_salt = bytearray([x ^ salt_mask for x in salt])
        hmac_key = hashlib.pbkdf2_hmac('sha1', key, hmac_salt, hmac_key_iter, hmac_key_sz)
        return key, hmac_key
