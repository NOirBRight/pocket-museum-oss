"""把仓库外的卡带外壳 STL 做成应用用的 GLB。

来源是 DiniertoDesigns 的 “Gameboy Advance Cartridge”（Thingiverse thing:6569544，
Creative Commons - Attribution - Share Alike）。原始 STL 不进仓库，这里只读。

成品坐标和旧模型（`prototype/tools/gba_cartridge.py`）一致：+X 向右，+Y 是卡带上沿，
+Z 是贴标签的正面；宽度居中，标签和旧模型的标签在同一个位置上。
"""

from __future__ import annotations

import json
import math
import struct
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

REPO = Path(__file__).resolve().parents[3]
GLB = REPO / "app" / "models" / "gba_cartridge.glb"

# 原始 STL（毫米）：X 宽，Y 厚（+Y 是正面），Z 高（−Z 是握持的那一头）。换了别的文件就停下。
SOURCE_LOW = (-30.0, -22.0, -12.5)
SOURCE_HIGH = (30.0, -12.5, 22.0)
SOURCE_FRONT_Y = -14.5      # 机身正面
SOURCE_LABEL_Z = 6.25       # 标签凹槽的中心

# 握把两耳的总宽 60 mm 对到旧模型的 1.539（旧模型是 57 mm × 0.027）。
SCALE = 1.539 / 60.0

# 下面都是转过之后的毫米坐标。
# 应用按旧模型的标签摆字：大字和名字的位置相对标签写死，深度在 z = 0.093。所以原点跟着标签走：
# 凹槽中心对到旧标签的中心 y = −0.9 mm × 0.027，贴纸面对到旧贴纸面 z = 3.41 mm × 0.027。
# 这样外形的上沿和旧模型只差 0.002，下沿比旧模型高 0.031（新卡带矮一些）。
LABEL_Y = -0.9 * 0.027 / SCALE
LABEL_LIFT = 0.05
STICKER_Z = 3.41 * 0.027 / SCALE
LABEL_FLOOR = STICKER_Z - LABEL_LIFT   # 标签凹槽、字样凹带、箭头的底
FRONT = LABEL_FLOOR + 0.4              # 机身正面。握持部的弧再鼓出 2 mm
BACK = FRONT - 7.5
PLATE_FLOOR = BACK + 0.4               # 背面铭牌凹区的底
BOTTOM = LABEL_Y - 15.75               # 卡带下沿。上沿在 LABEL_Y + 18.75


def _zone(x0: float, x1: float, y0: float, y1: float):
    """x0 x1 y0 y1，y 从标签凹槽的中心量起。"""
    return (x0, x1, LABEL_Y + y0, LABEL_Y + y1)


RECESS = _zone(-22.5, 22.5, -11.75, 11.75)   # 标签凹槽：45 × 23.5
WORDMARK = _zone(-14.0, 14.0, 11.7, 15.2)    # 正面 GAME BOY ADVANCE 的凹带
ARROW = _zone(-6.5, 6.5, -15.0, -12.5)
PLATE = _zone(-11.6, 11.6, 1.15, 12.35)      # 背面铭牌凹区
SCREW = (0.0, LABEL_Y + 15.25)               # 背面螺丝的圆心
SCREW_HEAD_RADIUS = 2.0                      # 螺丝头。外面一圈到 2.5 是外壳上的沉孔

# 贴纸照卡带标签的 43 : 22 做，放进 45 × 23.5 的凹槽：左右各留 0.2，上下各留 0.34。
LABEL_ASPECT = 43.0 / 22.0
LABEL_W = 44.6
LABEL_H = LABEL_W / LABEL_ASPECT
LABEL_RADIUS = 1.0

# 插槽是原模型自带的空腔：x ±25，从下沿往里 10 mm，前壁在机身正面后 1.25，后壁在后 5.25。
# 电路板和触点照旧模型的尺寸放进去，触点面离前壁 2 mm。
SLOT_DEPTH = 10.0
PCB_HALF_W = 24.6
PCB_Z = (FRONT - 4.05, FRONT - 3.25)
PIN_COUNT = 32
PIN_PITCH = 1.5
PIN_W = 1.0
PIN_Y = (0.45, 4.6)
PIN_THICK = 0.08

CREASE_DEG = 35.0

# 减面的误差，相对模型最长边。原模型 36,378 面，这个误差下剩 6,380 面，离原表面最远 0.05 mm；
# 展柜正中那张卡带一毫米约 7 个像素。铭牌的字去掉侧壁之后是 4,208 面。
SIMPLIFY_ERROR = 0.0003

MATERIALS = [
    # 名字、sRGB、粗糙度、金属度。Shell、Gloss、Label 在应用里会被换掉，其余用这里的值。
    ("Shell", "46464b", 0.62, 0.0),
    ("Gloss", "46464b", 0.22, 0.0),
    ("Label", "e8e8e8", 0.35, 0.0),
    ("PCB", "2f7d4a", 0.55, 0.0),
    ("Gold", "d9a441", 0.25, 1.0),
    ("Metal", "b8a36c", 0.3, 1.0),
    ("ShellBack", "4b4c4e", 0.62, 0.0),
    ("GlossBack", "4b4c4e", 0.22, 0.0),
    ("Chip", "202322", 0.8, 0.0),
]
SHELL, GLOSS, LABEL, PCB, GOLD, METAL = range(6)
SHELL_BACK, GLOSS_BACK, CHIP = range(6, 9)


def build(source: Path, godot: Path, out: Path = GLB) -> dict:
    vertices, faces = decimate(*load_source(source), SIMPLIFY_ERROR, godot)
    faces = flatten_nameplate(vertices, faces)
    material = classify(vertices, faces)
    back = vertices[faces].mean(axis=1)[:, 2] < (FRONT + BACK) / 2
    material[back & (material == SHELL)] = SHELL_BACK
    material[back & (material == GLOSS)] = GLOSS_BACK
    normals = corner_normals(vertices, faces, CREASE_DEG)
    parts = [(index, *split(vertices, faces, normals, material == index), None) for index in np.unique(material)]
    parts.append((LABEL, *label_sticker()))
    parts.append((PCB, *flat(*pcb_board()), None))
    parts.append((GOLD, *flat(*pins()), None))
    parts.extend(chips())
    primitives = merge_parts(parts)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(write_glb(primitives))
    return report(primitives, out)


def load_source(source: Path):
    mesh = trimesh.load(source, process=True)
    low, high = mesh.bounds
    if not (np.allclose(low, SOURCE_LOW, atol=0.01) and np.allclose(high, SOURCE_HIGH, atol=0.01)):
        raise SystemExit(f"不是票 54 的那份 STL：包围盒 {low.tolist()} {high.tolist()}")
    if not mesh.is_watertight:
        raise SystemExit("STL 不是封闭实体")
    return to_cart(np.asarray(mesh.vertices, dtype=np.float64)), np.asarray(mesh.faces, dtype=np.int64)


def to_cart(vertices: np.ndarray) -> np.ndarray:
    """原模型 → 卡带坐标（毫米）。是一个旋转，面的绕向不变。"""
    return np.column_stack((
        vertices[:, 0],
        SOURCE_LABEL_Z + LABEL_Y - vertices[:, 2],
        vertices[:, 1] - SOURCE_FRONT_Y + FRONT,
    ))


def flatten_nameplate(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """背面铭牌的字只留顶面：字的侧壁和被字挖空的凹区底删掉，凹区底换成一整片。

    背面在应用里看不到，这些字原样留着要占掉一半的面。减面只挑顶点不挪顶点，所以减完再做，深度还对得上。
    """
    normals, _areas = face_normals(vertices, faces)
    corners = vertices[faces]
    x0, x1, y0, y1 = PLATE
    xs, ys, zs = corners[:, :, 0], corners[:, :, 1], corners[:, :, 2]
    in_zone = (xs.min(axis=1) > x0) & (xs.max(axis=1) < x1) & (ys.min(axis=1) > y0) & (ys.max(axis=1) < y1)
    floor = in_zone & (normals[:, 2] < -0.999) & (np.abs(zs.mean(axis=1) - PLATE_FLOOR) < 0.01)
    # 字离凹区的外壁至少 1 mm。往里收 0.5，外壁就不会被当成字的侧壁。
    deep = (xs.min(axis=1) > x0 + 0.5) & (xs.max(axis=1) < x1 - 0.5) & (ys.min(axis=1) > y0 + 0.5) & (ys.max(axis=1) < y1 - 0.5)
    walls = deep & (zs.max(axis=1) < PLATE_FLOOR + 0.01) & (np.abs(normals[:, 2]) < 0.999)
    # 凹区底的外圈：底面的边里，对面不是字的侧壁、也不是底面的那些。照底面的绕向接成一片扇面。
    gone = floor | walls
    directed = np.column_stack((faces[floor][:, [0, 1, 2]].reshape(-1), faces[floor][:, [1, 2, 0]].reshape(-1)))
    owner = {}
    for row in np.nonzero(~gone)[0]:
        tri = faces[row]
        for k in range(3):
            owner[(int(tri[(k + 1) % 3]), int(tri[k]))] = row
    rim = np.asarray([edge for edge in directed if (int(edge[0]), int(edge[1])) in owner])
    hub = rim[0, 0]
    fan = np.asarray([(hub, a, b) for a, b in rim if hub not in (a, b)], dtype=np.int64)
    return np.vstack((faces[~gone], fan))


def decimate(vertices: np.ndarray, faces: np.ndarray, error: float, godot: Path):
    """整体减面，用 Godot 自带的 meshoptimizer（见 simplify.gd）。减完外壳还得是封闭的。"""
    with tempfile.TemporaryDirectory() as work:
        given = Path(work) / "in.bin"
        taken = Path(work) / "out.bin"
        given.write_bytes(struct.pack("<ii", len(vertices), len(faces)) + vertices.astype("<f4").tobytes() + faces.astype("<i4").tobytes())
        script = Path(__file__).with_name("simplify.gd")
        subprocess.run([str(godot), "--headless", "--script", str(script), "--", str(given), str(taken), repr(error)],
                       cwd=work, check=True, capture_output=True)
        reduced = np.frombuffer(taken.read_bytes(), dtype="<i4").reshape(-1, 3).astype(np.int64)
    if len(open_edges(reduced)):
        raise SystemExit(f"误差 {error} 时外壳破了")
    used, reduced = np.unique(reduced, return_inverse=True)
    return vertices[used], reduced.reshape(-1, 3)


def open_edges(faces: np.ndarray) -> np.ndarray:
    """只属于一个面的边。"""
    edges = np.sort(faces[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
    uniq, counts = np.unique(edges, axis=0, return_counts=True)
    return uniq[counts == 1]


def face_normals(vertices: np.ndarray, faces: np.ndarray):
    tri = vertices[faces]
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    length = np.linalg.norm(cross, axis=1)
    return cross / np.maximum(length, 1e-12)[:, None], length * 0.5


def face_pairs(faces: np.ndarray) -> np.ndarray:
    """共用一条边的两个面。"""
    edges = np.sort(faces[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
    owner = np.repeat(np.arange(len(faces)), 3)
    order = np.lexsort((edges[:, 1], edges[:, 0]))
    edges, owner = edges[order], owner[order]
    same = np.all(edges[1:] == edges[:-1], axis=1)
    return np.column_stack((owner[:-1][same], owner[1:][same]))


def planar_regions(faces: np.ndarray, normals: np.ndarray, cos_limit: float) -> np.ndarray:
    """连着、朝向又一样的面算一块。返回每个面的块号。"""
    pairs = face_pairs(faces)
    pairs = pairs[np.einsum("ij,ij->i", normals[pairs[:, 0]], normals[pairs[:, 1]]) >= cos_limit]
    graph = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(faces), len(faces)))
    _count, labels = connected_components(graph, directed=False)
    return labels


def classify(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """每个面归哪种材质。亮面是正面字样的顶面、箭头的底和背面铭牌凹区的底；螺丝头是金属。"""
    normals, _areas = face_normals(vertices, faces)
    material = np.full(len(faces), SHELL, dtype=np.int64)
    corners = vertices[faces]
    labels = planar_regions(faces, normals, math.cos(math.radians(2.5)))
    levels = corners[:, :, 2].mean(axis=1)
    for sign, level, zone, kind in (
        (1.0, FRONT, WORDMARK, GLOSS),
        (1.0, LABEL_FLOOR, ARROW, GLOSS),
        (-1.0, PLATE_FLOOR, PLATE, GLOSS),
    ):
        on_level = (normals[:, 2] * sign > 0.999) & (np.abs(levels - level) < 0.02)
        x0, x1, y0, y1 = zone
        xs, ys = corners[:, :, 0], corners[:, :, 1]
        outside = (xs.min(axis=1) < x0) | (xs.max(axis=1) > x1) | (ys.min(axis=1) < y0) | (ys.max(axis=1) > y1)
        # 一整块都在框里才算。机身的大平面也在这个深度上，它伸到框外。
        spills = np.zeros(labels.max() + 1, dtype=bool)
        spills[labels[on_level & outside]] = True
        material[on_level & ~spills[labels]] = kind
    radius = np.hypot(corners[:, :, 0] - SCREW[0], corners[:, :, 1] - SCREW[1]).max(axis=1)
    material[(radius <= SCREW_HEAD_RADIUS + 0.02) & (corners[:, :, 2].max(axis=1) < 0.0)] = METAL
    return material


def corner_normals(vertices: np.ndarray, faces: np.ndarray, crease_deg: float) -> np.ndarray:
    """按折角分平滑组：同一顶点上夹角小于折角的面共用法线。返回每个面三个角的法线。

    权重是面所在那块平面的总面积，同一块只算一次。这样大平面保持平，
    圆角贴着平面的那条边跟平面同向，明暗只落在圆角自己的窄面上。
    """
    normals, areas = face_normals(vertices, faces)
    labels = planar_regions(faces, normals, math.cos(math.radians(0.8)))
    weight = np.bincount(labels, weights=areas)[labels]
    limit = math.cos(math.radians(crease_deg))
    corner_face = np.repeat(np.arange(len(faces)), 3)
    corner_vertex = faces.reshape(-1)
    order = np.argsort(corner_vertex, kind="stable")
    starts = np.flatnonzero(np.r_[True, np.diff(corner_vertex[order]) != 0, True])
    result = np.zeros((len(corner_vertex), 3))
    for a, b in zip(starts[:-1], starts[1:]):
        corners = order[a:b]
        around = corner_face[corners]
        _regions, first = np.unique(labels[around], return_index=True)
        once = around[first]
        near = normals[around] @ normals[once].T >= limit
        result[corners] = (near * weight[once][None, :]) @ normals[once]
    result /= np.maximum(np.linalg.norm(result, axis=1), 1e-12)[:, None]
    return result.reshape(-1, 3, 3)


def split(vertices: np.ndarray, faces: np.ndarray, normals: np.ndarray, picked: np.ndarray):
    """取出一部分面，位置和法线都相同的角并成一个顶点。"""
    corner_vertex = faces[picked].reshape(-1)
    corner_normal = normals[picked].reshape(-1, 3)
    key = np.column_stack((corner_vertex, np.round(corner_normal * 2000.0).astype(np.int64)))
    _uniq, first, inverse = np.unique(key, axis=0, return_index=True, return_inverse=True)
    return vertices[corner_vertex[first]], corner_normal[first], inverse.reshape(-1, 3)


def flat(vertices: np.ndarray, faces: np.ndarray):
    """每个面自己的法线，棱全是利的。"""
    normals, _area = face_normals(vertices, faces)
    return vertices[faces].reshape(-1, 3), np.repeat(normals, 3, axis=0), np.arange(len(faces) * 3).reshape(-1, 3)


def rounded_rect(width: float, height: float, radius: float, segments: int = 6) -> np.ndarray:
    points = []
    corners = [(width / 2 - radius, -height / 2 + radius, -90), (width / 2 - radius, height / 2 - radius, 0),
               (-width / 2 + radius, height / 2 - radius, 90), (-width / 2 + radius, -height / 2 + radius, 180)]
    for cx, cy, start in corners:
        for step in range(segments + 1):
            angle = math.radians(start + 90.0 * step / segments)
            points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return np.asarray(points)


def label_sticker():
    """贴纸：凹槽里的一张圆角片，UV 铺满它的外接矩形。glTF 的 V 从贴图上沿算起。"""
    x0, x1, y0, y1 = RECESS
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    ring = rounded_rect(LABEL_W, LABEL_H, LABEL_RADIUS)
    flat_points = np.vstack(((0.0, 0.0), ring))
    count = len(ring)
    faces = np.asarray([(0, 1 + index, 1 + (index + 1) % count) for index in range(count)], dtype=np.int64)
    vertices = np.column_stack((flat_points[:, 0] + cx, flat_points[:, 1] + cy, np.full(len(flat_points), LABEL_FLOOR + LABEL_LIFT)))
    normals = np.tile((0.0, 0.0, 1.0), (len(vertices), 1))
    uv = np.column_stack((flat_points[:, 0] / LABEL_W + 0.5, 0.5 - flat_points[:, 1] / LABEL_H))
    return vertices, normals, faces, uv


def box(x0, x1, y0, y1, z0, z1):
    vertices = np.asarray([(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)], dtype=np.float64)
    quads = [(4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5), (0, 2, 3, 1)]
    faces = []
    for a, b, c, d in quads:
        faces += [(a, b, c), (a, c, d)]
    return vertices, np.asarray(faces, dtype=np.int64)


def pcb_board():
    """电路板：贴着插槽的顶，下沿比外壳缩进 0.35。"""
    return box(-PCB_HALF_W, PCB_HALF_W, BOTTOM + 0.35, LABEL_Y + 13.0, PCB_Z[0], PCB_Z[1])


def chips():
    # Only silhouettes; clear of the slot contacts and the central rear screw post.
    return [(CHIP, *flat(*box(x0, x1, LABEL_Y + y0, LABEL_Y + y1, z0, z1)), None)
            for z0, z1 in [(PCB_Z[1], PCB_Z[1] + 0.65), (PCB_Z[0] - 0.65, PCB_Z[0])]
            for x0, x1, y0, y1 in [(-18, -3, -5, 5), (5, 17, -3, 6), (-18, -10, 8, 11)]]


def pins():
    """一排金手指，朝正面。只要正面那一片，0.08 mm 的侧边看不见。"""
    first = -(PIN_COUNT - 1) * PIN_PITCH / 2.0
    z = PCB_Z[1] + PIN_THICK
    vertices = []
    faces = []
    for index in range(PIN_COUNT):
        x = first + index * PIN_PITCH
        y0, y1 = BOTTOM + PIN_Y[0], BOTTOM + PIN_Y[1]
        vertices += [(x - PIN_W / 2, y0, z), (x + PIN_W / 2, y0, z), (x + PIN_W / 2, y1, z), (x - PIN_W / 2, y1, z)]
        faces += [(4 * index, 4 * index + 1, 4 * index + 2), (4 * index, 4 * index + 2, 4 * index + 3)]
    return np.asarray(vertices, dtype=np.float64), np.asarray(faces, dtype=np.int64)


def merge_parts(parts) -> list[dict]:
    """同一种材质并成一个面组，顺序照 MATERIALS。"""
    primitives = []
    for index, (name, _color, _rough, _metal) in enumerate(MATERIALS):
        mine = [part for part in parts if part[0] == index]
        if not mine:
            continue
        offset = 0
        vertices, normals, faces, uvs = [], [], [], []
        for _index, part_v, part_n, part_f, part_uv in mine:
            vertices.append(part_v)
            normals.append(part_n)
            faces.append(part_f + offset)
            uvs.append(part_uv)
            offset += len(part_v)
        with_uv = all(uv is not None for uv in uvs)
        primitives.append({
            "material": index,
            "name": name,
            "vertices": np.vstack(vertices) * SCALE,
            "normals": np.vstack(normals),
            "faces": np.vstack(faces),
            "uv": np.vstack(uvs) if with_uv else None,
        })
    return primitives


def srgb_to_linear(hex_color: str) -> list[float]:
    values = []
    for start in (0, 2, 4):
        channel = int(hex_color[start:start + 2], 16) / 255.0
        values.append(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4)
    return values


def write_glb(primitives: list[dict]) -> bytes:
    """一个节点、一个网格，都叫 Cartridge；每种材质一个面组。"""
    blob = bytearray()
    views = []
    accessors = []

    def push(array: np.ndarray, target: int, component: int, kind: str, bounds: bool = False) -> int:
        while len(blob) % 4:
            blob.append(0)
        views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": array.nbytes, "target": target})
        blob.extend(array.tobytes())
        accessor = {"bufferView": len(views) - 1, "componentType": component, "count": int(len(array)), "type": kind}
        if bounds:
            accessor["min"] = [float(value) for value in array.min(axis=0)]
            accessor["max"] = [float(value) for value in array.max(axis=0)]
        accessors.append(accessor)
        return len(accessors) - 1

    used = [item["material"] for item in primitives]
    mesh_primitives = []
    for item in primitives:
        attributes = {
            "POSITION": push(item["vertices"].astype("<f4"), 34962, 5126, "VEC3", bounds=True),
            "NORMAL": push(item["normals"].astype("<f4"), 34962, 5126, "VEC3"),
        }
        if item["uv"] is not None:
            attributes["TEXCOORD_0"] = push(item["uv"].astype("<f4"), 34962, 5126, "VEC2")
        indices = push(item["faces"].astype("<u4").reshape(-1), 34963, 5125, "SCALAR")
        mesh_primitives.append({"attributes": attributes, "indices": indices, "material": used.index(item["material"])})
    materials = []
    for index in used:
        name, color, roughness, metallic = MATERIALS[index]
        materials.append({
            "name": name,
            "pbrMetallicRoughness": {
                "baseColorFactor": [round(value, 6) for value in srgb_to_linear(color)] + [1.0],
                "metallicFactor": metallic,
                "roughnessFactor": roughness,
            },
        })
    while len(blob) % 4:
        blob.append(0)
    document = {
        "asset": {"version": "2.0", "generator": "tools.models.cartridge"},
        "scene": 0,
        "scenes": [{"name": "Scene", "nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "Cartridge"}],
        "meshes": [{"name": "Cartridge", "primitives": mesh_primitives}],
        "materials": materials,
        "accessors": accessors,
        "bufferViews": views,
        "buffers": [{"byteLength": len(blob)}],
    }
    text = json.dumps(document, separators=(",", ":")).encode("utf-8")
    text += b" " * (-len(text) % 4)
    total = 12 + 8 + len(text) + 8 + len(blob)
    return b"".join((
        struct.pack("<4sII", b"glTF", 2, total),
        struct.pack("<I4s", len(text), b"JSON"), text,
        struct.pack("<I4s", len(blob), b"BIN\x00"), bytes(blob),
    ))


def report(primitives: list[dict], out: Path) -> dict:
    low = np.min([item["vertices"].min(axis=0) for item in primitives], axis=0)
    high = np.max([item["vertices"].max(axis=0) for item in primitives], axis=0)
    return {
        "out": str(out),
        "bytes": out.stat().st_size,
        "triangles": int(sum(len(item["faces"]) for item in primitives)),
        "by_material": {item["name"]: int(len(item["faces"])) for item in primitives},
        "low": [round(float(value), 4) for value in low],
        "high": [round(float(value), 4) for value in high],
    }
