"""
posts/ 폴더 안 글들을 스캔해서 index.html과 posts.json을 처음부터 새로 만드는 스크립트.

- 각 글 파일(posts/*.html) 맨 위의 <!--POST_META:{...}--> 주석에서 제목/주제/날짜를 읽어옴
- 매번 posts/ 폴더 전체를 다시 스캔해서 "완전히 새로" 만들기 때문에, 이전 posts.json 내용에
  의존하지 않음 -> 이 스크립트를 아무리 여러 번 실행해도 결과가 항상 똑같음(=충돌이 날 수가 없음)
- main 브랜치에 새 글이 merge될 때마다 GitHub Actions가 이 스크립트를 자동으로 실행하고,
  바로 main에 커밋함 (PR 필요 없음 - 사람이 쓴 글 내용은 그대로 두고, 목록만 다시 만드는 것뿐이라 안전)

실행: python rebuild_index.py
"""

import os
import re
import json
import html as html_lib
import datetime

POSTS_DIR = "posts"
POSTS_JSON = "posts.json"
INDEX_FILE = "index.html"
SITE_NAME = "생활 정보 블로그"
KST = datetime.timezone(datetime.timedelta(hours=9))

META_RE = re.compile(r"<!--POST_META:(.*?)-->")
H1_RE = re.compile(r"<h1>(.*?)</h1>", re.DOTALL)

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


def load_legacy_posts_json():
    """POST_META 주석이 생기기 전(마이그레이션 이전)에 쓰인 글들의 제목/주제 정보를
    옛날 posts.json에서 slug 기준으로 찾아 쓰기 위한 사전(dict)을 만든다."""
    legacy = {}
    if os.path.exists(POSTS_JSON):
        try:
            with open(POSTS_JSON, encoding="utf-8") as f:
                data = json.load(f)
            for p in data:
                if "slug" in p:
                    legacy[p["slug"]] = p
        except Exception:
            pass
    return legacy


def scan_posts():
    posts = []
    if not os.path.isdir(POSTS_DIR):
        return posts

    legacy = load_legacy_posts_json()

    for fname in sorted(os.listdir(POSTS_DIR)):
        if not fname.endswith(".html"):
            continue
        path = os.path.join(POSTS_DIR, fname)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        head = content[:2000]  # 메타 주석은 파일 맨 앞부분에 있으므로 앞부분만 읽으면 충분

        m = META_RE.search(head)
        if m:
            try:
                posts.append(json.loads(m.group(1)))
                continue
            except json.JSONDecodeError:
                pass

        slug = fname[:-5]
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})", slug)
        fallback_date = date_match.group(1) if date_match else "1970-01-01"

        # 1순위: 마이그레이션 이전 글 -> 옛 posts.json에 저장돼있던 제목/주제 그대로 사용
        if slug in legacy:
            entry = legacy[slug]
            posts.append({
                "slug": slug,
                "title": entry.get("title", slug),
                "topic": entry.get("topic", ""),
                "date": entry.get("date", fallback_date),
            })
            continue

        # 2순위: posts.json에도 없으면 글 본문의 <h1> 제목을 그대로 가져다 씀
        h1_match = H1_RE.search(content)
        title = h1_match.group(1).strip() if h1_match else slug
        posts.append({"slug": slug, "title": title, "topic": "", "date": fallback_date})

    return posts


def render_index(posts):
    items = ""
    for p in posts:
        # 어디서 가져온 제목이든(메타 주석/옛 posts.json/h1 추출) 한 번 unescape 후
        # 다시 escape 해서 이중 이스케이프(&amp;amp; 같은) 없이 안전하게 통일함
        clean_title = html_lib.escape(html_lib.unescape(p["title"]))
        items += (
            f'<li><a href="posts/{p["slug"]}.html">{clean_title}</a>'
            f'<span class="date"> - {p["date"]}</span></li>\n'
        )
    return INDEX_TEMPLATE.format(
        site_name=SITE_NAME, items=items, year=datetime.datetime.now(KST).year
    )


def main():
    posts = scan_posts()
    # 최신 글이 위로 오도록 날짜 내림차순, 같은 날짜면 slug 내림차순(대략 최근 생성 순)
    posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)

    with open(POSTS_JSON, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(render_index(posts))

    print(f"[완료] 글 {len(posts)}개 기준으로 index.html / posts.json 재생성함")


if __name__ == "__main__":
    main()
