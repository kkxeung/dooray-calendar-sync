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
    *   Google Cloud Console ([https://console.cloud.google.com/](https://console.cloud.google.com/))에 접속하여 새 프로젝트를 생성합니다.
    *   생성한 프로젝트에서 'API 및 서비스' > '라이브러리'로 이동하여 "Google Calendar API"를 검색하고 활성화합니다.
    *   'API 및 서비스' > '사용자 인증 정보'로 이동하여 '사용자 인증 정보 만들기' > 'OAuth 클라이언트 ID'를 선택합니다.
    *   '애플리케이션 유형'은 '데스크톱 앱'으로 선택하고 적절한 이름을 지정합니다.
    *   생성이 완료되면 `credentials.json` 파일을 다운로드하여 프로젝트 폴더에 저장합니다. (이 파일은 `.gitignore`에 의해 GitHub에는 업로드되지 않습니다.)
2.  **두레이 API 토큰 준비:**
    *   두레이 개인 설정에서 API 토큰을 발급받습니다.
    *   프로젝트 폴더 안에 `dooray_api_key.txt` 파일을 직접 생성하고, 발급받은 API 토큰을 그 파일 안에 저장합니다. (이 파일은 `.gitignore`에 의해 GitHub에는 업로드되지 않습니다.)
3.  **Python 환경 설정:**
    *   Python 3.x 설치 후, 필요한 라이브러리를 설치합니다:
        ```bash
        pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib requests
        ```
4.  **스크립트 설정:**
    *   `sync_calendar.py` 파일 내 `TARGET_CALENDAR_IDS` 변수에 동기화할 두레이 캘린더의 ID를 입력합니다. (캘린더 ID는 스크립트의 `list_dooray_calendars` 함수를 통해 확인할 수 있습니다.)
    *   **캘린더 ID 확인 방법:** `sync_calendar.py` 파일 상단에 있는 `list_dooray_calendars()` 함수를 `main()` 함수 내에서 임시로 호출하거나, Python 인터프리터에서 직접 실행하여 확인할 수 있습니다. (예: `python -c