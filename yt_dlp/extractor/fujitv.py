# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class FujiTVFODPlus7IE(InfoExtractor):
    _VALID_URL = r'https?://fod\.fujitv\.co\.jp/title/[0-9a-z]{4}/(?P<id>[0-9a-z]+)'
    _BASE_URL = 'http://i.fod.fujitv.co.jp/'
    _BITRATE_MAP = {
        300: (320, 180),
        800: (640, 360),
        1200: (1280, 720),
        2000: (1280, 720),
        4000: (1920, 1080),
    }

    _TESTS = [{
        'url': 'https://fod.fujitv.co.jp/title/5d40/5d40810075',
        'info_dict': {
            'id': '5d40810075',
            'title': 'ちびまる子ちゃん　#1317 『おっちゃんのまほうカード』の巻／『まるちゃん おばけ屋敷にいく』の巻',
            'description': '【原作35周年！あなたの好きな“神回”さくらももこ原作まつり】\n明日から夏休み。まる子は、一学期の荷物をいっきにひきずりながら歩いていた。下校途中の木の下で、おじさんが不思議なカードを売っているのを見かけたまる子とお姉ちゃんは、どうしても欲しくなり…／お母さんにデパートでやっているおばけ屋敷に連れていってとせが むまる子。あっさり却下されるが、お父さんが実は自分も行きたかったと連れて行ってくれることに。いよいよおばけ屋敷に入ったまる子と父ヒロシ。次々あらわれるおばけに二人の運命は…？',
            'ext': 'mp4',
            'format_id': '4000',
            'thumbnail': 'http://i.fod.fujitv.co.jp/pc/image/wbtn/wbtn_5d40810075.jpg'
        },
        'skip': 'Expires after a week'
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        self._download_webpage(url, video_id, fatal=False)
        formats = self._extract_m3u8_formats(
            self._BASE_URL + 'abr/tv_android/%s.m3u8' % video_id, video_id, 'mp4')
        token = self._get_cookies(url).get('CT').value
        json_info = self._download_json('https://fod-sp.fujitv.co.jp/apps/api/episode/detail/?ep_id=%s&is_premium=false' % video_id, video_id, headers={'x-authorization': f'Bearer {token}'})
        for f in formats:
            wh = self._BITRATE_MAP.get(f.get('tbr'))
            if wh:
                f.update({
                    'width': wh[0],
                    'height': wh[1],
                })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': f"{json_info.get('lu_title')}　{json_info.get('ep_title')}",
            'description': json_info.get('ep_description'),
            'formats': formats,
            'thumbnail': self._BASE_URL + 'pc/image/wbtn/wbtn_%s.jpg' % video_id,
        }
