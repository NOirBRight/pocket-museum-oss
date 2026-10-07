"""卡带模型。原始 STL 在仓库外，由调用方传入。

python -m tools.models.cartridge --source <Gameboy_Advance_Cartridge.stl> --godot <Godot_v4.7.2-stable_win64_console.exe>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.models.cartridge.build import GLB, build


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="把仓库外的卡带外壳 STL 做成 app/models/gba_cartridge.glb")
    parser.add_argument("--source", required=True, help="Gameboy_Advance_Cartridge.stl 的路径")
    parser.add_argument("--godot", required=True, help="Godot 4.7.2 的控制台程序。减面用它自带的 meshoptimizer")
    parser.add_argument("--out", default=str(GLB))
    args = parser.parse_args(argv)
    print(json.dumps(build(Path(args.source), Path(args.godot), Path(args.out)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
