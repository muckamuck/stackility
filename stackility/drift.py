'''
Utility to find drift in CloudFormation stacks.
'''
import os
import time
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


class DriftTool(object):
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
        try:
            self.nap_time = int(os.environ.get('CSU_POLL_INTERVAL', 30))
        except Exception:
            self.nap_time = 15
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

    def determine_drift(self):
        """
        Determine the drift of the stack.

        Args:
            None

        Returns:
            Good or Bad; True or False
        """
        try:
            response = self._cloud_formation.detect_stack_drift(StackName=self._stack_name)
            drift_request_id = response.get('StackDriftDetectionId', None)
            if drift_request_id:
                logging.info('drift_request_id: %s - polling', drift_request_id)
                drift_calc_done = False
                while not drift_calc_done:
                    time.sleep(self.nap_time)
                    response = self._cloud_formation.describe_stack_drift_detection_status(
                        StackDriftDetectionId=drift_request_id
                    )
                    current_state = response.get('DetectionStatus', None)
                    logging.info(
                        'describe_stack_drift_detection_status(): {}'.format(current_state)
                    )
                    drift_calc_done = current_state in CALC_DONE_STATES
                    drift_answer = response.get('StackDriftStatus', 'UNKNOWN')

                logging.info('drift of {}: {}'.format(
                    self._stack_name,
                    drift_answer
                ))

                if drift_answer == 'DRIFTED':
                    if self._verbose:
                        self._print_drift_report()
                    return False
                else:
                    return True
            else:
                logging.warning('drift_request_id is None')

            return False
        except Exception as wtf:
            logging.error(wtf, exc_info=True)
            return False

    def _print_drift_report(self):
        """
        Report the drift of the stack.

        Args:
            None

        Returns:
            Good or Bad; True or False

        Note: not yet implemented
        """
        try:
            response = self._cloud_formation.describe_stack_resources(StackName=self._stack_name)
            rows = []
            for resource in response.get('StackResources', []):
                row = []
                row.append(resource.get('LogicalResourceId', 'unknown'))
                row.append(resource.get('PhysicalResourceId', 'unknown'))
                row.append(resource.get('ResourceStatus', 'unknown'))
                row.append(resource.get('DriftInformation', {}).get('StackResourceDriftStatus', 'unknown'))
                rows.append(row)

            print('Drift Report:')
            print(tabulate(rows, headers=[
                'Logical ID',
                'Physical ID',
                'Resource Status',
                'Drift Info'
            ]))
        except Exception as wtf:
            logging.error(wtf, exc_info=True)
            return False

        return True
