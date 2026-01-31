# AutoReview-AI 작업 요약

## 이번 작업
- 언어/프레임워크 규칙 템플릿 추가(Python, FastAPI)
- 에이전트 프롬프트에 규칙 템플릿 포함
- AutoFix 재시도 정책(시도 횟수/백오프/패치 제한) 추가

## 생성/수정 파일
- `config/rules/python.yaml`
- `config/rules/fastapi.yaml`
- `config/review-policy.yaml`
- `scripts/ai_review.py`
- `scripts/ai_autofix.py`
- `.github/workflows/ai-autofix.yml`
