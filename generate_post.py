"""
자동 블로그 포스팅 스크립트
- topics.txt 에서 주제를 하나 골라 Claude API로 글을 생성
- posts/ 폴더에 개별 HTML 파일로 저장
- index.html (글 목록 페이지) 자동 갱신
- posts.json 에 이력을 남겨서 같은 주제 반복을 최대한 피함

실행: python generate_post.py
필요 환경변수: ANTHROPIC_API_KEY (필수), PEXELS_API_KEY (선택 - 없으면 이미지 없이 생성)
"""

import os
import re
import json
import random
import datetime
import html as html_lib

import anthropic
import requests

# ---------- 설정 ----------
TOPICS_FILE = "topics.txt"
POSTS_DIR = "posts"
POSTS_JSON = "posts.json"
INDEX_FILE = "index.html"
SITE_NAME = "생활 정보 블로그"  # 사이트 이름 - 원하는 대로 수정
MODEL = "claude-sonnet-4-6"

# AI가 이 목록 중에서만 골라 쓰도록 해서, 존재하지 않는 URL을 지어내는 걸 방지
OFFICIAL_SITES = {
    "정부24": "https://www.gov.kr",
    "홈택스": "https://www.hometax.go.kr",
    "위택스": "https://www.wetax.go.kr",
    "국민연금공단": "https://www.nps.or.kr",
    "고용보험": "https://www.ei.go.kr",
    "국민건강보험공단": "https://www.nhis.or.kr",
    "인터넷등기소": "http://www.iros.go.kr",
    "청약홈": "https://www.applyhome.co.kr",
    "여신금융협회": "https://www.crefia.or.kr",
    "국토교통부": "https://www.molit.go.kr",
    "금융감독원": "https://www.fss.or.kr",
    "금융상품한눈에": "https://finlife.fss.or.kr",
    "도로교통공단": "https://www.koroad.or.kr",
    "자동차365": "https://www.car365.go.kr",
    "국가동물보호정보시스템": "https://www.animal.go.kr",
    "HRD-Net": "https://www.hrd.go.kr",
    "국가평생교육진흥원": "https://www.nile.or.kr",
    "외교부 해외안전여행": "https://www.0404.go.kr",
    "한국소비자원": "https://www.kca.go.kr",
    "카드포인트 통합조회": "https://www.cardpoint.or.kr",
}

# ---------- 유틸 ----------

def load_topics():
    with open(TOPICS_FILE, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_posts_meta():
    if os.path.exists(POSTS_JSON):
        with open(POSTS_JSON, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_posts_meta(posts):
    with open(POSTS_JSON, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)


def pick_topic(topics, posts_meta):
    used_recent = {p["topic"] for p in posts_meta[-15:]}
    available =
