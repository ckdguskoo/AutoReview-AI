# AutoReview-AI 사용자용 설치 가이드

이 문서는 **다른 사용자가 이 저장소를 설치/운영**할 수 있도록 최소 절차를 정리합니다.

## 1) 사전 준비
- GitHub 계정
- GitHub Actions 사용 가능 권한
- OpenAI API 키
- GitHub App 또는 PAT (권장: GitHub App)

## 2) 저장소 준비
1. 이 저장소를 자신의 GitHub에 복사(포크/클론)합니다.
2. GitHub Actions가 실행 가능하도록 설정합니다.

## 3) GitHub App 생성/설치
### 권장 권한
- Pull requests: Read & write
- Contents: Read & write
- Checks: Read & write
- Issues: Read & write

App을 대상 저장소에 **설치**합니다.

## 4) Repository Secrets 설정
`Settings → Secrets and variables → Actions`에서 아래를 추가합니다.
- `OPENAI_API_KEY` (필수)
- `OPENAI_ORG` (선택)
- `OPENAI_PROJECT` (선택)
- `AI_GITHUB_TOKEN` (GitHub App 설치 토큰)

## 5) 브랜치 보호 및 Auto-merge (권장: 자동 설정 스크립트)
**권장 방법:** 프로젝트 폴더에서 자동 설정 스크립트를 실행합니다.

```powershell
# gh CLI 로그인 필요
# gh auth login

.\scripts\configure_github.ps1 -Owner "ORG" -Repo "REPO" -Branch "main"
```

수동으로 설정하려면 아래를 적용하세요.
1. Auto-merge 활성화
2. Default merge method: **rebase**
3. Branch protection rules에서 아래 체크를 필수로 설정
   - `ai_suitability`

## 6) 정책/프롬프트 수정
- 정책: `config/review-policy.yaml`
- 에이전트 프롬프트: `config/agent-prompts.yaml`
- 룰 템플릿: `config/rules/*.yaml`

## 7) 사용 방법
1. 사용자가 PR 생성
2. Actions가 자동 실행되어 AI 리뷰 등록
3. 적합성 통과 시 rebase auto-merge
4. 실패 시 AutoFix가 수정 PR 자동 생성

## 8) 문제 해결(간단)
- 리뷰/PR 코멘트가 안 보이면: `AI_GITHUB_TOKEN` 권한 확인
- 체크가 실패하면: `OPENAI_API_KEY` 유효성 확인
- AutoFix PR이 안 뜨면: Auto-merge/브랜치 보호 설정 확인
- 스크립트 실행이 실패하면: `gh` 설치 및 로그인 확인
