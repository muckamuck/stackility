'''
A utility class to extract and print info about a
CloudFormation stack.
'''
# pylint: disable=broad-except
# pylint: disable=invalid-name

import os
import sys
import logging
import datetime

import boto3
from tabulate import tabulate

logger = logging.getLogger(__name__)
zero_time = datetime.datetime.utcfromtimestamp(0)


class StackTool:
    '''
    A utility class to extract and print info about a
    CloudFormation stack.
    '''
    def __init__(self, stack_name, region, cf_client):
        """
        StackTool is a simple tool to print some specific data about a
        CloudFormation stack.

        Args:
            stack_name - name of the stack of interest
            region - AWS region where the stack was created

        Returns:
           not a damn thing

        Raises:
            SystemError - if everything isn't just right
        """
        try:
            self._stack_name = stack_name
            self._region = region
            self._cf_client = cf_client
        except Exception as wtf:
            logger.error(wtf, exc_info=True)
            raise SystemError

    def print_stack_info(self):
        '''
        List resources from the given stack

        Args:
            None

        Returns:
            A dictionary filled resources or None if things went sideways
        '''
        try:
            rest_api_id = None
            deployment_found = False

            response = self._cf_client.describe_stack_resources(
                StackName=self._stack_name
            )

            print('\nThe following resources were created:')
            rows = []
            for resource in response['StackResources']:
                if resource['ResourceType'] == 'AWS::ApiGateway::RestApi':
                    rest_api_id = resource['PhysicalResourceId']
                elif resource['ResourceType'] == 'AWS::ApiGateway::Deployment':
                    deployment_found = True

                row = []
                row.append(resource['ResourceType'])
                row.append(resource['LogicalResourceId'])
                row.append(resource['PhysicalResourceId'])
                rows.append(row)
            print(tabulate(rows, headers=['Resource Type', 'Logical ID', 'Physical ID']))

            if rest_api_id and deployment_found:
                url = f'https://{rest_api_id}.execute-api.{self._region}.amazonaws.com/<stage>'
                print('\nThe deployed service can be found at this URL:')
                print(f'\t{url}\n')

            return response
        except Exception as wtf:
            print(wtf)
            return None

    def print_stack_events(self):
        '''
        List events from the given stack

        Args:
            None

        Returns:
            None
        '''
        first_token = '7be7981bd6287dd8112305e8f3822a6f'
        keep_going = True
        next_token = first_token
        current_request_token = None
        rows = []
        try:
            while keep_going and next_token:
                if next_token == first_token:
                    response = self._cf_client.describe_stack_events(
                        StackName=self._stack_name
                    )
                else:
                    response = self._cf_client.describe_stack_events(
                        StackName=self._stack_name,
                        NextToken=next_token
                    )

                next_token = response.get('NextToken', None)
                for event in response['StackEvents']:
                    row = []
                    event_time = event.get('Timestamp')
                    request_token = event.get('ClientRequestToken', 'unknown')
                    if current_request_token is None:
                        current_request_token = request_token
                    elif current_request_token != request_token:
                        keep_going = False
                        break

                    row.append(event_time.strftime('%x %X'))
                    row.append(event.get('LogicalResourceId'))
                    row.append(event.get('ResourceStatus'))
                    row.append(event.get('ResourceStatusReason', ''))
                    rows.append(row)

            if len(rows) > 0:
                print('\nEvents for the current upsert:')
                print(tabulate(rows, headers=['Time', 'Logical ID', 'Status', 'Message']))
                return True

            print('\nNo stack events found\n')
        except Exception as wtf:
            print(wtf)

        return False


if __name__ == '__main__':
    the_cf_client = None
    try:
        the_region = os.environ.get('region', 'us-east-1')
        b3Sess = boto3.session.Session()
        the_cf_client = b3Sess.client('cloudformation', region_name=the_region)
    except Exception as ruh_rog_shaggy:
        logger.error('Exception caught in intialize_session():')
        logger.error(ruh_rog_shaggy, exc_info=True)
        sys.exit(1)

    int(datetime.datetime.now().strftime('%s'))
    int(datetime.datetime.utcnow().strftime('%s'))
    stack_tool = StackTool(sys.argv[1], 'us-east-1', the_cf_client)
    '''
    stack_tool.print_stack_info()
    '''
    stack_tool.print_stack_events()
