# GENIE — Thí nghiệm sinh và kiểm chứng workflow Helpdesk

Workspace Python giúp so sánh cách sinh workflow từ yêu cầu và cách kiểm chứng cấu trúc, hợp đồng công cụ, chính sách, hành vi. Có thể đọc kết quả đã lưu và chạy reference mà không cần mô hình ngôn ngữ lớn (LLM). Các workflow chỉ mô phỏng ticket trong bộ nhớ, không gửi email hoặc thực hiện hành động lên khách hàng thật.

**Bắt đầu đọc:** [Giải thích và so sánh phương pháp](docs/START.md) · [Trực quan tương tác tiếng Việt](docs/START.html) · [Báo cáo thí nghiệm](outputs/report.html).

## Yêu cầu môi trường

Python 3.11+; phần runtime chỉ dùng standard library, không cần cài dependency bằng pip để chạy từ source. Chạy lệnh tại root repository. Ollama và model đã cài chỉ cần cho bước inference tùy chọn; chương trình không tự tải model. Xem [pyproject.toml](pyproject.toml) và [.env.example](.env.example). Chương trình đọc biến môi trường, không tự nạp file dotenv.

## Cài đặt và chạy nhanh

```bash
python3 -m venv .venv
source .venv/bin/activate
export PYTHONPATH="$PWD/src"
python -m genie_eval.cli list-cases
```

Mở `docs/START.html` hoặc `outputs/report.html` trực tiếp bằng trình duyệt; cả hai hoạt động offline, không cần server/CDN. Các liên kết nguồn web chỉ cần Internet khi bạn chủ động mở chúng. Lần chỉnh tài liệu này chỉ kiểm tra CLI `--help`/`list-cases`, đọc kết quả đã lưu và kiểm tra trang offline; không chạy lại model, benchmark hay tạo lại outputs.

## Tạo và xem kết quả khi cần

Các lệnh sau đã có trong CLI và từng được dùng ở workspace; chúng là hướng dẫn cho lần chạy chủ động, **không được chạy lại trong lần viết tài liệu này**. Thư mục output riêng giúp giữ báo cáo thực nghiệm đã lưu.

```bash
python -m genie_eval.cli test
python -m genie_eval.cli demo --mode reference --output-dir /tmp/genie-reference
python -m genie_eval.cli report --results /tmp/genie-reference/results.json --output-dir /tmp/genie-reference
```

`test` chạy unit tests; `demo --mode reference` kiểm chứng graph tham chiếu và mutation do người xây dựng. Mở `/tmp/genie-reference/report.html` để xem kết quả vừa tạo. Nếu muốn dựng lại báo cáo từ dữ liệu đã lưu, `python -m genie_eval.cli report` ghi lại báo cáo ở `outputs/`; nó không gọi LLM nhưng vẫn thay đổi file báo cáo.

Kiểm tra một graph độc lập bằng `evaluate --workflow /đường/dẫn/workflow.json`. Nếu bỏ `--workflow`, lệnh dùng reference có nhãn rõ:

```bash
python -m genie_eval.cli evaluate --case intake-en --methods all --output /tmp/genie-intake-evaluation.json
python -m genie_eval.cli evaluate --case order-en --methods D,E,F --output /tmp/genie-order-evaluation.json
```

`--methods all` liệt kê B–G nhưng Judge vẫn tắt nếu chưa chọn `--judge`/`--judge-all`. Những phương pháp sinh, đánh giá và cấu hình B0–B5 được giải thích trong [START.md](docs/START.md).

### Inference local tùy chọn

Cần Ollama đang chạy và model đã cài. `doctor` đọc danh sách model, không tải model; lệnh này ghi `outputs/doctor.json`. Sau khi chủ động kiểm tra, có thể sinh một candidate:

```bash
python -m genie_eval.cli doctor --model qwen3:4b
python -m genie_eval.cli generate --case intake-en --model qwen3:4b \
  --num-ctx 8192 --num-predict 2048 --timeout 300 \
  --output /tmp/genie-new-intake.json
```

Đây là cấu hình tương ứng lần đo qwen3:4b/v2. Mặc định CLI khác: qwen3.5:9b, context 16384, completion cap 4096, timeout 120 giây; một candidate, temperature 0, seed 17, retries 0, không Judge. Model có thể chọn qua `--model` hoặc `GENIE_MODEL`. Không hứa cấu hình nào chạy nhanh hay tạo workflow đúng trên mọi máy.

`generate --strategy hierarchical` chọn phân cấp; `--candidates 2`/`3` chọn nhiều phương án; `--planner-model`/`--detail-model` chọn model từng vai trò. `evaluate --judge` chỉ hỏi mục chưa rõ; `--judge-all` hỏi mọi mục; `--judge-models` chọn Judge. `benchmark --all-methods` là cấu hình nhiều lời gọi tốn thêm tài nguyên. Xem [giao thức thí nghiệm](docs/05-experiments.md) và `python -m genie_eval.cli benchmark --help` trước khi chạy; không cần các bước đó để đọc tài liệu.

## Đọc kết quả đã lưu

- Reference: 23/23 fixtures và 10/10 quan hệ metamorphic pass; đó là graph tự xây, không phải chất lượng model.
- Direct qwen3:4b/v2: 7/7 phản hồi đúng hình dạng schema, 0/7 graph hợp lệ. Không đồng nhất JSON đúng với nghiệp vụ đúng.
- B4 phát hiện 46/46 lỗi mutation thiết kế; ba verdict ngữ nghĩa trên variant hợp lệ còn UNKNOWN. Không suy ra an toàn tổng quát.
- Subset hierarchy dừng do dependency sai; N=2 không chọn được workflow chấp nhận. Judge-All có một đồng thuận quyết định và một UNKNOWN; Selective timeout. Chưa có dữ liệu để kết luận phương pháp tốt nhất tuyệt đối.

Nguồn số liệu và mẫu số: [summary](outputs/summary.md), [results](outputs/results.json), [phân tích tiếng Việt](docs/START.md). Raw phản hồi, cấu hình, cache và lỗi được giữ trong kết quả; không dùng graph reference thay cho phản hồi model thiếu.

## Tài liệu và đường dẫn

| Tài liệu | Nội dung |
|---|---|
| [docs/START.md](docs/START.md) | Hướng dẫn tiếng Việt: khái niệm, sáu nhóm phương pháp, so sánh và chú giải report |
| [docs/START.html](docs/START.html) | Pipeline, chọn phương pháp, lọc ưu tiên, metric và khám phá dữ liệu offline |
| [outputs/report.html](outputs/report.html) | Báo cáo gốc: graph, trace, bảng B0–B5 và generation |
| [docs/02-sources-and-provenance.md](docs/02-sources-and-provenance.md) | Nguồn, cách phỏng theo và giả định simulator |
| [docs/04-evaluation-methods.md](docs/04-evaluation-methods.md) | Mô tả kỹ thuật A–H |
| [docs/05-experiments.md](docs/05-experiments.md) | Cấu hình và kết quả thực nghiệm |
| [docs/06-python-to-typescript.md](docs/06-python-to-typescript.md) | Chuyển hợp đồng, runner và kiểm chứng sang TypeScript |
| [docs/07-limitations.md](docs/07-limitations.md) | Giới hạn và các đe dọa tính hợp lệ |
| [docs/08-verification.md](docs/08-verification.md) | Bằng chứng kiểm chứng lịch sử |

`src/genie_eval/` chứa triển khai; `data/` chứa SOP, prompts, oracle và reference; `tests/` chứa kiểm thử; `scripts/` điều phối thí nghiệm/tổng hợp; `outputs/graphs/` chứa SVG. Không cần sửa ứng dụng TypeScript để dùng lab.

## Lưu ý và xử lý lỗi

| Hiện tượng | Cách hiểu / xử lý có căn cứ |
|---|---|
| `No module named genie_eval` | Chạy ở root và đặt `PYTHONPATH="$PWD/src"` trong terminal hiện tại. |
| `MODEL_MISSING` | Model yêu cầu chưa có trong danh sách local; chương trình không tự tải. Model được cài không chứng minh đã inference thành công. |
| `UNAVAILABLE`, `Operation not permitted` | Kiểm tra Ollama và quyền kết nối loopback của môi trường. Không kết luận model lỗi chỉ từ lỗi quyền mạng sandbox. |
| `timed out` | Đã có request vượt timeout; token có thể null. Cân nhắc ngân sách/model/context; giữ nguyên first-pass để so sánh, không ghi nhận thành công. CPU local từng chậm trong dữ liệu lưu. |
| `INVALID_WORKFLOW` | Phản hồi parse được nhưng graph/hợp đồng sai; đọc validation_errors và fixture failures. Không chạy graph chỉ vì call.status=OK. |
| Exit code | 0: tác vụ hoàn thành theo kiểm tra bắt buộc; 1: kiểm chứng xác định fail; 2: cấu hình/lệnh/model/transport hoặc benchmark thiếu kết quả; 3: đánh giá bắt buộc còn UNKNOWN. Benchmark hoàn thành đo không nghĩa mọi candidate đúng. |
| Cache hit / token 0 | Không inference mới; xem original_* để biết chi phí gốc. Null không phải 0. |
| File node | Có hợp đồng metadata nhưng runtime `FILE_UNSUPPORTED`; không có xử lý ảnh/tệp thật. |

Dữ liệu là fixture tổng hợp phỏng theo nguồn, không có khách hàng thật và không phải bộ benchmark chính thức. Bản dịch tiếng Việt chưa được người đánh giá song ngữ độc lập duyệt. WorkflowJudge DOI chưa được xác minh; việc viết tài liệu này không dùng web. Judge không phải ground truth và không được xóa hard FAIL của code.
