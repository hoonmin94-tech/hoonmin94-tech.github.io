"""
자동 블로그 포스팅 스크립트
- topics.txt 에서 주제를 하나 골라 Claude API로 글을 생성
- posts/ 폴더에 개별 HTML 파일로 저장
- index.html (글 목록 페이지) 자동 갱신
- posts.json 에 이력을 남겨서 같은 주제 반복을 최대한 피함

실행: python generate_post.py
필요 환경변수: ANTHROPIC_API_KEY
"""

import os
import re
import json
import random
import datetime
import html as html_lib

import anthropic

# ---------- 설정 ----------
TOPICS_FILE = "topics.txt"
POSTS_DIR = "posts"
POSTS_JSON = "posts.json"
INDEX_FILE = "index.html"
SITE_NAME = "생활 정보 블로그"  # 사이트 이름 - 원하는 대로 수정
MODEL = "claude-sonnet-4-6"

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
    # 한글 제목 -> 파일명으로 쓸 안전한 slug (날짜 + 랜덤 숫자 조합, 윈도우/한글 파일명 이슈 회피)
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
- 전문용어가 나오면 바로 옆에 괄호로 쉬운 설명을 덧붙이기
- 각 소제목은 "그래서 뭘 하면 되는지" 결론부터 먼저 말하고 부가설명 이어가기

요구사항:
- 분량: 1200~1500자 내외의 실질적인 정보 (공백 포함)
- 서론(공감형 후킹, 키워드 포함) - 본론(소제목 3~4개) - 결론(요약) - Q&A(1~2개) 구조
- 본론 중 최소 1개 소제목에는 핵심 절차/서류/조건을 정리한 체크리스트(3개 이상 항목) 포함
- 본론 중 자연스러운 곳에, 공식 신청처(정부24, 국민연금공단, 홈택스 등 주제에 맞는 공식기관)를
  확인해보라고 안내하는 문장을 1개 포함 (예: "정부24에서 본인이 지원대상인지 바로 확인해보실 수 있어요")
- 의학적/법적 조언처럼 단정하지 말고 "전문가와 상담하세요" 같은 문구를 필요한 곳에 자연스럽게 포함
- 과장된 효능/보장 표현 금지 (예: "무조건", "100% 효과")
- 광고성 문구, 특정 제품 브랜드명 언급 금지

아래 JSON 형식으로만 응답해. 다른 설명이나 마크다운 코드블럭 없이 순수 JSON만 출력해.
{{
  "title": "글 제목 (30자 내외, 키워드 앞배치, 질문형/해결형)",
  "meta_description": "검색 결과에 노출될 요약 (80자 내외)",
  "sections": [
    {{"heading": "소제목1", "body": "본문 내용 (HTML 태그 없이 순수 텍스트, 문단은 \\n\\n으로 구분)", "checklist": null}},
    {{"heading": "소제목2 (체크리스트 넣을 소제목)", "body": "본문 내용", "checklist": ["체크항목1", "체크항목2", "체크항목3"]}},
    {{"heading": "소제목3", "body": "..."}}
  ],
  "intro": "서론 부분 텍스트 (첫 1~2문장에 메인 키워드 포함)",
  "conclusion": "결론/요약 부분 텍스트",
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
{sections_html}
<div class="post-conclusion"><h2>정리하며</h2><p>{conclusion}</p></div>
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


def render_post_html(post, date_str):
    sections_html = ""
    for sec in post["sections"]:
        sections_html += f"<h2>{html_lib.escape(sec['heading'])}</h2>\n"
        sections_html += paragraphs_to_html(sec["body"]) + "\n"
        checklist = sec.get("checklist")
        if checklist:
            items = "".join(f"<li>{html_lib.escape(item)}</li>" for item in checklist)
            sections_html += f'<ul class="checklist">{items}</ul>\n'

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
        sections_html=sections_html,
        conclusion=html_lib.escape(post["conclusion"]),
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

    today = datetime.date.today().isoformat()
    slug = slugify(post["title"], today)

    html_out = render_post_html(post, today)
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
