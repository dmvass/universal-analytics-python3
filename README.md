# Universal Analytics for Python

[![Build Status](https://travis-ci.com/dmvass/universal-analytics-python3.svg?branch=master)](https://travis-ci.com/dmvass/universal-analytics-python3)
[![image](https://img.shields.io/pypi/v/universal-analytics-python3.svg)](https://pypi.python.org/pypi/universal-analytics-python3)
[![codecov](https://codecov.io/gh/dmvass/universal-analytics-python3/branch/master/graph/badge.svg)](https://codecov.io/gh/dmvass/universal-analytics-python3)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/dmvass/universal-analytics-python3/blob/master/LICENSE)

It's a fork of [universal-analytics-python](https://github.com/adswerve/universal-analytics-python)
whith support for Python 3, batch requests, synchronous and asynchronous API calls.

This library provides a Python interface to Google Analytics, supporting the
Universal Analytics Measurement Protocol, with an interface modeled (loosely)
after Google's `analytics.js`.

**NOTE** this project is reasonably feature-complete for most use-cases, covering
all relevant features of the Measurement Protocol, however we still consider it
_beta_. Please feel free to file issues for feature requests.

## Installation

The easiest way to install universal-analytics is directly from PyPi using `pip`
by running the following command:

```bash
pip install universal-analytics-python3
```

## Usage

For the most accurate data in your reports, Analytics Pros recommends establishing
a distinct ID for each of your users, and integrating that ID on your front-end web
tracking, as well as back-end tracking calls. This provides for a consistent, correct
representation of user engagement, without skewing overall visit metrics (and others).

A simple example for synchronous usage:

```python
from universal_analytics import Tracker, HTTPRequest, HTTPBatchRequest

with HTTPRequest() as http:
    tracker = Tracker("UA-XXXXX-Y", http, client_id="unique-id")
    tracker.send("event", "Subscription", "billing")

with HTTPBatchRequest() as http:
    tracker = Tracker("UA-XXXXX-Y", http, client_id="unique-id")
    tracker.send("event", "Subscription", "billing")
```

A simple example for asynchronous usage:

```python
import asyncio
from universal_analytics import Tracker, AsyncHTTPRequest, AsyncHTTPBatchRequest

async def main():
    async with AsyncHTTPRequest() as http:
        tracker = Tracker("UA-XXXXX-Y", http, client_id="unique-id")
        await tracker.send("event", "Subscription", "billing")

    async with AsyncHTTPBatchRequest() as http:
        tracker = Tracker("UA-XXXXX-Y", http, client_id="unique-id")
        await tracker.send("event", "Subscription", "billing")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
```

This library support the following tracking types, with corresponding (optional) arguments:

* pageview: [ page path ]
* event: category, action, [ label [, value ] ]
* social: network, action [, target ]
* timing: category, variable, time [, label ]

Additional tracking types supported with property dictionaries:

* transaction
* item
* screenview
* exception

Property dictionaries permit the same naming conventions given in the [analytics.js Field Reference](https://developers.google.com/analytics/devguides/collection/analyticsjs/field-reference),
with the addition of common spelling variations, abbreviations, and hyphenated names
(rather than camel-case).

Further, the property dictionaries support names as per the [Measurement Protocol Parameter Reference](https://developers.google.com/analytics/devguides/collection/protocol/v1/parameters),
and properties/parameters can be passed as named arguments.

Example:

```python
# As python named-arguments
tracker.send("pageview", path="/test", title="Test page")

# As property dictionary
tracker.send("pageview", {"path": "/test", "title": "Test page"})
```

Server-side experiments:

```python
# Set the experiment ID and variation ID
tracker.set("exp", "$experimentId.$variationId")

# Send a pageview hit to Google Analytics
tracker.send("pageview", path="/test", title="Test page")
```

## License

This code is distributed under the terms of the MIT license.

## Changes

A full changelog is maintained in the [CHANGELOG](https://github.com/dmvass/universal-analytics-python3/blob/master/CHANGELOG.md) file.

## Contributing

**universal-analytics-python3** is an open source project and contributions are
welcome! Check out the [Issues](https://github.com/dmvass/universal-analytics-python3/issues)
page to see if your idea for a contribution has already been mentioned, and feel
free to raise an issue or submit a pull request.
