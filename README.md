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
See the *Properties* section below for a description about INI file format.

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

#### Properties:
The INI file fed to the ```upsert``` command has the followning sections:

**[environment]:**
The environment for the creation/update of a CloudFormation stack. These are the following 
elements of this section:

* bucket - an S3 bucket where the template can be uploaded *[required]*
* template - the name of the CloudFormation to be used in the operation *[required]*
* stack_name - the name of the stack. If this element is not present then the
```--stack``` argument must be given *[optional]*
* region - specify the target region for this stack *[optional]*
* profile - the credentials profile to be used *[optional]*

**[tags]:** - key/value pairs that will be created as tags on the stack and
supported resources.

**[parameters]:** - key/value pairs that will be injected as parameter(s) for the
stack. You can, of course, enter the values as text. However, there are two
special ways to specify the value in this section:

* [ask] - this will ask for (and not echo) the values when a stack upsert is
done (example below). 
* [ssm:<SSM-PARAMETER>] - specify a parameter key that will be used to retrieve
the value from [AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-paramstore.html)

**[meta-parameters]:** - (optional) if this section exists in the INI file it is assumed
that the template file given in the ```[environment]``` section is a [Jinja2](http://jinja.pocoo.org/docs/)
template file. The given template is rendered with the key/value pairs injected before the upload to the S3
bucket.

#### Example parameters file:
```
[environment]
template=template.json
bucket=account-cf-artifacts-bucket
stack_name=example-stack
region=us-west-2

[tags]
OWNER=nobody@gmail.com
PROJECT=Stackility Examples
THE_DATA=important
Name=example-stack

[parameters]
theCIDR=10.22.0.0/16
subnetCIDROne=10.22.10.0/24
bar=some value
db_password=[ask]
api_key=[ssm:api_key]

[meta-parameters]
food=pizza
drink=beer
```

#### Example invocations:
```stackility upsert --ini vpc_stack.ini --region us-east-2```

* use the template in vpc_stack.ini to create a VPC in the us-east-2 region.

```stackility delete --stack example-stack --region us-east-2```

* tear down the example-stack stack from us-east-2

```stackility list --region us-east-2```

* list the CloudFormation stacks in us-east-2

#### Environment notes:
By default the utility polls the status of stack operation every 30 seconds. If
needed ```CSU_POLL_INTERVAL``` can be set to a number of seconds to override the 
poll interval

---

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

#### TODO:

* print CloudFormation Outputs at the end of the upsert command
* the example directory sucks; fix it
* investigate giving an IAM role, something like the profile  selection
