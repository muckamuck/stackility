import os
import sys
import boto3
import logging
import traceback
import datetime
from tabulate import tabulate

zero_time = datetime.datetime.utcfromtimestamp(0)


class StackTool:
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
                '''
                print('\t{}\t{}\t{}'.format(
                        resource['ResourceType'],
                        resource['LogicalResourceId'],
                        resource['PhysicalResourceId']
                    )
                )
                '''
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
            else:
                print('\nNo stack events found\n')
        except Exception as wtf:
            print(wtf)

        return False

if __name__ == '__main__':
    cf_client = None
    try:
        region = os.environ.get('region', 'us-east-1')
        b3Sess = boto3.session.Session()
        cf_client = b3Sess.client('cloudformation', region_name=region)
    except Exception as wtf:
        logging.error('Exception caught in intialize_session(): {}'.format(wtf))
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

    int(datetime.datetime.now().strftime('%s'))
    int(datetime.datetime.utcnow().strftime('%s'))
    stack_tool = StackTool(sys.argv[1], 'us-east-1', cf_client)
    '''
    stack_tool.print_stack_info()
    '''
    stack_tool.print_stack_events()
