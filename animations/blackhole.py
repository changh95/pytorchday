"""슬라이드 6, 7 — Blackhole 아키텍처.

타일 배치는 tt-metal 의 SoC descriptor (tt_metal/soc_descriptors/blackhole_140_arch.yaml) 그대로:
  NoC 그리드 17 × 12
  Tensix   x = 1–7, 10–16 / y = 2–11   → 140개 (코어당 SRAM 1.5 MB)
           ※ 제품(p100a / p150a)은 120개 활성 — tenstorrent.com 스펙 표 기준
  DRAM     x = 0, 9 열 전체            → GDDR6 8 bank × 3 endpoint (bank 당 4 GB)
  Ethernet y = 1 행                    → 14개
  PCIe     (2, 0), (11, 0) · ARC (8, 0) · 나머지는 router-only
NoC 은 2개(NoC0: → ↓, NoC1: ← ↑)이고 2D torus — 가장자리에서 반대편으로 이어진다.

BlackholeNoC      : 칩 구조 → NoC → NoC 위 패킷 이동(loop)
BlackholeDataflow : Tensix 열마다 layer 할당 → 두 DRAM 열에서 Tensix 로 좌→우 streaming(loop)

BlackholeDataflow 는 BlackholeNoC 의 마지막 화면에서 그대로 시작한다 (슬라이드 6 → 7 이음새 없음).

미리보기:  make preview FILE=animations/blackhole.py SCENE=BlackholeNoC
"""

import random

import numpy as np
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Create,
    Dot,
    FadeIn,
    FadeOut,
    LaggedStart,
    Line,
    Square,
    Succession,
    SurroundingRectangle,
    Text,
    Transform,
    VGroup,
    Write,
    color_gradient,
    linear,
)

from theme import ACCENT, ACCENT_2, FG, GREEN, LOOP, MUTED, VIOLET, YELLOW, TalkScene, heading

# ── SoC descriptor ─────────────────────────────────────────────────────
GRID_W, GRID_H = 17, 12
DRAM_X = (0, 9)
TENSIX_X = (*range(1, 8), *range(10, 17))
TENSIX_Y = tuple(range(2, 12))
ETH = {(x, 1) for x in TENSIX_X}
PCIE = {(2, 0), (11, 0)}
ARC = {(8, 0)}

KINDS = {
    #          color      fill  legend
    "tensix": (ACCENT, 0.22, "Tensix × 140 (다이)"),
    "dram": (ACCENT_2, 0.3, "DRAM (GDDR6) × 8"),
    "eth": (GREEN, 0.3, "Ethernet × 14"),
    "pcie": (VIOLET, 0.4, "PCIe × 2"),
    "arc": (YELLOW, 0.4, "ARC"),
    "other": (MUTED, 0.0, "라우터 / 기타"),
}


def kind_of(x: int, y: int) -> str:
    if x in DRAM_X:
        return "dram"
    if (x, y) in PCIE:
        return "pcie"
    if (x, y) in ARC:
        return "arc"
    if (x, y) in ETH:
        return "eth"
    if x in TENSIX_X and y in TENSIX_Y:
        return "tensix"
    return "other"


# ── 레이아웃 ───────────────────────────────────────────────────────────
TILE, GAP = 0.40, 0.07
STEP = TILE + GAP
GRID_CENTER = np.array([-1.75, -0.2, 0])
CAPTION_Y = -3.62
N_LAYERS = len(TENSIX_X)  # Tensix 한 열 = layer 하나
LAYER_COLORS = color_gradient([ACCENT, YELLOW, GREEN, ACCENT_2, VIOLET], N_LAYERS)
HOP_TIME = 0.07  # 패킷이 타일 하나 지나가는 시간


def pos(x: int, y: int) -> np.ndarray:
    origin = GRID_CENTER + np.array([-(GRID_W - 1) / 2 * STEP, (GRID_H - 1) / 2 * STEP, 0])
    return origin + np.array([x * STEP, -y * STEP, 0])


class Chip:
    """두 scene 이 공유하는 칩 그림."""

    def __init__(self):
        self.title = heading("Blackhole")
        self.tiles = {}
        groups = {k: VGroup() for k in KINDS}
        for y in range(GRID_H):
            for x in range(GRID_W):
                k = kind_of(x, y)
                color, fill, _ = KINDS[k]
                sq = Square(
                    TILE,
                    stroke_color=color,
                    stroke_width=2 if k != "other" else 1.2,
                    stroke_opacity=1 if k != "other" else 0.45,
                    fill_color=color,
                    fill_opacity=fill,
                ).move_to(pos(x, y))
                self.tiles[(x, y)] = sq
                groups[k].add(sq)
        self.groups = groups
        self.all_tiles = VGroup(*self.tiles.values())
        self.die = SurroundingRectangle(self.all_tiles, buff=0.18, corner_radius=0.15, stroke_color=MUTED, stroke_width=3)

        rows = VGroup()
        for k, (color, fill, label) in KINDS.items():
            sw = Square(0.28, stroke_color=color, stroke_width=2, stroke_opacity=1 if k != "other" else 0.45)
            sw.set_fill(color, opacity=max(fill, 0.0))
            rows.add(VGroup(sw, Text(label, font_size=22, color=FG if k != "other" else MUTED)).arrange(RIGHT, buff=0.2))
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.22)
        spec = VGroup(
            Text("p100a · p150a: 120개 활성", font_size=20, color=MUTED),
            Text("Tensix 1개 = SRAM 1.5 MB", font_size=20, color=MUTED),
            Text("GDDR6 최대 32 GB", font_size=20, color=MUTED),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        self.legend = VGroup(rows, spec).arrange(DOWN, aligned_edge=LEFT, buff=0.45)
        self.legend.next_to(self.die, RIGHT, buff=0.45).align_to(self.die, UP).shift(DOWN * 0.1)

        # NoC 링크: 행/열 방향 + 가장자리 → 반대편으로 이어지는 torus 링크(짧은 꼬리로 표시)
        L, R = self.die.get_left()[0], self.die.get_right()[0]
        T, B = self.die.get_top()[1], self.die.get_bottom()[1]
        self.edges = (L, R, T, B)
        mesh = VGroup()
        for y in range(GRID_H):
            yy = pos(0, y)[1]
            mesh.add(Line([L, yy, 0], [R, yy, 0]))
        for x in range(GRID_W):
            xx = pos(x, 0)[0]
            mesh.add(Line([xx, T, 0], [xx, B, 0]))
        self.mesh = mesh.set_stroke(ACCENT_2, width=1.6, opacity=0.5).set_z_index(-1)

    def build(self):
        return VGroup(self.title, self.die, self.all_tiles, self.legend)


def caption(text: str) -> Text:
    t = Text(text, font_size=28)
    if t.width > 8.6:  # 다이 폭을 넘으면 줄인다
        t.scale_to_fit_width(8.6)
    return t.move_to([GRID_CENTER[0], CAPTION_Y, 0])


NOC_CAPTION = "NoC: 모든 타일을 잇는 2D torus 네트워크"


def route(chip: Chip, src, dst, noc: int):
    """dimension-order routing (X 다음 Y). NoC0 은 +x/+y(→↓), NoC1 은 -x/-y(←↑). torus wrap 포함.

    [("move" | "jump", point), ...] 를 반환. 같은 방향의 연속 hop 은 하나로 합친다.
    """
    L, R, T, B = chip.edges
    step = 1 if noc == 0 else -1
    (x, y), (tx, ty) = src, dst
    out = []

    def emit(kind, p, hops=1):
        if kind == "move" and out and out[-1][0] == "move" and out[-1][3] == direction:
            out[-1] = ("move", p, out[-1][2] + hops, direction)
        else:
            out.append((kind, p, hops, direction))

    direction = "x"
    while x != tx:
        nx = x + step
        if nx in (GRID_W, -1):  # wrap
            edge_out, edge_in = (R, L) if step == 1 else (L, R)
            emit("move", np.array([edge_out, pos(0, y)[1], 0]), 0.5)
            out.append(("jump", np.array([edge_in, pos(0, y)[1], 0]), 0, "jump"))
            nx = 0 if step == 1 else GRID_W - 1
        x = nx
        emit("move", pos(x, y), 1 if out and out[-1][0] != "jump" else 0.5)
    direction = "y"
    while y != ty:
        ny = y + step
        if ny in (GRID_H, -1):
            edge_out, edge_in = (B, T) if step == 1 else (T, B)
            emit("move", np.array([pos(x, 0)[0], edge_out, 0]), 0.5)
            out.append(("jump", np.array([pos(x, 0)[0], edge_in, 0]), 0, "jump"))
            ny = 0 if step == 1 else GRID_H - 1
        y = ny
        emit("move", pos(x, y), 1 if out and out[-1][0] != "jump" else 0.5)
    return out


# 주의: d.animate 는 목표 상태를 d.target 하나에 덮어쓰고, Succession 에 넘길 때 비로소 애니메이션이
# 만들어진다. 그러면 모든 구간이 '마지막' 목표를 향해 대각선으로 움직이므로, 구간마다 즉시 .build() 한다.
def packet_anim(chip: Chip, src, dst, noc: int):
    color = YELLOW if noc == 0 else GREEN
    d = Dot(pos(*src), radius=0.085, color=color).set_z_index(10)
    steps = [FadeIn(d, scale=0.5, run_time=0.12)]
    for kind, p, hops, _ in route(chip, src, dst, noc):
        if kind == "jump":
            steps.append(d.animate(run_time=1 / 60).move_to(p).build())
        else:
            steps.append(d.animate(run_time=HOP_TIME * hops, rate_func=linear).move_to(p).build())
    steps.append(FadeOut(d, scale=0.5, run_time=0.12))
    return Succession(*steps)


class BlackholeNoC(TalkScene):
    def construct(self):
        chip = Chip()
        cap = caption(NOC_CAPTION)

        # ── section 0: 칩 구조 ──────────────────────────────────────────
        self.next_section("arch")
        self.play(Write(chip.title), Create(chip.die))
        self.play(
            LaggedStart(
                *[FadeIn(chip.groups[k], scale=0.8) for k in ("dram", "eth", "pcie", "arc", "other")],
                lag_ratio=0.25,
            ),
            run_time=1.2,
        )
        self.play(LaggedStart(*[FadeIn(t, scale=0.5) for t in chip.groups["tensix"]], lag_ratio=0.006, run_time=1.6))
        self.play(FadeIn(chip.legend, shift=0.2 * LEFT))
        self.wait(0.3)

        # ── section 1: NoC ──────────────────────────────────────────────
        self.next_section("mesh")
        self.play(LaggedStart(*[Create(l) for l in chip.mesh], lag_ratio=0.04, run_time=1.5), FadeIn(cap))
        self.wait(0.3)

        # ── section 2: 패킷 이동 (loop) ──────────────────────────────────
        # DRAM → Tensix 읽기, Tensix ↔ Tensix 전달. 시작/끝에 패킷이 없어야 반복 재생이 끊기지 않는다.
        self.next_section("packets", section_type=LOOP)
        rng = random.Random(11)
        tensix = [(x, y) for x in TENSIX_X for y in TENSIX_Y]
        dram = [(x, y) for x in DRAM_X for y in range(GRID_H)]
        packets = []
        for i in range(14):
            src = rng.choice(dram if i % 3 == 0 else tensix)
            dst = rng.choice(tensix)
            packets.append(packet_anim(chip, src, dst, noc=i % 2))
        self.play(LaggedStart(*packets, lag_ratio=0.14))
        self.wait(0.2)


class BlackholeDataflow(TalkScene):
    def construct(self):
        chip = Chip()
        cap = caption(NOC_CAPTION)
        cols = [VGroup(*[chip.tiles[(x, y)] for y in TENSIX_Y]) for x in TENSIX_X]

        # layer 색 범례 (범례 아래): layer 1 → 14
        strip = VGroup(*[Square(0.2, stroke_width=0, fill_color=c, fill_opacity=0.9) for c in LAYER_COLORS])
        strip.arrange(RIGHT, buff=0.04)
        layer_key = VGroup(Text(f"layer 1 → {N_LAYERS}", font_size=20, color=FG), strip)
        layer_key.arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        layer_key.next_to(chip.legend, DOWN, buff=0.5, aligned_edge=LEFT)

        # BlackholeNoC 의 마지막 화면과 동일한 상태에서 시작
        self.add(chip.build(), chip.mesh, cap)

        # ── section 0: Tensix 열마다 layer 할당 ──────────────────────────
        self.next_section("assign")
        self.play(
            LaggedStart(
                *[c.animate.set_stroke(LAYER_COLORS[i]).set_fill(LAYER_COLORS[i], 0.32) for i, c in enumerate(cols)],
                lag_ratio=0.1,
            ),
            FadeIn(layer_key, shift=0.1 * UP),
            chip.mesh.animate.set_stroke(opacity=0.25),
            Transform(cap, caption("Tensix 한 열 = 모델 layer 하나")),
            run_time=1.8,
        )
        self.wait(0.3)

        # ── streaming: DRAM → Tensix, 좌→우 ─────────────────────────────────────
        # 왼쪽 DRAM 열(x = 0)은 왼쪽 Tensix(x = 1–7, layer 1–7)로,
        # 가운데 DRAM 열(x = 9)은 오른쪽 Tensix(x = 10–16, layer 8–14)로 흘려 보낸다.
        # 모든 Tensix 행에서 동시에, 매 tick 마다 한 칸씩 오른쪽으로. streams[y][x] = (x, y) 의 데이터
        streams = {y: {} for y in TENSIX_Y}
        right_edge = chip.edges[1]
        LAST = {7: pos(8, 0)[0], 16: right_edge}  # 각 흐름의 마지막 Tensix 열 → 빠져나가는 x

        def color_at(x):
            return LAYER_COLORS[TENSIX_X.index(x)] if x in TENSIX_X else FG

        def tick(run_time: float):
            """모든 데이터가 한 칸 오른쪽으로. 각 흐름의 끝은 빠져나가고, 두 DRAM 열에서 새로 들어온다."""
            anims, leaving = [], []
            for y, row in streams.items():
                for x in sorted(row, reverse=True):
                    d = row.pop(x)
                    if x in LAST:
                        anims.append(d.animate.move_to([LAST[x], pos(0, y)[1], 0]).set_opacity(0))
                        leaving.append(d)
                    else:
                        anims.append(d.animate.move_to(pos(x + 1, y)).set_color(color_at(x + 1)))
                        row[x + 1] = d
                for x in DRAM_X:
                    d = Dot(pos(x, y), radius=0.085, color=FG).set_z_index(10)
                    anims.append(FadeIn(d, scale=0.3))
                    row[x] = d
            self.play(*anims, run_time=run_time, rate_func=linear)
            self.remove(*leaving)

        # ── section 1: 파이프라인 채우기 ─────────────────────────────────
        # 두 DRAM 열에서 데이터가 한 칸씩 들어오면서 모든 layer 가 차례로 일을 시작한다.
        self.next_section("flow")
        self.play(Transform(cap, caption("Streaming NoC: DRAM → Tensix, 모든 코어가 동시에 다음 layer 로")), run_time=0.5)
        for _ in range(8):  # DRAM 열 + Tensix 7열 = 8칸이 차면 파이프라인이 가득 찬다
            tick(0.28)

        # ── section 2: 꽉 찬 파이프라인이 계속 흐름 (loop) ────────────────
        # tick 하나가 끝나면 배치가 처음과 같아지므로 반복 재생이 끊기지 않는다.
        self.next_section("stream", section_type=LOOP)
        for _ in range(8):
            tick(0.28)
