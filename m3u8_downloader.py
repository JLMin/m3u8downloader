import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import m3u8

from util import get_response
import sys
import requests

# slice
# D:\software\ffmpeg\bin\ffmpeg -i EP4.ts -c copy -map 0 -f
# segment -segment_list ep4.m3u8 -segment_time 200 ep4%03d.ts
PATH_BASE = Path(__file__).parents[0]
PATH_TEMP = Path(PATH_BASE, 'temp')


class Downloader:

    def __init__(self, m3u8_url, use_proxy=False):
        self.m3u8_url  = m3u8_url
        self.use_proxy = use_proxy
        self.base_url  = m3u8_url.rsplit('/', 1)[0] + '/'
        self.ep_name   = m3u8_url.rsplit('/', 1)[-1].split('.')[0]
        self.finished  = 0

    def download(self, workers=8):
        response = get_response(self.m3u8_url, use_proxy=self.use_proxy)
        segments = m3u8.loads(response.text).data['segments']
        self.playlist = list((self.base_url + s['uri']) for s in segments)
        self.total = len(self.playlist)
        Path.mkdir(PATH_TEMP, exist_ok=True)
        print(f'开始下载[{self.total}]:')
        self._download_playlist(workers)
        print('下载成功.')
        self._merge()
        print('合并成功.')
        shutil.rmtree(PATH_TEMP)

    def _download_playlist(self, workers):
        fail_list = []
        with ThreadPoolExecutor(max_workers=workers) as e:
            futures = {e.submit(self._download_ts, i, ts_url): ts_url
                       for i, ts_url in enumerate(self.playlist)}
            for future in as_completed(futures):
                ts_url = futures[future]
                try:
                    data = future.result()
                except Exception as exc:
                    print(exc)
                    fail_list.append(ts_url)
                else:
                    self.finished += 1
                    print(f'{self.finished / self.total:.2%}', end='\r')
        if len(fail_list) > 0:
            print(f'下载失败[{len(fail_list)}], 重新下载:')
            self._download_playlist(workers)

    def _download_ts(self, index, url):
        ts_response = get_response(url, use_proxy=self.use_proxy, timeout=10)
        if ts_response.status_code != 200:
            raise Exception(f'download{url} fail')
        else:
            digit = len(str(self.total))
            ts_id = f'{index:0{digit}}.ts'
            file = Path.joinpath(PATH_TEMP, ts_id)
            with open(file, 'wb') as ts_file:
                ts_file.write(ts_response.content)

    def _merge(self):
        path_video = Path(PATH_BASE, self.ep_name)
        with open(path_video, 'w+b') as video:
            for ts in (item for item in PATH_TEMP.iterdir()
                       if item.suffix == '.ts'):
                with open(ts, 'rb') as fp:
                    video.write(fp.read())


def get_response(url, use_proxy=False, **kwargs):
    headers = {'User-Agent': 'Mozilla/5.0'}
    proxies = {'https': 'https://127.0.0.1:1080',
               'http': 'http://127.0.0.1:1080'}
    proxy__ = proxies if use_proxy else None
    response = requests.get(url, headers=headers, proxies=proxy__, **kwargs)
    response.raise_for_status()
    return response
