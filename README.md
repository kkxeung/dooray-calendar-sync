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
    *   `sync_calendar.py` 파일 내 `TARGET_CALENDAR_IDS` 변수는 스크립트가 자동으로 관리합니다.
    *   **캘린더 선택:** 스크립트를 처음 실행하면 사용 가능한 두레이 캘린더 목록을 보여주고 동기화할 캘린더를 선택하도록 안내합니다. 선택된 캘린더 ID는 `config.json` 파일에 저장되어 다음 실행부터 자동으로 사용됩니다.
5.  **첫 실행 및 Google 인증:**
    *   스크립트를 처음 실행하면 웹 브라우저가 열리며 Google 계정 인증을 요청합니다. 인증을 완료하면 `token.json` 파일이 생성됩니다.
6.  **자동 실행 설정 (Windows 작업 스케줄러):**
    *   **Python 실행 파일 경로:** `C:\Users\a\AppData\Local\Programs\Python\Python314\python.exe`
    *   **스크립트 경로:** `C:\Users\a\gemini\dooray_calendar\sync_calendar.py`
    *   **작업 스케줄러 설정 방법:**
        1.  **작업 스케줄러 열기:** `Win` 키 + `R` → `taskschd.msc` 입력 후 `Enter`.
        2.  **기본 작업 만들기:** 오른쪽 '작업' 패널에서 '기본 작업 만들기...' 클릭.
        3.  **이름/설명:** `Dooray 캘린더 동기화` 등으로 지정 후 `다음`.
        4.  **트리거:** `매일` 선택 후 `다음`.
        5.  **매일:** 시작 날짜, `반복 간격: 1일`, `시간: 오전 9:00:00` 설정. **'표준 시간대 간 동기화'는 체크하지 않음.** `다음`.
        6.  **작업:** `프로그램 시작` 선택 후 `다음`.
        7.  **프로그램 시작:**
            *   **프로그램/스크립트:** 위에서 확인한 Python 실행 파일 경로 입력.
            *   **인수 추가(옵션):** 위에서 확인한 스크립트 경로 입력.
            *   **시작 위치(옵션):** `C:\Users\a\gemini\dooray_calendar` 입력.
            *   `다음`.
        8.  **마침:** '마침을 클릭할 때 이 작업의 속성 대화 상자 열기' 체크 후 `마침`.
        9.  **작업 속성 (권장):**
            *   '일반' 탭: **'사용자가 로그온했는지 여부에 관계없이 실행'** 선택, **'가장 높은 권한으로 실행'** 체크. (암호 입력 필요할 수 있음)
            *   '설정' 탭: **'예약된 시작 시간을 놓친 경우 가능한 빨리 작업 시작'** 체크.
            *   `확인`.

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
    *   **`500 Internal Server Error` (따옴표 문제):** `timeMin`, `timeMax` 값에 큰따옴표(`