import os
import requests
import json
from datetime import datetime, timedelta, timezone
import time
import sys
from dotenv import load_dotenv

# 최종월 저장 파일 경로
LAST_MONTH_FILE = "last_month.txt"

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

def get_kst_now():
    """한국 시간(KST) 현재 datetime 반환"""
    # GitHub Actions 환경(UTC)에서도 한국 시간을 정확히 구하기 위해 timezone.utc 사용
    return datetime.now(timezone.utc) + timedelta(hours=9)

def get_current_yyyymm():
    """현재 날짜를 KST 기준 YYYYMM 형식으로 반환"""
    return get_kst_now().strftime("%Y%m")

def get_last_month():
    """저장된 최종월을 가져오거나 기본값 반환"""
    if os.path.exists(LAST_MONTH_FILE):
        try:
            with open(LAST_MONTH_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception as e:
            print(f"최종월 파일 읽기 오류: {e}")

    # 기본값: 6개월 전 분기 월
    now = get_kst_now()
    # 대략 6개월 전으로 이동하여 가장 가까운 이전 분기말 찾기
    last_date = now - timedelta(days=180)
    month = last_date.month
    # 분기월(3, 6, 9, 12)로 조정
    adj_month = (month // 3) * 3
    if adj_month == 0:
        return f"{last_date.year - 1}12"
    return f"{last_date.year}{adj_month:02d}"

def save_last_month(yyyymm):
    """최종월을 파일에 저장"""
    try:
        with open(LAST_MONTH_FILE, 'w') as f:
            f.write(yyyymm)
        print(f"최종월 저장: {yyyymm}")
    except Exception as e:
        print(f"최종월 파일 쓰기 오류: {e}")

def call_fisis_api(yyyymm):
    """FISIS API 호출"""
    if not API_KEY:
        print("에러: FISIS_API_KEY 환경변수가 설정되지 않았습니다.")
        return None

    params = {
        "auth": API_KEY,
        "accountCd": ACCOUNT_CD,
        "financeCd": FINANCE_CD,
        "listNo": LIST_NO,
        "lang": LANG,
        "term": TERM,
        "startBaseMm": yyyymm,
        "endBaseMm": yyyymm
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API 호출 실패 ({yyyymm}): {e}")
        return None

def check_for_new_data(data):
    """새로운 데이터가 있는지 확인"""
    if not data or "result" not in data:
        return False

    result = data["result"]
    # err_cd "000" 이 정상
    if result.get("err_cd") != "000":
        return False

    # list가 존재하고 비어있지 않은 경우 새로운 데이터가 있는 것으로 간주
    if "list" in result and result["list"]:
        return True

    return False

def send_ntfy_notification(month, data_list):
    """ntfy.sh로 알림 전송"""
    try:
        item = data_list[0]
        finance_nm = item.get('finance_nm', '금융기관')
        account_nm = item.get('account_nm', '항목')
        value = item.get('a', '값 없음')

        message = f"새로운 FISIS 데이터가 등록되었습니다.\n\n대상: {finance_nm}\n기준월: {month}\n항목: {account_nm}\n값: {value}"

        # ntfy.sh에 JSON 형식으로 알림 전송 (한글 헤더 오류 방지)
        payload = {
            "topic": NTFY_TOPIC,
            "message": message,
            "title": "FISIS 데이터 업데이트 알림",
            "priority": 3,  # 3: default
            "tags": ["chart_with_upwards_trend", "moneybag"]
        }

        response = requests.post(
            "https://ntfy.sh/",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        print(f"알림 전송 성공: {month}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"알림 전송 실패: {e}")
        return False

def monitor_fisis_data():
    """FISIS 데이터 모니터링 메인 함수"""
    kst_now = get_kst_now()
    print(f"FISIS 데이터 모니터링 시작... (KST: {kst_now.strftime('%Y-%m-%d %H:%M:%S')})")

    current_yyyymm = get_current_yyyymm()
    last_saved_month = get_last_month()

    print(f"현재 연월: {current_yyyymm}")
    print(f"마지막 저장된 데이터 연월: {last_saved_month}")

    # 현재 월부터 마지막 저장 월 다음달까지 역순으로 리스트 생성
    curr_dt = datetime.strptime(current_yyyymm, "%Y%m")
    last_dt = datetime.strptime(last_saved_month, "%Y%m")

    months_to_check = []
    temp_dt = curr_dt
    while temp_dt > last_dt:
        months_to_check.append(temp_dt.strftime("%Y%m"))
        # 1개월 전으로 이동
        if temp_dt.month == 1:
            temp_dt = datetime(temp_dt.year - 1, 12, 1)
        else:
            temp_dt = datetime(temp_dt.year, temp_dt.month - 1, 1)

    if not months_to_check:
        print("이미 최신 월까지 확인이 완료되었습니다.")
        return

    print(f"확인 대상 기간: {months_to_check[-1]} ~ {months_to_check[0]}")

    new_latest_month = None

    # 거꾸로 올라가면서 확인 (최신 월부터 과거 순)
    for month in months_to_check:
        # 분기 월(3, 6, 9, 12)만 확인
        if int(month[4:]) % 3 != 0:
            continue

        print(f"{month} API 호출 중...")
        data = call_fisis_api(month)

        if check_for_new_data(data):
            print(f"-> {month} 데이터 발견!")
            send_ntfy_notification(month, data["result"]["list"])

            # 발견된 데이터 중 가장 최신 월을 새 최종월로 설정
            if new_latest_month is None:
                new_latest_month = month
            # 이미 최신 데이터를 찾았으므로 루프를 계속 돌며 이전 데이터들도 알림을 보낼지 결정
            # 여기서는 루프를 계속 돌아 과거 데이터 중 안 보낸 것도 확인하도록 함
        else:
            print(f"-> {month} 데이터 없음")

    # 상태 업데이트 (데이터가 발견된 경우 그 중 최신 월로 업데이트)
    if new_latest_month:
        save_last_month(new_latest_month)
    else:
        print("새롭게 등록된 데이터가 없습니다.")

def keep_alive():
    """GitHub Action의 sleep을 방지하기 위한 self keep alive 기능"""
    print("Keep alive 시작...")
    # 단순히 프로세스를 유지하는 것은 GitHub Action의 60일 비활성화 방지에 도움이 되지 않음
    # 하지만 사용자 요구사항에 따라 5분간 활성 상태를 유지하는 로그를 남김
    for i in range(5):
        print(f"Keep alive: 동작 중... ({i+1}/5)")
        time.sleep(60)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "keep-alive":
        keep_alive()
    else:
        monitor_fisis_data()
