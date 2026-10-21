# 一键重建 mGBA 0.10.5 的 libretro 内核，产出不进版本库。
# Set MGBA_SRC and ANDROID_SDK_ROOT before running this exported script.
$ErrorActionPreference = "Stop"
$Sdk = if ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT } else { throw "Set ANDROID_SDK_ROOT to the Android SDK path." }
$Ndk = Join-Path $Sdk "ndk\28.2.13676358"
$Cmake = Join-Path $Sdk "cmake\3.22.1\bin\cmake.exe"
$Ninja = Join-Path $Sdk "cmake\3.22.1\bin\ninja.exe"
$Src = if ($env:MGBA_SRC) { $env:MGBA_SRC } else { throw "Set MGBA_SRC to the mGBA 0.10.5 source path." }
$Build = Join-Path $PSScriptRoot "build-libretro"
$OutDir = Join-Path $PSScriptRoot "src\main\jniLibs\arm64-v8a"

if (!(Test-Path $Src)) { throw "找不到 mGBA 源码：$Src" }
$ver = Get-Content (Join-Path $Src "version.cmake") -Raw
if ($ver -notmatch "LIB_VERSION_MAJOR 0" -or $ver -notmatch "LIB_VERSION_MINOR 10" -or $ver -notmatch "LIB_VERSION_PATCH 5") {
    throw "源码不是 mGBA 0.10.5：$Src"
}
$Patches = Get-ChildItem (Join-Path $PSScriptRoot "patches") -Filter '*.patch' | Sort-Object Name
foreach ($PatchFile in $Patches) {
    $Patch = $PatchFile.FullName
    git -C $Src apply --check --whitespace=nowarn $Patch
    if ($LASTEXITCODE -eq 0) {
        git -C $Src apply --whitespace=nowarn $Patch
        if ($LASTEXITCODE -ne 0) { throw "打补丁失败：$Patch" }
    } else {
        git -C $Src apply --reverse --check --whitespace=nowarn $Patch
        if ($LASTEXITCODE -ne 0) { throw "补丁既打不上，也不是已经打过：$Patch" }
    }
}
New-Item -ItemType Directory -Force -Path $Build, $OutDir | Out-Null
& $Cmake -S $Src -B $Build -G Ninja "-DCMAKE_MAKE_PROGRAM=$Ninja" `
    "-DCMAKE_TOOLCHAIN_FILE=$Ndk\build\cmake\android.toolchain.cmake" `
    -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-26 -DCMAKE_BUILD_TYPE=Release `
    -DBUILD_LIBRETRO=ON -DSKIP_LIBRARY=ON -DBUILD_LTO=ON `
    -DM_CORE_GB=OFF -DM_CORE_GBA=ON `
    -DBUILD_QT=OFF -DBUILD_SDL=OFF -DBUILD_GL=OFF -DBUILD_GLES2=OFF -DBUILD_GLES3=OFF `
    -DBUILD_CINEMA=OFF -DBUILD_DOCGEN=OFF -DBUILD_EXAMPLE=OFF -DBUILD_PERF=OFF -DBUILD_PGO=OFF `
    -DBUILD_PYTHON=OFF -DBUILD_ROM_TEST=OFF -DBUILD_SHARED=OFF -DBUILD_STATIC=OFF `
    -DBUILD_SUITE=OFF -DBUILD_TEST=OFF -DENABLE_SCRIPTING=OFF `
    -DUSE_DEBUGGERS=OFF -DUSE_DISCORD_RPC=OFF -DUSE_EDITLINE=OFF -DUSE_ELF=OFF -DUSE_EPOXY=OFF `
    -DUSE_FFMPEG=OFF -DUSE_GDB_STUB=OFF -DUSE_LIBZIP=OFF -DUSE_LUA=OFF `
    -DUSE_LZMA=OFF -DUSE_MINIZIP=OFF -DUSE_PNG=OFF -DUSE_SQLITE3=OFF -DUSE_ZLIB=OFF
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Cmake --build $Build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$so = Get-ChildItem $Build -Recurse -Filter "mgba_libretro.so" | Select-Object -First 1
if (-not $so) { throw "没有找到 mgba_libretro.so" }
$dest = Join-Path $OutDir "libmgba_libretro.so"
Copy-Item $so.FullName $dest -Force
Write-Output "wrote $dest"
