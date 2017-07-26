import os

import yaml


def stable_write(folder_name, file_name, content, mode='w'):
    try:
        f = open(os.path.join(folder_name, file_name), mode, 0)
        f.write(content)
        f.close()
    except IOError as (errno, strerror):
        print "I/O error({0}): {1}".format(errno, strerror)


def cache_check(folder_name, file_name):
    if os.path.exists(os.path.join(folder_name, file_name)):
        with open(os.path.join(folder_name, file_name)) as f:
            return yaml.load(f)
    else:
        return None


def cache_dump(folder_name, file_name, obj):
    stable_write(folder_name, file_name, yaml.dump(obj, default_style='|'), 'w')
