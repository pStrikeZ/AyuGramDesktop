# Building AyuGram Desktop for Windows ARM64

This document describes a **cross build from an AMD64 Windows host to a
Windows ARM64 target**. It produces an ARM64 `AyuGram.exe`, while every build
time code generator remains a native AMD64 executable that can run on the
build host.

The build intentionally produces both Debug and Release dependencies. Build
the Release client to get the normal end-user performance profile.

## Prerequisites

Use Visual Studio 2026 and Windows SDK `10.0.26100.0`, as described in
[`building-win.md`](building-win.md). In addition to the usual C++ workload,
install the MSVC ARM64 build tools. The required compiler is
`Hostx64/arm64/cl.exe` from the v14.44 toolset.

From the build root, create `ThirdParty` and `Libraries`, clone recursively,
and initialise the ARM64 cross environment:

```bat
git clone --recursive https://github.com/AyuGram/AyuGramDesktop.git tdesktop
%comspec% /k "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" amd64_arm64 -vcvars_ver=14.44
```

For a Build Tools installation, use its `VC\Auxiliary\Build\vcvarsall.bat`
instead.

The important part is `amd64_arm64`: `amd64` is the architecture that runs
the build tools and `arm64` is the architecture of the output.

## Build dependencies

From the build root, run:

```bat
tdesktop\Telegram\build\prepare\win.bat silent
```

Do not pass `skip-release` when preparing a Release client. The script builds
the ARM64 Debug and optimized `RelWithDebInfo` Qt libraries (and ARM64 Release
libraries for other dependencies) and also creates these native AMD64 host
tools:

- Qt tools (`moc`, `rcc`, `qsb`, and others) in `Libraries\Qt-*-host`;
- `codegen_emoji.exe`, `codegen_lang.exe`, and `codegen_style.exe` in
  `Libraries\host_codegen\Debug`;
- `protoc.exe` in `Libraries\protobuf_host\build\Debug`;
- the tde2e/TDLib source generators in `Libraries\tde2e\out\host`.

Those host tools being Debug binaries is intentional. They run only while
building and do not affect the performance of the target application. The
target libraries and `AyuGram.exe` built for the Release configuration are
ARM64. Qt's `RelWithDebInfo` configuration is still optimized; it merely keeps
debug information, and is mapped only to the application's `Release`
configuration.

### Avoiding `machine type mismatch` dialogs

On an AMD64 build host, a `machine type mismatch` dialog means a build step
attempted to start an ARM64 executable. Do not dismiss it and continue: stop
the build and fix that dependency's host/target split. In particular, Meson
cross files must declare `needs_exe_wrapper = true` and use the explicit
`Hostx64/arm64` compiler paths. Test and console executable targets from
third-party libraries should be disabled when the application needs only their
static library. CMake dependency configurations must receive
`-DCMAKE_SYSTEM_NAME=Windows -DCMAKE_SYSTEM_PROCESSOR=ARM64` so `try_run()`
checks are not executed on the host.

The supported preparation script already applies these rules to dav1d,
OpenH264, Little CMS, and the CMake-based dependencies. A correct build log
reports an AMD64 *build machine* and ARM64 *host machine* for Meson, while
CMake reports that compiler run checks are skipped.

## Configure and build Release

Use the same `amd64_arm64` terminal and configure the project:

```bat
cd tdesktop\Telegram
configure.bat arm -D TDESKTOP_API_ID=2040 -D TDESKTOP_API_HASH=b18441a1ff607e10a989891a5462e627
cd ..
cmake --build out --config Release --target Telegram
```

The result is:

```
tdesktop\out\Release\AyuGram.exe
```

`winarm` is selected automatically by `configure.bat arm`. The project uses
the native host tools for all custom commands, so an AMD64 machine never tries
to execute an ARM64 generator.

## Verification

Use `dumpbin` from the Visual Studio toolset:

```bat
dumpbin /headers tdesktop\out\Release\AyuGram.exe | findstr /i "machine"
dumpbin /headers Libraries\host_codegen\Debug\codegen_emoji.exe | findstr /i "machine"
```

Expected values are `AA64 machine (ARM64)` for `AyuGram.exe` and `8664 machine
(x64)` for a host code generator.

## Packaging note

The public repository deliberately does not contain
`Telegram/SourceFiles/_other/packer_private.h`, which holds update-signing
private keys. The `Packer` target is therefore excluded for the local `winarm`
cross target. This does not affect building or running `AyuGram.exe`; it only
prevents creation of signed update packages.

## Committing the CMake submodule changes

`tdesktop/cmake` is a Git submodule. The main repository stores only a commit
identifier for it (a *gitlink*), not the files in its working tree. Therefore
the following order is required:

```bat
cd tdesktop\cmake
git switch -c winarm-cross-build
git add run_cmake.py host_tools.cmake host_codegen external\cld3 external\cmark_gfm external\qt
git commit -m "Add Windows ARM64 cross-build host tools"
git push -u <your-cmake-fork> winarm-cross-build

cd ..
git add cmake
git add CMakeLists.txt Telegram docs .gitignore
git commit -m "Add Windows ARM64 cross-build workflow"
git push
```

For a PR to the upstream projects, first merge or otherwise publish the CMake
submodule commit to a repository reachable from the main project's submodule
URL. Then commit the updated `cmake` gitlink in the main repository.

If the main repository must be self-contained under a personal fork, change
the `cmake` URL in `.gitmodules` to the corresponding CMake fork and commit
both `.gitmodules` and the new gitlink. A parent-repository commit alone
cannot preserve uncommitted submodule edits.
