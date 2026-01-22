# FISISMonitor

FISIS (금융감독원 금융정보시스템) 데이터 모니터링 도구

## 기능

- FISIS API를 통해 금융 데이터 모니터링
- 새로운 데이터 감지 시 ntfy.sh로 알림 전송
- GitHub Action을 통한 자동화 실행 (1시간 간격)
- Self keep alive 기능으로 GitHub Action sleep 방지

## 설정 방법

1. **API 키 설정**:
   - `.env` 파일에 FISIS API 키를 설정합니다:
     ```
     FISIS_API_KEY=your_api_key_here
     ```
   - `.env` 파일은 `.gitignore`에 포함되어 있으므로 안전하게 관리됩니다.

2. **의존성 설치**:
   ```
   pip install -r requirements.txt
   ```

3. **GitHub Action 설정**:
   - GitHub 저장소의 Settings > Secrets > Actions에서 `FISIS_API_KEY`를 추가합니다.
   - `.github/workflows/monitor.yml` 파일이 자동으로 실행됩니다.

## 실행 방법

### 로컬 실행
```
python main.py
```

### Keep Alive 모드 (GitHub Action용)
```
python main.py keep-alive
```

## GitHub Action

- 매시간 0분에 자동 실행됩니다.
- 12개월 치 데이터를 확인합니다.
- 새로운 데이터가 감지되면 ntfy.sh/stock-info로 알림을 전송합니다.

## 주의사항

- API 키는 절대 코드에 노출되지 않도록 주의하세요.
- ntfy.sh 토픽은 필요에 따라 변경할 수 있습니다.
- GitHub Action은 60분 후 sleep되므로 keep-alive 기능이 필수적입니다.
