from .common import InfoExtractor
from ..utils import (
    clean_podcast_url,
    get_element_by_id,
    parse_iso8601,
    traverse_obj,
)


class ApplePodcastsIE(InfoExtractor):
    _VALID_URL = r'https?://podcasts\.apple\.com/(?:[^/]+/)?podcast(?:/[^/]+){1,2}.*?\bi=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://podcasts.apple.com/us/podcast/ferreck-dawn-to-the-break-of-dawn-117/id1625658232?i=1000665010654',
        'md5': '82cc219b8cc1dcf8bfc5a5e99b23b172',
        'info_dict': {
            'id': '1000665010654',
            'ext': 'mp3',
            'title': 'Ferreck Dawn - To The Break of Dawn 117',
            'description': 'md5:1fc571102f79dbd0a77bfd71ffda23bc',
            'upload_date': '20240812',
            'timestamp': 1723449600,
            'duration': 3596,
            'series': 'Ferreck Dawn - To The Break of Dawn',
            'thumbnail': 're:.+[.](png|jpe?g|webp)',
        },
    }, {
        'url': 'https://podcasts.apple.com/us/podcast/207-whitney-webb-returns/id1135137367?i=1000482637777',
        'md5': 'baf8a6b8b8aa6062dbb4639ed73d0052',
        'info_dict': {
            'id': '1000482637777',
            'ext': 'mp3',
            'title': '207 - Whitney Webb Returns',
            'description': 'md5:75ef4316031df7b41ced4e7b987f79c6',
            'upload_date': '20200705',
            'timestamp': 1593932400,
            'duration': 5369,
            'series': 'The Tim Dillon Show',
            'thumbnail': 're:.+[.](png|jpe?g|webp)',
        },
    }, {
        'url': 'https://podcasts.apple.com/podcast/207-whitney-webb-returns/id1135137367?i=1000482637777',
        'only_matching': True,
    }, {
        'url': 'https://podcasts.apple.com/podcast/207-whitney-webb-returns?i=1000482637777',
        'only_matching': True,
    }, {
        'url': 'https://podcasts.apple.com/podcast/id1135137367?i=1000482637777',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        episode_id = self._match_id(url)
        webpage = self._download_webpage(url, episode_id)
        server_data = self._parse_json(
            get_element_by_id('serialized-server-data', webpage),
            episode_id) or [{}]
        model_data = traverse_obj(
            server_data,
            (0, 'data', 'headerButtonItems',
             {lambda x: next(y for y in x
                             if y.get('$kind') == 'bookmark' and y.get('modelType') == 'EpisodeOffer')},
             'model'))
        schema_content = traverse_obj(server_data, (0, 'data', 'seoData', 'schemaContent'))

        return {
            'id': episode_id,
            'title': model_data.get('title') or schema_content.get('name') or self._og_search_title(webpage),
            'url': clean_podcast_url(model_data['streamUrl']),
            'description': schema_content.get('description'),
            'timestamp': parse_iso8601(model_data.get('releaseDate')),
            'duration': model_data.get('duration'),
            'series': schema_content.get('partOfSeries', {}).get('name'),
            'thumbnail': self._og_search_thumbnail(webpage),
            'vcodec': 'none',
        }
