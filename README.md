# APK Crawler
APK Crawler is a tool to automatically retrieve APKs from various internet sources

## Usage
### Default
Fetches all APKs for all applications supported by OpenGApps
```
python apkcrawler.py
```
### Specific
Fetches app APKs for specified applications supported by OpenGApps
```
python apkcrawler.py drive docs slides sheets
```
### Inline
APK Crawler emits the downloaded filename so it can be used inline
```
./add_sourceapp.sh $(python apkcrawler.py drive docs slides sheets)
```

## Requirements
- [python](https://www.python.org/downloads/)
- [requests](https://pypi.python.org/pypi/requests)
- [beautifulsoup4](https://pypi.python.org/pypi/beautifulsoup4/)
- [html5lib](https://pypi.python.org/pypi/html5lib)

## Installation
```
pip install requests
pip install beautifulsoup4
pip install html5lib
```

## Known Issues

- Current support is limited to APKMirror, but future support will include Google Play
- There needs to be a way to grab an older version of an application as the current version (e.g. Current WebView on APKMirror is the beta version)
