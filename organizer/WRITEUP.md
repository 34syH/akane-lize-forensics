# 출제자용 풀이 — Cute Evidence

## 정답 정보

- 플래그: `flag{L1se_Is_s00_CUt3}`
- ZIP 비밀번호: `akanelize1001`

## 풀이 과정

### 1. LSB 분석

```bash
zsteg akane_lize_evidence.png
```

`b1,rgb,lsb,xy` 항목에서 다음 Base64 문자열을 발견할 수 있다.

```text
YWthbmVsaXplMTAwMQ==
```

### 2. Base64 디코딩

```bash
printf '%s' 'YWthbmVsaXplMTAwMQ==' | base64 -d
```

ZIP 비밀번호 `akanelize1001`이 나온다.

### 3. 숨겨진 ZIP 탐색

```bash
binwalk akane_lize_evidence.png
```

출력에서 ZIP 아카이브가 시작되는 10진수 오프셋 `206291`을 확인하고 ZIP
부분을 분리한다.

```bash
dd if=akane_lize_evidence.png of=secret.zip bs=1 skip=206291 status=none
unzip -P akanelize1001 secret.zip
```

원본 이미지를 교체하거나 문제를 다시 빌드하면 오프셋이 달라질 수 있으므로,
그때는 현재 `binwalk` 출력에 표시된 값을 사용한다.

### 4. 플래그 확인

```bash
cat flag.txt
```

```text
flag{L1se_Is_s00_CUt3}
```
