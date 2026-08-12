"""The single Qt version policy for local source builds.

Selecting Qt 5 or Qt 6 is part of the public build command.  The exact patch
level is intentionally pinned here so Windows preparation and the CentOS image
cannot silently use different Qt source revisions.
"""

QT_VERSIONS = {
    5: '5.15.19',
    6: '6.11.1',
}


def version_for_major(major):
    try:
        return QT_VERSIONS[int(major)]
    except (KeyError, TypeError, ValueError):
        raise ValueError('Unsupported Qt major version: %s.' % major)
