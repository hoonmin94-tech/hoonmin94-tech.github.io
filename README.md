# 자동 블로그 포스팅 시스템 - 설정 가이드

## 1. GitHub 저장소 만들기
1. github.com 에서 새 저장소 생성 (예: `my-parenting-blog`), Public으로 설정
2. 이 폴더 안 파일 전부를 저장소에 업로드 (기존 사이트 파일이 있으면 같이 합치기)

## 2. Anthropic API 키 발급
1. console.anthropic.com 접속 → 로그인
2. 왼쪽 메뉴 "API Keys" → "Create Key" 눌러서 키 생성 (sk-ant-로 시작하는 문자열)
3. 결제수단 등록 필요 (하루 3개 글 기준 한 달 몇천원 수준)

## 3. GitHub 저장소에 API 키 등록 (절대 코드에 직접 넣지 말 것)
1. 저장소 페이지 → Settings → Secrets and variables → Actions
2. "New repository secret" 클릭
3. Name: `ANTHROPIC_API_KEY`
4. Secret: 위에서 발급받은 키 붙여넣기 → Add secret

## 4. GitHub Pages 켜기 (사이트를 실제로 공개하는 단계)
1. 저장소 Settings → Pages
2. Source: "Deploy from a branch" → Branch: main / 폴더: `/ (root)` 선택 → Save
3. 몇 분 후 `https://[아이디].github.io/[저장소이름]/` 주소로 사이트 접속 가능

## 5. 자동 실행 & 검토/발행 방식
- `.github/workflows/auto-post.yml` 덕분에 매일 08:00 / 13:00 / 20:00(한국시간)에 자동으로 **초안이 생성되고 PR(Pull Request)이 만들어집니다** (바로 사이트에 올라가지 않음)
- 저장소 상단 "Pull requests" 탭에서 새 PR 확인 → 글 내용 읽어보고 → 문제없으면 **Merge pull request** 버튼 클릭 → 그 즉시 사이트에 반영
- 폰에서도 GitHub 앱으로 PR 확인하고 Merge 가능
- 마음에 안 드는 글은 그냥 Close 하면 사이트에 안 올라감
- 수정하고 싶으면 PR 안에서 파일 직접 편집 후 Merge
- 지금 바로 테스트하고 싶으면 Actions 탭 → "Auto Blog Draft" → "Run workflow" 버튼으로 즉시 실행

## 6. 주제 관리
- `topics.txt` 파일에 한 줄에 주제 하나씩 적혀 있음 (현재는 생활정보 위주 예시로 채워둠)
- 자유롭게 추가/삭제/수정 가능. 최근 15개 글과 겹치는 주제는 자동으로 피해서 선택됨
- 육아 블로그는 별도로 직접 운영하시는 걸로 알고 있어서, 이 저장소는 정보성 블로그(블로그2) 전용으로 세팅했습니다

## 7. 이미 자체 호스팅(카페24 등) 중이라 GitHub Pages를 안 쓴다면
- 4번 단계는 건너뛰고, generate_post.py 실행 후 posts/ index.html 을 FTP로 업로드하는 스텝을 워크플로우에 추가해야 합니다
- 이 경우 알려주시면 FTP 업로드 버전으로 바꿔드릴게요

## 주의사항
- 애드센스 심사 중에는 콘텐츠 품질이 중요합니다. 생성된 글을 가끔 직접 확인해서 이상한 내용 없는지 체크하는 걸 추천해요
- 과장/보장성 표현은 프롬프트에서 이미 금지시켜뒀지만, 초반 며칠은 결과물을 검수하시는 게 안전합니다
