#!/bin/bash
set -e
virtualenv -p /usr/bin/python2.7 .py27env
source .py27env/bin/activate
pip install -U pytidylib6 chardet six
