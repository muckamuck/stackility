"""
stack_tool
"""

import os
import sys
import traceback
import logging
import boto3
from tabulate import tabulate


class StackTool:
    """
    StackTool
    """
    _cf_client = None
    _stack_name = None
    _region = None

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
        except Exception:
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
                url = 'https://{}.execute-api.{}.amazonaws.com/{}'.format(
                    rest_api_id,
                    self._region,
                    '<stage>'
                )
                print('\nThe deployed service can be found at this URL:')
                print('\t{}\n'.format(url))

            return response
        except Exception as wtf:
            print(wtf)
            return None


if __name__ == '__main__':
    CF_CLIENT = None
    try:
        REGION = os.environ.get('region', 'us-east-2')
        B3SESS = boto3.session.Session()
        CF_CLIENT = B3SESS.client('cloudformation', region_name=REGION)
    except Exception as wtf:
        logging.error('Exception caught in intialize_session(): %s', wtf)
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

    STACK_TOOL = StackTool(sys.argv[1], None, 'us-east-2', CF_CLIENT)
    STACK_TOOL.print_stack_info()
