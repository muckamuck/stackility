from __future__ import print_function
import boto3
import sys


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
    except Exception:
        pass

    return ''


def main():
    value = get_ssm_parameter(sys.argv[1])
    print(value, end='')

if __name__ == '__main__':
    main()
