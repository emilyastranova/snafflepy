import os
# import magic
import string
import random
import logging
import ipaddress
from pathlib import Path
from ldap3 import ALL_ATTRIBUTES, Server, Connection, DSA, ALL, SUBTREE


# RT: Stolen from manspider - https://github.com/blacklanternsecurity/MANSPIDER

log = logging.getLogger('snafflepy.util')


def str_to_list(s):

    l = set()
    # try to open as file
    try:
        with open(s) as f:
            lines = set([l.strip() for l in f.readlines()])
            for line in lines:
                if line:
                    l.add(line)
    except OSError:
        l.add(s)

    return list(l)


def make_targets(s):
    '''
    Accepts filename, CIDR, IP, hostname, file, or folder
    Returns list of targets as IPs, hostnames, or Path() objects
    '''

    targets = set()

    if s.startswith('\\'):
        p = s.strip("'\"").replace('/', '\\').lstrip('\\')
        parts = [x for x in p.split('\\') if x]
        if len(parts) >= 2:
            server = parts[0]
            share = parts[1]
            folder = '\\'.join(parts[2:])
            targets.add(('unc', server, share, folder))
        return list(targets)

    p = Path(s)
    if p.is_dir():
        targets.add(p)


    else:
        for i in str_to_list(s):
            try:
                for ip in ipaddress.ip_network(i, strict=False):
                    targets.add(str(ip))
            except ValueError:
                targets.add(i)

    return list(targets)


def human_to_int(h):
    '''
    converts human-readable number to integer
    e.g. 1K --> 1000
    '''

    if type(h) == int:
        return h

    units = {'': 1, 'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}

    try:
        h = h.upper().strip()
        i = float(''.join(c for c in h if c in string.digits + '.'))
        unit = ''.join([c for c in h if c in units.keys()])
    except (ValueError, KeyError):
        raise ValueError(f'Invalid filesize "{h}"')

    return int(i * units[unit])


def bytes_to_human(_bytes):
    '''
    converts bytes to human-readable filesize
    e.g. 1024 --> 1KB
    '''

    sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB']
    units = {}
    count = 0
    for size in sizes:
        units[size] = pow(1024, count)
        count += 1

    for size in sizes:
        if abs(_bytes) < 1024.0:
            if size == sizes[0]:
                _bytes = str(int(_bytes))
            else:
                _bytes = '{:.2f}'.format(_bytes)
            return '{}{}'.format(_bytes, size)
        _bytes /= 1024

    raise ValueError


'''
def better_decode(b):

    # detect encoding with libmagic
    m = magic.Magic(mime_encoding=True)
    encoding = m.from_buffer(b)

    try:
        return b.decode(encoding)
    except Exception:
        return str(b)[2:-1]
'''


def random_string(length):

    return ''.join(random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for i in range(length))


def list_files(path):

    path = Path(path)

    if path.is_file() and not path.is_symlink():
        yield path

    elif path.is_dir():
        for dir_name, dirnames, filenames in os.walk(path):
            for file in filenames:
                file = Path(dir_name) / file
                if file.is_file() and not file.is_symlink():
                    yield file


def rmdir(directory):
    '''
    Recursively remove directory
    '''
    directory = Path(directory)
    for item in directory.iterdir():
        if item.is_dir():
            rmdir(item)
        else:
            item.unlink()
    directory.rmdir()

def get_domain_dn(domain):
    base_dn = ''
    domain_parts = domain.split('.')
    for i in domain_parts:
        base_dn += 'DC=%s,' % i
    base_dn = base_dn[:-1]
    return base_dn

def get_domain(target):

    log.debug("Domain not provided, retrieving automatically.")
    s = Server(target, get_info=ALL)
    c = Connection(s)
    if not c.bind():
        log.error("Could not get domain automatically")
        return ""

    else:
        try:
            domain = str(s.info.other["ldapServiceName"][0].split("@")[1]).lower()

        except Exception as e:
            log.error("Could not get domain automatically")
            domain = ""

    c.unbind()
    log.debug(f"Domain:{domain}")
    return domain