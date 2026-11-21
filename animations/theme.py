"""모든 scene이 공유하는 룩앤필.

색상은 site/css/theme.css 의 CSS 변수와 반드시 맞춰 둘 것 — 배경색이 같아야
manim 영상 슬라이드와 HTML 슬라이드가 이음새 없이 이어진다.
"""

from manim import BOLD, UL, WHITE, Scene, Text

# ── palette (site/css/theme.css 와 동기화) ──────────────────────────────
BG = "#0f1117"
FG = "#e6e6e6"
ACCENT = "#ee4c2c"  # PyTorch orange
ACCENT_2 = "#4c9be8"  # blue
MUTED = "#8b93a7"
VIOLET = "#a78bfa"
GREEN = "#34d399"
YELLOW = "#f2b134"

# ── fonts (로컬에 설치된 폰트 이름) ─────────────────────────────────────
# "Pretendard" 로 지정하면 Pango 가 Regular 파일만 잡아서 weight=BOLD 가 먹지 않는다.
FONT = "Pretendard Variable"
MONO = "Menlo"

# self.next_section(..., section_type=LOOP) 로 지정하면
# 덱에서 해당 구간 영상이 다음 클릭 전까지 반복 재생된다.
LOOP = "loop"


def heading(text: str) -> Text:
    """HTML 슬라이드의 h2 와 비슷한 위치/무게의 제목."""
    return Text(text, font=FONT, weight=BOLD, font_size=40, color=WHITE).to_corner(UL, buff=0.5)


class TalkScene(Scene):
    """발표용 scene 베이스 클래스.

    `self.next_section("name")` 한 번 = 덱에서 클릭(→) 한 번.
    각 section은 별도 mp4로 export 되어 슬라이드 하나가 된다.
    """

    def setup(self):
        self.camera.background_color = BG
        Text.set_default(font=FONT, color=FG)
