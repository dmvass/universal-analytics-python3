# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]
- Updated the supported version of httpx
- Changed the close behaviour of AsyncHTTPRequest to use `aclose()` rather than `close()` as per 
(https://www.python-httpx.org/async/#opening-and-closing-clients) 

## [1.1.0] - 2020-03-30
- Added [Server-side Experiments](https://developers.google.com/optimize/devguides/experiments) alias [issues-4]
- Added support of python 3.8, 3.9
- Removed support of python 3.6

## [1.0.1] - 2019-11-25
- Fixed documentation.

## [0.1.0] - 2019-11-22
- First release.
