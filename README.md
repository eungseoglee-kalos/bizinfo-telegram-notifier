# bizinfo-telegram-notifier

기업마당(bizinfo.go.kr) 오픈API에서 **전남광주** 지역 공고와 **전국 대상**(지역 태그 없음) 공고를
매일 아침 확인해서, 새로 올라온 것만 텔레그램으로 보내주는 자동화입니다.

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
3. Actions 탭에서 `Daily bizinfo notify` 워크플로를 한 번 수동 실행(`Run workflow`)해서
   정상 동작 확인
4. 이후 매일 07:00(KST)에 자동 실행됨

## 로컬 테스트

```bash
pip install -r requirements.txt
BIZINFO_API_KEY=... TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python notify.py
```

## 동작 방식

- `pblancNm`(공고명) 맨 앞의 `[지역]` 태그를 확인해서 `[전남광주]`이거나 태그가 없으면(전국 대상) 채택
- `sent_ids.json`에 이미 보낸 공고 ID를 기록해두고 새 항목만 전송 (120일 지난 기록은 자동 정리)
- 워크플로가 실행될 때마다 `sent_ids.json` 변경사항을 자동 커밋

## 필터 기준 조정

다른 지역도 함께 받고 싶으면 `notify.py`의 `TARGET_REGION_TAG` 값을 바꾸거나,
`is_target()` 함수를 여러 지역을 허용하도록 수정하면 됩니다.
