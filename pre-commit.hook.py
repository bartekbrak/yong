#!/usr/bin/env python3
from argparse import ArgumentParser
from collections import namedtuple
import functools
import logging
import os
from pprint import pformat
import subprocess
import sys

from flake8.main.git import find_modified_files

EXCLUDED_FILES = set()

# common part (copied verbatim to other hooks, no imports please)
JIRA_PROJECT_SYMBOL = 'YO'
DEBUG = False
LINE = '█' * 40
Result = namedtuple('Result', ['out', 'rc'])

colours = {'RED': 41, 'GREEN': 42, 'YELLOW': 43, 'blue': 94, 'magenta': 95, 'red': 31, 'green': 32, 'yellow': 33}


def set_logging():
    if DEBUG:
        # flake has nice logs, useful for getting setup.cfg right, isort doesn't have logs
        log = logging.getLogger('flake8.options.config')
        log.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(f'\033[{colours["yellow"]}m%(name)s %(message)s\033[0m', datefmt='%H:%M:%S')
        ch.setFormatter(formatter)
        log.addHandler(ch)


def colour(colour_label: str, msg: str):
    sys.stdout.write(f'\033[{colours[colour_label]:d}m{msg}\033[0m\n')


def debug(*msgs, c='yellow'):
    # takes strings or callables to save time if not DEBUG
    if DEBUG:
        colour(c, ' '.join(str(x()) if callable(x) else str(x) for x in msgs))


def git_available():
    return os.path.exists('.git')


@functools.lru_cache()
def run(cmd: str, fine_if_command_not_found=False, doprint=False, **kwargs) -> Result:
    try:
        result = subprocess.run(
            cmd if kwargs.get('shell', False) else cmd.split(),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs
        )
        out, rc = result.stdout.decode('utf-8'), result.returncode
    except Exception as e:
        out, rc = str(e), -100
        if fine_if_command_not_found and 'No such file or directory' in str(e):
            rc = 0
    debug('run', cmd, kwargs, out.strip(), rc, c='blue')
    if doprint:
        sys.stdout.write(out)
    return Result(out, rc)


def generic_debug_info():
    debug('in:', __file__, c='magenta')
    debug('repo exists:', lambda: git_available())
    debug('cwd:', lambda: os.getcwd())
    debug('last commit:', lambda: run('git rev-parse --short=8 HEAD~1').out)
    debug('branch_name:', lambda: repr(run('git rev-parse --abbrev-ref HEAD').out.rstrip()))


# hook specific
fails = {}


def title(msg: str):
    sys.stdout.write(f'\n{LINE}\r\t {msg} \n')


def backend():
    title('backend style test')
    from flake8.main.git import hook as flake8_hook
    from isort.hooks import git_hook as isort_hook
    return {
        'isort': isort_hook(strict=True),
        'flake8': flake8_hook(strict=True),
    }


def run_backend_tests():
    title('backend tests')
    tests = run('pytest')
    if tests.rc != 0:
        sys.stdout.write(tests.out)
    return {
        'backend_tests': tests.rc
    }


INVALID_PATTERNS = [
    b'<<<<<<< ',  # noqa
    b'======= ',  # noqa
    b'=======\n',   # noqa
    b'>>>>>>> ',  # noqa
    b'print(',  # noqa
    b'dupa',  # noqa
    b'chuj',  # noqa
    b'kurwa',  # noqa
    b'jeba\xc4\x87',  # noqa
]


def detect_invalid_patterns(modified_files):
    title('detect_invalid_patterns')
    debug('modified_files', modified_files)
    count = 0
    for filename in modified_files:
        with open(filename, 'rb') as inputfile:
            for i, line in enumerate(inputfile, start=1):
                for pattern in INVALID_PATTERNS:
                    if pattern in line and b'  # noqa' not in line:
                        count += 1
                        sys.stdout.write('Invalid pattern %r found in %s:%s\n' % (pattern.decode(), filename, i))
    return {'invalid_patterns': count}


prod = [line.rstrip() for line in open('requirements.txt').readlines() if not line.startswith('#')]
dev = [line.rstrip() for line in open('requirements_dev.txt').readlines() if not line.startswith('#')]


def requirements_are_pinned():
    title('requirements are pinned')
    prod_not_pinned = [l for l in prod if not l.startswith('#') and '==' not in l and l]
    dev_not_pinned = [l for l in dev if not l.startswith('#') and '==' not in l and l]
    if prod_not_pinned:
        sys.stdout.write('prod_not_pinned %r\n' % prod_not_pinned)
    debug('prod_not_pinned', prod_not_pinned)
    debug('dev_not_pinned', dev_not_pinned)
    return {
        'requirements_pinned_prod': len(prod_not_pinned),
    }


def test(func, *args_, **kwargs):
    if func.__name__ not in skip:
        fails.update(func(*args_, **kwargs))
    else:
        debug(func.__name__, 'skipped')


def hook():
    generic_debug_info()
    debug('all_files', all_files)
    test(backend)
    title('other')
    files = set(find_modified_files(True)) - EXCLUDED_FILES
    test(detect_invalid_patterns, files)
    test(requirements_are_pinned)
    title('TODO|HACK|EXPLAIN|REMOVE|THINK|@Someone')
    # find patterns and highlight separately
    # https://stackoverflow.com/a/981831/1472229
    run(
        '''
        egrep -rn --exclude-dir=tmp -e "TODO|HACK|EXPLAIN|REMOVE|THINK|@[A-Z][a-z]+" |
        GREP_COLORS='mt=01;33' egrep --color=always "TODO|$" |
        GREP_COLORS='mt=01;31' egrep --color=always "HACK|$" |
        GREP_COLORS='mt=01;32' egrep --color=always "EXPLAIN|$" |
        GREP_COLORS='mt=01;34' egrep --color=always "REMOVE|$" |
        GREP_COLORS='mt=01;35' egrep --color=always "THINK|$" |
        GREP_COLORS='mt=01;36' egrep --color=always "@[A-Z][a-z]+|$"
        ''',
        doprint=True,
        shell=True,
    )

    any_fails = sum(fails.values())
    if any_fails:
        colour('RED', pformat(fails))
    debug('fails', fails)
    return any_fails


parser = ArgumentParser()
parser.add_argument(
    '-a', '--all-files',
    help='Run on all files rather on git "Changes to be committed", the default.',
    action='store_true'
)
parser.add_argument(
    '-d', '--debug',
    action='store_true'
)
parser.add_argument(
    '-s', '--skip',
    help='Functions to skip',
    default=[],
    choices=[k for k, v in locals().items() if callable(v)]
)
args = parser.parse_args()
if args.debug:
    DEBUG = True
debug('argparse', args)
all_files = args.all_files
skip = args.skip
set_logging()
sys.exit(hook())
