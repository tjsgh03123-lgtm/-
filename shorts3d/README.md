# 비탈 지하실 쇼츠 – 3D 자동 생성

`slope_basement.py` 하나로 건축 단면도 스타일의 세로 쇼츠(1080x1920, 30fps, 약 93초)
장면을 Blender에서 자동으로 만듭니다.

만들어지는 것:
- 경사 지형 단면(흙·잔디), 나무, 구름, 하늘
- 하늘에서 떨어져 내려앉는 집과 실내 소품
- 단계별로 '뿅' 하고 튀어나오는 구조물: 옹벽, 자갈, 배수관, 도랑, 돌담, 창문, 환기구, 문, 빗장, 난로, 작업대
- 새로 생긴 구조물에 주황색 빛 테두리, 힘·물·바람 화살표
- 캐릭터: 사람(짐 들고 이동), 멧돼지(침입 후 도망), 고양이
- 카메라 이동 + 바위 충돌 때 화면 흔들림
- 키워드 자막(옹벽 / 배수관 / …)을 화면에 직접 렌더 (`--font` 지정 시)
- `narration.txt`(TTS용 대본), `captions.srt`(자막 파일)

## 1. 준비

[Blender](https://www.blender.org/download/) 4.2 이상 설치 (5.x 권장, 무료).
이 스크립트는 Blender 5.3에서 테스트했습니다.

## 2. 실행

### A. Blender 화면에서 (가장 쉬움)
1. Blender 실행 → 상단 **Scripting** 탭
2. **Open** → `slope_basement.py` → **▶ Run Script**
3. 장면이 만들어지면 **Layout** 탭에서 스페이스바로 애니메이션 재생
4. **Render → Render Animation** 으로 영상 출력
   (출력 형식은 Output Properties에서 FFmpeg Video / MPEG-4로 지정)

### B. 명령줄
```bash
# 주요 장면 20컷 확인 (저해상도)
blender -b -P slope_basement.py -- --mode stills --out out --pct 30 --samples 16 --font "C:/Windows/Fonts/malgunbd.ttf"

# 미리보기 영상 (10fps, 저해상도)
blender -b -P slope_basement.py -- --mode preview --out out --pct 25 --samples 8

# 최종 렌더 (PNG 시퀀스)
blender -b -P slope_basement.py -- --mode final --out out --font "C:/Windows/Fonts/malgunbd.ttf"
# EEVEE는 GPU가 있으면 프레임당 1~3초 수준으로 빠름
blender -b -P slope_basement.py -- --mode final --engine eevee --samples 32 --out out
# PNG → mp4
ffmpeg -framerate 30 -i out/frames/f_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 out/video.mp4
```

Mac은 `blender` 대신 `/Applications/Blender.app/Contents/MacOS/Blender`를 씁니다.
Mac 한글 폰트 예시: `/System/Library/Fonts/AppleSDGothicNeo.ttc`

## 3. 완성까지의 작업 흐름

1. `narration.txt`를 AI 음성(Typecast, ElevenLabs, 클로바더빙 등)에 넣어 음성 생성
2. 음성 길이에 맞춰 스크립트의 `STEPS` 각 단계 `t`(시작 초)와 각 단계 애니메이션 시간을 조정
3. 렌더 → CapCut에 영상, 음성, `captions.srt`(또는 자동 자막), 효과음(뿅, 쾅, 줄줄), 배경음악 넣기
4. 업로드: 설명란에 용어를 «꺾쇠»로 강조하고, 마지막 줄에 댓글 유도 질문

## 4. 다른 주제로 바꾸기

- **`STEPS`**: 단계별 내레이션 문장, 시작 시간, 키워드 자막
- **`CAMS` / `SHOTS`**: 카메라 위치와 언제 어느 카메라로 이동할지
- **`build_story()`**: 실제 오브젝트와 애니메이션. 단계마다 `# ---------- N. 제목 ----------` 블록으로 나뉨

자주 쓰는 도우미 함수:

| 함수 | 하는 일 |
|---|---|
| `box(name, 최소좌표, 최대좌표, 재질, pivot)` | 상자 만들기 (pivot=bottom이면 아래에서 자라남) |
| `pop(obj, 초, axes="z")` | 해당 초에 튀어나오며 등장 |
| `shrink(obj, 초)` | 줄어들며 사라짐 |
| `outline(obj, 초, 지속)` | 주황색 빛 테두리 강조 |
| `arrow(name, 시작점, 끝점, 재질)` | 화살표 |
| `path(obj, [(초, 위치), ...])` | 이동 경로 (진행 방향을 자동으로 바라봄) |
| `boolean_cut(대상, 커터)` | 땅 파기 / 구멍 뚫기 |

좌표계: X = 왼쪽(언덕) ↔ 오른쪽(마당), Y = 화면 안쪽 깊이, Z = 높이.
단면은 y=0 면이고, 단면에 보여야 하는 물체는 y를 -0.03 정도로 살짝 앞으로 내밉니다.
