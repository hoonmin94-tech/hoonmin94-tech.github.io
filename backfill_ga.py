"""
posts/ 폴더 안 '기존에 이미 만들어진' 글 파일들에 구글 애널리틱스(GA4) 추적 코드를
한 번에 넣어주는 일회성 스크립트.

새로 만드는 글은 generate_post.py가 알아서 GA 코드를 넣어주지만, 이 스크립트를
돌리기 "전에" 이미 만들어져 있던 글들에는 GA 코드가 없어서 방문자 추적이 안 됩니다.
이 스크립트를 한 번만 실행하면 기존 글 전체에 GA 코드가 빠짐없이 들어갑니다.

이미 GA 코드가 들어있는 파일은 건너뛰기 때문에, 실수로 여러 번 실행해도
중복으로 들어가지 않습니다 (안전하게 다시 실행 가능).

실행: python backfill_ga.py
"""

import os
import re

POSTS_DIR = "posts"
GA_ID = "G-CJJ7DZYG8Q"

SNIPPET = f"""<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());

  gtag('config', '{GA_ID}');
</script>
"""


def main():
    if not os.path.isdir(POSTS_DIR):
        print("posts 폴더가 없습니다.")
        return

    updated = 0
    skipped = 0

    for fname in sorted(os.listdir(POSTS_DIR)):
        if not fname.endswith(".html"):
            continue
        path = os.path.join(POSTS_DIR, fname)
        with open(path, encoding="utf-8") as f:
            content = f.read()

        if GA_ID in content:
            skipped += 1
            continue

        new_content, n = re.subn(r"(<head>\n)", r"\1" + SNIPPET, content, count=1)
        if n == 0:
            print(f"[건너뜀 - <head> 못 찾음] {fname}")
            continue

        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        updated += 1

    print(f"[완료] {updated}개 파일에 GA 코드 추가, {skipped}개는 이미 있어서 건너뜀")


if __name__ == "__main__":
    main()
