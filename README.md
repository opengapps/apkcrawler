# APK Crawler
APK Crawler is a tool to automatically retrieve APKs from various internet sources

## Usage
Fetch all Open GApps [supported](https://github.com/opengapps/opengapps/wiki/Advanced-Features-and-Options#include-and-exclude-google-applications) APKs from a given source
```sh
./report_sources.sh nosig | ./apkdlcrawler.py
./report_sources.sh nosig | ./apkmirrorcrawler.py
./report_sources.sh nosig | ./aptoidecrawler.py
./report_sources.sh nosig | ./mobogeniecrawler.py
./report_sources.sh nosig | ./plazzacrawler.py
./report_sources.sh nosig | ./uptodowncrawler.py
```

### Inline
APK Crawlers emits the downloaded filename so it can be used inline
```sh
./add_sourceapp.sh $(./apkdlcrawler.py      report.txt)
./add_sourceapp.sh $(./apkmirrorcrawler.py  report.txt)
./add_sourceapp.sh $(./aptoidecrawler.py    report.txt)
./add_sourceapp.sh $(./mobogeniecrawler.py  report.txt)
./add_sourceapp.sh $(./plazzacrawler.py     report.txt)
./add_sourceapp.sh $(./uptodowncrawler.py   report.txt)
```

## Supported Sites
- [APK Mirror](http://apkmirror.com)
- [Aptoide](http://aptoide.com)
- [APK Downloader](http://apk-dl.com)
- [Mobogenie](http://mobogenie.com/)
- [Plazza.ir](http://plazza.ir)
- [UpToDown](http://en.uptodown.com/android)
- ~~Google Play~~ (Not yet added)

## Requirements
- [python3](https://www.python.org/downloads/)
- [requests](https://pypi.python.org/pypi/requests)
- [beautifulsoup4](https://pypi.python.org/pypi/beautifulsoup4/)
- [html5lib](https://pypi.python.org/pypi/html5lib)
- [requesocks](https://pypi.python.org/pypi/requesocks) (ONLY for SOCKS5 support)

## Installation
```sh
pip3 install requests beautifulsoup4 html5lib requesocks
```

## Known Issues
- There needs to be a way to grab an older version of an application as the current version (e.g. Current WebView on APK Mirror is the beta version)
