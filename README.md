# bizinfo-telegram-notifier

기업마당(bizinfo.go.kr) 오픈API에서 **전남 관련 지원사업**(`[전남]`, `[전남광주]`,
전남광주가 포함된 다지역 협업사업)만 걸러서 텔레그램으로 보내주는 자동화입니다.
전국 대상 공고와 `[광주]` 단독 표기 공고는 제외합니다.

Docker 컨테이너로 서버에서 상시 실행되는 데몬(`bot_daemon.py`) 구조입니다 —
GitHub Actions의 `schedule` 트리거가 신뢰할 수 없어(등록 자체가 안 되거나,
설정한 것보다 훨씬 드물게 실행됨) 서버 배포로 전환했습니다.

## 준비물

1. **텔레그램 봇 토큰**: [@BotFather](https://t.me/BotFather)에게 `/newbot`
2. **본인 chat_id**: 봇과 대화를 시작한 뒤
   `https://api.telegram.org/bot<TOKEN>/getUpdates` 접속 → `message.chat.id`
3. **기업마당 오픈API 인증키**: [오픈API 안내](https://www.bizinfo.go.kr/web/lay1/program/S1T175C174/apiDetail.do?id=bizinfoApi)
   또는 [공공데이터포털](https://www.data.go.kr/data/15122782/fileData.do)에서 활용신청
4. Docker / Docker Compose가 설치된 서버

## 배포 (서버, Docker)

1. 저장소를 서버에 clone
2. `.env.example`을 `.env`로 복사하고 `BIZINFO_API_KEY`, `TELEGRAM_BOT_TOKEN`,
   `TELEGRAM_CHAT_ID` 값 입력
3. `data/` 폴더에 `sent_ids.json`(`{}`), `last_update_id.json`(`{"offset": 0}`),
   `last_daily_run.json`(`{"date": null}`) 준비 (최초 1회, 없으면 자동 생성되지 않으므로 직접 생성)
4. `docker compose up -d --build`
5. `docker compose logs -f`로 `bizinfo-telegram-notifier daemon started` 확인

## 동작 방식

- **bot_daemon.py**: 컨테이너 안에서 무한 루프로 동작하는 상시 프로세스
  1. 매 반복마다 `poll_command.py`를 호출 — 텔레그램 `getUpdates`를
     `TELEGRAM_POLL_TIMEOUT`(기본 30초) 동안 롱폴링해서, `TELEGRAM_CHAT_ID`로
     등록된 채팅에서 `/list`가 오면 **즉시** 현재 조건에 맞는 공고 전체를 응답
     (이미 보낸 것 포함). `last_update_id.json`으로 중복 응답 방지
  2. KST 08:00 이후이고 오늘 아직 안 보냈으면(`last_daily_run.json` 기준)
     `notify.py`를 호출해 신규 공고만 전송 — `sent_ids.json`으로 중복 방지
     (120일 지난 기록은 자동 정리)
  3. 예외가 나도 데몬은 죽지 않고 재시도

## 로컬 테스트 (Docker 없이)

```bash
pip install -r requirements.txt
BIZINFO_API_KEY=... TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python notify.py
BIZINFO_API_KEY=... TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python poll_command.py
BIZINFO_API_KEY=... TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python bot_daemon.py
```

## 필터 기준 (`notify.py`의 `is_target()`)

1. 제목이 `[광주]`로만 표기된 공고는 제외
2. `hashtags`에서 지역 코드만 추출했을 때, 태그가 없거나(전국) 17개 지역이 전부
   있으면(전국) 제외
3. 남은 건 중 `전남광주` 태그가 포함된 경우만 채택 (단일 지역이든 다지역 협업이든)

다른 지역을 대상으로 하고 싶으면 `TARGET_REGION` 값을 바꾸면 됩니다.
