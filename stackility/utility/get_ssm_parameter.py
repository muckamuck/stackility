'''
For getting ssm parameters
'''
from __future__ import print_function
import sys
import boto3
from botocore.exceptions import ClientError, ParamValidationError


def get_ssm_parameter(parameter_name):
    '''
    Get the decrypted value of an SSM parameter

    Args:
        parameter_name - the name of the stored parameter of interest

    Return:
        Value if allowed and present else None
    '''
    try:
        response = boto3.client('ssm').get_parameters(
            Names=[parameter_name],
            WithDecryption=True
        )

        return response.get('Parameters', None)[0].get('Value', '')
    except ParamValidationError as err:
        print("Parameter validation error: "+str(err))
    except ClientError as err:
        print("Unexpected error: "+str(err))

    return ''


def main():
    '''
    Main
    '''
    value = get_ssm_parameter(sys.argv[1])
    print(value, end='')

if __name__ == '__main__':
    main()
