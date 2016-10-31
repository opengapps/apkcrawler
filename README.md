# APK Crawler
APK Crawler is a tool to automatically retrieve APKs from various internet sources

## License
**Take note that APKCrawler's GNU Affero General Public License v3.0 is strict concerning application service providers**.
If you use apkcrawler for a (web)service you need to open source your changes!

## Usage
Fetch all Open GApps [supported](https://github.com/opengapps/opengapps/wiki/Advanced-Features-and-Options#include-and-exclude-google-applications) APKs from a given source
```sh
./report_sources.sh nosig | ./apkcrawler.py
```
or
```sh
./report_sources.sh nosig | ./apkbeastcrawler.py
./report_sources.sh nosig | ./apkdlcrawler.py
./report_sources.sh nosig | ./apkmirrorcrawler.py
./report_sources.sh nosig | ./apkpurecrawler.py
./report_sources.sh nosig | ./aptoidecrawler.py
./report_sources.sh nosig | ./mobogeniecrawler.py
./report_sources.sh nosig | ./playstorecrawler.py
./report_sources.sh nosig | ./plazzacrawler.py
./report_sources.sh nosig | ./uptodowncrawler.py
```

### Inline
APK Crawlers emits the downloaded filename(s) so it can be used inline with Open GApps' `add_sourceapp.sh`
```sh
./add_sourceapp.sh $(./apkcrawler.py        report.txt)
```
or
```sh
./add_sourceapp.sh $(./apkbeastcrawler.py   report.txt)
./add_sourceapp.sh $(./apkdlcrawler.py      report.txt)
./add_sourceapp.sh $(./apkmirrorcrawler.py  report.txt)
./add_sourceapp.sh $(./apkpurecrawler.py    report.txt)
./add_sourceapp.sh $(./aptoidecrawler.py    report.txt)
./add_sourceapp.sh $(./mobogeniecrawler.py  report.txt)
./add_sourceapp.sh $(./playstorecrawler.py  report.txt)
./add_sourceapp.sh $(./plazzacrawler.py     report.txt)
./add_sourceapp.sh $(./uptodowncrawler.py   report.txt)
```

## Supported Sites
- [APK Beast](http://apkbeast.com)
- [APK Mirror](http://apkmirror.com)
- [APK Pure](http://apkpure.com)
- [Aptoide](http://aptoide.com)
- [APK Downloader](http://apk-dl.com)
- [Google Play Store](https://play.google.com/store/)
- [Mobogenie](http://mobogenie.com/)
- [Plazza.ir](http://plazza.ir)
- [UpToDown](http://en.uptodown.com/android)

## Requirements
- [python3](https://www.python.org/downloads/)
- [beautifulsoup4](https://pypi.python.org/pypi/beautifulsoup4/)
- [html5lib](https://pypi.python.org/pypi/html5lib)
- [protobuf >=3](https://pypi.python.org/pypi/protobuf)
- [requests](https://pypi.python.org/pypi/requests)

## Installation
You can use [mfonville's protobuf PPA](https://launchpad.net/~maarten-fonville/+archive/ubuntu/protobuf) for `python3-protobuf`
```sh
sudo apt install python3-bs4 python3-html5lib python3-protobuf python3-requests python3-tz
```
or
```sh
pip3 install beautifulsoup4 html5lib protobuf requests pytz
```

## Known Issues
- There needs to be a way to grab an older version of an application as the current version (e.g. Current WebView on APK Mirror is the beta version)
