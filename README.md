# YouTube Slide Extractor

YouTube 발표 영상에서 슬라이드처럼 보이는 장면을 자동으로 추출하는 작은 Python 도구입니다.

영상을 `yt-dlp`로 내려받고, `ffmpeg`로 일정 간격의 프레임을 샘플링한 뒤, 빈 화면과 비슷한 중복 프레임을 걸러냅니다. 최종 결과는 번호가 붙은 JPEG 이미지들과 하나의 PDF 파일로 저장됩니다.

개인 참고용으로 발표 자료를 복습하거나, 녹화된 강의/세미나에서 핵심 슬라이드만 빠르게 모아보고 싶을 때 쓰기 좋습니다.

## 주요 기능

- YouTube 영상 1개 다운로드
- `ffmpeg`를 이용한 후보 프레임 추출
- 빈 화면 및 유사 프레임 제거
- 추출된 슬라이드를 번호가 붙은 JPEG로 저장
- 추출된 슬라이드를 하나의 PDF로 생성
- 여러 URL을 순차 처리하는 배치 스크립트 제공

## 요구 사항

- Python 3.10 이상
- `yt-dlp`
- `ffmpeg`

macOS에서 Homebrew를 사용한다면 다음처럼 설치할 수 있습니다.

```bash
brew install yt-dlp ffmpeg
```

별도의 Python 서드파티 패키지는 필요하지 않습니다.

## yt-dlp 업데이트

YouTube는 플레이어와 다운로드 동작을 자주 바꿉니다. 이 때문에 오래된 `yt-dlp` 버전에서는 다운로드 실패, extractor 오류, 추가 challenge 처리 문제 등이 생길 수 있습니다.

다운로드가 갑자기 실패하면 먼저 `yt-dlp`를 업데이트해보세요.

```bash
brew upgrade yt-dlp
```

필요하면 Homebrew 패키지 전체도 갱신합니다.

```bash
brew update
brew upgrade
```

다른 방식으로 `yt-dlp`를 설치했다면 해당 설치 방식의 업데이트 명령을 사용하세요. 예를 들어 standalone 설치에서는 아래 명령을 쓰는 경우가 많습니다.

```bash
yt-dlp -U
```

Homebrew로 설치한 `yt-dlp`는 `yt-dlp -U`가 아니라 `brew upgrade yt-dlp`로 업데이트하는 것이 좋습니다.

## 사용법

### 영상 1개에서 슬라이드 추출

```bash
python3 extract_youtube_slides.py "https://youtu.be/VIDEO_ID"
```

기본 출력 위치는 다음과 같습니다.

```text
output/youtube_slides/
```

주요 결과 파일은 아래에 생성됩니다.

```text
output/youtube_slides/slides_reference.pdf
output/youtube_slides/slides/
output/youtube_slides/work/raw_frames/
```

출력 폴더를 직접 지정할 수도 있습니다.

```bash
python3 extract_youtube_slides.py \
  --out output/my_video \
  "https://youtu.be/VIDEO_ID"
```

### 여러 영상 처리

URL을 직접 넘길 수 있습니다.

```bash
python3 extract_batch.py \
  "https://youtu.be/VIDEO_ID_1" \
  "https://youtu.be/VIDEO_ID_2"
```

또는 한 줄에 하나씩 URL이 적힌 텍스트 파일을 사용할 수 있습니다.

```bash
python3 extract_batch.py --urls-file urls.example.txt
```

배치 결과는 `output/<video_id>/` 아래에 저장되고, 요약 파일은 다음 위치에 생성됩니다.

```text
output/batch_index.md
```

## 옵션 조정

기본 프레임 샘플링 간격은 1초입니다. 대부분의 발표 영상에서 슬라이드를 놓칠 가능성을 줄이기 위한 보수적인 설정입니다.

더 촘촘하게 캡처하려면 다음처럼 실행합니다.

```bash
python3 extract_youtube_slides.py --sample-interval 0.5 "https://youtu.be/VIDEO_ID"
```

더 빠르게 처리하고 후보 프레임을 줄이고 싶다면 간격을 늘립니다.

```bash
python3 extract_youtube_slides.py --sample-interval 2.0 "https://youtu.be/VIDEO_ID"
```

비슷한 슬라이드가 너무 많이 남는다면 `--dedupe-distance` 값을 올리고, 서로 다른 슬라이드가 하나로 합쳐지는 것 같다면 값을 낮춰보세요.

## GitHub 업로드 참고

생성 결과물은 Git에 포함하지 않도록 `.gitignore`에 등록되어 있습니다.

```text
output/
```

PDF, 추출 이미지, 원본 프레임, 다운로드된 영상 캐시 등은 저장소에 올리지 않고, 스크립트와 문서만 커밋하는 것을 권장합니다.

## 라이선스

이 프로젝트의 코드는 [MIT License](LICENSE)로 배포됩니다.

이 프로젝트는 `yt-dlp`와 `ffmpeg`를 외부 명령어로 호출합니다. `yt-dlp` 프로젝트는 현재 Unlicense로 배포되며, `yt-dlp` 릴리스 파일에는 빌드 방식에 따라 다른 라이선스의 구성요소가 포함될 수 있습니다. `ffmpeg`의 라이선스도 설치한 빌드 구성에 따라 달라질 수 있습니다.

이 저장소에는 `yt-dlp` 또는 `ffmpeg`의 소스 코드를 포함하지 않습니다. 각 도구의 라이선스와 사용 조건은 해당 프로젝트의 공식 문서를 확인하세요.

## 저작권 및 사용 주의

이 도구는 영상에서 이미지를 추출해 개인 참고용으로 활용하는 워크플로를 돕기 위한 것입니다. 다운로드, 저장, 활용하려는 영상과 추출 이미지에 대해 필요한 권리가 있는지 확인하세요.

권한 없이 추출한 슬라이드나 이미지를 재배포하지 마세요.
