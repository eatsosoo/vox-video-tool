# VOX Video Tool — MVP

Tool tạo video explainer theo pipeline hybrid. Bản MVP có giao diện web, Scene JSON chuẩn hóa, job chạy nền, subtitle SRT và xuất MP4 bằng FFmpeg. `APP_MODE=demo` chạy toàn bộ mà không cần API key.

## Kiến trúc

1. **Director**: chủ đề/script → danh sách scene có narration, loại cảnh, visual prompt và overlay.
2. **Router**: `cinematic` dành cho FlowKit/Veo; `infographic`, `chart`, `map` dành cho renderer có kiểm soát.
3. **Audio**: adapter Vbee tạo voice; timing dùng để tạo subtitle.
4. **Composer**: FFmpeg ghép cảnh, voice, subtitle, nhạc và xuất MP4.
5. **API/UI**: tạo job, theo dõi tiến độ, xem và tải kết quả.

Hiện MVP dùng renderer placeholder để kiểm thử pipeline miễn phí. Điểm tích hợp production đã được tách khỏi API và schema; bước tiếp theo là nối FlowKit và Vbee theo thông tin tài khoản/API chính thức của bạn.

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

- `OPENAI_API_KEY`: viết/chỉnh script và tạo Scene JSON.
- `OPENAI_MODEL`: model dùng cho Director.
- `VBEE_API_KEY`, `VBEE_APP_ID`, `VBEE_VOICE_CODE`: giọng đọc Việt.
- `FLOWKIT_COMMAND`: lệnh wrapper gọi FlowKit cho từng scene cinematic.
- Không commit `.env`; secret chỉ được đặt trên máy/server.

## Lộ trình triển khai thật

- Phase 1 (đã có): API, UI, lưu job, schema, demo renderer, SRT, MP4, Docker, test.
- Phase 2: adapter FlowKit có retry/poll/download; adapter Vbee có polling và cache theo hash.
- Phase 3: Remotion/SVG templates cho title, chart, timeline, map; căn duration theo voice thật.
- Phase 4: hàng đợi Redis/Celery, Postgres, đăng nhập, quota/cost tracking, object storage.
- Phase 5: moderation, kiểm tra nguồn/citation, monitoring và deploy.

## Lưu ý

Google Flow/FlowKit có thể phụ thuộc phiên đăng nhập hoặc giao diện thay đổi. Khi dùng thật cần tuân thủ điều khoản nhà cung cấp. Không đưa cookie/tài khoản vào source code; ưu tiên API chính thức nếu có.
