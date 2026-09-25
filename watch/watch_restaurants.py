#!/usr/bin/env python3
"""Run both independent restaurant watchers, preserving failures in the exit code."""
import sys

import watch_chairman
import watch_sevenrooms


def main():
    failed = watch_chairman.main()
    try:
        watch_sevenrooms.main()
    except Exception as exc:
        watch_sevenrooms.log(f'Wing: ERROR {exc}')
        failed = 1
    return failed


if __name__ == '__main__':
    sys.exit(main())
