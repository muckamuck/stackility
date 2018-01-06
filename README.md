## Stackility
Description: a utility to help create CloudFormation stacks.

#### Usage:
```
stackility upsert [OPTIONS]

Options:
  -v, --version TEXT  code version
  -s, --stack TEXT    stack name
  -i, --ini TEXT      INI file with needed information  [required]
  -d, --dryrun        dry run
  -y, --yaml          YAML template
  --help              Show this message and exit.
```
* See below Properties section below for description about INI file format *

```
stackility delete [OPTIONS]

Options:
  -s, --stack TEXT    [required]
  -r, --region TEXT
  -f, --profile TEXT
  --help              Show this message and exit.
```

```
stackility list [OPTIONS]

Options:
  -r, --region TEXT
  -f, --profile TEXT
  --help              Show this message and exit.
```

#### Properties
The INI file fed to the ```upsert``` command has the followning sections:

**[environment]:**
The environment for the creation/update of a CloudFormation stack. These the following 
elements of this section:

* bucket - an S3 bucket where the template can be uploaded [required]
* template - the name of the CloudFormation to be used in the operation [required]
* stack_name - the name of the stack. If this element is not present the the ```--stack``` argument must be given [optional]
* region - specify the target region for this stack. [optional]
* profile - the credentials profile to be used [optional]

**[tags]** - key/value pairs that will be created as tags on the stack and supported resources.
**[parameters]** - key/value pairs that will be injected as parameter for the stack


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

#### TODO:

* print CloudFormation Outputs at the end of the upsert command
* the example directory sucks; fix it
* write something about the INI file usage for upsert
