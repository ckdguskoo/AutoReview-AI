# AutoReview-AI 현재 구현 상태

## 핵심 흐름
- 사용자가 PR 생성
- GitHub Actions 자동 실행
- AI 리뷰 코멘트 작성 + 적합성 체크 생성
- 통과 시 rebase auto-merge 활성화
- 실패 시 AutoFix 자동 수정 PR 생성

## 구현된 기능
- FastAPI 기본 헬스체크 API
- 멀티 에이전트 설정(Style/BugRisk/Performance/Security/Summary)
- 에이전트별 프롬프트/스키마/체크리스트/심각도 가이드
- 리뷰 정책 파일(차단 기준, 코멘트 캡, 중복 제거)
- OpenAI API 연동(리뷰/자동수정)
- AutoFix 안전장치(패치 크기/확장자 제한, 재시도 정책)
- GitHub Actions 워크플로우(리뷰/자동수정)
- GitHub App/브랜치 보호 설정 문서 및 자동 설정 스크립트
- 사용자 설치 가이드 문서

## 필수 설정(사용자 추가)
- `OPENAI_API_KEY`
- `AI_GITHUB_TOKEN`

## 선택 설정
- `OPENAI_ORG`
- `OPENAI_PROJECT`

## 리포지토리 설정
- Auto-merge 활성화
- rebase merge 허용
- `ai_suitability` 체크 필수 브랜치 보호
