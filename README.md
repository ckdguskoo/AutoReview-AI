# AutoReview-AI

PR 생성부터 AI 리뷰, 자동 수정, rebase 자동 머지까지 이어지는 **AI 기반 코드 리뷰/PR 평가 자동화 시스템**입니다. GitHub Actions와 멀티 에이전트를 활용해 리뷰 품질과 일관성을 높이고, 위험도가 높은 변경은 자동으로 차단/수정하도록 설계되었습니다.

## 시스템 아키텍처

```mermaid
flowchart TD
  Dev[Developer Push/PR] --> PR[GitHub PR]
  PR --> AR[Workflow: AI Review]
  AR --> ReviewScript[scripts/ai_review.py]
  ReviewScript -->|load| Configs[config/*.yaml]
  ReviewScript -->|diff/changed files| OpenAI[OpenAI Responses API]
  ReviewScript --> ReviewJson[ai_review.json]
  ReviewJson --> PostReview[PR Review Comment]
  ReviewJson --> Suitability[Check: ai_suitability]
  Suitability -->|pass| AutoMerge[Enable auto-merge (rebase)]
  Suitability -->|fail or blocking| AutoFixWF[Workflow: AI AutoFix]
  AutoFixWF --> AutoFixScript[scripts/ai_autofix.py]
  AutoFixScript --> OpenAI2[OpenAI Responses API]
  AutoFixScript --> Patch[git apply patch / marker replace]
  Patch --> PushBranch[Push auto/fix branch]
  PushBranch --> AutoFixPR[Create AutoFix PR]
```

## AI 활용 아키텍처
- 멀티 에이전트 리뷰는 `config/agent-prompts.yaml`의 프롬프트/스키마와 `config/review-policy.yaml`의 에이전트 순서를 사용합니다.
- 리뷰/자동수정 모델, 온도, 토큰 제한은 `config/review-policy.yaml`의 `ai` 섹션에서 제어됩니다.
- OpenAI 호출은 `scripts/ai_common.py`에서 Responses API로 수행됩니다.
- `OPENAI_API_KEY`가 없으면 AI 호출 대신 간단한 휴리스틱 검사(보안/자동수정 마커, 라인 길이 등)를 수행합니다.

## 컴포넌트별 역할
- GitHub Actions 워크플로
  - `AI Review`: PR 변경사항을 분석하고 리뷰 코멘트/체크 생성
  - `AI AutoFix`: 리뷰 실패 시 자동 수정 PR 생성
- 리뷰/자동수정 스크립트
  - `scripts/ai_review.py`: diff 기반 멀티 에이전트 리뷰 실행 및 결과 산출
  - `scripts/ai_autofix.py`: 수정 패치 생성/적용 및 PR 생성 메타데이터 출력
  - `scripts/ai_common.py`: OpenAI 호출, YAML/파일 유틸
- 정책/프롬프트/룰
  - `config/review-policy.yaml`: 리뷰/차단 정책, 모델 설정
  - `config/agent-prompts.yaml`: 에이전트 프롬프트/출력 스키마
  - `config/rules/*.yaml`: 언어/프레임워크 규칙 템플릿
- FastAPI 앱
  - `app/main.py`, `app/api/health.py`: 헬스 체크용 API

## 핵심 흐름
1. 사용자가 PR 생성
2. GitHub Actions가 AI 리뷰 실행 → PR 코멘트 + `ai_suitability` 체크 생성
3. 통과 시 rebase auto-merge 활성화
4. 실패 시 AutoFix가 자동 수정 브랜치/PR 생성

## 데이터 흐름
1. `AI Review` 워크플로가 PR의 base/head SHA로 diff와 변경 파일 목록을 수집합니다.
2. `scripts/ai_review.py`가 정책/프롬프트/룰을 로드해 OpenAI에 리뷰를 요청합니다.
3. 결과는 `ai_review.json`으로 저장되고, PR 코멘트와 `ai_suitability` 체크에 반영됩니다.
4. 차단 또는 부적합 판단 시 `AI AutoFix` 워크플로가 실행됩니다.
5. `scripts/ai_autofix.py`가 수정 패치를 생성/적용하고 `ai_autofix.json`에 결과를 저장합니다.
6. 수정이 적용되면 자동 수정 브랜치/PR이 생성됩니다.

## 주요 기능
- 멀티 에이전트 리뷰(Style/BugRisk/Performance/Security/Summary)
- 에이전트별 프롬프트/체크리스트 기반 리뷰
- OpenAI API 연동(리뷰/자동수정)
- AutoFix 안전장치(패치 크기/확장자 제한, 재시도 정책)
- 정책 기반 머지/차단 관리(`config/review-policy.yaml`)

## 빠른 실행(로컬)

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

헬스 체크:
```
GET http://127.0.0.1:8000/health
```

## 사용법(운영)
1. GitHub App 설치 및 권한 부여(필수 권한: Pull requests/Checks/Contents/Issues)
2. Repository Secrets 설정
   - 필수: `OPENAI_API_KEY`, `GH_APP_ID`, `GH_APP_PRIVATE_KEY`
   - 선택: `OPENAI_ORG`, `OPENAI_PROJECT`
3. 브랜치 보호 규칙에 `ai_suitability` 체크를 필수로 지정
4. PR을 생성하면 `AI Review`가 자동 실행되고 결과에 따라 auto-merge 또는 AutoFix가 동작

## 필수 설정(Repository Secrets)
- `OPENAI_API_KEY`
- `GH_APP_ID`
- `GH_APP_PRIVATE_KEY`

선택:
- `OPENAI_ORG`
- `OPENAI_PROJECT`

> GitHub App 토큰은 Actions에서 **자동 생성**합니다.

## 브랜치 보호 및 Auto-merge 설정(권장)
자동 설정 스크립트 사용:
```powershell
# gh auth login 필요
.\scripts\configure_github.ps1 -Owner "ORG" -Repo "REPO" -Branch "main"
```

## 테스트 체크리스트
- `TEST-CHECKLIST.md`

## 구성 파일
- `config/review-policy.yaml`: 머지/차단 정책
- `config/agent-prompts.yaml`: 에이전트 프롬프트/체크리스트
- `config/agents.yaml`: 에이전트 메타데이터(포커스/우선순위 등)
- `config/rules/*.yaml`: 언어/프레임워크 규칙 템플릿

## 개발/운영 FAQ

**Q. 리뷰/코멘트가 PR에 안 보입니다.**
- GitHub App 권한 확인(Pull requests/Checks/Contents/Issues)
- GitHub App이 해당 저장소에 설치되어 있는지 확인
- `GH_APP_ID`, `GH_APP_PRIVATE_KEY` 설정 여부 확인

**Q. `ai_suitability` 체크가 생성되지 않습니다.**
- Actions 실행 여부 확인
- `OPENAI_API_KEY`가 설정되어 있는지 확인

**Q. AutoFix PR이 생성되지 않습니다.**
- Auto-merge 활성화 여부 확인
- 브랜치 보호 규칙에 `ai_suitability` 필수 체크가 설정되어 있는지 확인

**Q. 비용을 줄이려면 어떻게 하나요?**
- `config/review-policy.yaml`에서 모델/토큰 제한을 낮추고, 룰 템플릿을 강화해 AI 호출량을 줄입니다.
