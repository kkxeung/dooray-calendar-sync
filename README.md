# Dooray! → Google Calendar Sync

Dooray! 캘린더 이벤트를 Google Calendar로 **단방향 동기화**하는 Python 스크립트입니다.

## 핵심 기능

- Dooray → Google 단방향 동기화
- 이벤트 **추가 / 수정 / 삭제** 반영
- 동기화 상태(`sync_state.json`) 기반 중복 방지
- 동기화 윈도우(기본: 현재달+다음달) 밖의 과거 이벤트 보호
- Google 기본 알림 자동 비활성화
- `config.json` + 환경변수 기반 설정
- `--dry-run` 지원 (실제 반영 없이 변경점 미리보기)

---

## 빠른 시작 (Linux 서버 기준)

```bash
apt install -y python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 requests

cp config.example.json config.json
python3 sync_calendar.py --dry-run
python3 sync_calendar.py
```

> Ubuntu 24 계열에서는 시스템 Python에 `pip install`이 바로 막힐 수 있으므로 `venv` 사용을 권장합니다.  
> 대부분의 Linux 환경에서는 `python` 대신 `python3`를 사용하세요.

---

## 요구 사항

- Python 3.10+
- Google 계정 (Calendar API 사용 가능)
- Dooray API 토큰

필수 패키지:

```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 requests
```

---

## 1) Google Calendar API 설정

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
2. **Google Calendar API** 활성화
3. **OAuth Client ID (Desktop app)** 생성
4. JSON 다운로드 후 프로젝트 루트에 `credentials.json`으로 저장

### 브라우저가 가능한 환경
첫 실행 시 브라우저 인증 후 `token.json`이 자동 생성됩니다.

### Linux 서버 / 헤드리스 환경
브라우저를 열 수 없는 서버에서는 Google OAuth 인증 단계에서 실패할 수 있습니다.  
이 경우 **로컬 PC에서 `token.json`을 만든 뒤 서버에 복사**해서 사용하세요.

#### 1-1. 로컬 PC에서 `token.json` 생성

`credentials.json`을 로컬 PC 작업 폴더에 둔 뒤 아래 스크립트를 실행합니다.

`make_token.py`

```python
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]

flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=0)

with open("token.json", "w", encoding="utf-8") as f:
    f.write(creds.to_json())

print("token.json created")
```

패키지 설치:

```bash
python -m pip install google-auth-oauthlib google-auth
```

실행:

```bash
python make_token.py
```

완료되면 같은 폴더에 `token.json`이 생성됩니다.

#### 1-2. 생성한 `token.json`을 서버에 복사

예시 경로:

```bash
/home/c/dooray-calendar-sync/token.json
```

프로젝트 루트에 아래 파일들이 있어야 합니다.

```text
/home/c/dooray-calendar-sync/config.json
/home/c/dooray-calendar-sync/credentials.json
/home/c/dooray-calendar-sync/dooray_api_key.txt
/home/c/dooray-calendar-sync/token.json
```

---

## 2) Dooray 설정

두 가지 방식 중 하나를 사용합니다.

### A. 파일 방식
- 프로젝트 루트에 `dooray_api_key.txt` 생성
- 파일에 Dooray API 토큰 저장

### B. 환경변수 방식
- `DOORAY_API_TOKEN` 설정

---

## 3) Dooray 캘린더 ID 확인

`config.json`의 `dooray_calendar_ids`에는 **Dooray 캘린더 ID**가 들어가야 합니다.

Dooray API로 확인할 수 있습니다.

### 민간 클라우드

```bash
TOKEN=$(cat dooray_api_key.txt)

curl -s \
  -H "Authorization: dooray-api ${TOKEN}" \
  https://api.dooray.com/calendar/v1/calendars
```

### 공공 / 금융 등 다른 환경
사용 중인 Dooray 환경에 따라 API 엔드포인트가 다를 수 있습니다.

- 민간 클라우드: `https://api.dooray.com`
- 공공 클라우드: `https://api.gov-dooray.com`
- 공공 업무망 클라우드: `https://api.gov-dooray.co.kr`
- 금융 클라우드: `https://api.dooray.co.kr`

예시 응답:

```json
{
  "header": {
    "resultCode": 0,
    "resultMessage": "",
    "isSuccessful": true
  },
  "result": [
    {
      "id": "3771874802837352562",
      "name": "김승종",
      "type": "private",
      "me": {
        "default": true
      }
    }
  ],
  "totalCount": 1
}
```

여기서 `id` 값이 캘린더 ID입니다.

- 보통 개인 기본 캘린더는 `me.default=true`
- 여러 캘린더를 동기화하려면 배열에 여러 개 넣을 수 있습니다

---

## 4) 동기화 설정

예시 파일 복사:

```bash
cp config.example.json config.json
```

기본 예시:

```json
{
  "dooray_calendar_ids": ["YOUR_DOORAY_CALENDAR_ID"],
  "google_calendar_id": "primary",
  "timezone": "Asia/Seoul",
  "months_ahead": 2
}
```

실사용 예시:

```json
{
  "dooray_calendar_ids": ["3771874802837352562"],
  "google_calendar_id": "primary",
  "timezone": "Asia/Seoul",
  "months_ahead": 2
}
```

설명:

- `dooray_calendar_ids`: 동기화 대상 Dooray 캘린더 ID 목록
- `google_calendar_id`: 대상 Google 캘린더 (`primary` 권장)
- `timezone`: 기본 타임존
- `months_ahead`: 조회 개월 수 (기본 2 = 현재달 + 다음달)

---

## 5) Ubuntu / Debian 계열 권장 설치 방법

Ubuntu 24 계열에서는 아래와 같이 가상환경을 사용하는 것을 권장합니다.

```bash
apt install -y python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 requests
```

> 프로젝트 경로를 옮긴 경우 `.venv`는 다시 만드는 것을 권장합니다.

예:

```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 requests
```

---

## 6) 실행

먼저 변경사항 미리보기:

```bash
python3 sync_calendar.py --dry-run
```

정상 확인 후 실제 실행:

```bash
python3 sync_calendar.py
```

---

## 환경변수 우선순위

아래 값이 있으면 `config.json`보다 우선 적용됩니다.

- `DOORAY_API_TOKEN`
- `DOORAY_CALENDAR_IDS` (`id1,id2` 형태)
- `GOOGLE_CALENDAR_ID`
- `TIMEZONE`
- `SYNC_MONTHS_AHEAD`

---

## 자동 실행

### Windows 작업 스케줄러

- 프로그램: `python.exe` 또는 `pythonw.exe`
- 인수: `sync_calendar.py`
- 시작 위치: 이 프로젝트 폴더
- 권장 반복 간격: 5~10분

### Linux cron 예시

로그 디렉터리 생성:

```bash
mkdir -p /home/c/dooray-calendar-sync/logs
```

10분마다 실행:

```cron
*/10 * * * * cd /home/c/dooray-calendar-sync && /usr/bin/flock -n /tmp/dooray-calendar-sync.lock /home/c/dooray-calendar-sync/.venv/bin/python /home/c/dooray-calendar-sync/sync_calendar.py >> /home/c/dooray-calendar-sync/logs/sync.log 2>&1
```

설정:

```bash
crontab -e
```

등록 확인:

```bash
crontab -l
```

로그 확인:

```bash
tail -f /home/c/dooray-calendar-sync/logs/sync.log
```

> `flock`을 사용해 이전 실행이 끝나지 않았을 때 중복 실행을 방지합니다.

---

## 파일 설명

- `sync_calendar.py`: 메인 스크립트
- `config.example.json`: 설정 템플릿
- `.env.example`: 환경변수 템플릿
- `credentials.json`: Google OAuth 클라이언트 파일
- `token.json`: Google OAuth 토큰
- `sync_state.json`: 동기화 상태 저장 (자동 생성)

---

## 문제 해결

- `python: command not found`  
  → `python3`로 실행하세요.

- `ModuleNotFoundError: No module named 'google'`  
  → 가상환경을 활성화한 뒤 필수 패키지를 설치하세요.

- `error: externally-managed-environment`  
  → Ubuntu 24 계열에서는 시스템 Python 대신 `venv` 사용을 권장합니다.

- `Google auth error: could not locate runnable browser`  
  → 서버에 브라우저가 없으므로 로컬 PC에서 `token.json`을 생성해 서버에 복사하세요.

- `credentials.json` 없음  
  → Google OAuth 클라이언트 파일이 프로젝트 루트에 있는지 확인하세요.

- Dooray 토큰 오류  
  → `DOORAY_API_TOKEN` 또는 `dooray_api_key.txt` 값을 확인하세요.

- 잘못된 대상 동기화  
  → `config.json`, 환경변수, Dooray 캘린더 ID를 다시 확인하세요.

- 인증 꼬임  
  → `token.json` 삭제 후 다시 발급하세요.

---

## 보안 권장사항

- `credentials.json`, `token.json`, `dooray_api_key.txt`, `.env`, `config.json`은 외부 공유 금지
- 토큰/키는 Git에 커밋하지 않도록 `.gitignore` 유지
