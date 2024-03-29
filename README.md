A [yt-dlp](https://github.com/yt-dlp/yt-dlp) extractor [plugin](https://github.com/yt-dlp/yt-dlp#plugins) for the italian StreamingCommunity website.

---

## Installation

Requires yt-dlp `2023.01.02` or above.

1) Install `pycryptodomex` with:
    ```
    pip3 install pycryptodomex
    ```

2) You can install this package with pip:
    ```
    python3 -m pip install -U https://github.com/Blu-Tiger/StreamingCommunity-yt-dlp-plugin/archive/master.zip
    ```
    or 
    ```
    git clone https://github.com/Blu-Tiger/StreamingCommunity-yt-dlp-plugin.git
    ```
    in one of these directories:
    
    - User Plugins
        - `${XDG_CONFIG_HOME}/yt-dlp/plugins/` (recommended on Linux/macOS)
        - `${XDG_CONFIG_HOME}/yt-dlp-plugins/`
        - `${APPDATA}/yt-dlp/plugins/` (recommended on Windows)
        - `${APPDATA}/yt-dlp-plugins/` 
        - `~/.yt-dlp/plugins/`
        - `~/yt-dlp-plugins/`
    - System Plugins
        - `/etc/yt-dlp/plugins/`
        - `/etc/yt-dlp-plugins/`

Run yt-dlp with --verbose to check if the plugin has been loaded.

See [yt-dlp installing plugins](https://github.com/yt-dlp/yt-dlp#installing-plugins) for the many other ways this plugin package can be installed.
