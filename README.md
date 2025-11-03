# 📅 Dooray 캘린더 ↔ Google 캘린더 동기화 스크립트

이 프로젝트는 두레이(Dooray) 캘린더의 특정 일정을 Google 캘린더와 자동으로 동기화하는 Python 스크립트입니다.

## ✨ 주요 기능

*   **양방향 동기화 (True Sync):**
    *   두레이 캘린더에 새로운 일정이 추가되면 Google 캘린더에도 자동으로 추가됩니다.
    *   두레이 캘린더의 일정이 수정되면 Google 캘린더에도 자동으로 반영됩니다.
    *   두레이 캘린더에서 일정이 삭제되면 Google 캘린더에서도 자동으로 삭제됩니다.
*   **특정 캘린더 선택:** 사용자가 원하는 두레이 캘린더(예: '김승종 캘린더')의 일정만 동기화할 수 있습니다.
*   **유연한 동기화 기간:** 현재 달과 다음 달의 일정을 동기화하여, 월말에 다음 달 일정을 추가해도 누락되지 않습니다.
*   **자동 실행:** Windows 작업 스케줄러를 통해 매일 특정 시간에 자동으로 실행되도록 설정할 수 있습니다.

## 🛠️ 설정 및 사용 방법

1.  **Google Cloud Project 설정:**
    *   Google Cloud Console에서 새 프로젝트를 생성하고 Google Calendar API를 활성화합니다.
    *   OAuth 2.0 클라이언트 ID (데스크톱 앱)를 생성하고 `credentials.json` 파일을 다운로드하여 프로젝트 폴더에 저장합니다.
2.  **두레이 API 토큰 준비:**
    *   두레이 개인 설정에서 API 토큰을 발급받아 `dooray_api_key.txt` 파일에 저장합니다.
3.  **Python 환경 설정:**
    *   Python 3.x 설치 후, 필요한 라이브러리를 설치합니다:
        ```bash
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib requests
        ```
4.  **스크립트 설정:**
    *   `sync_calendar.py` 파일 내 `TARGET_CALENDAR_IDS` 변수에 동기화할 두레이 캘린더의 ID를 입력합니다. (캘린더 ID는 스크립트의 `list_dooray_calendars` 함수를 통해 확인할 수 있습니다.)
    *   **캘린더 ID 확인 방법:** `sync_calendar.py` 파일 상단에 있는 `list_dooray_calendars()` 함수를 `main()` 함수 내에서 임시로 호출하거나, Python 인터프리터에서 직접 실행하여 확인할 수 있습니다. (예: `python -c "from sync_calendar import list_dooray_calendars; list_dooray_calendars()"`)
5.  **첫 실행 및 Google 인증:**
    *   스크립트를 처음 실행하면 웹 브라우저가 열리며 Google 계정 인증을 요청합니다. 인증을 완료하면 `token.json` 파일이 생성됩니다.
6.  **자동 실행 설정:**
    *   Windows '작업 스케줄러'를 사용하여 `sync_calendar.py` 스크립트가 매일 원하는 시간에 실행되도록 설정합니다. (자세한 설정 방법은 별도 안내 참조)

## 🚀 개발 과정 및 문제 해결 기록

이 스크립트는 두레이 API의 특성과 Google Calendar API의 연동 과정에서 발생할 수 있는 다양한 문제들을 해결하며 개발되었습니다.

*   **Google API 인증:** `credentials.json` 및 `token.json`을 이용한 OAuth 2.0 인증 흐름을 구축했습니다.
*   **두레이 API 연동:**
    *   `dooray_api_key.txt`를 통한 API 토큰 관리.
    *   `GET /calendar/v1/calendars/*/events` 엔드포인트를 사용하여 일정 데이터를 가져옵니다.
    *   `timeMin`, `timeMax` 파라미터는 ISO 8601 형식의 시간 문자열을 사용합니다.
*   **초기 오류 및 해결:**
    *   **`KeyError: 'summary'`:** 두레이 API 응답 구조(`result` 키 안에 실제 데이터)를 잘못 해석하여 발생. `response.json().get('result', [])`로 수정하여 해결.
    *   **`404 Client Error: Not Found`:** 특정 캘린더 ID를 URL 경로에 직접 넣으려 시도하여 발생. API 문서에 따라 `calendars` 쿼리 파라미터를 사용해야 함을 확인.
    *   **`400 Client Error: Bad Request` (기간 문제):** `timeMin`과 `timeMax` 파라미터의 기간이 너무 길어 발생. 두레이 API가 한 번에 처리할 수 있는 기간에 제한이 있음을 확인.
    *   **`500 Internal Server Error` (따옴표 문제):** `timeMin`, `timeMax` 값에 큰따옴표(`"`)를 포함하여 요청했을 때 발생. API 문서 예시와 달리 실제로는 따옴표 없이 표준 ISO 8601 문자열을 기대함을 확인.
*   **최종 동기화 로직:**
    *   **안정적인 기간 조회:** `timeMin`, `timeMax` 파라미터에 큰따옴표 없이, '현재 달'과 '다음 달'을 각각 따로 API 호출하여 결과를 합치는 방식으로 구현. 이는 API의 제한을 우회하면서도 월말/월초 동기화 문제를 해결하는 가장 안정적인 방법입니다.
    *   **True Sync 구현:** `sync_state.json` 파일을 통해 두레이 일정 ID와 Google 일정 ID를 매핑하여 관리합니다. 이를 통해 추가, 수정, 삭제를 정확하게 반영합니다.
        *   **추가:** `sync_state.json`에 없는 일정은 Google 캘린더에 새로 생성.
        *   **수정:** 두레이 일정과 Google 일정의 제목, 시작/종료 시간 등을 비교하여 변경 사항이 있으면 Google 캘린더에서 업데이트.
        *   **삭제:** 두레이 일정 목록에 없는 일정은 `sync_state.json`에서 찾아 Google 캘린더에서 삭제.

---