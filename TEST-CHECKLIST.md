# AutoReview-AI 테스트 체크리스트

## 1) 레포 준비
- [ ] 테스트용 GitHub 레포 생성
- [ ] 이 프로젝트 파일을 레포에 추가
- [ ] GitHub Actions 활성화

## 2) GitHub App 설치
- [ ] GitHub App 생성 및 레포에 설치
- [ ] 권한 확인 (Pull requests / Contents / Checks / Issues: Read & Write)

## 3) Secrets 설정
- [ ] `OPENAI_API_KEY`
- [ ] `GH_APP_ID`
- [ ] `GH_APP_PRIVATE_KEY`
- [ ] `OPENAI_ORG` (선택)
- [ ] `OPENAI_PROJECT` (선택)

## 4) 레포 설정
- [ ] Auto-merge 활성화
- [ ] rebase merge 허용
- [ ] `ai_suitability` 체크를 브랜치 보호 규칙에 추가
- [ ] (선택) 자동 설정 스크립트 실행

## 5) 테스트 실행
- [ ] 테스트 브랜치 생성
- [ ] 변경 커밋
- [ ] PR 생성
- [ ] AI 리뷰 코멘트 생성 확인
- [ ] `ai_suitability` 체크 생성 확인
- [ ] 통과 시 auto-merge 작동 확인
- [ ] 실패 시 AutoFix PR 생성 확인
