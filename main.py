import os
import requests
import json
from datetime import datetime, timedelta
import time
import sys
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# API 설정
API_KEY = os.getenv('FISIS_API_KEY')
BASE_URL = "https://fisis.fss.or.kr/openapi/statisticsInfoSearch.json"
ACCOUNT_CD = "A"
FINANCE_CD = "0010635"
LIST_NO = "SI021"
LANG = "kr"
TERM = "Q"

# ntfy.sh 설정
NTFY_TOPIC = "stock-info"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

def get_current_yyyymm():
    """현재 날짜를 YYYYMM 형식으로 반환"""
    now = datetime.now()
    return now.strftime("%Y%m")

def generate_months(start_yyyymm, count=12):
    """시작 연월부터 과거로 count개월 동안의 연월 목록 생성"""
    months = []
    current = datetime.strptime(start_yyyymm, "%Y%m")

    for _ in range(count):
        months.append(current.strftime("%Y%m"))
        # 1개월 전으로 이동
        if current.month == 1:
            current = datetime(current.year - 1, 12, 1)
        else:
            current = datetime(current.year, current.month - 1, 1)

    return months

def call_fisis_api(start_yyyymm, end_yyyymm):
    """FISIS API 호출"""
    params = {
        "auth": API_KEY,
        "accountCd": ACCOUNT_CD,
        "financeCd": FINANCE_CD,
        "listNo": LIST_NO,
        "lang": LANG,
        "term": TERM,
        "startBaseMm": start_yyyymm,
        "endBaseMm": end_yyyymm
    }

    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API 호출 실패: {e}")
        return None

def check_for_new_data(data):
    """새로운 데이터가 있는지 확인"""
    if not data or "result" not in data:
        return False

    result = data["result"]
    if result["err_cd"] != "000":
        print(f"API 오류: {result['err_msg']}")
        return False

    # list가 존재하고 비어있지 않은 경우 새로운 데이터가 있는 것으로 간주
    if "list" in result and result["list"]:
        return True

    return False

def send_ntfy_notification(message):
    """ntfy.sh로 알림 전송"""
    try:
        response = requests.post(
            NTFY_URL,
            data=message.encode('utf-8'),
            headers={"Content-Type": "text/plain"}
        )
        response.raise_for_status()
        print("알림 전송 성공")
        return True
    except requests.exceptions.RequestException as e:
        print(f"알림 전송 실패: {e}")
        return False

def monitor_fisis_data():
    """FISIS 데이터 모니터링 메인 함수"""
    print("FISIS 데이터 모니터링 시작...")

    # 현재 연월 가져오기
    current_yyyymm = get_current_yyyymm()
    print(f"현재 연월: {current_yyyymm}")

    # 과거 12개월 동안의 연월 목록 생성
    months = generate_months(current_yyyymm, 12)
    print(f"모니터링할 연월 목록: {months}")

    # 각 연월에 대해 API 호출
    for i, month in enumerate(months):
        print(f"\n{month} 데이터 확인 중...")

        # API 호출
        data = call_fisis_api(month, month)

        if data is None:
            continue

        # 새로운 데이터 확인
        if check_for_new_data(data):
            message = f"새로운 FISIS 데이터 발견!\n연월: {month}\n데이터: {json.dumps(data['result']['list'], indent=2, ensure_ascii=False)}"
            print(message)

            # 알림 전송
            send_ntfy_notification(message)
        else:
            print(f"{month}에는 새로운 데이터가 없습니다.")

def keep_alive():
    """GitHub Action sleep 방지를 위한 self keep alive 기능"""
    print("Keep alive 시작...")
    start_time = time.time()

    while True:
        # 5분마다 메시지 출력 (GitHub Action은 60분 후 sleep)
        elapsed = time.time() - start_time
        print(f"Keep alive: 활성 상태 유지 중... ({elapsed:.0f}초 경과)")
        time.sleep(300)  # 5분 대기

if __name__ == "__main__":
    # 인수 확인
    if len(sys.argv) > 1 and sys.argv[1] == "keep-alive":
        keep_alive()
    else:
        monitor_fisis_data()
