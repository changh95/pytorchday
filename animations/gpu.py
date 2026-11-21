"""슬라이드 5 — GPU 메모리 계층과 데이터 왕복.

구조는 NVIDIA H100 블록 다이어그램 기준:
  SM 블록(GPC) 8개 × SM 18개(=144), L2 cache 2 파티션, 좌우 메모리 컨트롤러 6개씩,
  HBM3 스택 좌우 3개씩(컨트롤러 2개 = 스택 1개), PCIe 5.0 / NVLink.

layer 하나마다 모든 SM 이 동시에
  HBM → (MC) → L2 → L1 → 연산 → L1 → L2 → (MC) → HBM
왕복을 하고, 이게 layer 수만큼 반복되면서 레이턴시가 쌓인다는 점을 보여준다.

미리보기:  make preview FILE=animations/gpu.py SCENE=GpuMemory
"""

import numpy as np
from manim import (
    BOLD,
    DOWN,
    LEFT,
    RIGHT,
    UP,
    UR,
    Create,
    FadeIn,
    GrowFromEdge,
    Indicate,
    LaggedStart,
    Line,
    MoveAlongPath,
    Rectangle,
    RoundedRectangle,
    Square,
    Text,
    Transform,
    VGroup,
    VMobject,
    Write,
    linear,
)

from theme import ACCENT, ACCENT_2, BG, FG, GREEN, MUTED, VIOLET, YELLOW, TalkScene, heading

HBM_C, L2_C, L1_C, MC_C = ACCENT_2, VIOLET, GREEN, ACCENT_2

DIE_W, DIE_H, DIE_Y = 8.4, 6.1, -0.2
INNER_W = 7.1  # SM 블록 / L2 / strip 이 차지하는 폭
GPC_W, GPC_H, GPC_GAP = 1.685, 1.98, 0.12
SM_W, SM_H = 0.21, 0.47
L2_H = 0.55

# 레이턴시 바에서 단계 하나가 차지하는 길이 — HBM 왕복이 가장 길다
COST = {"hbm": 0.55, "l2": 0.15, "compute": 0.08}
N_LAYERS = 7  # 바를 채우는 layer 수 (layer 1 은 section 1, 나머지는 section 2)
BAR_Y = -3.65


def make_sm(l1_side) -> VGroup:
    """SM 하나. L1 이 L2 쪽(l1_side)에 붙어 있다."""
    box = Rectangle(width=SM_W, height=SM_H, stroke_color=MUTED, stroke_width=1.2, fill_color=FG, fill_opacity=0.04)
    l1 = Rectangle(width=SM_W, height=0.08, stroke_width=0, fill_color=L1_C, fill_opacity=0.75)
    l1.move_to(box.get_edge_center(l1_side) - l1_side * 0.04)
    g = VGroup(box, l1)
    g.box, g.l1, g.l1_side = box, l1, l1_side
    return g


def make_gpc(l1_side) -> VGroup:
    frame = Rectangle(width=GPC_W, height=GPC_H, stroke_color=MUTED, stroke_width=1.5, stroke_opacity=0.8)
    sms = VGroup(*[make_sm(l1_side) for _ in range(18)]).arrange_in_grid(rows=3, cols=6, buff=(0.05, 0.06))
    # SM 은 L2 쪽으로 붙이고, 반대쪽에 라벨
    sms.move_to(frame).align_to(frame, l1_side).shift(-l1_side * 0.09)
    label = Text("SM", font_size=14, color=MUTED).move_to(frame).align_to(frame, -l1_side).shift(l1_side * 0.1)
    g = VGroup(frame, sms, label)
    g.sms = sms
    return g


def make_hbm() -> VGroup:
    r = Rectangle(width=1.05, height=1.6, stroke_color=HBM_C, fill_color=HBM_C, fill_opacity=0.2)
    return VGroup(r, Text("HBM3", font_size=20, color=HBM_C).move_to(r))


def make_strip(text: str, center_y: float) -> VGroup:
    r = Rectangle(width=INNER_W, height=0.32, stroke_color=MUTED, stroke_width=1.2, fill_color=MUTED, fill_opacity=0.12)
    r.move_to([0, center_y, 0])
    return VGroup(r, Text(text, font_size=15, color=MUTED).move_to(r))


def polyline(*points) -> VMobject:
    return VMobject().set_points_as_corners([list(p) for p in points])


def packet(p, size=0.09) -> Square:
    return Square(size, stroke_width=0, fill_color=YELLOW, fill_opacity=1).move_to(p).set_z_index(10)


class GpuMemory(TalkScene):
    def construct(self):
        # ── 레이아웃 ────────────────────────────────────────────────────
        title = heading("GPU")
        sub = Text("NVIDIA H100", font_size=22, color=MUTED)
        sub.next_to(title, RIGHT, buff=0.35).align_to(title, DOWN)

        def chip(color, label):
            return VGroup(
                Square(0.2, stroke_width=0, fill_color=color, fill_opacity=0.9),
                Text(label, font_size=18, color=MUTED),
            ).arrange(RIGHT, buff=0.12)

        legend = VGroup(chip(L1_C, "L1 (SM 안)"), chip(YELLOW, "데이터")).arrange(RIGHT, buff=0.45)
        legend.move_to([0.6, sub.get_y(), 0])

        die = RoundedRectangle(corner_radius=0.18, width=DIE_W, height=DIE_H, stroke_color=MUTED, stroke_width=3)
        die.move_to([0, DIE_Y, 0])
        L, R, T, B = die.get_left()[0], die.get_right()[0], die.get_top()[1], die.get_bottom()[1]

        top_strip = make_strip("PCIe 5.0  ·  GigaThread Engine", T - 0.28)
        nvlink = make_strip("NVLink", B + 0.28)

        def l2_part(x0, x1):
            r = Rectangle(width=x1 - x0, height=L2_H, stroke_color=L2_C, fill_color=L2_C, fill_opacity=0.25)
            r.move_to([(x0 + x1) / 2, DIE_Y, 0])
            return VGroup(r, Text("L2 cache", font_size=22, color=L2_C).move_to(r))

        l2_l, l2_r = l2_part(-INNER_W / 2, -0.08), l2_part(0.08, INNER_W / 2)

        gpc_xs = [-INNER_W / 2 + GPC_W / 2 + i * (GPC_W + GPC_GAP) for i in range(4)]
        gpc_dy = L2_H / 2 + 0.15 + GPC_H / 2
        gpcs_top = VGroup(*[make_gpc(DOWN).move_to([x, DIE_Y + gpc_dy, 0]) for x in gpc_xs])
        gpcs_bot = VGroup(*[make_gpc(UP).move_to([x, DIE_Y - gpc_dy, 0]) for x in gpc_xs])
        all_sms = [sm for g in [*gpcs_top, *gpcs_bot] for sm in g.sms]
        all_l1 = VGroup(*[sm.l1 for sm in all_sms])

        # 메모리 컨트롤러: 좌우 6개씩
        mc_top, mc_bot = top_strip.get_bottom()[1] - 0.1, nvlink.get_top()[1] + 0.1
        mc_h = (mc_top - mc_bot - 5 * 0.1) / 6

        def mc_column(x):
            col = VGroup()
            for i in range(6):
                r = Rectangle(width=0.4, height=mc_h, stroke_color=MC_C, stroke_width=1.5, fill_color=MC_C, fill_opacity=0.12)
                r.move_to([x, mc_top - mc_h / 2 - i * (mc_h + 0.1), 0])
                col.add(VGroup(r, Text("MC", font_size=12, color=MC_C).move_to(r)))
            return col

        mcs_l, mcs_r = mc_column(L + 0.32), mc_column(R - 0.32)

        hbm_l = VGroup(*[make_hbm() for _ in range(3)]).arrange(DOWN, buff=0.3).move_to([L - 0.35 - 0.525, DIE_Y, 0])
        hbm_r = VGroup(*[make_hbm() for _ in range(3)]).arrange(DOWN, buff=0.3).move_to([R + 0.35 + 0.525, DIE_Y, 0])
        phy = VGroup(
            *[Line([hbm_l[i // 2].get_right()[0], m.get_y(), 0], m.get_left()) for i, m in enumerate(mcs_l)],
            *[Line([hbm_r[i // 2].get_left()[0], m.get_y(), 0], m.get_right()) for i, m in enumerate(mcs_r)],
        ).set_stroke(HBM_C, width=3, opacity=0.6)

        # 레이턴시 바
        lat_label = Text("latency", font_size=24, color=MUTED).move_to([-6.0, BAR_Y, 0])
        bar_x0 = lat_label.get_right()[0] + 0.3
        track = Line([bar_x0, BAR_Y, 0], [6.6, BAR_Y, 0]).set_stroke(MUTED, width=2, opacity=0.4)
        bar = VGroup()

        def bar_segment(kind: str, color) -> Rectangle:
            seg = Rectangle(width=COST[kind], height=0.28, stroke_width=0, fill_color=color, fill_opacity=0.9)
            x = bar[-1].get_right()[0] if len(bar) else bar_x0
            seg.move_to([x + COST[kind] / 2, BAR_Y, 0])
            bar.add(seg)
            return seg

        layer_txt = Text("layer 1", font_size=28, color=YELLOW).to_corner(UR, buff=0.55)

        # ── 경로 ────────────────────────────────────────────────────────
        # HBM ↔ L2: 메모리 컨트롤러 12개마다 한 줄씩. MC 열을 따라 L2 높이까지 간 뒤 L2 로 들어간다.
        mem_routes = []
        for mcs, hbms, part in ((mcs_l, hbm_l, l2_l), (mcs_r, hbm_r, l2_r)):
            xs = np.linspace(part.get_left()[0] + 0.3, part.get_right()[0] - 0.3, 6)
            if part is l2_r:
                xs = xs[::-1]
            for i, mc in enumerate(mcs):
                h = hbms[i // 2]
                mem_routes.append(
                    [[h.get_x(), mc.get_y(), 0], mc.get_center(), [mc.get_x(), DIE_Y, 0], [xs[i], DIE_Y, 0]]
                )

        # L2 ↔ L1: SM 144개마다 한 줄씩 (L2 가장자리 ↔ SM 의 L1)
        def l2_edge(sm):
            y = DIE_Y + L2_H / 2 if sm.l1_side is DOWN else DIE_Y - L2_H / 2
            return [sm.get_x(), y, 0]

        sm_routes = [[l2_edge(sm), sm.l1.get_center()] for sm in all_sms]

        def stage(routes, cost, color, run_time, reverse=False, fade_in=False):
            pkts = [packet(r[-1] if reverse else r[0], size=0.11 if len(routes) < 20 else 0.08) for r in routes]
            if fade_in:
                self.play(*[FadeIn(p, scale=0.5) for p in pkts], run_time=0.2)
            else:
                self.add(*pkts)
            self.play(
                *[MoveAlongPath(p, polyline(*(r[::-1] if reverse else r)), rate_func=linear) for p, r in zip(pkts, routes)],
                GrowFromEdge(bar_segment(cost, color), LEFT, rate_func=linear),
                run_time=run_time,
            )
            self.remove(*pkts)

        def layer_pass(speed: float, first: bool = False):
            """모든 SM 이 동시에 HBM → L2 → L1 → 연산 → L1 → L2 → HBM."""
            stage(mem_routes, "hbm", HBM_C, 0.9 * speed, fade_in=first)
            stage(sm_routes, "l2", L2_C, 0.6 * speed)
            self.play(
                Indicate(all_l1, color=YELLOW, scale_factor=1.0),
                GrowFromEdge(bar_segment("compute", FG), LEFT, rate_func=linear),
                run_time=0.45 * speed,
            )
            stage(sm_routes, "l2", L2_C, 0.6 * speed, reverse=True)
            stage(mem_routes, "hbm", HBM_C, 0.9 * speed, reverse=True)

        # ── section 0: 구조 ─────────────────────────────────────────────
        self.next_section("arch")
        self.play(Write(title), FadeIn(sub), Create(die))
        self.play(FadeIn(hbm_l), FadeIn(hbm_r), FadeIn(mcs_l), FadeIn(mcs_r), Create(phy), FadeIn(top_strip), FadeIn(nvlink))
        self.play(FadeIn(l2_l), FadeIn(l2_r))
        self.play(LaggedStart(*[FadeIn(g, scale=0.9) for g in [*gpcs_top, *gpcs_bot]], lag_ratio=0.1, run_time=1.4))
        self.play(FadeIn(legend), FadeIn(lat_label), Create(track))
        self.wait(0.3)

        # ── section 1: layer 1 — 모든 SM 이 동시에 왕복 (천천히) ─────────
        self.next_section("roundtrip")
        self.play(FadeIn(layer_txt))
        layer_pass(speed=1.3, first=True)
        self.wait(0.3)

        # ── section 2: layer 마다 반복 → 레이턴시 누적 ───────────────────
        self.next_section("layers")
        for k in range(2, N_LAYERS + 1):
            self.play(Transform(layer_txt, Text(f"layer {k}", font_size=28, color=YELLOW).move_to(layer_txt)), run_time=0.1)
            layer_pass(speed=0.3)

        box = RoundedRectangle(corner_radius=0.2, width=7.0, height=2.2, stroke_color=ACCENT, stroke_width=3)
        box.set_fill(BG, opacity=0.94).move_to(die)
        msg = VGroup(
            Text("데이터가 오갈수록", font_size=40),
            Text("레이턴시가 쌓인다", font_size=52, weight=BOLD, color=ACCENT),
        ).arrange(DOWN, buff=0.25).move_to(box)
        self.play(FadeIn(box), FadeIn(msg, shift=0.2 * UP))
        self.play(Indicate(bar, color=ACCENT, scale_factor=1.0))
        self.wait(0.5)
