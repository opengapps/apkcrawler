# APK Crawler
APK Crawler is a tool to automatically retrieve APKs from various internet sources

## Usage
### Default
Fetches all APKs for all applications supported by Open GApps from APK Mirror
```sh
python apkcrawler.py
```
or missing APKs from Aptoide and APK-DL
```sh
./report_sources.sh nohelp nosig | python aptoidecrawler.py
./report_sources.sh nohelp nosig | python apk-dlcrawler.py
```
### Specific
Fetches app APKs for specified applications supported by Open GApps using their [`.gapps-config` codename](https://github.com/opengapps/opengapps/wiki/Advanced-Features-and-Options#include-and-exclude-google-applications)
```sh
python apkcrawler.py drive docs slides sheets
```
### Inline
APK Crawler emits the downloaded filename so it can be used inline
```sh
./add_sourceapp.sh $(python apkcrawler.py drive docs slides sheets)
```
or
```sh
./add_sourceapp.sh $(python aptoidecrawler.py report.txt)
./add_sourceapp.sh $(python apk-dlcrawler.py report.txt)
```


## Supported Sites
- [APK Mirror](http://apkmirror.com)
- [Aptoide](http://aptoide.com)
- [APK Downloader](http://apk-dl.com)
- ~~Google Play~~ (Not yet added)

## Requirements
- [python](https://www.python.org/downloads/)
- [requests](https://pypi.python.org/pypi/requests)
- [beautifulsoup4](https://pypi.python.org/pypi/beautifulsoup4/)
- [html5lib](https://pypi.python.org/pypi/html5lib)
- [requesocks](https://pypi.python.org/pypi/requesocks) (ONLY for SOCKS5 support)

## Installation
```sh
pip install requests beautifulsoup4 html5lib requesocks
```

## Known Issues
- There needs to be a way to grab an older version of an application as the current version (e.g. Current WebView on APK Mirror is the beta version)
