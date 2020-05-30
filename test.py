from m3u8_downloader import Downloader

base_url = (
    'https://youku.com-l-youku.com/20181215/3759_7c65a40b/1000k/hls/index.m3u8'
)


d = Downloader(base_url, use_proxy=False)
d.download(workers=16)
