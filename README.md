# VOX Video Tool — MVP

Tool tạo video explainer theo pipeline hybrid. Bản MVP có giao diện web, Scene JSON chuẩn hóa, job chạy nền, subtitle SRT và xuất MP4 bằng FFmpeg. `APP_MODE=demo` chạy toàn bộ mà không cần API key.

## Kiến trúc

1. **Director**: chủ đề/script → danh sách scene có narration, loại cảnh, visual prompt và overlay.
2. **Router**: `cinematic` dành cho FlowKit/Veo; `infographic`, `chart`, `map` dành cho renderer có kiểm soát.
3. **Audio**: adapter Vbee tạo voice; timing dùng để tạo subtitle.
4. **Composer**: FFmpeg ghép cảnh, voice, subtitle, nhạc và xuất MP4.
5. **API/UI**: tạo job, theo dõi tiến độ, xem và tải kết quả.

MVP hiện có renderer editorial local để kiểm thử miễn phí. Chế độ production hỗ trợ OpenAI Director bằng Structured Outputs, Vbee TTS theo cơ chế polling/cache và cổng wrapper FlowKit cho scene cinematic. Chart, map, infographic và archive vẫn được render có kiểm soát bằng FFmpeg.

## Chạy nhanh

```bash
cd vox-video-tool
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
cp .env.example .env
uvicorn app.main:app --reload
```

Mở http://localhost:8000. Nhập chủ đề, đợi xử lý rồi xem/tải MP4.

## Chạy Docker

```bash
cp .env.example .env
docker compose up --build
```

## Kiểm thử

```bash
pytest -q
```

## Cấu hình production

- `APP_MODE=production`: bật pipeline production và kiểm tra cấu hình trước khi nhận job.
- `OPENAI_API_KEY`: viết/chỉnh script và tạo Scene JSON có schema.
- `OPENAI_MODEL`: model Responses API dùng cho Director.
- `TTS_PROVIDER=vbee`: bật giọng đọc Vbee. Đặt `demo` để tạo video không voice.
- `VBEE_API_KEY`, `VBEE_APP_ID`, `VBEE_VOICE_CODE`: token, App ID và mã giọng Vbee.
- `VISUAL_PROVIDER=local|flowkit`: renderer cho cinematic. Các scene đồ họa luôn dùng local renderer.
- `FLOWKIT_COMMAND`: lệnh wrapper gọi provider video cho scene cinematic.
- `FONT_FILE`: đường dẫn font `.ttf` hỗ trợ tiếng Việt.
- `BACKGROUND_MUSIC`: file nhạc nền local; `MUSIC_VOLUME` điều chỉnh âm lượng.
- `FFMPEG_BIN`, `FFPROBE_BIN`: đường dẫn executable trên Windows nếu chưa có trong PATH.
- Không commit `.env`; secret chỉ được đặt trên máy/server.

Ví dụ cấu hình chưa có secret:

```env
APP_MODE=production
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
TTS_PROVIDER=vbee
VBEE_API_KEY=
VBEE_APP_ID=
VBEE_VOICE_CODE=hn_female_ngochuyen_full_48k-fhg
VISUAL_PROVIDER=local
FFMPEG_BIN=D:/tools/ffmpeg/bin/ffmpeg.exe
FFPROBE_BIN=D:/tools/ffmpeg/bin/ffprobe.exe
FONT_FILE=D:/assets/fonts/Inter-SemiBold.ttf
BACKGROUND_MUSIC=D:/assets/music/editorial-bed.mp3
MUSIC_VOLUME=0.12
```

### Hợp đồng `FLOWKIT_COMMAND`

Tool gọi wrapper bằng các argument sau:

```text
<FLOWKIT_COMMAND> --prompt <text> --duration <seconds> --aspect-ratio <ratio> --output <path.mp4>
```

Wrapper phải đợi provider xử lý xong, tải MP4 và ghi đúng vào `--output`. Ví dụ:

```env
VISUAL_PROVIDER=flowkit
FLOWKIT_COMMAND=python D:/tools/flowkit_wrapper.py
```

Không đưa cookie hoặc token vào `FLOWKIT_COMMAND`; wrapper phải đọc secret từ biến môi trường riêng.

## Lộ trình triển khai thật

- Phase 1 (đã có): API, UI, lưu job, schema, editorial renderer, SRT, MP4, Docker, test.
- Phase 2 (đã có nền tảng): OpenAI Structured Outputs, Vbee polling/cache, duration theo voice thật, visual router và FlowKit wrapper contract.
- Phase 3: nâng template SVG/Remotion cho title, chart, timeline, map; word-level subtitle và asset sourcing.
- Phase 4: hàng đợi Redis/Celery, Postgres, đăng nhập, quota/cost tracking, object storage.
- Phase 5: moderation, kiểm tra nguồn/citation, monitoring và deploy.

## Lưu ý

Google Flow/FlowKit có thể phụ thuộc phiên đăng nhập hoặc giao diện thay đổi. Khi dùng thật cần tuân thủ điều khoản nhà cung cấp. Không đưa cookie/tài khoản vào source code; ưu tiên API chính thức nếu có.
