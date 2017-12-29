#!/bin/bash
set -e

cd $(dirname ${0})
rm -rf *.egg-info/ build/ dist/
find . -name .ropeproject -type d | xargs rm -rf
find . -name "*.pyc" -type f | xargs rm -f

python setup.py sdist bdist_wheel
