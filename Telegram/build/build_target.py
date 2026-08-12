"""Shared build target selection for local desktop builds.

The public command line deliberately describes the produced binary, not the
architecture of a particular compiler executable.  Platform-specific runners
use this module before doing any work so prepare and configure cannot silently
select different dependency trees.
"""

from dataclasses import dataclass
import os
import platform as host_platform
import sys
from qt_versions import version_for_major


class BuildTargetError(Exception):
    pass


@dataclass(frozen=True)
class BuildTarget:
    target_platform: str
    arch: str
    mode: str
    qt_major: int

    @property
    def target(self):
        return self.target_platform + '-' + self.arch

    @property
    def key(self):
        return self.target + '-' + self.mode + '-qt' + str(self.qt_major)

    @property
    def special_target(self):
        if self.target_platform != 'windows':
            return ''
        return {
            'x86': 'win',
            'x64': 'win64',
            'arm64': 'winarm',
        }[self.arch]

    @property
    def cmake_arch(self):
        return {
            'x86': 'Win32',
            'x64': 'x64',
            'arm64': 'ARM64',
        }.get(self.arch, '')

    @property
    def is_windows_arm64_cross(self):
        return (
            self.target_platform == 'windows'
            and self.arch == 'arm64'
            and self.mode == 'cross')

    def describe(self):
        return '%s (mode=%s, Qt %d)' % (self.target, self.mode, self.qt_major)


def _normalise_arch(value):
    value = (value or '').lower()
    return {
        'x86': 'x86',
        'i386': 'x86',
        'i686': 'x86',
        'x64': 'x64',
        'amd64': 'x64',
        'x86_64': 'x64',
        'arm64': 'arm64',
        'aarch64': 'arm64',
    }.get(value, '')


def _take_value(arguments, index, option):
    if index + 1 >= len(arguments):
        raise BuildTargetError(option + ' requires a value.')
    return arguments[index + 1]


def _parse_public_arguments(arguments):
    target = None
    qt_major = None
    requested_mode = 'auto'
    remaining = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in ['--target', '--qt', '--mode']:
            value = _take_value(arguments, index, argument)
            if argument == '--target':
                if target is not None:
                    raise BuildTargetError('--target was specified more than once.')
                target = value
            elif argument == '--qt':
                if qt_major is not None:
                    raise BuildTargetError('--qt was specified more than once.')
                qt_major = value
            else:
                requested_mode = value
            index += 2
            continue
        if argument.startswith('--target=') or argument.startswith('--qt=') or argument.startswith('--mode='):
            raise BuildTargetError('Use a space after %s.' % argument.split('=', 1)[0])
        if argument in ['arm', 'x86', 'x64', 'qt5', 'qt6']:
            raise BuildTargetError(
                'Legacy argument "%s" is not supported; use --target and --qt.' % argument)
        remaining.append(argument)
        index += 1
    return target, qt_major, requested_mode, remaining


def _validate_qt(target_platform, arch, qt_major):
    if qt_major not in ['5', '6']:
        raise BuildTargetError('--qt must be 5 or 6.')
    qt_major = int(qt_major)
    if target_platform == 'linux' and qt_major != 6:
        raise BuildTargetError('Linux builds currently require --qt 6.')
    if target_platform == 'windows' and arch == 'arm64' and qt_major != 6:
        raise BuildTargetError('windows-arm64 requires --qt 6.')
    if target_platform == 'linux' and arch == 'x86':
        raise BuildTargetError('linux-x86 is not supported by this build environment.')
    return qt_major


def _validate_windows(target_arch, requested_mode, environment):
    vs_target = _normalise_arch(
        environment.get('VSCMD_ARG_TGT_ARCH') or environment.get('Platform'))
    vs_host = _normalise_arch(environment.get('VSCMD_ARG_HOST_ARCH'))
    if not vs_target or not vs_host:
        raise BuildTargetError(
            'Run from a Visual Studio Native Tools terminal; VSCMD_ARG_HOST_ARCH '
            'and VSCMD_ARG_TGT_ARCH (or Platform) must be set.')
    if vs_target != target_arch:
        raise BuildTargetError(
            '--target windows-%s requires a Visual Studio terminal targeting %s, '
            'but the current terminal targets %s.' % (target_arch, target_arch, vs_target))

    if vs_host == target_arch:
        detected_mode = 'native'
    elif vs_host == 'x64' and target_arch == 'arm64':
        detected_mode = 'cross'
    else:
        raise BuildTargetError(
            'Unsupported Windows host/target pair: host %s, target %s. '
            'Only native builds and x64-to-arm64 cross builds are supported.'
            % (vs_host, target_arch))

    if requested_mode not in ['auto', 'native', 'cross']:
        raise BuildTargetError('--mode must be auto, native, or cross.')
    if requested_mode != 'auto' and requested_mode != detected_mode:
        raise BuildTargetError(
            '--mode %s conflicts with the Visual Studio environment (%s build).' % (
                requested_mode, detected_mode))
    return detected_mode


def _validate_linux(target_arch, requested_mode, machine):
    if requested_mode not in ['auto', 'native', 'cross']:
        raise BuildTargetError('--mode must be auto, native, or cross.')
    host_arch = _normalise_arch(machine)
    if not host_arch:
        raise BuildTargetError('Unsupported Linux host architecture: %s.' % machine)
    detected_mode = 'native' if host_arch == target_arch else 'cross'
    if requested_mode == 'native' and detected_mode != 'native':
        raise BuildTargetError(
            '--target linux-%s does not match the native host architecture %s.'
            % (target_arch, host_arch))
    if requested_mode == 'cross' or detected_mode == 'cross':
        raise BuildTargetError(
            'Linux cross compilation is reserved by this interface but is not implemented yet. '
            'Run on a native linux-%s host instead.' % target_arch)
    return 'native'


def parse_build_arguments(
        arguments, system=None, environment=None, machine=None, allow_implicit=False):
    """Return ``(BuildTarget | None, remaining_arguments)``.

    macOS keeps its existing universal-build workflow and therefore does not use
    this interface yet. Windows and Linux require both --target and --qt.
    ``system``, ``environment`` and ``machine`` are injectable for unit tests.
    """
    system = system or sys.platform
    environment = environment or os.environ
    machine = machine or host_platform.machine()
    target, qt_major, requested_mode, remaining = _parse_public_arguments(arguments)

    if system == 'darwin':
        if target is not None or qt_major is not None or requested_mode != 'auto':
            raise BuildTargetError('The --target/--mode/--qt interface is not implemented for macOS.')
        return None, remaining

    expected_platform = 'windows' if system == 'win32' else 'linux' if system.startswith('linux') else ''
    if not expected_platform:
        raise BuildTargetError('Unsupported host platform: %s.' % system)
    if target is None and allow_implicit and qt_major is None and requested_mode == 'auto':
        return None, remaining
    if target is None:
        raise BuildTargetError('--target is required.')
    if qt_major is None:
        raise BuildTargetError('--qt is required.')

    parts = target.split('-', 1)
    if len(parts) != 2 or parts[0] not in ['windows', 'linux'] or parts[1] not in ['x86', 'x64', 'arm64']:
        raise BuildTargetError(
            '--target must be one of windows-x86, windows-x64, windows-arm64, '
            'linux-x64, or linux-arm64.')
    target_platform, arch = parts
    if target_platform != expected_platform:
        raise BuildTargetError('--target %s must be configured on %s.' % (target, target_platform))
    qt_major = _validate_qt(target_platform, arch, qt_major)
    if target_platform == 'windows':
        mode = _validate_windows(arch, requested_mode, environment)
    else:
        mode = _validate_linux(arch, requested_mode, machine)
    return BuildTarget(target_platform, arch, mode, qt_major), remaining


def _main(arguments):
    if not arguments or arguments[0] not in ['validate-linux', 'linux-environment']:
        print('Usage: build_target.py validate-linux|linux-environment --target linux-<x64|arm64> --qt 6 [--mode auto|native]')
        return 1
    try:
        selection, remaining = parse_build_arguments(arguments[1:])
        if selection.target_platform != 'linux' or (
                arguments[0] == 'validate-linux' and remaining):
            raise BuildTargetError('Linux prepare accepts only --target, --mode, and --qt.')
    except BuildTargetError as error:
        print('[ERROR] ' + str(error))
        return 1
    if arguments[0] == 'linux-environment':
        print('BUILD_TARGET=%s' % selection.target)
        print('BUILD_MODE=%s' % selection.mode)
        print('BUILD_KEY=%s' % selection.key)
        print('QT_MAJOR=%d' % selection.qt_major)
        print('QT_VERSION=%s' % version_for_major(selection.qt_major))
    else:
        print('Selected ' + selection.describe())
    return 0


if __name__ == '__main__':
    sys.exit(_main(sys.argv[1:]))
