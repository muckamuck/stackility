#!/bin/bash
set -e

cd $(dirname ${0})

pdb_count=$(find . -name "*.py" | xargs egrep '(import\s*pdb|set_trace)' | wc -l)

if [ ${pdb_count} -gt 0 ]; then
    echo "Some PDB cruft was found"
    exit $pdb_count
fi

rm -rf *.egg-info/ build/ dist/
find . -name .ropeproject -type d | xargs rm -rf
find . -name "*.pyc" -type f | xargs rm -f

python setup.py sdist
python setup.py bdist_wheel --universal

echo
echo "================================================================================"
echo "Upload with:"
echo "twine upload dist/*"
