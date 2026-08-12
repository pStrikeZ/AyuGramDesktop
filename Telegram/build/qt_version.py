import sys, os
from qt_versions import version_for_major

def resolve(arch, qt_major = None):
    if sys.platform == 'darwin':
        os.environ['QT'] = version_for_major(6)
    elif sys.platform == 'win32':
        if qt_major is None:
            qt_major = 6 if arch in ['arm', 'arm64'] or 'qt6' in sys.argv else 5
        if qt_major == 6:
            print('Choosing Qt 6.')
            os.environ['QT'] = version_for_major(6)
        elif qt_major == 5:
            print('Choosing Qt 5.')
            os.environ['QT'] = version_for_major(5)
        else:
            return False
    return True
