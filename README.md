# 모두의 AI 가속기 - Tenstorrent Blackhole

PyTorch KR 5분 lightning talk 슬라이드.

- 슬라이드: https://changh95.github.io/pytorchday/
- 덱: [reveal.js](https://revealjs.com) (CDN, 빌드 없음)
- 애니메이션: [manim](https://www.manim.community) → section 단위 mp4 → 슬라이드 배경 영상

## 구조

```
animations/            manim scene (Python)
  theme.py             공통 색상/폰트 + TalkScene 베이스 클래스 + heading()
  gpu.py               슬라이드 5: GpuMemory (HBM ↔ L2 ↔ L1 왕복 → 레이턴시)
  blackhole.py         슬라이드 6, 7: BlackholeNoC, BlackholeDataflow
scripts/
  build_animations.py  렌더 → site/assets/anim 으로 export + manifest.js 생성
site/                  ← GitHub Pages 로 배포되는 폴더
  index.html           슬라이드 본문
  css/theme.css        덱 테마 (색상은 animations/theme.py 와 동기화)
  js/manim.js          <section data-manim="..."> 를 슬라이드들로 펼침
  assets/anim/         export 된 영상 (자동 생성, 커밋함)
  assets/img/          사진·로고·스크린샷 (아래 '넣어야 할 이미지')
  js/placeholders.js   이미지가 없으면 넣을 경로를 점선 박스로 표시
.github/workflows/pages.yml   main 에 push 하면 site/ 배포
```

## 이미지 출처

| 파일 | 출처 |
| --- | --- |
| `jim-keller.jpg` | LG Electronics, [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/), via [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Jim_Keller_(engineer).jpg) — 슬라이드에 크레딧 표기 필요 |
| `p100a.jpg`, `p150a.jpg`, `quietbox2.jpg`, `galaxy.jpg` | tenstorrent.com 제품 페이지 이미지 |
| `logos/tenstorrent.svg` | tenstorrent.com 헤더 SVG (글자색만 흰색으로 변경) |
| `logos/{amd,tesla,intel,apple}.svg` | [simple-icons](https://simpleicons.org) |
| `github-*.png` | headless Chrome 스크린샷 (dark mode, 2x) |
| `tweet-day0.png` | X 공식 임베드(platform.twitter.com/embed) 스크린샷 (dark, 2x) |
| `openrouter-tenstorrent.png` | openrouter.ai/provider/tenstorrent 모델 목록 부분 스크린샷 (dark, 2x) |
| `newsroom-galaxy-gpt-oss.png` | tenstorrent.com/newsroom/tenstorrents-galaxy-blackhole-gpt-oss-12 상단 스크린샷 (2x) |

이미지가 없으면 `js/placeholders.js` 가 넣을 경로를 점선 박스로 보여준다.

### 영상

원본은 `videos/` 에 넣고 `make media` → `site/assets/media/` 에 웹용 mp4 가 생긴다 (GIF 도 mp4 로 변환).
`videos/` 자체는 `.gitignore` 에 들어 있어 커밋되지 않는다. 슬라이드에서는
`<video data-autoplay muted loop playsinline src="assets/media/...">` 로 쓰면 슬라이드에 들어올 때 재생되고 나가면 멈춘다.

## 준비

```sh
brew install cairo pango pkgconf ffmpeg   # manim 의존성 (macOS)
make setup                                # uv sync
```

- 폰트: manim 은 로컬에 설치된 폰트를 쓴다 (`Pretendard Variable`, `Menlo`). 바꾸려면 `animations/theme.py`.
  `"Pretendard"` 로 지정하면 굵게(`weight=BOLD`)가 적용되지 않으니 Variable 이름을 쓸 것.
- `MathTex`/`Tex` 를 쓰려면 LaTeX 가 필요하다: `brew install --cask basictex`.

## 작업 흐름

```sh
make preview FILE=animations/gpu.py SCENE=GpuMemory   # scene 하나를 저화질로 바로 재생
make draft                      # 전체 저화질 렌더 → site/ 반영 (빠름)
make serve                      # http://localhost:8000 에서 덱 확인
make anim                       # 최종 1080p60 렌더 → 커밋 전에 실행
```

### 애니메이션 추가하기

1. `animations/` 에 scene 작성 — `TalkScene` 을 상속하고 클릭 단위로 `self.next_section()` 을 나눈다.

   ```python
   from theme import LOOP, TalkScene

   class MyScene(TalkScene):
       def construct(self):
           self.next_section("step1")
           ...                                   # 클릭 1
           self.next_section("step2")
           ...                                   # 클릭 2
           self.next_section("idle", section_type=LOOP)
           ...                                   # 다음 클릭까지 반복 재생
   ```

2. `make draft` (또는 `make anim`)
3. `site/index.html` 에 자리 표시:

   ```html
   <section data-manim="MyScene">
     <aside class="notes">step1 발표자 노트</aside>
     <aside class="notes">step2 발표자 노트</aside>
   </section>
   ```

   section 개수만큼 슬라이드가 생기고, section 사이에는 전환 효과가 없어서
   클릭할 때마다 애니메이션이 이어서 재생되는 것처럼 보인다.

팁

- section 하나는 앞 section 의 마지막 프레임에서 시작하므로 이음새가 보이지 않는다.
- `LOOP` section 은 시작과 끝 상태가 같게 만들어야 반복이 자연스럽다.
- 배경색은 `theme.py` 의 `BG` 와 `theme.css` 의 `--bg` 가 같아야 한다.
- 비어 있는(애니메이션 없는) section 은 manim 이 영상을 만들지 않으니 주의.
- placeholder 에 붙인 `data-*` 속성은 첫 슬라이드에 적용된다. 앞 scene 의 마지막 화면에서 이어지는
  scene 은 `data-transition="none" data-background-transition="none"` 을 붙인다 (슬라이드 7 참고).
- HTML 슬라이드의 제목은 manim `heading()` 과 같은 자리(좌상단)에 오도록 맞춰 두었다 (`margin: 0`, `center: false`).

## 발표

| 키 | 기능 |
| --- | --- |
| `→` / `Space` | 다음 (fragment / manim section) |
| `S` | 발표자 뷰 — 노트, 다음 슬라이드, 5분 pacing 타이머 |
| `F` | 전체 화면 |
| `O` / `Esc` | 슬라이드 개요 |
| `B` | 화면 끄기 |

시간 배분은 각 `<section>` 의 `data-timing`(초)과 `totalTime: 300` 으로 잡혀 있다.

> 오프라인 대비: reveal.js 와 폰트를 CDN 에서 받으므로, 현장 네트워크가 불안하면
> 미리 한 번 열어 캐시해 두거나 reveal.js 를 `site/vendor/` 로 받아 두자.

## 배포 (GitHub Pages)

1. GitHub repo → **Settings → Pages → Source: GitHub Actions**
2. `make anim` 후 `main` 에 push → Actions 가 `site/` 를 배포
