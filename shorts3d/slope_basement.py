"""
비탈 지하실 쇼츠 — Blender 3D 단면도 애니메이션 자동 생성 스크립트
=====================================================================

"문제 → 해결 → 이름 붙이기"를 반복하는 건축 과정 쇼츠(9:16, 약 93초)를
코드만으로 만들어 줍니다. 지형 단면, 집, 단계별로 튀어나오는 구조물,
주황색 강조 테두리, 화살표, 카메라 이동, 캐릭터(사람, 멧돼지, 고양이)까지
전부 자동으로 생성됩니다.

실행 방법
---------
1) Blender 앱(4.2 이상 / 5.x 권장)에서:
   Scripting 탭 → 이 파일 열기 → ▶ Run Script  → 장면이 만들어짐
   → Render > Render Animation 으로 영상 출력

2) 명령줄(백그라운드):
   blender -b -P slope_basement.py -- --mode final --out ./out
   blender -b -P slope_basement.py -- --mode stills --out ./out   (확인용 스틸 컷)

3) pip 의 bpy 모듈로:
   python slope_basement.py --mode stills --out ./out

옵션
----
--mode   build(장면만 만들고 .blend 저장) | stills(주요 장면 PNG)
         | preview(저해상도 10fps 미리보기 mp4) | final(전체 렌더)
--engine cycles(기본, 고품질) | eevee(GPU 필요, 매우 빠름)
--out    출력 폴더 (기본 ./out)
--pct    해상도 % (기본 100 = 1080x1920, 미리보기는 50)
--samples Cycles 샘플 수 (기본 64)
--font   한글 폰트 경로. 지정하면 "옹벽" 같은 키워드 자막을 화면에 직접 렌더
         (예: Windows  C:/Windows/Fonts/malgunbd.ttf)

출력
----
out/slope_basement.blend   장면 파일 (Blender로 열어 수정 가능)
out/narration.txt          AI 음성(TTS)에 넣을 내레이션 대본
out/captions.srt           CapCut 등에 넣을 자막 파일 (시간 포함)
out/still_XX.png / frames  렌더 결과

다른 주제로 바꾸려면
--------------------
맨 아래 STEPS(대본과 시간)를 고치고, build_story()의 각 단계 함수를 바꾸면 됩니다.
TTS 음성을 먼저 만든 뒤 실제 문장 길이에 맞춰 STEPS의 t(초)를 조정하세요.
"""

import bpy
import bmesh
import math
import os
import random
import sys
import argparse
from mathutils import Vector, Matrix

FPS = 30
DURATION = 93.0


def F(t):
    """초 → 프레임"""
    return int(round(t * FPS)) + 1


# =====================================================================
# 대본 (내레이션 / 자막 / 시간)  ← 여기만 고쳐도 자막·TTS 대본이 바뀜
# =====================================================================
STEPS = [
    dict(t=0.0, say="언덕 경사면에 집을 짓고, 그 아래 흙을 파내면 지하실이 생깁니다."),
    dict(t=4.0, say="그런데 평지처럼 네 면을 전부 파려니 흙더미만 산처럼 쌓입니다. "
                    "그래서 언덕 쪽만 파고, 낮은 쪽은 원래 땅 높이를 그대로 씁니다."),
    dict(t=12.0, say="하지만 언덕 흙이 벽을 꾹꾹 밀어서 벽이 배불뚝이처럼 휘어 버립니다. "
                     "그래서 발을 넓게 뻗은 ㄴ자 벽을 세우고, 발 위에 흙을 얹어 무게로 버팁니다. "
                     "이게 바로 옹벽입니다.", keyword="옹벽", kt=20.5),
    dict(t=23.0, say="하지만 비만 오면 언덕 물이 벽을 타고 스며들어 바닥이 흥건해집니다. "
                     "그래서 벽 뒤에 자갈을 채우고 구멍 뚫린 관을 묻어 물을 마당으로 흘려보냅니다. "
                     "이게 배수관입니다.", keyword="배수관", kt=31.5),
    dict(t=33.0, say="하지만 폭우가 그친 다음 날, 언덕 위 바위가 데굴데굴 굴러와 집 뒤에 쾅! "
                     "그래서 집 뒤 언덕에 도랑을 파고 돌담을 둘러 물과 돌이 옆으로 비켜 가게 합니다. "
                     "이게 산마루 도랑입니다.", keyword="산마루 도랑", kt=43.5),
    dict(t=45.0, say="하지만 해가 안 드는 지하는 늘 눅눅해서 벽마다 곰팡이가 핍니다. "
                     "그래서 낮은 쪽 벽엔 큰 창문을, 높은 쪽 벽 꼭대기엔 작은 바람 구멍을 냅니다. "
                     "창으로 들어온 바람이 위로 빠져나가며 곰팡내까지 싹 데려갑니다."),
    dict(t=58.0, say="하지만 무거운 짐을 들고 1층 계단으로 빙 돌아 내려가려니 허리가 휩니다. "
                     "그래서 낮은 쪽 벽에 문을 달아 마당에서 곧장 들어가게 합니다. "
                     "이게 지하 현관입니다.", keyword="지하 현관", kt=65.0),
    dict(t=66.5, say="하지만 문을 열어 둔 틈에 멧돼지가 지하로 쿵쾅쿵쾅 쳐들어옵니다. "
                     "그래서 멧돼지를 내쫓고 문 안쪽에 굵은 나무 빗장을 덜컥 겁니다."),
    dict(t=74.0, say="그리고 위층에 현관이 따로 있는 건 실수가 아닙니다. "
                     "언덕 쪽에선 1층으로, 마당 쪽에선 지하로, 두 층 모두 땅에서 바로 드나드는 겁니다."),
    dict(t=82.0, say="여기에 장작 난로와 작업대, 창가에서 졸고 있는 고양이까지 더하면… "
                     "축하합니다! 비탈 지하실이 완성됐습니다.", keyword="완성!", kt=90.0),
]

# 카메라 프리셋: (카메라 위치, 바라보는 점)
CAMS = {
    "wide":     ((0, -31, 6.5),   (0, 0, 4.2)),
    "hill":     ((-5, -17, 3.2),  (-5.5, 0, 2.0)),
    "mid":      ((1.5, -27, 4.5), (1.5, 0, 2.4)),
    "aerial":   ((-3, -13, 15),   (-11, 5, 4)),
    "interior": ((1, -9, 2.5),    (-1, 4, 1.8)),
    "yard":     ((20, -6, 4.2),   (5, 4.5, 1.6)),
    "threeq":   ((-19, -20, 12),  (-3, 3, 3.5)),
}
# (시작 초, 프리셋) — 0.6초 동안 부드럽게 이동
SHOTS = [(0, "wide"), (12, "hill"), (27.5, "mid"), (33, "aerial"), (44.6, "mid"),
         (45.3, "interior"), (49.0, "yard"), (52.4, "interior"), (58.0, "yard"),
         (66.5, "mid"), (74.0, "threeq"), (77.4, "yard"), (80.0, "wide"),
         (82.2, "interior"), (88.5, "wide")]

# 확인용 스틸 컷 시점
STILL_TIMES = [1.0, 3.5, 8.0, 15.5, 20.5, 25.5, 30.5, 36.0, 43.5, 47.5,
               50.5, 55.0, 61.0, 64.5, 69.5, 73.8, 76.0, 79.0, 86.0, 91.0]

# =====================================================================
# 기본 헬퍼
# =====================================================================
SCENE = None
COLL = None
M = {}  # 재질 캐시


def set_interp(kind):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = kind


def key(obj, path, frame, value=None, interp="BEZIER", index=-1):
    if value is not None:
        setattr(obj, path, value)
    set_interp(interp)
    obj.keyframe_insert(data_path=path, frame=frame, index=index)


def _vis(obj, frame, hidden):
    for o in [obj] + list(obj.children_recursive):
        if o.get("is_outline") and o is not obj:
            continue
        o.hide_render = hidden
        o.hide_viewport = hidden
        set_interp("CONSTANT")
        o.keyframe_insert("hide_render", frame=frame)
        o.keyframe_insert("hide_viewport", frame=frame)


def show_at(obj, t):
    _vis(obj, 0, True)
    _vis(obj, F(t), False)


def hide_at(obj, t):
    _vis(obj, F(t), True)


def pop(obj, t, dur=0.45, axes="xyz"):
    """t초에 '뿅' 하고 튀어나오는 등장 (BACK 이징)"""
    tgt = Vector(obj.get("base_scale", obj.scale))
    obj["base_scale"] = list(tgt)
    s0 = Vector([0.001 if a in axes else tgt[i] for i, a in enumerate("xyz")])
    show_at(obj, t)
    key(obj, "scale", F(t), s0, "BACK")
    key(obj, "scale", F(t + dur), tgt, "BEZIER")


def shrink(obj, t, dur=0.4, hide=True):
    tgt = Vector(obj.get("base_scale", obj.scale))
    key(obj, "scale", F(t), tgt, "QUAD")
    key(obj, "scale", F(t + dur), (0.001, 0.001, 0.001), "CONSTANT")
    if hide:
        hide_at(obj, t + dur)


def path(obj, pts, face=True):
    """pts = [(초, (x,y,z)), ...] 순서대로 이동. face=True면 진행 방향을 바라봄(모델은 +X가 정면)"""
    for i, (t, p) in enumerate(pts):
        key(obj, "location", F(t), p, "LINEAR")
        if face and i + 1 < len(pts):
            d = Vector(pts[i + 1][1]) - Vector(p)
            if d.xy.length > 0.01:
                key(obj, "rotation_euler", F(t), (0, 0, math.atan2(d.y, d.x)), "CONSTANT")


def attach(child, parent, keep=True):
    child.parent = parent
    if keep:
        child.matrix_parent_inverse = parent.matrix_basis.inverted()
    return child


def empty(name, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.3
    COLL.objects.link(e)
    e.location = loc
    return e


# ---------------- 재질 ----------------
def mat(name, color, rough=0.7, emit=0.0, alpha=1.0):
    if name in M:
        return M[name]
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            try:
                setattr(m, attr, val)
            except Exception:
                pass
    m.diffuse_color = (*color, 1)
    M[name] = m
    return m


def nmat(name, c1, c2, scale=5.0, rough=0.9, detail=4.0, const=False):
    """노이즈 무늬 재질 (흙, 잔디, 자갈)"""
    if name in M:
        return M[name]
    m = mat(name, c1, rough)
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    el = cr.color_ramp.elements
    el[0].position, el[0].color = 0.42, (*c2, 1)
    el[1].position, el[1].color = 0.58, (*c1, 1)
    if const:
        cr.color_ramp.interpolation = "CONSTANT"
    nt.links.new(nz.outputs["Fac"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], b.inputs["Base Color"])
    return m


def build_materials():
    nmat("soil", (0.64, 0.34, 0.17), (0.50, 0.25, 0.12), scale=0.35, detail=2.0)
    nmat("grass", (0.30, 0.58, 0.16), (0.22, 0.46, 0.12), scale=6)
    nmat("gravel", (0.62, 0.60, 0.56), (0.34, 0.33, 0.31), scale=28, const=True)
    nmat("rock", (0.50, 0.49, 0.47), (0.36, 0.35, 0.34), scale=4)
    mat("concrete", (0.66, 0.66, 0.63), 0.85)
    mat("concrete2", (0.74, 0.74, 0.71), 0.85)
    mat("plaster", (0.86, 0.82, 0.75))
    mat("inwall", (0.80, 0.66, 0.50))
    mat("wood", (0.42, 0.25, 0.12), 0.6)
    mat("floorwood", (0.56, 0.37, 0.21), 0.5)
    mat("roof", (0.10, 0.10, 0.12), 0.6)
    mat("dark", (0.03, 0.03, 0.03), 0.9)
    mat("water", (0.15, 0.45, 0.95), 0.05, emit=0.4, alpha=0.75)
    mat("glass", (0.65, 0.85, 1.0), 0.05, emit=0.6, alpha=0.5)
    mat("white", (0.92, 0.92, 0.92), 0.5)
    mat("glow", (1.0, 0.42, 0.05), 0.5, emit=8.0)          # 주황 강조
    mat("blueglow", (0.2, 0.6, 1.0), 0.5, emit=6.0)        # 물 화살표
    mat("windglow", (0.7, 0.95, 1.0), 0.5, emit=6.0)       # 바람 화살표
    mat("mold", (0.12, 0.22, 0.10), 0.95)
    mat("trunk", (0.30, 0.20, 0.12))
    mat("leaf1", (0.30, 0.52, 0.18))
    mat("leaf2", (0.42, 0.60, 0.22))
    mat("cloud", (1.0, 1.0, 1.0), 1.0)
    mat("shirt", (0.15, 0.35, 0.70))
    mat("pants", (0.15, 0.15, 0.20))
    mat("skin", (0.85, 0.65, 0.50))
    mat("hair", (0.08, 0.06, 0.05))
    mat("boar", (0.22, 0.15, 0.10), 0.95)
    mat("snout", (0.55, 0.38, 0.33))
    mat("cat", (0.90, 0.52, 0.18))
    mat("sofa", (0.25, 0.45, 0.65))
    mat("rug", (0.70, 0.20, 0.15))
    mat("fire", (1.0, 0.45, 0.1), 0.5, emit=15.0)
    mat("box", (0.70, 0.52, 0.30))
    mat("labelw", (1, 1, 1), 1.0, emit=3.0)
    mat("labelb", (0, 0, 0), 1.0)


# ---------------- 도형 ----------------
def mesh_obj(name, verts, faces, mats, face_mat=None, smooth=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    for m in mats:
        me.materials.append(M[m] if isinstance(m, str) else m)
    if face_mat:
        for i, p in enumerate(me.polygons):
            p.material_index = face_mat[i]
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    COLL.objects.link(ob)
    return ob


def box(name, mn, mx, m, pivot="center"):
    """mn~mx 범위의 상자. pivot: center|bottom|top|left|right|front|back 또는 좌표"""
    mn, mx = Vector(mn), Vector(mx)
    c = (mn + mx) / 2
    piv = {
        "center": c,
        "bottom": Vector((c.x, c.y, mn.z)),
        "top": Vector((c.x, c.y, mx.z)),
        "left": Vector((mn.x, c.y, c.z)),
        "right": Vector((mx.x, c.y, c.z)),
        "front": Vector((c.x, mn.y, c.z)),
        "back": Vector((c.x, mx.y, c.z)),
    }.get(pivot) if isinstance(pivot, str) else Vector(pivot)
    vs = [Vector((x, y, z)) - piv for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    ob = mesh_obj(name, vs, faces, [m])
    ob.location = piv
    return ob


def _active(name, m):
    ob = bpy.context.active_object
    ob.name = name
    ob.data.materials.append(M[m] if isinstance(m, str) else m)
    return ob


def sphere(name, loc, r, m, scale=(1, 1, 1), seg=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=r, location=loc)
    ob = _active(name, m)
    ob.scale = scale
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def ico(name, loc, r, m, scale=(1, 1, 1), sub=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc)
    ob = _active(name, m)
    ob.scale = scale
    return ob


def cyl(name, a, b, r, m, verts=16):
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length, location=(a + b) / 2)
    ob = _active(name, m)
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    for p in ob.data.polygons:
        if len(p.vertices) == 4:
            p.use_smooth = True
    return ob


def cone(name, loc, r, h, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=r, depth=h, location=loc, rotation=rot)
    return _active(name, m)


def arrow(name, a, b, m, r=0.09):
    """a→b 방향 화살표 (그룹 empty 반환, empty 원점 = 꼬리)"""
    a, b = Vector(a), Vector(b)
    d = b - a
    L = d.length
    e = empty(name, a)
    e.rotation_euler = d.to_track_quat("X", "Z").to_euler()
    sh = cyl(name + "_s", (0, 0, 0), (L * 0.7, 0, 0), r, m, 12)
    hd = cone(name + "_h", (L * 0.85, 0, 0), r * 2.6, L * 0.3, m, rot=(0, math.pi / 2, 0))
    attach(sh, e, keep=False)
    attach(hd, e, keep=False)
    return e


def group(name, objs, loc=(0, 0, 0)):
    g = empty(name, loc)
    for o in objs:
        attach(o, g)
    return g


def outline(obj, t, dur=2.5, thick=0.07):
    """새로 생긴 구조물에 주황색 빛나는 테두리 (t초부터 dur초 동안)"""
    srcs = [o for o in [obj] + list(obj.children_recursive)
            if o.type == "MESH" and not o.get("is_outline")]
    for s in srcs:
        o = s.copy()
        o.animation_data_clear()
        o.modifiers.clear()
        COLL.objects.link(o)
        o.parent = s
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.location, o.rotation_euler, o.scale = (0, 0, 0), (0, 0, 0), (1, 1, 1)
        o["is_outline"] = True
        mod = o.modifiers.new("wf", "WIREFRAME")
        mod.thickness = thick
        mod.use_even_offset = True
        for slot in o.material_slots:
            slot.link = "OBJECT"
            slot.material = M["glow"]
        show_at(o, t)
        hide_at(o, t + dur)


def enable_mod_at(mod, t):
    """모디파이어를 t초부터 켬 (그 전엔 꺼짐)"""
    set_interp("CONSTANT")
    mod.show_render = mod.show_viewport = False
    mod.keyframe_insert("show_render", frame=1)
    mod.keyframe_insert("show_viewport", frame=1)
    mod.show_render = mod.show_viewport = True
    mod.keyframe_insert("show_render", frame=F(t))
    mod.keyframe_insert("show_viewport", frame=F(t))


def boolean_cut(target, cutter, name="cut"):
    cutter.display_type = "WIRE"
    cutter.hide_render = True
    mod = target.modifiers.new(name, "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    try:
        mod.solver = "EXACT"
    except Exception:
        pass
    return mod


# =====================================================================
# 지형
# =====================================================================
def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ztop(x):
    """지형 높이: 오른쪽(마당)=0, 집 아래 경사, 왼쪽 언덕 위로 올라감"""
    if x >= 5.5:
        return 0.0
    if x >= -5.0:
        return 3.5 * (1 - smooth((x + 5) / 10.5))
    if x >= -9.0:
        return 3.5
    return 3.5 + 5.5 * smooth((-9 - x) / 21)


def build_terrain():
    X0, X1, D, BOT, STEP, GR = -45.0, 45.0, 150.0, -25.0, 0.25, 0.35
    xs = [X0 + i * STEP for i in range(int((X1 - X0) / STEP) + 1)]
    v, f, fm = [], [], []
    for x in xs:
        z = ztop(x)
        v += [(x, 0, z), (x, 0, z - GR), (x, 0, BOT), (x, D, z), (x, D, BOT)]
    for i in range(len(xs) - 1):
        T, Mi, B, Tb, Bb = [5 * i + k for k in range(5)]
        T2, M2, B2, Tb2, Bb2 = [5 * (i + 1) + k for k in range(5)]
        f += [(Mi, M2, T2, T), (B, B2, M2, Mi), (T, T2, Tb2, Tb), (Bb, Tb, Tb2, Bb2), (B, Bb, Bb2, B2)]
        fm += [1, 0, 1, 0, 0]
    n = len(xs) - 1
    f += [(2, 1, 0, 3, 4), (5 * n + 2, 5 * n + 1, 5 * n, 5 * n + 3, 5 * n + 4)]
    fm += [0, 0]
    return mesh_obj("Terrain", v, f, ["soil", "grass"], fm)


def build_scenery():
    rnd = random.Random(7)
    n = 0
    while n < 55:
        x, y = rnd.uniform(-40, 40), rnd.uniform(2, 45)
        if abs(x) < 8 and y < 12:
            continue
        if -13.5 < x < -9.5:        # 도랑 자리
            continue
        if x < -5 and y < 6:        # 바위 굴러가는 길
            continue
        z = ztop(x)
        h = rnd.uniform(1.2, 2.0)
        tr = cyl(f"trunk{n}", (x, y, z), (x, y, z + h), 0.14, "trunk", 8)
        cr = ico(f"crown{n}", (x, y, z + h + 0.9), rnd.uniform(0.9, 1.5),
                 rnd.choice(["leaf1", "leaf2"]), scale=(1, 1, rnd.uniform(1.1, 1.6)))
        n += 1
    for c in range(8):
        cx, cz = rnd.uniform(-60, 60), rnd.uniform(28, 48)
        for k in range(4):
            sphere(f"cloud{c}_{k}", (cx + k * 3.2 - 5, 170, cz + rnd.uniform(-1, 1.5)),
                   rnd.uniform(3, 5), "cloud", scale=(1.4, 0.6, 0.8), seg=16)


def build_world():
    w = bpy.data.worlds.new("Sky")
    SCENE.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    el = ramp.color_ramp.elements
    el[0].position, el[0].color = 0.3, (0.78, 0.87, 0.96, 1)
    el[1].position, el[1].color = 1.0, (0.28, 0.52, 0.88, 1)
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    bg_amb = nt.nodes.new("ShaderNodeBackground")
    bg_amb.inputs["Color"].default_value = (0.62, 0.72, 0.86, 1)
    bg_amb.inputs["Strength"].default_value = 0.9
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tc.outputs["Window"], sep.inputs[0])
    nt.links.new(sep.outputs["Y"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg_cam.inputs["Color"])
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(bg_amb.outputs[0], mix.inputs[1])
    nt.links.new(bg_cam.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])

    sun_d = bpy.data.lights.new("Sun", "SUN")
    sun_d.energy = 3.5
    sun_d.angle = math.radians(3)
    sun = bpy.data.objects.new("Sun", sun_d)
    COLL.objects.link(sun)
    sun.rotation_euler = Vector((0, 0, -1)).rotation_difference(
        Vector((0.35, 0.55, -0.75)).normalized()).to_euler()


# =====================================================================
# 캐릭터
# =====================================================================
def person(name):
    parts = [
        cyl(name + "_l1", (0, 0.12, 0), (0, 0.12, 0.85), 0.09, "pants", 10),
        cyl(name + "_l2", (0, -0.12, 0), (0, -0.12, 0.85), 0.09, "pants", 10),
        box(name + "_body", (-0.15, -0.24, 0.82), (0.15, 0.24, 1.5), "shirt"),
        cyl(name + "_a1", (0, 0.31, 1.45), (0.08, 0.33, 0.88), 0.07, "shirt", 10),
        cyl(name + "_a2", (0, -0.31, 1.45), (0.08, -0.33, 0.88), 0.07, "shirt", 10),
        sphere(name + "_head", (0, 0, 1.72), 0.17, "skin"),
        sphere(name + "_hair", (-0.03, 0, 1.78), 0.175, "hair", scale=(1, 1, 0.6)),
    ]
    return group(name, parts)


def boar(name):
    parts = [sphere(name + "_body", (0, 0, 0.62), 1.0, "boar", scale=(0.9, 0.42, 0.42)),
             sphere(name + "_head", (0.85, 0, 0.62), 0.3, "boar", scale=(1.15, 0.85, 0.9)),
             cyl(name + "_snout", (1.1, 0, 0.56), (1.33, 0, 0.56), 0.11, "snout"),
             cone(name + "_t1", (1.2, 0.12, 0.5), 0.03, 0.18, "white", rot=(0, -0.6, 0)),
             cone(name + "_t2", (1.2, -0.12, 0.5), 0.03, 0.18, "white", rot=(0, -0.6, 0)),
             cone(name + "_e1", (0.78, 0.16, 0.92), 0.07, 0.18, "boar"),
             cone(name + "_e2", (0.78, -0.16, 0.92), 0.07, 0.18, "boar")]
    for i, (lx, ly) in enumerate([(0.5, 0.2), (0.5, -0.2), (-0.5, 0.2), (-0.5, -0.2)]):
        parts.append(cyl(f"{name}_leg{i}", (lx, ly, 0), (lx, ly, 0.4), 0.07, "boar", 8))
    return group(name, parts)


def cat(name):
    parts = [sphere(name + "_body", (0, 0, 0.12), 1.0, "cat", scale=(0.28, 0.16, 0.12)),
             sphere(name + "_head", (0.27, 0, 0.17), 0.11, "cat"),
             cone(name + "_e1", (0.28, 0.06, 0.29), 0.04, 0.08, "cat"),
             cone(name + "_e2", (0.28, -0.06, 0.29), 0.04, 0.08, "cat"),
             cyl(name + "_tail", (-0.25, 0, 0.1), (-0.42, 0.14, 0.05), 0.035, "cat", 8)]
    return group(name, parts)


# =====================================================================
# 집과 지하 구조물 + 단계별 애니메이션
# =====================================================================
def build_story():
    terrain = build_terrain()

    # ---------- 집 (위에서 떨어져 내려앉음) ----------
    H = []
    H.append(box("h_slab", (-5.4, 0, 3.5), (5.4, 8, 3.8), "concrete"))
    H.append(box("h_floor", (-5.1, 0, 3.8), (5.1, 7.7, 3.86), "floorwood"))
    H.append(box("h_back", (-5.4, 7.7, 3.86), (5.4, 8.0, 7.0), "inwall"))
    H.append(box("h_left", (-5.4, 0, 3.86), (-5.1, 8, 7.0), "plaster"))
    H.append(box("h_right", (5.1, 0, 3.86), (5.4, 8, 7.0), "plaster"))
    H.append(box("h_ceil", (-5.4, 0, 7.0), (5.4, 8, 7.15), "concrete"))
    H.append(mesh_obj("h_gable", [(-5.4, 7.7, 7.15), (5.4, 7.7, 7.15), (0, 7.7, 8.9),
                                  (-5.4, 8.0, 7.15), (5.4, 8.0, 7.15), (0, 8.0, 8.9)],
                      [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], ["plaster"]))
    L = math.hypot(6.2, 2.4)
    a = math.atan2(2.4, 6.2)
    for side, sgn in (("l", -1), ("r", 1)):
        r = box("h_roof" + side, (0, -0.4, -0.3) if sgn > 0 else (-L, -0.4, -0.3),
                (L, 8.4, 0) if sgn > 0 else (0, 8.4, 0), "roof", pivot=(0, 0, 0))
        r.location = (0, 0, 9.15)
        r.rotation_euler = (0, a * sgn, 0)
        H.append(r)
    # 실내 소품
    H.append(box("sofa", (-3.0, 6.6, 3.86), (-0.6, 7.6, 4.3), "sofa"))
    H.append(box("sofa_b", (-3.0, 7.3, 4.3), (-0.6, 7.6, 4.9), "sofa"))
    H.append(box("rug", (-3.5, 5.0, 3.86), (0.2, 7.6, 3.88), "rug"))
    H.append(box("table", (-2.3, 5.5, 4.1), (-1.2, 6.2, 4.25), "wood"))
    H.append(cyl("lamp_p", (0.4, 7.3, 3.86), (0.4, 7.3, 5.2), 0.03, "dark", 8))
    H.append(cone("lamp_s", (0.4, 7.3, 5.3), 0.25, 0.3, "white"))
    H.append(box("shelf", (2.0, 7.3, 4.6), (4.6, 7.7, 5.0), "wood"))
    H.append(box("pic1", (-2.6, 7.66, 5.4), (-1.6, 7.7, 6.2), "rug"))
    H.append(box("pic2", (-1.3, 7.66, 5.6), (-0.7, 7.7, 6.2), "sofa"))
    updoor = box("up_door", (-5.47, 3.2, 3.86), (-5.38, 4.6, 5.95), "wood")
    H.append(updoor)
    # 기둥 (땅 파기 전까지)
    posts = []
    for x in (0.0, 2.5, 4.6):
        for y in (0.3, 7.6):
            posts.append(cyl(f"post{x}_{y}", (x, y, ztop(x) - 0.2), (x, y, 3.5), 0.12, "wood", 10))
    house = group("House", H + posts)
    key(house, "location", F(0.0), (0, 0, 22), "BOUNCE")
    key(house, "location", F(1.4), (0, 0, 0), "BEZIER")
    for p in posts:
        hide_at(p, 4.0)

    # ---------- 1. 땅 파기 ----------
    dig = box("cut_dig", (-5.0, -1.0, 0.0), (6.0, 8.0, 3.5), "dark", pivot="right")
    boolean_cut(terrain, dig, "dig")
    key(dig, "scale", F(1.6), (0.01, 1, 1), "QUAD")
    key(dig, "scale", F(3.8), (1, 1, 1), "BEZIER")

    pile = ico("dirt_pile", (10.5, 2.5, 0), 1.0, "soil", scale=(3.0, 2.2, 2.2), sub=3)
    pop(pile, 4.6, dur=2.2)
    shrink(pile, 10.8)

    shell = [box("b_floor", (-5.0, 0, -0.2), (5.3, 8, 0.3), "concrete", pivot="bottom"),
             box("b_back", (-5.0, 7.7, 0.3), (5.3, 8.0, 3.5), "concrete", pivot="bottom")]
    low = box("b_low", (4.9, 0, 0.3), (5.3, 8, 3.5), "concrete", pivot="bottom")
    shell.append(low)
    for i, s in enumerate(shell):
        pop(s, 9.0 + i * 0.35, axes="z")

    worker = person("worker")
    worker.location = (-1.0, 3.0, 0.3)
    pop(worker, 10.4)

    # ---------- 2. 옹벽 ----------
    slabs = []
    for k in range(8):
        s = box(f"thin{k}", (-5.3, 0, 0.3 + k * 0.4), (-4.95, 7.7, 0.7 + k * 0.4), "concrete")
        slabs.append(s)
        pop(s, 12.2 + k * 0.06)
        bulge = 0.55 * math.sin(math.pi * (k + 0.5) / 8)
        key(s, "location", F(14.2), None, "QUAD")
        key(s, "location", F(16.2), s.location + Vector((bulge, 0, 0)), "BEZIER")
        hide_at(s, 17.2)
    push = [arrow(f"push{i}", (-9.0, -0.15, z), (-5.6, -0.15, z), M["glow"]) for i, z in enumerate((1.0, 2.0, 3.0))]
    for i, ar in enumerate(push):
        pop(ar, 13.0 + i * 0.15)
        key(ar, "location", F(14.2), None, "SINE")
        key(ar, "location", F(16.0), ar.location + Vector((0.5, 0, 0)), "BEZIER")
        shrink(ar, 17.0)

    lwall = group("Lwall", [box("lw_stem", (-5.35, -0.03, 0.3), (-4.95, 7.7, 3.5), "concrete2"),
                            box("lw_foot", (-8.0, -0.03, -0.4), (-4.95, 7.7, 0.3), "concrete2")],
                  loc=(-5.15, 0, -0.4))
    pop(lwall, 17.2, dur=0.6, axes="z")
    outline(lwall, 17.4, 3.5)
    weight = [arrow(f"weight{i}", (x, -0.15, 3.0), (x, -0.15, 0.7), M["glow"]) for i, x in enumerate((-7.3, -6.2))]
    for i, ar in enumerate(weight):
        pop(ar, 18.6 + i * 0.2)
        shrink(ar, 22.0)

    # ---------- 3. 배수관 ----------
    seep = [arrow(f"seep{i}", (-9.5, -0.15, z + 0.8), (-5.7, -0.15, z), M["blueglow"]) for i, z in enumerate((1.2, 2.2))]
    for i, ar in enumerate(seep):
        pop(ar, 23.4 + i * 0.2)
        shrink(ar, 27.0)
    drips = []
    for d in range(3):
        dr = sphere(f"drip{d}", (-4.6, 1.0 + d * 0.8, 3.3), 0.09, "water", scale=(1, 1, 1.4), seg=12)
        show_at(dr, 24.0)
        for c in range(4):
            t0 = 24.0 + d * 0.25 + c * 0.75
            key(dr, "location", F(t0), (-4.6, 1.0 + d * 0.8, 3.3), "QUAD")
            key(dr, "location", F(t0 + 0.6), (-4.6, 1.0 + d * 0.8, 0.35), "CONSTANT")
        hide_at(dr, 27.2)
        drips.append(dr)
    puddle = cyl("puddle", (-2.3, 3.0, 0.3), (-2.3, 3.0, 0.34), 1.0, "water", 32)
    puddle.scale = (2.0, 1.4, 1)
    pop(puddle, 24.6, dur=2.0)
    shrink(puddle, 30.5, dur=1.2)

    gravel = box("gravel", (-6.4, -0.03, 0.3), (-5.36, 7.7, 3.2), "gravel", pivot="bottom")
    pop(gravel, 27.4, axes="z", dur=0.6)
    outline(gravel, 27.6, 2.0)
    pipe = group("Pipe", [cyl("pipe_v", (-5.9, -0.12, 0.45), (-5.9, -0.12, -0.45), 0.14, "white"),
                          cyl("pipe_h", (-5.9, -0.12, -0.45), (9.5, -0.12, -0.45), 0.14, "white")],
                 loc=(-5.9, 0, -0.45))
    pop(pipe, 28.4, axes="x", dur=0.7)
    outline(pipe, 28.6, 3.0)
    for i in range(3):
        ar = arrow(f"flow{i}", (0, -0.35, -0.45), (1.2, -0.35, -0.45), M["blueglow"], r=0.07)
        show_at(ar, 29.2)
        for c in range(2):
            t0 = 29.2 + c * 1.8 + i * 0.6
            key(ar, "location", F(t0), (-5.6, -0.35, -0.45), "LINEAR")
            key(ar, "location", F(t0 + 1.8), (8.5, -0.35, -0.45), "CONSTANT")
        hide_at(ar, 33.0)

    # ---------- 4. 산마루 도랑 ----------
    def roll(rock, x0, x1, t0, t1, r=0.6, y=3.0, steps=24):
        show_at(rock, t0)
        for i in range(steps + 1):
            u = i / steps
            x = x0 + (x1 - x0) * (u ** 1.6)
            key(rock, "location", F(t0 + (t1 - t0) * u), (x, y, ztop(x) + r), "LINEAR")
            key(rock, "rotation_euler", F(t0 + (t1 - t0) * u), (0, (x - x0) / r, 0), "LINEAR")

    rock = ico("rock1", (-28, 3, ztop(-28) + 0.6), 0.6, "rock", sub=2)
    roll(rock, -28, -5.95, 33.8, 37.4)
    key(rock, "location", F(37.8), (-6.8, 3.0, 3.5 + 0.6), "BEZIER")
    shrink(rock, 39.0)

    zb = ztop(-10.8) - 0.9
    trench = box("cut_trench", (-12.2, -1.0, zb), (-10.8, 151, ztop(-12.2) + 3), "dark", pivot="front")
    enable_mod_at(boolean_cut(terrain, trench, "trench"), 39.3)
    key(trench, "scale", F(39.3), (1, 0.01, 1), "QUAD")
    key(trench, "scale", F(41.3), (1, 1, 1), "BEZIER")
    tw = box("trench_water", (-12.1, -0.02, zb), (-10.9, 150, zb + 0.25), "water", pivot="front")
    pop(tw, 42.4, axes="y", dur=1.0)
    for k in range(36):
        x = -10.35
        st = box(f"stone{k}", (x - 0.3, k * 1.0, ztop(x) - 0.1), (x + 0.3, k * 1.0 + 0.9, ztop(x) + 0.6),
                 "rock", pivot="bottom")
        pop(st, 40.6 + k * 0.04, axes="z", dur=0.35)
        if k < 6:
            outline(st, 41.0, 2.5, thick=0.05)
    rock2 = ico("rock2", (-28, 3, 0), 0.5, "rock", sub=2)
    roll(rock2, -28, -11.5, 42.6, 44.3, r=0.5)

    # ---------- 5. 환기 (곰팡이 → 창문 + 바람 구멍) ----------
    rnd = random.Random(3)
    molds = []
    for k in range(12):
        x, z = rnd.uniform(-4.2, 4.2), rnd.uniform(0.6, 3.1)
        mo = sphere(f"mold{k}", (x, 7.68, z), rnd.uniform(0.18, 0.4), "mold", scale=(1, 0.06, 0.8), seg=12)
        pop(mo, 45.6 + k * 0.15, dur=0.6)
        shrink(mo, 55.5 + k * 0.08, dur=0.6)
        molds.append(mo)

    window = group("Window", [box("win_glass", (4.85, -0.04, 1.3), (5.36, 2.6, 2.9), "glass"),
                              box("win_f1", (4.83, -0.05, 1.22), (5.4, 2.68, 1.3), "white"),
                              box("win_f2", (4.83, -0.05, 2.9), (5.4, 2.68, 2.98), "white"),
                              box("sill", (4.25, 0.2, 1.2), (4.85, 2.5, 1.3), "wood")],
                   loc=(5.1, 1.3, 2.1))
    pop(window, 49.6, dur=0.5)
    outline(window, 49.8, 2.5)
    vent = box("vent", (-5.42, -0.05, 3.0), (-4.88, 1.2, 3.35), "dark")
    pop(vent, 51.3)
    outline(vent, 51.4, 2.5, thick=0.05)
    wa, wb = Vector((4.5, -0.3, 2.0)), Vector((-4.6, -0.3, 3.15))
    wd = (wb - wa).normalized()
    for i in range(4):
        ar = arrow(f"wind{i}", (0, 0, 0), tuple(wd * 1.4), M["windglow"], r=0.07)
        show_at(ar, 53.0)
        for c in range(2):
            t0 = 53.0 + c * 2.0 + i * 0.5
            key(ar, "location", F(t0), tuple(wa), "LINEAR")
            key(ar, "location", F(t0 + 2.0), tuple(wb - wd * 1.4), "CONSTANT")
        hide_at(ar, 57.6)

    # ---------- 6. 지하 현관 ----------
    hole = box("cut_door", (4.6, 4.65, 0.3), (5.7, 6.05, 2.45), "dark")
    enable_mod_at(boolean_cut(low, hole, "doorhole"), 62.0)

    door = group("Door", [box("door_p", (5.3, 4.6, 0.3), (5.42, 6.1, 2.5), "wood"),
                          sphere("door_k", (5.46, 5.85, 1.4), 0.06, "white", seg=10)],
                 loc=(5.36, 4.6, 0.3))
    pop(door, 62.0, dur=0.5)
    outline(door, 62.2, 2.5)
    key(door, "rotation_euler", F(63.2), (0, 0, 0), "QUAD")
    key(door, "rotation_euler", F(63.8), (0, 0, -1.75), "BEZIER")
    key(door, "rotation_euler", F(72.6), (0, 0, -1.75), "QUAD")
    key(door, "rotation_euler", F(73.0), (0, 0, 0), "BEZIER")

    cargo = box("cargo", (0.25, -0.25, 0.9), (0.75, 0.25, 1.35), "box")
    attach(cargo, worker, keep=False)
    show_at(cargo, 58.0)
    hide_at(cargo, 66.2)
    key(worker, "location", F(57.9), (-1.0, 3.0, 0.3), "CONSTANT")
    path(worker, [(58.0, (13.0, 5.35, 0.0)), (60.8, (6.6, 5.35, 0.0))])
    path(worker, [(63.8, (6.6, 5.35, 0.0)), (64.4, (5.1, 5.35, 0.3)), (65.6, (1.5, 4.3, 0.3))])

    # ---------- 7. 멧돼지 + 빗장 ----------
    pig = boar("boar")
    pig.location = (16, 5.35, 0)
    show_at(pig, 66.8)
    path(pig, [(66.8, (16, 5.35, 0)), (68.8, (6.0, 5.35, 0)), (69.4, (5.0, 5.35, 0.3)),
               (70.2, (2.6, 3.4, 0.3)), (70.9, (2.6, 3.4, 0.3)), (71.4, (5.0, 5.35, 0.3)),
               (72.6, (15, 5.35, 0))])
    key(pig, "rotation_euler", F(70.85), (0, 0, -0.9), "CONSTANT")  # 쫓겨서 뒤돌기
    hide_at(pig, 72.7)
    path(worker, [(70.6, (1.5, 4.3, 0.3)), (71.8, (4.2, 5.2, 0.3)), (73.5, (3.6, 5.0, 0.3))])

    bar = box("bar", (4.62, 4.3, 1.25), (4.88, 6.4, 1.5), "wood")
    pop(bar, 73.2, dur=0.4)
    outline(bar, 73.3, 2.0, thick=0.05)

    # ---------- 8. 현관이 두 개인 이유 ----------
    outline(updoor, 75.4, 2.5)
    up_ar = arrow("up_ar", (-10.0, 3.9, 4.6), (-5.9, 3.9, 4.6), M["glow"], r=0.12)
    pop(up_ar, 75.6)
    shrink(up_ar, 79.8)
    outline(door, 77.9, 2.4)
    lo_ar = arrow("lo_ar", (10.0, 5.35, 1.4), (5.9, 5.35, 1.4), M["glow"], r=0.12)
    pop(lo_ar, 78.2)
    shrink(lo_ar, 81.5)
    path(worker, [(80.0, (2.0, 6.2, 0.3)), (80.1, (2.0, 6.2, 0.3))], face=False)
    key(worker, "rotation_euler", F(80.0), (0, 0, -math.pi / 2), "CONSTANT")

    # ---------- 9. 마무리: 난로, 작업대, 고양이 ----------
    stove = group("Stove", [box("stove_b", (-4.6, 6.4, 0.3), (-3.4, 7.5, 1.4), "dark"),
                            box("stove_f", (-4.3, 6.38, 0.5), (-3.7, 6.41, 1.0), "fire"),
                            cyl("stove_p", (-4.0, 7.0, 1.4), (-4.0, 7.0, 3.5), 0.12, "dark", 12)],
                  loc=(-4.0, 7.0, 0.3))
    pop(stove, 82.8)
    outline(stove, 83.0, 2.0)
    bench = group("Bench", [box("wb_top", (0.6, 6.7, 1.15), (3.4, 7.6, 1.3), "wood"),
                            box("wb_l1", (0.7, 6.8, 0.3), (0.85, 7.5, 1.15), "wood"),
                            box("wb_l2", (3.15, 6.8, 0.3), (3.3, 7.5, 1.15), "wood"),
                            box("wb_tool", (1.2, 7.0, 1.3), (1.9, 7.4, 1.55), "rug")],
                  loc=(2.0, 7.1, 0.3))
    pop(bench, 84.3)
    outline(bench, 84.5, 2.0)
    kitty = cat("cat")
    kitty.location = (4.55, 1.3, 1.3)
    kitty.rotation_euler = (0, 0, math.pi)
    pop(kitty, 85.8)
    outline(kitty, 86.0, 2.0, thick=0.03)

    lamp_d = bpy.data.lights.new("warm", "POINT")
    lamp_d.color = (1.0, 0.7, 0.4)
    lamp = bpy.data.objects.new("warm", lamp_d)
    COLL.objects.link(lamp)
    lamp.location = (0, 3.5, 2.8)
    lamp_d.energy = 0
    set_interp("BEZIER")
    lamp_d.keyframe_insert("energy", frame=F(86.0))
    lamp_d.energy = 450
    lamp_d.keyframe_insert("energy", frame=F(88.0))


# =====================================================================
# 카메라 / 자막
# =====================================================================
def build_camera():
    cd = bpy.data.cameras.new("Cam")
    cd.lens = 35
    cd.clip_end = 1000
    cam = bpy.data.objects.new("Cam", cd)
    COLL.objects.link(cam)
    SCENE.camera = cam
    tgt = empty("CamTarget")
    c = cam.constraints.new("TRACK_TO")
    c.target = tgt
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    prev = None
    for t, name in SHOTS:
        loc, look = CAMS[name]
        if prev is not None:
            key(cam, "location", F(t), prev[0], "BEZIER")
            key(tgt, "location", F(t), prev[1], "BEZIER")
        tt = t if prev is None else t + 0.6
        key(cam, "location", F(tt), loc, "BEZIER")
        key(tgt, "location", F(tt), look, "BEZIER")
        prev = (loc, look)
    # 바위가 '쾅' 부딪힐 때 화면 흔들림
    base = Vector(CAMS["aerial"][0])
    rnd = random.Random(1)
    f0 = F(37.4)
    for i in range(9):
        amp = 0.35 * (1 - i / 9)
        key(cam, "location", f0 + i, base + Vector((rnd.uniform(-amp, amp), 0, rnd.uniform(-amp, amp))), "LINEAR")
    key(cam, "location", f0 + 9, base, "BEZIER")
    return cam


def build_labels(cam, font_path):
    font = bpy.data.fonts.load(font_path)
    for st in STEPS:
        if "keyword" not in st:
            continue
        objs = []
        for nm, mt, off in (("b", "labelb", (0.025, -0.025, -0.01)), ("w", "labelw", (0, 0, 0))):
            cu = bpy.data.curves.new("lbl_" + nm, "FONT")
            cu.body = st["keyword"]
            cu.font = font
            cu.align_x = "CENTER"
            cu.align_y = "CENTER"
            cu.size = 0.42
            ob = bpy.data.objects.new("lbl_" + st["keyword"] + nm, cu)
            ob.data.materials.append(M[mt])
            COLL.objects.link(ob)
            ob.location = Vector((0, -0.35, -4.0)) + Vector(off)
            objs.append(ob)
        g = empty("label_" + st["keyword"], (0, -0.35, -4.0))
        g.parent = cam
        for o in objs:
            o.location = Vector(o.location) - Vector((0, -0.35, -4.0))
            o.parent = g
        pop(g, st["kt"], dur=0.35)
        shrink(g, st["kt"] + 1.8, dur=0.25)


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def write_texts(out):
    with open(os.path.join(out, "narration.txt"), "w", encoding="utf-8") as fp:
        for st in STEPS:
            fp.write(st["say"] + "\n\n")
    # 자막: 문장 단위로 쪼개 시간 배분
    lines = []
    for i, st in enumerate(STEPS):
        end = STEPS[i + 1]["t"] if i + 1 < len(STEPS) else DURATION
        parts = [p.strip() for p in st["say"].replace("! ", "!|").replace(". ", ".|").split("|") if p.strip()]
        total = sum(len(p) for p in parts)
        t = st["t"]
        for p in parts:
            d = (end - st["t"]) * len(p) / total
            lines.append((t, t + d, p))
            t += d
    with open(os.path.join(out, "captions.srt"), "w", encoding="utf-8") as fp:
        for i, (a, b, txt) in enumerate(lines, 1):
            fp.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{txt}\n\n")


# =====================================================================
# 렌더 설정 / 메인
# =====================================================================
def setup_render(pct, samples, engine="cycles"):
    r = SCENE.render
    if engine == "eevee":
        for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
            try:
                r.engine = eng
                break
            except Exception:
                pass
        try:
            SCENE.eevee.taa_render_samples = samples
            SCENE.eevee.use_shadows = True
        except Exception:
            pass
    else:
        r.engine = "CYCLES"
        try:   # GPU가 있으면 GPU 사용 (훨씬 빠름)
            prefs = bpy.context.preferences.addons["cycles"].preferences
            for dev in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
                try:
                    prefs.compute_device_type = dev
                    prefs.get_devices()
                    if any(d.type != "CPU" for d in prefs.devices):
                        for d in prefs.devices:
                            d.use = True
                        SCENE.cycles.device = "GPU"
                        break
                except Exception:
                    continue
        except Exception:
            pass
        SCENE.cycles.samples = samples
        SCENE.cycles.use_denoising = True
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1080, 1920, pct
    r.fps = FPS
    SCENE.frame_start, SCENE.frame_end = 1, F(DURATION)
    try:
        SCENE.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass


def build(font=None):
    global SCENE, COLL
    bpy.ops.wm.read_factory_settings(use_empty=True)
    SCENE = bpy.context.scene
    COLL = SCENE.collection
    M.clear()
    build_materials()
    build_world()
    build_scenery()
    build_story()
    cam = build_camera()
    if font and os.path.exists(font):
        build_labels(cam, font)
    set_interp("BEZIER")
    SCENE.frame_set(1)
    return cam


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="build", choices=["build", "stills", "preview", "final"])
    ap.add_argument("--out", default="out")
    ap.add_argument("--pct", type=int, default=100)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--font", default=None)
    ap.add_argument("--engine", default="cycles", choices=["cycles", "eevee"])
    ap.add_argument("--only", default=None, help="stills 모드에서 특정 초만 (쉼표 구분)")
    args, _ = ap.parse_known_args(argv)
    return args


def main():
    in_gui = not bpy.app.background and bpy.context.window_manager.windows
    args = parse_args() if not in_gui else argparse.Namespace(mode="build", out=None, pct=100, samples=64, font=None, only=None, engine="cycles")
    build(args.font)
    setup_render(args.pct, args.samples, args.engine)
    if in_gui:
        return
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    write_texts(out)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "slope_basement.blend"))
    if args.mode == "stills":
        times = [float(x) for x in args.only.split(",")] if args.only else STILL_TIMES
        for i, t in enumerate(times):
            SCENE.frame_set(F(t))
            SCENE.render.filepath = os.path.join(out, f"still_{i:02d}_{t:05.1f}s.png")
            bpy.ops.render.render(write_still=True)
            print("rendered", t, flush=True)
    elif args.mode == "preview":
        # 3프레임마다 1장(10fps)만 렌더 → preview.mp4 (움직임 확인용)
        SCENE.frame_step = 3
        SCENE.render.filepath = os.path.join(out, "pv", "p_")
        SCENE.render.image_settings.file_format = "JPEG"
        bpy.ops.render.render(animation=True)
        import glob, shutil, subprocess
        files = sorted(glob.glob(os.path.join(out, "pv", "p_*.jpg")))
        seq = os.path.join(out, "pv_seq")
        os.makedirs(seq, exist_ok=True)
        for i, fn in enumerate(files):
            shutil.copy(fn, os.path.join(seq, f"{i:05d}.jpg"))
        if shutil.which("ffmpeg"):
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "10", "-i",
                            os.path.join(seq, "%05d.jpg"), "-pix_fmt", "yuv420p", "-vf",
                            "scale=trunc(iw/2)*2:trunc(ih/2)*2", os.path.join(out, "preview.mp4")])
            print("preview →", os.path.join(out, "preview.mp4"))
    elif args.mode == "final":
        SCENE.render.filepath = os.path.join(out, "frames", "f_")
        SCENE.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(animation=True)
        print("frames →", os.path.join(out, "frames"), "  (ffmpeg로 mp4 변환: README 참고)")


if __name__ == "__main__":
    main()
