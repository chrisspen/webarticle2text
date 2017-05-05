# Webarticle2Text - Extracts the main article text from a webpage.

[![](https://img.shields.io/pypi/v/webarticle2text.svg)](https://pypi.python.org/pypi/webarticle2text) [![Build Status](https://img.shields.io/travis/chrisspen/webarticle2text.svg?branch=master)](https://travis-ci.org/chrisspen/webarticle2text) [![](https://pyup.io/repos/github/chrisspen/webarticle2text/shield.svg)](https://pyup.io/repos/github/chrisspen/webarticle2text)

## Overview
-----------

This project is obsolete and now only serves as a reference. I recommend you instead use [newspaper](https://github.com/codelucas/newspaper), which is an order-of-magnitude more accurate than any other article extraction library I've encountered.

Please see `compare.csv` for a performance comparison of several similar tools.

This attempts to locate and extract the largest cluster of text in a
webpage. It does this by walking the DOM-tree, identifying all text
segments and their depth inside the DOM, appends all text at roughly
the same depth, and then returns the chunk with the largest total
length.

This approach usually works well with typical news sites where one
news article is displayed per URL. This approach usually fails with
URLs displaying multiple news blurbs (e.g. news aggregators).

## Installation
---------------

You may need to install the tidylib system package, which you can get on Ubuntu 12.04 using:

    sudo apt-get install libtidy-0.99-0

or on Fedora using:

    sudo yum install libtidy

Then, simply install the package using pip:

    pip install webarticle2text

## Usage
--------

You can invoke the script either as a Python module:

    from webarticle2text import webarticle2text
    print webarticle2text.extractFromURL("http://some/arbitrary/url")

or as a standalone command line script:

    webarticle2text.py http://some/arbitrary/url
    
Note, to use it from the command line, you'll need to ensure it has execute
permission and is located in your PATH. On most platforms, this should
automatically be done by setup.py.

## Development

Tests require the Python development headers to be installed, which you can install on Ubuntu with:

    sudo apt-get install python-dev python3-dev python3.4-dev

To run unittests across multiple Python versions, install:

    sudo apt-get install python3.4-minimal python3.4-dev python3.5-minimal python3.5-dev

To run all [tests](http://tox.readthedocs.org/en/latest/):

    export TESTNAME=; tox

To run tests for a specific environment (e.g. Python 2.7):
    
    export TESTNAME=; tox -e py27

To run a specific test:
    
    export TESTNAME=.test_extract; tox -e py27

## History
----------

* 1.0.0 (2008.9.16) Initial public release.
* 1.2.0 (2011.1.3) Update to support Unicode.
* 1.2.2 (2011.12.17) Cleaned up installation procedure and documentation and moved to github.com. 
* 1.2.3 (2011.12.21) Fixed encoding error when redirecting stdout. e.g. webarticle2text.py http://some/arbitrary/url > output.txt
* 1.2.5 (2012.11.5) Added the option to specify user-agent header to use when requesting URLs.
* 2.0.0 (2014.4.20) Added support for Python 3.2.
