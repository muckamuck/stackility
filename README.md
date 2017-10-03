## Stackility
Description: a utility to help create CloudFormation stacks.

#### Properties
Note: if there are *secret* property values you can specify the value as ```[ask]```
Example:

```db_password=[ask]```

This will ask for (and not echo) the values when a stack upsert is done.

#### Development notes:

Do some work on the thing:
```bash
virtualenv stkvenv
. stkenv/bin/activate
pip install --editable .
```

Publish the thing:
```bash
python setup.py sdist bdist_wheel
twine upload dist/*
```

#### Environment notes:
By default the utility polls the status of stack operation every 30 seconds. If
needed ```CSU_POLL_INTERVAL``` can be set to a number of seconds to override the 
poll interval
