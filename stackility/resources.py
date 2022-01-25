'''
Utility to find resources in CloudFormation stacks.
'''
import sys
import datetime
import json
import logging
import boto3
from tabulate import tabulate

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s (%(module)s) %(message)s',
    datefmt='%Y/%m/%d-%H:%M:%S'
)

CALC_DONE_STATES = [
    'DETECTION_FAILED',
    'DETECTION_COMPLETE'
]

FIRST = 'e0d9da36-7d50-11ec-8092-1295ea1aedfd'

def date_converter(o):
    '''
    Helper thing to convert dates for JSON modulet.

    Args:
        o - the thing to dump as string.

    Returns:
        if an instance of datetime the a string else None
    '''
    if isinstance(o, datetime.datetime):
        return o.__str__()


class ResourceTool(object):
    '''
    Utility to find drift in CloudFormation stacks.
    '''

    def __init__(self, **kwargs):
        """
        The initializer sets up stuff to do the work

        Args:
            dict of args

        Returns:
            kwarg[Profile]: asdasdf

        Raises:
            SystemError if thing are not all good
        """
        self._stack_name = kwargs.get('Stack')
        self._verbose = kwargs.get('Verbose', False)
        if not self._stack_name:
            logging.error('no stack name given, exiting')
            raise SystemError

        if not self._init_boto3_clients(kwargs.get('Profile'), kwargs.get('Region')):
            logging.error('client initialization failed, exiting')
            raise SystemError

    def _init_boto3_clients(self, profile, region):
        """
        The utililty requires boto3 clients to CloudFormation.

        Args:
            None

        Returns:
            Good or Bad; True or False
        """
        try:
            session = None
            if profile and region:
                session = boto3.session.Session(profile_name=profile, region_name=region)
            elif profile:
                session = boto3.session.Session(profile_name=profile)
            elif region:
                session = boto3.session.Session(region_name=region)
            else:
                session = boto3.session.Session()

            self._cloud_formation = session.client('cloudformation')
            return True
        except Exception as wtf:
            logging.error(wtf, exc_info=True)
            return False

    def list_resources(self):
        """
        List the resources in a given CloudFormation stack.

        Args:
            None

        Returns:
            Good or Bad; True or False
        """
        try:
            rows = []
            next_token = FIRST

            while next_token:
                if next_token == FIRST:
                    response = self._cloud_formation.list_stack_resources(
                        StackName=self._stack_name
                    )
                else:
                    response = self._cloud_formation.list_stack_resources(
                        StackName=self._stack_name,
                        NextToken=next_token
                    )
                next_token = response.get('NextToken')
                if response:
                    for thing in response.get('StackResourceSummaries', []):
                        print(json.dumps(thing, indent=2, default=date_converter))
                        row = []
                        row.append(thing.get('LogicalResourceId', 'unknown'))
                        row.append(thing.get('PhysicalResourceId', 'unknown'))
                        row.append(thing.get('ResourceStatus', 'unknown'))
                        row.append(thing.get('ResourceType', 'unknown'))
                        row.append(thing.get('DriftInformation', {}).get('StackResourceDriftStatus', 'unknown'))
                        rows.append(row)

            print(f'Resource Report - {self._stack_name}:')
            print(tabulate(rows, headers=[
                'Logical ID',
                'Physical ID',
                'Resource Status',
                'Resource Type',
                'Drift Info'
            ]))
            return True
        except Exception as wtf:
            logging.error(wtf, exc_info=True)

        return False


if __name__ == '__main__':
    tool = ResourceTool(Stack=sys.argv[1])
    tool.list_resources()
