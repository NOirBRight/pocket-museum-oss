# Pocket Museum - GBA：公开源码材料

本目录只收录本应用 `0.1` 中对应的 mGBA 内核来源材料与改过的卡带模型。不含应用其余代码与素材，也不含 `libmgba_libretro.so` 内核二进制。

## mGBA 内核

- 上游： [mGBA](https://github.com/mgba-emu/mgba)，版本 `0.10.5`，提交 [`26b7884bc25a5933960f3cdcd98bac1ae14d42e2`](https://github.com/mgba-emu/mgba/commit/26b7884bc25a5933960f3cdcd98bac1ae14d42e2)。许可：MPL-2.0，全文见 [`LICENSES/MPL-2.0.txt`](LICENSES/MPL-2.0.txt)。
- 本项目补丁：`android/emulator/patches/0001-keep-savedata-on-unserialize.patch`（当前共 1 个）。它增加 `SAVESTATE_KEEP_SAVEDATA` 标志，并在 libretro 导出默认启用的 `mgba_keep_savedata`，使 `retro_unserialize` 可跳过即时存档状态内的游戏内存档恢复。
- 重建脚本：[`android/emulator/rebuild-libretro.ps1`](android/emulator/rebuild-libretro.ps1)。该副本不含开发机默认路径；运行前需要设置 `MGBA_SRC` 和 `ANDROID_SDK_ROOT`。`MGBA_SRC` 应指向提交 `26b7884bc25a5933960f3cdcd98bac1ae14d42e2` 的干净源码检出。

```powershell
git clone https://github.com/mgba-emu/mgba.git mgba
git -C mgba checkout --detach 26b7884bc25a5933960f3cdcd98bac1ae14d42e2
$env:MGBA_SRC = (Resolve-Path .\mgba).Path
$env:ANDROID_SDK_ROOT = '<Android SDK path>'
pwsh -NoProfile -File .\android\emulator\rebuild-libretro.ps1
```

构建配置为 NDK `28.2.13676358`、CMake `3.22.1`、Ninja、`arm64-v8a`、Android API 26、Release；启用 `BUILD_LIBRETRO`、GBA core 与 LTO，关闭 GB core、Qt、SDL、GL/GLES、脚本、调试器、测试与示例工具。可选依赖 `discord-rpc`、FFmpeg、libzip、Lua、LZMA、minizip、PNG、SQLite3、zlib、libelf、libepoxy、editline 与 GDB stub 均在脚本中关闭。

### 内核中的第三方代码

- `blip_buf` 1.1.0：mGBA 源码位置 `src/third-party/blip_buf/blip_buf.c`，许可文件位置 `res/licenses/blip_buf.txt`；LGPL-2.1-or-later，全文见 [`LICENSES/blip_buf-LGPL-2.1.txt`](LICENSES/blip_buf-LGPL-2.1.txt)。
- `inih`：mGBA 源码位置 `src/third-party/inih/`，许可文件位置 `res/licenses/inih.txt`；BSD-3-Clause，全文见 [`LICENSES/inih-BSD-3-Clause.txt`](LICENSES/inih-BSD-3-Clause.txt)。
- 二进制核对：从两份本机 APK 提取的内核具有相同 SHA-256；NDK `llvm-nm -D` 在 `.dynsym` 找到 `blip_*` 与 `ini_parse*` 符号，确认这两个库实际进入所查 `.so`。APK 与 `.so` 均不包含在本目录。

## 卡带模型

`app/models/gba_cartridge.glb` 是 4312 个三角面的改后模型（177008 字节，SHA-256 `91c74ef6f97a74cd7b9994dddcbb79a0bee51f6b1523654f662d088c61c7878d`）。它改自 DiniertoDesigns 的 “Gameboy Advance Cartridge”：<https://www.thingiverse.com/thing:6569544>。

原页面和模型包只写 `Creative Commons - Attribution - Share Alike`，没有许可版本号；本目录的 [`LICENSES/cartridge-CC-BY-SA-source-notice.txt`](LICENSES/cartridge-CC-BY-SA-source-notice.txt) 只记录这个原始许可名称，不代选具体版本。改动包括在底部插槽内加入电路板和 32 个触点、拆分材质、增加标签贴纸面与 UV、减面并移除背面铭牌字的侧壁。改后模型按来源所写的同一许可提供。原始 STL 与 STEP 不包含在内。

生成工具位于 `tools/models/cartridge/`。需要原始 STL、Python 的 NumPy / trimesh / SciPy，以及 Godot 4.7.2 console；例如：

```powershell
python -m tools.models.cartridge --source '<original STL path>' --godot '<Godot 4.7.2 console executable>' --out app/models/gba_cartridge.glb
```

## 文件范围与校验

本目录只按本项目导出脚本中的白名单收集文件。`MANIFEST` 为除自身以外的每个文件列出 SHA-256；清单不可能在自身内部包含自身的 SHA-256。

---

# Pocket Museum - GBA: public source materials

This directory contains only the mGBA core source materials and the modified cartridge model used by app version `0.1`. It does not contain the rest of the app's code and assets or the `libmgba_libretro.so` core binary.

## mGBA core

- Upstream: [mGBA](https://github.com/mgba-emu/mgba), version `0.10.5`, commit [`26b7884bc25a5933960f3cdcd98bac1ae14d42e2`](https://github.com/mgba-emu/mgba/commit/26b7884bc25a5933960f3cdcd98bac1ae14d42e2). License: MPL-2.0; full text: [`LICENSES/MPL-2.0.txt`](LICENSES/MPL-2.0.txt).
- Project patch: `android/emulator/patches/0001-keep-savedata-on-unserialize.patch` (one patch at this revision). It adds the `SAVESTATE_KEEP_SAVEDATA` flag and a default-enabled `mgba_keep_savedata` libretro export, allowing `retro_unserialize` to skip restoring the in-game save embedded in a save state.
- Build script: [`android/emulator/rebuild-libretro.ps1`](android/emulator/rebuild-libretro.ps1). This exported copy has no workstation-specific defaults. Set `MGBA_SRC` and `ANDROID_SDK_ROOT`; `MGBA_SRC` must point to a clean checkout at commit `26b7884bc25a5933960f3cdcd98bac1ae14d42e2`.

The build uses NDK `28.2.13676358`, CMake `3.22.1`, Ninja, `arm64-v8a`, Android API 26, and Release configuration. It enables the libretro GBA core and LTO, and disables the GB core, Qt, SDL, GL/GLES, scripting, debuggers, tests, and example tools. Optional dependencies disabled by the script include Discord RPC, FFmpeg, libzip, Lua, LZMA, minizip, PNG, SQLite3, zlib, libelf, libepoxy, editline, and the GDB stub.

The checked `.so` binaries expose `blip_*` and `ini_parse*` symbols in `.dynsym`, as confirmed with NDK `llvm-nm -D`; the inspected binaries came from two local APKs and had matching SHA-256 values. Neither APK nor `.so` is included here.

### Third-party code in the core

- `blip_buf` 1.1.0: source path in mGBA is `src/third-party/blip_buf/blip_buf.c`; its license file is `res/licenses/blip_buf.txt`. License: LGPL-2.1-or-later; full text: [`LICENSES/blip_buf-LGPL-2.1.txt`](LICENSES/blip_buf-LGPL-2.1.txt).
- `inih`: source path in mGBA is `src/third-party/inih/`; its license file is `res/licenses/inih.txt`. License: BSD-3-Clause; full text: [`LICENSES/inih-BSD-3-Clause.txt`](LICENSES/inih-BSD-3-Clause.txt).

## Cartridge model

`app/models/gba_cartridge.glb` is the modified model with 4312 triangles (177008 bytes; SHA-256 `91c74ef6f97a74cd7b9994dddcbb79a0bee51f6b1523654f662d088c61c7878d`). It is adapted from “Gameboy Advance Cartridge” by DiniertoDesigns: <https://www.thingiverse.com/thing:6569544>.

The source page and model archive state `Creative Commons - Attribution - Share Alike` without a version number. [`LICENSES/cartridge-CC-BY-SA-source-notice.txt`](LICENSES/cartridge-CC-BY-SA-source-notice.txt) records that source wording and does not select a version. Changes: a circuit board and 32 contacts were added inside the bottom slot; materials were separated; a label sticker surface and UVs were added; the mesh was simplified and the side walls of the back nameplate lettering were removed. The modified model is offered under the same license stated by the source. The original STL and STEP files are not included.

The generator is in `tools/models/cartridge/`. It requires the original STL, Python NumPy / trimesh / SciPy, and the Godot 4.7.2 console executable. Example:

```powershell
python -m tools.models.cartridge --source '<original STL path>' --godot '<Godot 4.7.2 console executable>' --out app/models/gba_cartridge.glb
```

## Scope and checks

Files are collected only from the allowlist in this repository's export script. `MANIFEST` gives the SHA-256 of every other file; a manifest cannot include its own hash.