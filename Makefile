# 사용법은 README.md 참고
Q    ?= h
PORT ?= 8000
FILE ?= animations/blackhole.py
SCENE ?=

.PHONY: help setup anim draft media preview serve clean clean-anim

help:  ## 명령 목록
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-11s %s\n", $$1, $$2}'

setup:  ## Python 환경 설치 (uv)
	uv sync

anim:  ## 전체 scene 렌더 → site/ 로 export (기본 1080p60, Q=l|m|h|k)
	uv run python scripts/build_animations.py -q $(Q)

draft:  ## 빠른 저화질(480p15) 렌더 → site/ 로 export
	uv run python scripts/build_animations.py -q l

media:  ## videos/ 의 원본 영상(gif/mp4) → 웹용 mp4 로 변환해서 site/assets/media 로
	python3 scripts/build_media.py

preview:  ## scene 하나 미리보기: make preview FILE=animations/x.py SCENE=Name
	uv run manim render -pql --media_dir build/media $(FILE) $(SCENE)

serve:  ## 로컬 서버로 덱 띄우기 (http://localhost:8000)
	@echo "→ http://localhost:$(PORT)"
	python3 -m http.server $(PORT) -d site

clean:  ## manim 중간 산출물(build/) 삭제
	rm -rf build

clean-anim:  ## export 된 영상(site/assets/anim) 삭제 — 다시 make anim 필요
	rm -rf site/assets/anim
