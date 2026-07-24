# bizinfo-telegram-notifier

기업마당(bizinfo.go.kr) 오픈API에서 **전남 관련 지원사업**(`[전남]`, `[전남광주]`,
전남광주가 포함된 다지역 협업사업)만 걸러서 텔레그램으로 보내주는 자동화입니다.
전국 대상 공고와 `[광주]` 단독 표기 공고는 제외합니다.

## 준비물

1. **텔레그램 봇 토큰**: [@BotFather](https://t.me/BotFather)에게 `/newbot`
2. **본인 chat_id**: 봇과 대화를 시작한 뒤
   `https://api.telegram.org/bot<TOKEN>/getUpdates` 접속 → `message.chat.id`
3. **기업마당 오픈API 인증키**: [오픈API 안내](https://www.bizinfo.go.kr/web/lay1/program/S1T175C174/apiDetail.do?id=bizinfoApi)
   또는 [공공데이터포털](https://www.data.go.kr/data/15122782/fileData.do)에서 활용신청

## 배포

1. 이 폴더를 새 GitHub 저장소로 push (`git init` 이미 되어 있음)
2. 저장소 Settings → Secrets and variables → Actions 에 다음 3개 등록:
   - `BIZINFO_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. Actions 탭에서 `Poll /list command and daily digest` 워크플로를 한 번 수동
   실행(`Run workflow`)해서 정상 동작 확인
4. 이후 자동으로 신규 공고 알림(아침 7~11시 KST 사이, GitHub 스케줄 상황에 따라
   변동)과 `/list` 명령 응답을 받아볼 수 있음

## 로컬 테스트

```bash
pip install -r requirements.txt
BIZINFO_API_KEY=... TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python notify.py
BIZINFO_API_KEY=... TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python poll_command.py
```

## 동작 방식

- **poll_command.py** (`Poll /list command and daily digest`, 5분 간격 스케줄)
  - 매 실행마다 두 가지를 확인함:
    1. 텔레그램 `getUpdates`로 새 메시지를 확인, `TELEGRAM_CHAT_ID`로 등록된
       채팅에서 온 `/list` 명령이면 현재 조건에 맞는 공고 **전체**를 즉시 응답
       (이미 보낸 것 포함). `last_update_id.json`으로 중복 응답 방지
    2. KST 07~11시 사이이고 오늘 아직 안 보냈으면(`last_daily_run.json` 기준)
       신규 공고만 골라 전송 (`notify.py`의 로직 재사용)
  - `notify.py`는 이 스케줄에서 매일 호출되며, `sent_ids.json`에 이미 보낸 ID를
    기록해 새 공고만 전송 (120일 지난 기록은 자동 정리)
- **daily.yml**(`Daily bizinfo notify (manual)`)은 자동 스케줄이 계속 등록되지
  않아 수동 실행(`workflow_dispatch`) 전용으로만 남겨둠 — 필요시 언제든 수동
  실행 가능

> GitHub Actions의 `schedule`은 "몇 분마다"로 설정해도 실제로는 몇 시간 간격으로
> 실행되는 경우가 많고, 특정 워크플로는 아예 스케줄이 등록 안 되는 경우도
> 확인됐습니다. 정확한 시각 실행이 꼭 필요하다면 실제 서버(VPS)의 cron/systemd
> timer로 옮기는 것이 더 안정적입니다.

## 필터 기준 (`notify.py`의 `is_target()`)

1. 제목이 `[광주]`로만 표기된 공고는 제외
2. `hashtags`에서 지역 코드만 추출했을 때, 태그가 없거나(전국) 17개 지역이 전부
   있으면(전국) 제외
3. 남은 건 중 `전남광주` 태그가 포함된 경우만 채택 (단일 지역이든 다지역 협업이든)

다른 지역을 대상으로 하고 싶으면 `TARGET_REGION` 값을 바꾸면 됩니다.
