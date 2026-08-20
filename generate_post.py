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
    available = [t for t in topics if t not in used_recent]
    if not available:
        available = topics
    return random.choice(available)


def slugify(text, date_str):
    return f"{date_str}-{random.randint(1000, 9999)}"


def call_claude(topic):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    year = datetime.date.today().year

    prompt = f"""너는 한국어 정보성 블로그의 전문 작성자야. 아래 주제로 애드센스 승인 및
구글 검색 상위노출(SEO)에 적합한 블로그 글을 작성해줘.

주제: {topic}
기준 연도: {year}년 (제도/금액/조건은 {year}년 기준으로 작성. 연도가 바뀌면 달라질 수 있는
정보는 "{year}년 기준"이라고 명시)

제목 규칙:
- 메인 키워드를 제목 앞쪽에 배치
- 호기심을 유발하는 질문형이나 해결형 문장 (예: "2026년 실업급여 신청방법, 자발적 퇴사도 가능할까?")

톤 & 스타일 (중요 - 구간별로 다르게):
- 인트로/개인적인 팁을 전할 때 -> "~하더라구요", "~인 것 같아요" 같은 친근한 구어체
- 핵심 절차·숫자·서류 안내 부분 -> "~합니다", "~하셔야 해요" 같은 확신을 주는 어투로 전환
  (정보의 신뢰도가 중요한 부분이라 너무 애매한 말투는 피할 것)
- 서론 첫 1~2문장 안에 메인 키워드가 자연스럽게 들어가야 함
- 괄호를 이용한 용어 설명은 정말 낯선 용어 1개 정도에만 아주 가끔 사용하고, 나머지는 괄호 없이
  문장 속에 자연스럽게 풀어서 설명할 것
  (예: "LTV(주택담보대출비율)" 대신 "집값 대비 대출 가능한 비율을 뜻하는 LTV는" 처럼 풀어쓰기)
- 각 소제목은 "그래서 뭘 하면 되는지" 결론부터 먼저 말하고 부가설명 이어가기

요구사항:
- 분량: 1200~1500자 내외의 실질적인 정보 (공백 포함)
- 서론(공감형 후킹, 키워드 포함) - 본론(소제목 3~4개) - 결론(요약) - Q&A(1~2개) 구조
- 본론 중 최소 1개 소제목에는 핵심 절차/서류/조건을 정리한 체크리스트(3개 이상 항목) 포함
- 의학적/법적 조언처럼 단정하지 말고 "전문가와 상담하세요" 같은 문구를 필요한 곳에 자연스럽게 포함
- 과장된 효능/보장 표현 금지 (예: "무조건", "100% 효과")
- 광고성 문구, 특정 제품 브랜드명 언급 금지

공식기관 안내: 아래 목록 중 이 주제와 가장 관련 있는 곳 하나를 골라서 official_site에 정확히
그 이름 그대로 적어줘 (목록에 없으면 "정부24"로 적기):
정부24, 홈택스, 위택스, 국민연금공단, 고용보험, 국민건강보험공단, 인터넷등기소, 청약홈,
여신금융협회, 국토교통부, 금융감독원, 금융상품한눈에, 도로교통공단, 자동차365,
국가동물보호정보시스템, HRD-Net, 국가평생교육진흥원, 외교부 해외안전여행, 한국소비자원, 카드포인트 통합조회

대표 이미지 검색어: 이 글 내용을 잘 나타내는 영어 키워드 2~4단어를 image_query에 적어줘
(스톡사진 검색에 쓸 거라 영어로, 예: "car insurance document", "moving boxes apartment")

아래 JSON 형식으로만 응답해. 다른 설명이나 마크다운 코드블럭 없이 순수 JSON만 출력해.
{{
  "title": "글 제목 (30자 내외, 키워드 앞배치, 질문형/해결형)",
  "meta_description": "검색 결과에 노출될 요약 (80자 내외)",
  "image_query": "영어 이미지 검색어 2~4단어",
  "image_alt": "이미지 대체텍스트 (한국어, 15자 내외)",
  "sections": [
    {{"heading": "소제목1", "body": "본문 내용 (HTML 태그 없이 순수 텍스트, 문단은 \\n\\n으로 구분)", "checklist": null}},
    {{"heading": "소제목2 (체크리스트 넣을 소제목)", "body": "본문 내용", "checklist": ["체크항목1", "체크항목2", "체크항목3"]}},
    {{"heading": "소제목3", "body": "..."}}
  ],
  "intro": "서론 부분 텍스트 (첫 1~2문장에 메인 키워드 포함)",
  "conclusion": "결론/요약 부분 텍스트",
  "official_site": "위 목록 중 하나",
  "qna": [
    {{"q": "독자가 가장 궁금해할 질문1", "a": "간결한 답변1"}},
    {{"q": "질문2", "a": "답변2"}}
  ],
  "tags": ["태그1", "태그2", "태그3"]
}}"""

    resp = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = resp.content[0].text.strip()
    raw = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
    return json.loads(raw)


def fetch_image(query):
    """Pexels에서 주제에 맞는 무료 스톡사진 1장을 가져온다. 실패하면 None 반환 (이미지 없이 글은 계속 생성됨)."""
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        return None
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": 1, "orientation": "landscape"},
            timeout=10,
        )
        data = resp.json()
        photos = data.get("photos") or []
        if not photos:
            return None
        photo = photos[0]
        return {
            "url": photo["src"]["large"],
            "photographer": photo.get("photographer", "Pexels"),
            "photographer_url": photo.get("photographer_url", "https://www.pexels.com"),
        }
    except Exception as e:
        print(f"[이미지 가져오기 실패, 이미지 없이 계속 진행] {e}")
        return None


# ---------- HTML 렌더링 ----------

POST_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | {site_name}</title>
<meta name="description" content="{meta_description}">
<link rel="stylesheet" href="../style.css">
</head>
<body>
<header class="site-header"><a href="../index.html">{site_name}</a></header>
<main class="post">
<h1>{title}</h1>
<p class="post-date">{date_str}</p>
<p class="post-intro">{intro}</p>
{image_html}
{sections_html}
<div class="post-conclusion"><h2>정리하며</h2><p>{conclusion}</p></div>
{official_link_html}
{qna_html}
<p class="tags">{tags_html}</p>
</main>
<footer class="site-footer">
<p><a href="../about.html">소개</a> · <a href="../contact.html">문의</a> · <a href="../privacy.html">개인정보처리방침</a></p>
<p>&copy; {year} {site_name}</p>
</footer>
</body>
</html>
"""


def paragraphs_to_html(text):
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "\n".join(f"<p>{html_lib.escape(p)}</p>" for p in parts)


def render_post_html(post, date_str, image):
    sections_html = ""
    for sec in post["sections"]:
        sections_html += f"<h2>{html_lib.escape(sec['heading'])}</h2>\n"
        sections_html += paragraphs_to_html(sec["body"]) + "\n"
        checklist = sec.get("checklist")
        if checklist:
            items = "".join(f"<li>{html_lib.escape(item)}</li>" for item in checklist)
            sections_html += f'<ul class="checklist">{items}</ul>\n'

    image_html = ""
    if image:
        alt_text = html_lib.escape(post.get("image_alt", post["title"]))
        image_html = (
            f'<img src="{html_lib.escape(image["url"])}" alt="{alt_text}" class="post-image" loading="lazy">\n'
            f'<p class="image-credit">사진: '
            f'<a href="{html_lib.escape(image["photographer_url"])}" target="_blank" rel="noopener">'
            f'{html_lib.escape(image["photographer"])}</a> (Pexels)</p>\n'
        )

    official_link_html = ""
    site_name_key = post.get("official_site")
    site_url = OFFICIAL_SITES.get(site_name_key)
    if site_url:
        official_link_html = (
            '<div class="official-link">'
            f'👉 <a href="{site_url}" target="_blank" rel="noopener">{html_lib.escape(site_name_key)}</a>'
            "에서 본인 해당 여부를 직접 확인해보실 수 있어요."
            "</div>\n"
        )

    qna_html = ""
    qna_list = post.get("qna") or []
    if qna_list:
        qna_html = '<div class="qna"><h2>자주 묻는 질문</h2>\n'
        for item in qna_list:
            qna_html += (
                f'<p class="qna-q">Q. {html_lib.escape(item.get("q", ""))}</p>'
                f'<p class="qna-a">A. {html_lib.escape(item.get("a", ""))}</p>\n'
            )
        qna_html += "</div>\n"

    tags_html = " ".join(f"#{html_lib.escape(t)}" for t in post.get("tags", []))

    return POST_TEMPLATE.format(
        title=html_lib.escape(post["title"]),
        meta_description=html_lib.escape(post["meta_description"]),
        site_name=SITE_NAME,
        date_str=date_str,
        intro=html_lib.escape(post["intro"]),
        image_html=image_html,
        sections_html=sections_html,
        conclusion=html_lib.escape(post["conclusion"]),
        official_link_html=official_link_html,
        qna_html=qna_html,
        tags_html=tags_html,
        year=datetime.datetime.now().year,
    )


INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{site_name}</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="site-header">{site_name}</header>
<main>
<ul class="post-list">
{items}
</ul>
</main>
<footer class="site-footer">
<p><a href="about.html">소개</a> · <a href="contact.html">문의</a> · <a href="privacy.html">개인정보처리방침</a></p>
<p>&copy; {year} {site_name}</p>
</footer>
</body>
</html>
"""


def render_index(posts_meta):
    items = ""
    for p in sorted(posts_meta, key=lambda x: x["date"], reverse=True):
        items += (
            f'<li><a href="posts/{p["slug"]}.html">{html_lib.escape(p["title"])}</a>'
            f'<span class="date"> - {p["date"]}</span></li>\n'
        )
    return INDEX_TEMPLATE.format(
        site_name=SITE_NAME, items=items, year=datetime.datetime.now().year
    )


# ---------- 메인 ----------

def main():
    os.makedirs(POSTS_DIR, exist_ok=True)

    topics = load_topics()
    posts_meta = load_posts_meta()

    topic = pick_topic(topics, posts_meta)
    print(f"[선택된 주제] {topic}")

    post = call_claude(topic)

    image = fetch_image(post.get("image_query", topic))

    today = datetime.date.today().isoformat()
    slug = slugify(post["title"], today)

    html_out = render_post_html(post, today, image)
    with open(os.path.join(POSTS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html_out)

    posts_meta.append({
        "slug": slug,
        "title": post["title"],
        "topic": topic,
        "date": today,
    })
    save_posts_meta(posts_meta)

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(render_index(posts_meta))

    print(f"[완료] posts/{slug}.html 생성됨, index.html 갱신됨")


if __name__ == "__main__":
    main()
