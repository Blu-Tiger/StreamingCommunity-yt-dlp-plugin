import re
import json
import time
from yt_dlp.utils.traversal import traverse_obj
from yt_dlp.extractor.common import InfoExtractor
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


class StreamingCommunityIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?\w*stream\w*unity\w*\.\w+/(\w+/)*(?:watch|titles)/(?P<id>\d+)(?:\?e=\d+)?'

    def _get_title_id(self, info):
        """
        Extract the title ID from the info object.

        Parameters:
        - info (dict): The info object containing title data.

        Returns:
        - str: The title ID.
        """
        return str(traverse_obj(info, ('props', 'title', 'id')))

    def _iso8601_to_unix(self, iso8601_string):
        """
        Converts an ISO 8601 formatted string to a Unix timestamp.

        Parameters:
        - iso8601_string (str): The ISO 8601 date-time string to convert.

        Returns:
        - float: The Unix timestamp equivalent of the input date-time string.
        """
        # Remove 'Z' and strip milliseconds
        cleaned = re.sub(r'(\.\d+)?Z?$', '', iso8601_string)
        unix_timestamp = int(time.mktime(time.strptime(cleaned, "%Y-%m-%dT%H:%M:%S" if 'T' in cleaned else "%Y-%m-%d")))
        return unix_timestamp

    def _sanitize_filename(self, name):
        return re.sub(r'[\\/*?:"<>|]', "", name)

    def _get_domain(self, info):
        return re.match(r'(https?://)?([^/]+)/', traverse_obj(info, ('props', 'ziggy', 'location'))).group(2)

    def _get_base_path(self, info):
        return re.match(r'(https?://)?([^/]+)/([^/]+)', traverse_obj(info, ('props', 'ziggy', 'location'))).group(3)

    def _build_watch_url(self, domain, title_id, episode_id=None, base_path=None):
        return f"https://{domain}" + (f"/{base_path}" if base_path else "") + f"/watch/{title_id}" + (f"?e={episode_id}" if episode_id else "")

    def extract_js_object(self, html: str, var_name: str) -> str:
        """Grab the raw {...} text assigned to window.<var_name> = { ... }"""
        marker = f"window.{var_name}"
        start = html.index(marker)
        brace_start = html.index("{", start)
        depth = 0
        for i in range(brace_start, len(html)):
            if html[i] == "{":
                depth += 1
            elif html[i] == "}":
                depth -= 1
                if depth == 0:
                    return html[brace_start:i + 1]
        raise ValueError(f"Unbalanced braces for {var_name}")

    def js_object_to_dict(self, js_obj: str) -> dict:
        """Convert a (simple) JS object literal string into a Python dict."""
        s = js_obj
        s = re.sub(r'([{,]\s*)([A-Za-z_$][\w$]*)\s*:', r'\1"\2":', s)
        s = re.sub(r"'((?:[^'\\]|\\.)*)'", lambda m: json.dumps(m.group(1)), s)
        s = re.sub(r",\s*([}\]])", r"\1", s)
        return json.loads(s)

    def extract_bool(self, html: str, var_name: str) -> bool:
        marker = f"window.{var_name}"
        idx = html.index(marker)
        snippet = html[idx: idx + 100]
        match = re.search(r'=\s*(true|false)', snippet)
        return match.group(1) == "true"

    def build_dl_url(self, master_playlist: dict, can_play_fhd: bool) -> str:
        params = dict(master_playlist.get("params") or {})
        base_url = master_playlist.get("url") or ""

        params = {k: v for k, v in params.items() if v}

        if can_play_fhd:
            params["h"] = "1"

        parts = urlsplit(base_url)
        existing = dict(parse_qsl(parts.query))
        existing.update(params)

        new_query = urlencode(existing)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


    def _get_video(self, info):
        """
        Extracts the video information from the given info object.
        Parameters:
        - info (dict): The info object containing the StreamingCommunity video data.
        Returns:
        - dict: A dictionary containing extracted video information.
        """
        video_page_url = self._download_webpage(traverse_obj(
            info, ('props', 'embedUrl')), self._get_title_id(info))

        self.to_screen("Downloaded video page.")
        # Get the iframe url and iframe page
        iframe_url = self._html_search_regex(
            r'<iframe[^>]+src\s*=\s*"([^"]+)', video_page_url, 'iframe url')
        iframe_page = self._download_webpage(iframe_url, self._get_title_id(info))
        self.to_screen("Got video iframe.")

        master_playlist = self.js_object_to_dict(self.extract_js_object(iframe_page, "masterPlaylist"))
        can_play_fhd = self.extract_bool(iframe_page, "canPlayFHD")

        # Generate the playlist url
        dl_url = self.build_dl_url(master_playlist, can_play_fhd)
        self.to_screen("Generated download url.")

        # Add headers for the request to avoid being blocked
        headers = {
            'Referer': iframe_url,
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            dl_url, self._get_title_id(info), headers=headers)

        # Parse m3u8 subtitles
        for lang, subtitle in subtitles.items():
            sub_file = self._download_webpage(traverse_obj(
                subtitle[0], ('url')), self._get_title_id(info))
            self.to_screen("Downloaded subtitles page.")
            url = next(line for line in sub_file.splitlines() if not line.startswith("#"))
            subtitle[0]['url'] = url
            subtitle[0]['ext'] = 'vtt'


        video_return_dic = {
            'id': self._get_title_id(info),
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
                'series_id': self._get_title_id(info),
                'season_number': traverse_obj(info, ('props', 'episode', 'season', 'number')),
                'season_id': traverse_obj(info, ('props', 'episode', 'season', 'id')),
                'episode': traverse_obj(info, ('props', 'episode', 'name')),
                'episode_number': traverse_obj(info, ('props', 'episode', 'number')),
                'episode_id': traverse_obj(info, ('props', 'episode', 'id')),
                'duration': traverse_obj(info, ('props', 'episode', 'duration'))*60
            })

        return video_return_dic

    def _get_movie(self, info):
        """
        Extracts the movie information from the given info object.
        Parameters:
        - info (dict): The info object containing StreamingCommunity movie data.
        Returns:
        - dict: A dictionary containing extracted movie information.
        """
        title = traverse_obj(info, ('props', 'title', 'name'))
        title_id = self._get_title_id(info)

        domain = self._get_domain(info)
        base_path = self._get_base_path(info)

        movie_url = self._build_watch_url(domain, title_id, episode_id=None, base_path=base_path)
        # return self.playlist_from_matches([movie_url], title_id, title)
        return self.url_result(movie_url)

    def _get_season(self, info):
        """
        Extracts the season information from the given info object.
        Adapted from "https://forum.videohelp.com/threads/415994-need-help-with-py-script"
        Parameters:
        - info (dict): The info object containing StreamingCommunity season data.
        Returns:
        - dict: A dictionary containing extracted season information making loop for each episode exploiting `self.url_result`.
        """
        title = traverse_obj(info, ('props', 'title', 'name'))
        title_id = self._get_title_id(info)
        video_type = traverse_obj(info, ('props', 'title', 'type'))

        domain = self._get_domain(info)
        base_path = self._get_base_path(info)

        season = traverse_obj(info, ('props', 'loadedSeason'))
        playlist_title = self._sanitize_filename(title) + ' - S' + str(season['number']).zfill(2)
        if season:
            # s_number = season['number']
            episodes = []
            for episode in season['episodes']:
                # e_number = episode['number']
                # name = episode['name']
                episode_id = episode['id']
                episode_url = self._build_watch_url(domain, title_id, episode_id, base_path)
                # name_base = self.sanitize_filename(f"{title} S{str(s_number).zfill(2)}E{str(e_number).zfill(2)} {name}")
                episodes.append(episode_url)
            return self.playlist_from_matches(episodes, title_id, playlist_title)

    def _get_serie(self, info):
        """
        Extracts the series information from the given info object.
        Parameters:
        - info (dict): The info object containing StreamingCommunity series data.
        Returns:
        - dict: A dictionary containing extracted series information making loop for each season exploiting `self.url_result`.
        """
        def _build_season_url(domain, url, season_n=1):
            SEASON_PREFIX = 'season-'
            return f"https://{domain}{url}/{SEASON_PREFIX}{season_n}"

        title = traverse_obj(info, ('props', 'title', 'name'))
        title_id = self._get_title_id(info)
        video_type = traverse_obj(info, ('props', 'title', 'type'))

        domain = self._get_domain(info)
        url = traverse_obj(info, ('url'))
        seasons = [_build_season_url(domain, url, s['number']) for s in traverse_obj(info, ('props', 'title', 'seasons'))]
        return self.playlist_from_matches(seasons, title_id, title)


    def _real_extract(self, url):
        """
        Extracts information from the given URL of a StreamingCommunity video.

        Parameters:
        - url (str): The URL of the video to extract information from.

        Returns:
        - dict: A dictionary containing extracted video information such as ID, title, release date, timestamp, description, and more.
        """
        media_id = self._match_id(url)
        webpage = self._download_webpage(url, media_id)
        self.to_screen("Downloaded webpage.")
        info = json.loads(self._html_search_regex(r'data-page="([^"]+)', webpage, 'info'))

        if 'watch' in url:
            return self._get_video(info)
        elif 'titles' in url:
            video_type = traverse_obj(info, ('props', 'title', 'type'))
            if video_type == 'movie':
                return self._get_movie(info)
            else:
                if 'titles' in url.rsplit('/', 2)[0]:   # a season
                    return self._get_season(info)
                else:   # an entire series
                    return self._get_serie(info)
