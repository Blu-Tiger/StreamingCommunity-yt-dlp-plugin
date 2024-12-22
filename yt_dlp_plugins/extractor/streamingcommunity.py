import re
import json
from dateutil import parser
from yt_dlp.utils.traversal import traverse_obj
from yt_dlp.extractor.common import InfoExtractor


class StreamingCommunityIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?streamingcommunity\.\w+/watch/(?P<id>\d+)(\?e=\d+)?'

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

        # Extract information from data-page attribute
        info = json.loads(self._html_search_regex(
            r'data-page="([^"]+)', webpage, 'info'))

        # Extract the video page url
        video_page_url = self._download_webpage(traverse_obj(
            info, ('props', 'embedUrl')), video_id)

        # Get the iframe url and iframe page
        iframe_url = self._html_search_regex(
            r'<iframe[^>]+src\s*=\s*"([^"]+)', video_page_url, 'iframe url')
        iframe_page = self._download_webpage(iframe_url, video_id)

        # Extract the playlist params and url from the page js
        playlist_params = json.loads(re.sub(r',[^"]+}', '}', self._html_search_regex(
            r'window\.masterPlaylist[^:]+params:[^{]+({[^<]+?})', iframe_page, 'playlist params').replace('\'', '"')))
        playlist_url = self._html_search_regex(
            r'window\.masterPlaylist[^<]+url:[^<]+\'([^<]+?)\'', iframe_page, 'playlist url')
        # video_info = json.loads(self._html_search_regex(r'window\.video[^{]+({[^<]+});',vixcloud_iframe,'iframe info'))

        # Generate the playlist url
        dl_url = playlist_url + ('&' if bool(re.search(r'\?[^#]+', playlist_url)) else '?') + '&expires=' + \
            playlist_params.get('expires') + '&token=' + \
            playlist_params.get('token')

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            dl_url, video_id)

        video_return_dic = {
            'id': video_id,
            'title': traverse_obj(info, ('props', 'title', 'name')),
            'release_date': traverse_obj(info, ('props', 'title', 'release_date')).replace('-', ''),
            'timestamp': self._iso8601_to_unix(traverse_obj(info, ('props', 'title', 'created_at'))),
            'modified_timestamp': self._iso8601_to_unix(traverse_obj(info, ('props', 'title', 'updated_at'))),
            'description': traverse_obj(info, ('props', 'title', 'plot')),
            'playable_in_embed': True,
            'formats': formats,
            'subtitles': subtitles,
        }

        if traverse_obj(info, ('props', 'title', 'type')) == 'tv':
            video_return_dic.pop('release_date')
            SnEn = 'S' + str(traverse_obj(info, ('props', 'episode', 'season', 'number'))).zfill(
                2) + 'E' + str(traverse_obj(info, ('props', 'episode', 'number'))).zfill(2)
            title = traverse_obj(info, ('props', 'title', 'name')) + ' - ' + \
                SnEn + ' - ' + traverse_obj(info, ('props', 'episode', 'name'))
            video_return_dic.update({
                'timestamp': self._iso8601_to_unix(traverse_obj(info, ('props', 'episode', 'created_at'))),
                'modified_timestamp': self._iso8601_to_unix(traverse_obj(info, ('props', 'episode', 'updated_at'))),
                'title': title,
                'description': traverse_obj(info, ('props', 'episode', 'plot')),
                'series': traverse_obj(info, ('props', 'title', 'name')),
                'series_id': video_id,
                'season_number': traverse_obj(info, ('props', 'episode', 'season', 'number')),
                'season_id': traverse_obj(info, ('props', 'episode', 'season', 'id')),
                'episode': traverse_obj(info, ('props', 'episode', 'name')),
                'episode_number': traverse_obj(info, ('props', 'episode', 'number')),
                'episode_id': traverse_obj(info, ('props', 'episode', 'id')),
                'duration': traverse_obj(info, ('props', 'episode', 'duration'))*60
            })

        return video_return_dic
