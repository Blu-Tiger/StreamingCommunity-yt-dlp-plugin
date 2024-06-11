import re
import json
from dateutil import parser
# from datetime import datetime
# from yt_dlp.utils import (
#     clean_html,
#     extract_attributes,
#     get_element_by_attribute,
#     get_element_by_class,
#     get_element_html_by_class,
#     get_elements_by_class,
#     int_or_none,
#     join_nonempty,
#     parse_count,
#     parse_duration,
#     unescapeHTML,
# )
from yt_dlp.utils.traversal import traverse_obj

from yt_dlp.extractor.common import InfoExtractor


class StreamingCommunityIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?streamingcommunity\.\w+/watch/(?P<id>\d+)(\?e=\d+)?'
    _TESTS = [{
        'url': 'https://streamingcommunity.li/watch/7540?e=50636',
        'md5': '73c35edd689c3a1a1d93a13eb1338bc4',
        'info_dict': {
            'id': '7540',
            'ext': 'mp4',
            # 'description': "",
            'title': 'Hazbin Hotel - S01E02 - La radio ha ucciso la televisione',
            'duration': 1500,
            'series': 'Hazbin Hotel',
            'description': 'md5:af205da3f15380c37fec03364f55c267',
            'episode_id': 50636,
            'modified_timestamp': 1705636443.0,
            'season_id': 3965,
            'episode': 'La radio ha ucciso la televisione',
            'series_id': '7540',
            'season': 'Season 1',
            'episode_number': 2,
            'timestamp': 1705636443.0,
            'playable_in_embed': True,
            'season_number': 1,
            'upload_date': '20240119',
            'modified_date': '20240119',
            # 'series': '',
            # Then if the test run fails, it will output the missing/incorrect fields.
            # Properties can be added as:
            # * A value, e.g.
            #     'title': 'Video title goes here',
            # * MD5 checksum; start the string with 'md5:', e.g.
            #     'description': 'md5:098f6bcd4621d373cade4e832627b4f6',
            # * A regular expression; start the string with 're:', e.g.
            #     'thumbnail': r're:^https?://.*\.jpg$',
            # * A count of elements in a list; start the string with 'count:', e.g.
            #     'tags': 'count:10',
            # * Any Python type, e.g.
            #     'view_count': int,
        },

    },
    {
        'url': 'https://streamingcommunity.li/watch/6034',
        'md5': 'df75d007be6353835f28fba1a27d2814',
        'info_dict': {
            'id': '6034',
            'ext': 'mp4',
            'timestamp': 1673784691.0,
            'release_date': '20230719',
            'modified_date': '20240205',
            'modified_timestamp': 1707130801.0,
            'title': 'Oppenheimer',
            'description': 'md5:c93328d3e492970ac3bec6f9fb8c4e87',
            'upload_date': '20230115',
            'playable_in_embed': True,
        }
    }]

    def _iso8601_to_unix(self, iso8601_string):
        """
        Converts an ISO 8601 formatted string to a Unix timestamp.

        Parameters:
        - iso8601_string (str): The ISO 8601 date-time string to convert.

        Returns:
        - float: The Unix timestamp equivalent of the input date-time string.
        """
        datetime_obj = parser.parse(iso8601_string)
        unix_timestamp = datetime_obj.timestamp()
        return unix_timestamp

    def _real_extract(self, url):
        """
        Extracts information from the given URL of a StreamingCommunity video.

        Parameters:
        - url (str): The URL of the video to extract information from.

        Returns:
        - dict: A dictionary containing extracted video information such as ID, title, release date, timestamp, description, and more.
        """
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        info = json.loads(self._html_search_regex(r'data-page="([^"]+)',webpage,'info'))

        iframe = self._download_webpage(traverse_obj(info, ('props', 'embedUrl')), video_id)
        iframeinfo_url = self._html_search_regex(r'<iframe[^>]+src="([^"]+)',iframe,'iframe info')
        vixcloud_iframe = self._download_webpage(iframeinfo_url, video_id)
        playlist_info = json.loads(re.sub(r',[^"]+}','}',self._html_search_regex(r'window\.masterPlaylist[^:]+params:[^{]+({[^<]+?})',vixcloud_iframe,'iframe info').replace('\'','"')))
        playlist_url = self._html_search_regex(r'window\.masterPlaylist[^<]+url:[^<]+\'([^<]+?)\'',vixcloud_iframe,'iframe info')
        # video_info = json.loads(self._html_search_regex(r'window\.video[^{]+({[^<]+});',vixcloud_iframe,'iframe info'))
        tokens_url = ''
        for x,y in playlist_info.items():
            if y and x=='token':
                tokens_url = x + '=' + y
            if y and 'token' in x:
                tokens_url = tokens_url + '&'+ x + '=' + y

        dl_url = playlist_url + '?' + '&expires=' + playlist_info.get('expires')
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(dl_url, video_id)

        video_return_dic = {
            'id': video_id,
            'title': traverse_obj(info, ('props','title','name')),
            'release_date' : traverse_obj(info, ('props','title','release_date')).replace('-',''),
            'timestamp': self._iso8601_to_unix(traverse_obj(info, ('props','title','created_at'))),
            'modified_timestamp': self._iso8601_to_unix(traverse_obj(info, ('props','title','updated_at'))),
            'description': traverse_obj(info, ('props','title','plot')),
            'playable_in_embed': True,
            'formats': formats,
            'subtitles': subtitles,
        }

        if traverse_obj(info, ('props','title','type'))=='tv':
            video_return_dic.pop('release_date')
            SnEn = 'S' + str(traverse_obj(info, ('props','episode','season','number'))).zfill(2) + 'E' + str(traverse_obj(info, ('props','episode','number'))).zfill(2)
            title = traverse_obj(info, ('props','title','name')) + ' - ' + SnEn + ' - ' + traverse_obj(info, ('props','episode','name'))
            video_return_dic.update({
                'timestamp': self._iso8601_to_unix(traverse_obj(info, ('props','episode','created_at'))),
                'modified_timestamp': self._iso8601_to_unix(traverse_obj(info, ('props','episode','updated_at'))),
                'title': title,
                'description': traverse_obj(info, ('props','episode','plot')),
                'series': traverse_obj(info, ('props','title','name')),
                'series_id': video_id,
                'season_number': traverse_obj(info, ('props','episode','season','number')),
                'season_id': traverse_obj(info, ('props','episode','season','id')),
                'episode': traverse_obj(info, ('props','episode','name')),
                'episode_number': traverse_obj(info, ('props','episode','number')),
                'episode_id': traverse_obj(info, ('props','episode','id')),
                'duration': traverse_obj(info, ('props','episode','duration'))*60
            })

        return video_return_dic
