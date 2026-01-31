# GitHub App / Branch Protection Setup

이 문서는 **AI 리뷰/자동수정/자동 머지**를 위해 필요한 GitHub 권한/보호 규칙을 적용하는 방법을 정리합니다.

## 1) GitHub App 권한
필수 권한:
- Pull requests: Read & write
- Contents: Read & write
- Checks: Read & write
- Issues: Read & write

선택 권한:
- Actions: Read (workflow_run 이벤트 확인용)

## 2) Repository settings
- **Auto-merge** 활성화
- Default merge method: **Rebase**

## 3) Branch protection rules (예시)
대상 브랜치: `main`

필수 체크:
- `ai_suitability`

필수 리뷰:
- AI가 남긴 리뷰 승인 또는 차단 상태에 따라 병합 결정

권장:
- Require status checks to pass before merging
- Require branches to be up to date before merging

## 4) Secrets
- `OPENAI_API_KEY`
- `OPENAI_ORG` (옵션)
- `OPENAI_PROJECT` (옵션)
- `AI_GITHUB_TOKEN`
