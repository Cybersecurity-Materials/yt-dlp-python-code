import functools

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    str_or_none,
    traverse_obj,
    url_or_none,
    urljoin,
)


class AsobiStageIE(InfoExtractor):
    IE_DESC = 'ASOBISTAGE (アソビステージ)'
    _VALID_URL = r'https://asobistage\.asobistore\.jp/event/(?P<id>\w+/(?P<type>\w+)/\w+)(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://asobistage.asobistore.jp/event/315passionhour_2022summer/archive/frame',
        'info_dict': {
            'id': '315passionhour_2022summer/archive/frame/edff52f2',
            'title': '315passion_FRAME_only',
            'live_status': 'was_live',
            'thumbnail': r're:^https?://[\w.-]+/\w+/\w+',
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
    }, {
        'url': 'https://asobistage.asobistore.jp/event/idolmaster_idolworld2023_goods/archive/live',
        'info_dict': {
            'id': 'idolmaster_idolworld2023_goods/archive/live/3aef7110',
            'title': 'asobistore_station_1020_serverREC',
            'live_status': 'was_live',
            'thumbnail': r're:^https?://[\w.-]+/\w+/\w+',
        },
        'params': {
            'skip_download': True,
            'ignore_no_formats_error': True,
        },
    }, {
        'url': 'https://asobistage.asobistore.jp/event/ijigenfes_utagassen/player/day1',
        'only_matching': True,
    }]

    def _check_login(self, video_id):
        check_login_json = self._download_json(
            'https://asobistage-api.asobistore.jp/api/v1/check_login', video_id, expected_status=(400),
            note='Checking login status', errnote='Unable to check login status')
        error = traverse_obj(check_login_json, ('payload', 'error_message'), ('error'), get_all=False)

        if not error:
            return
        elif error == 'notlogin':
            self.raise_login_required(metadata_available=False)
        else:
            raise ExtractorError(f'Unknown error: {error}')

    def _get_token(self, video_id):
        return self._search_regex(r'\"([^"]+)\"', self._download_webpage(
            'https://asobistage-api.asobistore.jp/api/v1/vspf/token', video_id,
            note='Getting token', errnote='Unable to get token'),
            name="token")

    def _get_owned_tickets(self, video_id):
        for url, name in [
            ('https://asobistage-api.asobistore.jp/api/v1/purchase_history/list', 'ticket purchase history'),
            ('https://asobistage-api.asobistore.jp/api/v1/serialcode/list', 'redemption history'),
        ]:
            for id in traverse_obj(self._download_json(
                    url, video_id, note=f'Downloading {name}', errnote=f'Unable to download {name}'),
                    ('payload', 'value', ..., 'digital_product_id', {str})):
                yield id

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_type_name = self._match_valid_url(url).group('type')
        webpage = self._download_webpage(url, video_id)

        self._check_login(video_id)

        video_type_id, live_status = {
            'archive': ['archives', 'was_live'],
            'player': ['broadcasts', 'is_live'],
        }.get(video_type_name) or [None, None]
        if not video_type_id:
            raise ExtractorError('Unknown video type')

        event_data = self._search_nextjs_data(webpage, video_id)
        event_id = traverse_obj(event_data, ('query', 'event', {str}))
        event_slug = traverse_obj(event_data, ('query', 'player_slug', {str}))
        event_title = traverse_obj(event_data, ('props', 'pageProps', 'eventCMSData', 'event_name', {str}))
        if not all((event_id, event_slug, event_title)):
            raise ExtractorError('Unable to get required event data')

        channel_list_url = functools.reduce(urljoin, [
            self._search_regex(
                r'"(?P<url>https://asobistage\.asobistore\.jp/cdn/[^/]+/)', webpage,
                'cdn endpoint url', group=('url')),
            'events/', f'{event_id}/', f'{video_type_id}.json'])
        channels_json = self._download_json(
            channel_list_url, video_id, fatal=False,
            note='Getting channel list', errnote='Unable to get channel list')
        available_channels = traverse_obj(channels_json, (
            video_type_id, lambda _, v: v['broadcast_slug'] == event_slug, 'channels',
            lambda _, v: v['chennel_vspf_id'] != '00000', {dict}))

        owned_tickets = set(self._get_owned_tickets(video_id))
        if not owned_tickets.intersection(traverse_obj(
                available_channels, (..., 'viewrights', ..., 'tickets', ..., 'digital_product_id', {str_or_none}))):
            raise ExtractorError('No valid ticket for this event', expected=True)

        channel_ids = traverse_obj(available_channels, (..., 'chennel_vspf_id', {str}))

        token = self._get_token(video_id)

        entries = []
        for channel_id in channel_ids:
            channel_data = {}

            if video_type_name == 'archive':
                channel_json = self._download_json(
                    f'https://survapi.channel.or.jp/proxy/v1/contents/{channel_id}/get_by_cuid', f'{video_id}/{channel_id}',
                    note='Getting archive channel info', errnote='Unable to get archive channel info',
                    headers={'Authorization': f'Bearer {token}'})
                channel_data = traverse_obj(channel_json, ('ex_content', {
                    'm3u8_url': 'streaming_url',
                    'title': 'title',
                    'thumbnail': ('thumbnail', 'url'),
                }))
            elif video_type_name == 'player':
                channel_json = self._download_json(
                    f'https://survapi.channel.or.jp/ex/events/{channel_id}', f'{video_id}/{channel_id}',
                    note='Getting live channel info', errnote='Unable to get live channel info',
                    headers={'Authorization': f'Bearer {token}'}, query={'embed': 'channel'})
                channel_data = traverse_obj(channel_json, ('data', {
                    'm3u8_url': ('Channel', 'Custom_live_url'),
                    'title': 'Name',
                    'thumbnail': 'Poster_url',
                }))

            m3u8_url = channel_data.get('m3u8_url')
            if not m3u8_url:
                raise ExtractorError('Unable to get channel m3u8 url')

            entries.append({
                'id': channel_id,
                'title': channel_data.get('title'),
                'formats': self._extract_m3u8_formats(m3u8_url, video_id=f'{video_id}/{channel_id}', fatal=False),
                'live_status': live_status,
                'thumbnail': channel_data.get('thumbnail'),
            })

        return {
            '_type': 'playlist',
            'id': video_id,
            'title': event_title,
            'entries': entries,
            'thumbnail': traverse_obj(
                event_data, ('props', 'pageProps', 'eventCMSData', 'event_thumbnail_image', {url_or_none})),
        }