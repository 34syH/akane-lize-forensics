# 직접 문제를 다시 만드는 방법

## 1. 변경할 값

`build_challenge.py` 윗부분에 있는 다음 값을 원하는 내용으로 수정합니다.

```python
FLAG = "flag{L1se_Is_s00_CUt3}"
ZIP_PASSWORD = "akanelize1001"
SOURCE_FILENAME = "akane_lize.png"
```

다른 이미지를 사용하려면 PNG 파일을 `source` 폴더에 넣고
`SOURCE_FILENAME`도 같은 이름으로 변경합니다.

## 2. 문제 생성

터미널에서 문제 폴더로 이동한 뒤 실행합니다.

```bash
python3 build_challenge.py
```

완성된 문제 파일은 `dist/akane_lize_evidence.png`입니다.

## 3. 배포

참가자에게는 다음 두 파일만 제공합니다.

- `dist/CHALLENGE.md`
- `dist/akane_lize_evidence.png`

`build`와 `organizer` 폴더에는 정답이 있으므로 참가자에게 보내면 안 됩니다.

## 문제 내부 구조

```text
원본 PNG
  ├── RGB 채널 LSB: Base64로 인코딩한 ZIP 비밀번호
  └── PNG의 끝 뒤에 암호화 ZIP 연결
        └── flag.txt
```
