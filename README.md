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

## 요구 사항

- Python 3.10+
- Google 계정 (Calendar API 사용 가능)
- Dooray API 토큰

필수 패키지 설치:

```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 requests
```

---

## 1) Google Calendar API 설정

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
2. **Google Calendar API** 활성화
3. **OAuth Client ID (Desktop app)** 생성
4. JSON 다운로드 후 프로젝트 루트에 `credentials.json`으로 저장

첫 실행 시 브라우저 인증 후 `token.json`이 생성됩니다.

---

## 2) Dooray 설정

두 가지 방식 중 하나 사용:

### A. 파일 방식
- 프로젝트 루트에 `dooray_api_key.txt` 생성
- 파일에 Dooray API 토큰 저장

### B. 환경변수 방식(권장)
- `DOORAY_API_TOKEN` 설정

---

## 3) 동기화 설정

예시 파일 복사:

```bash
cp config.example.json config.json
```

`config.json` 예시:

```json
{
  "dooray_calendar_ids": ["YOUR_DOORAY_CALENDAR_ID"],
  "google_calendar_id": "primary",
  "timezone": "Asia/Seoul",
  "months_ahead": 2
}
```

- `dooray_calendar_ids`: 동기화 대상 Dooray 캘린더 ID 목록
- `google_calendar_id`: 대상 Google 캘린더 (기본 `primary`)
- `timezone`: 기본 타임존
- `months_ahead`: 조회 개월 수 (기본 2 = 현재달+다음달)

---

## 4) 실행

일반 실행:

```bash
python sync_calendar.py
```

변경사항 미리보기(dry-run):

```bash
python sync_calendar.py --dry-run
```

---

## 환경변수 우선순위

아래 값이 있으면 `config.json`보다 우선 적용됩니다.

- `DOORAY_API_TOKEN`
- `DOORAY_CALENDAR_IDS` (쉼표 구분: `id1,id2`)
- `GOOGLE_CALENDAR_ID`
- `TIMEZONE`
- `SYNC_MONTHS_AHEAD`

---

## 자동 실행 (Windows 작업 스케줄러)

- 프로그램: `python.exe` (또는 콘솔 없는 `pythonw.exe`)
- 인수: `sync_calendar.py`
- 시작 위치: 이 프로젝트 폴더
- 권장 반복 간격: 5~10분

---

## 파일 설명

- `sync_calendar.py`: 메인 스크립트
- `config.example.json`: 설정 템플릿
- `.env.example`: 환경변수 템플릿
- `sync_state.json`: 동기화 상태 저장 (자동 생성)
- `token.json`: Google OAuth 토큰 (자동 생성)

---

## 문제 해결

- `credentials.json` 없음 → Google OAuth 클라이언트 파일 확인
- Dooray 토큰 오류 → `DOORAY_API_TOKEN` 또는 `dooray_api_key.txt` 확인
- 인증 꼬임 → `token.json` 삭제 후 재인증
- 잘못된 대상 동기화 → `config.json`/환경변수 값 재확인

---

## 보안 권장사항

- `credentials.json`, `token.json`, `dooray_api_key.txt`, `.env`, `config.json`은 외부 공유 금지
- 토큰/키는 커밋하지 않도록 `.gitignore` 유지
