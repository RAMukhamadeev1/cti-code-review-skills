#!/usr/bin/env python3
"""Read local worktree changes without configured Git filters or diff helpers.

Return a patch or NUL-delimited status. Do not traverse dirty submodules.
"""

import argparse
import subprocess
import sys


def read_worktree(repository, mode='tracked'):
    """Read one fixed Git view with content conversion and executable hooks disabled."""
    modes = {
        'tracked': ['diff', 'HEAD'],
        'staged': ['diff', '--cached'],
        'unstaged': ['diff'],
        'status': ['status', '--porcelain=v1', '-z', '--untracked-files=all',
                   '--ignore-submodules=dirty'],
    }
    arguments = modes[mode]
    prefix = ['git', '--no-pager', '--no-optional-locks', '-C', repository, '-c', 'core.fsmonitor=false',
              '-c', 'core.hooksPath=/dev/null', '--literal-pathspecs']
    config = subprocess.run(prefix + ['config', '--null', '--name-only', '--get-regexp',
                                     r'^filter\..*\.(clean|process|required)$'],
                            capture_output=True, check=False)
    if config.returncode not in (0, 1):
        raise subprocess.CalledProcessError(config.returncode, ['git', 'config'])
    drivers = {key.rsplit('.', 1)[0] for key in
               config.stdout.decode('utf-8', errors='surrogateescape').split('\0') if key}
    if any('=' in driver for driver in drivers):
        raise ValueError('Unsupported filter name; no worktree command was run.')
    for driver in sorted(drivers):
        for setting, value in (('clean', ''), ('process', ''), ('required', 'false')):
            prefix.extend(['-c', f'{driver}.{setting}={value}'])
    if mode != 'status':
        arguments += ['--no-color', '--default-prefix', '--no-ext-diff', '--no-textconv',
                      '--ignore-submodules=dirty', '--submodule=short']
    return subprocess.run(prefix + arguments, capture_output=True, check=True).stdout


def main():
    """Print the selected view or fail without exposing Git configuration values."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, help='Explicit repository path')
    parser.add_argument('--mode', choices=('tracked', 'staged', 'unstaged', 'status'),
                        default='tracked')
    args = parser.parse_args()
    try:
        output = read_worktree(args.repo, args.mode)
    except (OSError, ValueError, subprocess.CalledProcessError):
        print('Unable to read worktree safely; check the repository and Git availability.',
              file=sys.stderr)
        return 1
    sys.stdout.buffer.write(output)
    return 0


if __name__ == '__main__':
    sys.exit(main())
