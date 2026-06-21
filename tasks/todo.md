# GitHub Actions Node 20 경고 수정

## 계획
- [x] 워크플로에서 Node 20 기반으로 경고가 나는 액션 참조 확인
- [x] 공식 릴리스 기준으로 대응할 최신 major 버전 확인
- [x] `.github/workflows/FISIS_monitor.yaml`의 액션 버전 갱신
- [x] 표준 테스트/검증 명령 확인 및 실행
- [x] diff와 비밀정보 포함 여부 점검
- [x] 커밋 및 현재 브랜치로 푸시

## 리뷰
- 표준 테스트 명령은 없음
- 검증: `python3 -m py_compile main.py` 통과
- 검증: Ruby YAML 파싱 통과
- 참고: Python YAML 파싱은 로컬 `PyYAML` 미설치로 실행 불가
- 비밀정보 패턴 검색: 발견 없음
