import ConfigParser
import logging
import traceback
import sys
import json


def read_config_info(ini_file):
    try:
        config = ConfigParser.ConfigParser()
        config.read(ini_file)
        the_stuff = {}
        for section in config.sections():
            the_stuff[section] = {}
            for option in config.options(section):
                the_stuff[section][option] = config.get(section, option)

        the_stuff = reformat_stuff(the_stuff)
        return the_stuff
    except Exception as wtf:
        logging.error('Exception caught in read_config_info(): {}'.format(wtf))
        traceback.print_exc(file=sys.stdout)
        return None


def reformat_stuff(old_stuff):
    new_stuff = {}
    for key in old_stuff.keys():
        wrk = key.split(':')
        section_key = wrk[0]

        if section_key not in new_stuff:
            new_stuff[section_key] = {}

        if len(wrk) == 1:
            new_stuff[section_key]['properties'] = old_stuff[key]
        elif len(wrk) == 2:
            new_stuff[section_key]['tags'] = old_stuff[key]

    return new_stuff


if __name__ == '__main__':
    stuff = read_config_info('test_config.ini')
    print(json.dumps(stuff, indent=2))
