## Stackility
Description: a utility to help create CloudFormation stacks.

#### Properties
Note: if there are *secret* property values you can specify the value as ```[ask]```
Example:

```db_password=[ask]```


#### Development notes:

* virtualenv stkvenv
* . stkenv/bin/activate
* pip install --editable .

#### Environment notes:
By default the utility polls the status of stack operation every 30 seconds. If
needed ```CSU_POLL_INTERVAL``` can be set to a number of seconds to override the 
poll interval
