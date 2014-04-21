#!/bin/bash
set -e
virtualenv -p /usr/bin/python3 .py3env
source .py3env/bin/activate
pip install -U pytidylib6 chardet six
