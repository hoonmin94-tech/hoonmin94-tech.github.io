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
import email.utils

POSTS_DIR = "posts"
POSTS_JSON = "posts.json"
INDEX_FILE = "index.html"
SITEMAP_FILE = "sitemap.xml"
RSS_FILE = "rss.xml"
SITE_NAME = "생활 정보 블로그"
SITE_URL = "https://hoonmin94-tech.github.io"
KST = datetime.timezone(datetime.timedelta(hours=9))

META_RE = re.compile(r"<!--POST_META:(.*?)-->")
H1_RE = re.compile(r"<h1>(.*?)</h1>", re.DOTALL)

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<!-- 네이버 서치어드바이저 사이트 소유 확인용 태그 (지우면 인증이 풀리니 삭제 금지) -->
<meta name="naver-site-verification" content="25108df4ed28cc3d6b5232fc23a305ebb0fee260" />
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-CJJ7DZYG8Q"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());

  gtag('config', 'G-CJJ7DZYG8Q');
</script>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{site_name}</title>
<link rel="stylesheet" href="style.css">
<link rel="alternate" type="application/rss+xml" title="{site_name}" href="rss.xml">
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
<p class="related-sites">함께 운영 중인 사이트: <a href="https://ichaniya.co.kr" target="_blank" rel="noopener">이차니야 육아정보</a> · <a href="https://blog.naver.com/hoonmin1994" target="_blank" rel="noopener">네이버 블로그</a></p>
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


def render_sitemap(posts):
    """검색엔진(구글/네이버)이 이 사이트에 어떤 글들이 있는지 한눈에 알 수 있도록
    정적 페이지 4개 + 글 전체 목록을 sitemap.xml로 만든다.
    (이전 버전은 정적 페이지 4개만 들어있고 실제 글은 하나도 안 들어있었음 -> 수정됨)"""
    today = datetime.datetime.now(KST).date().isoformat()
    urls = [
        ("", today),
        ("about.html", today),
        ("contact.html", today),
        ("privacy.html", today),
    ]
    for p in posts:
        urls.append((f"posts/{p['slug']}.html", p.get("date", today)))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, lastmod in urls:
        loc = html_lib.escape(f"{SITE_URL}/{path}")
        lines.append(f"  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod></url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def render_rss(posts):
    """네이버 서치어드바이저의 'RSS 제출' 기능에 쓸 rss.xml을 만든다.
    RSS를 등록해두면 새 글이 올라올 때마다 네이버가 더 빠르게 알아채고 크롤링해간다.
    (전체 글을 다 넣으면 파일이 계속 커지므로, 최신 20개만 넣음 - 일반적인 관행)"""
    limited = posts[:20]
    channel_link = f"{SITE_URL}/"
    now_rfc822 = email.utils.format_datetime(datetime.datetime.now(KST))

    items = []
    for p in limited:
        link = html_lib.escape(f"{SITE_URL}/posts/{p['slug']}.html")
        title = html_lib.escape(html_lib.unescape(p["title"]))
        try:
            d = datetime.date.fromisoformat(p.get("date", ""))
            pub_date = email.utils.format_datetime(
                datetime.datetime(d.year, d.month, d.day, tzinfo=KST)
            )
        except (ValueError, TypeError):
            pub_date = now_rfc822
        items.append(
            "  <item>\n"
            f"    <title>{title}</title>\n"
            f"    <link>{link}</link>\n"
            f"    <guid>{link}</guid>\n"
            f"    <pubDate>{pub_date}</pubDate>\n"
            "  </item>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0"><channel>\n'
        f"  <title>{SITE_NAME}</title>\n"
        f"  <link>{channel_link}</link>\n"
        f"  <description>{SITE_NAME} 최신 글</description>\n"
        f"  <lastBuildDate>{now_rfc822}</lastBuildDate>\n"
        + "\n".join(items) +
        "\n</channel></rss>\n"
    )


def main():
    posts = scan_posts()
    # 최신 글이 위로 오도록 날짜 내림차순, 같은 날짜면 slug 내림차순(대략 최근 생성 순)
    posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)

    with open(POSTS_JSON, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(render_index(posts))

    with open(SITEMAP_FILE, "w", encoding="utf-8") as f:
        f.write(render_sitemap(posts))

    with open(RSS_FILE, "w", encoding="utf-8") as f:
        f.write(render_rss(posts))

    print(f"[완료] 글 {len(posts)}개 기준으로 index.html / posts.json / sitemap.xml / rss.xml 재생성함")


if __name__ == "__main__":
    main()
