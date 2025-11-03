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