# Bắt đầu với GENIE Evaluation

## 1. Tổng quan: từ yêu cầu đến bằng chứng

Bạn yêu cầu: “Nếu nhân viên không phê duyệt thì không gửi trả lời khách hàng”. Model ngôn ngữ lớn (LLM) tạo một bản mô tả công việc bằng JSON. Chương trình kiểm tra xem bản mô tả có chạy được và có thực hiện đúng yêu cầu hay không. Agent ở lab là phần điều phối các bước sinh, kiểm tra và chọn; không phải một nhân viên tự có quyền làm mọi việc.

Đầu vào gồm yêu cầu tiếng Anh/Việt, SOP và hợp đồng capability. Đầu ra gồm workflow, verdict, lý do, trace (dấu vết chạy), thời gian và token. Runner chỉ mô phỏng một ticket trong bộ nhớ, không gửi email, hoàn tiền hay gọi hệ thống khách hàng thật. Mục tiêu là học cách kiểm chứng và đánh đổi chi phí, không chứng minh thêm nhiều LLM sẽ đảm bảo đúng.

Có ba nguồn graph khác nhau: **reference** do người xây dựng làm tham chiếu; **mutation** là bản reference cố ý sửa để tạo lỗi hoặc tạo cấu trúc tương đương; **actual Ollama output** mới là phản hồi model thật. Dữ liệu này là các ví dụ phỏng theo nguồn với giả định simulator, không phải benchmark chính thức của vendor.

Đọc trực quan tại [START.html](START.html), rồi mở [báo cáo hiện có](../outputs/report.html). Tài liệu chỉ diễn giải dữ liệu đã lưu, không chạy lại thí nghiệm. Nguồn tổng: [summary](../outputs/summary.md), [results](../outputs/results.json), [cấu hình subset](../outputs/selected-methods/configuration.json).

## 2. Đọc nhanh: chọn đúng nhóm công việc

| Nhóm | Cách làm | Khác biệt chính |
|---|---|---|
| Sinh workflow | Direct Generation — sinh trực tiếp | Chuyển yêu cầu thành một định nghĩa workflow JSON bằng một lần gọi model, tạo mốc đối chiếu (baseline) ít công đoạn. |
| Sinh workflow | Hierarchical Generation — sinh phân cấp | Chia nhiệm vụ phức tạp thành các phần có thể kiểm tra trước khi ghép thành graph. |
| Sinh + đánh giá/chọn | Multi-Candidate — sinh nhiều phương án và chọn | Tìm một candidate đạt yêu cầu trong nhiều phương án; không giả định phương án nào cũng đúng. |
| Đánh giá ngữ nghĩa | Selective LLM-as-a-Judge — chỉ hỏi mục chưa rõ | Dành model cho yêu cầu code chưa kết luận được, tránh dùng LLM để kiểm tra những sự thật xác định được bằng code. |
| Cấu hình đánh giá / ablation | Judge-All — đối chứng hỏi mọi mục checklist | Đo Judge khi hỏi cả các tiêu chí code đã giải được; đối chứng (ablation) để xem thêm LLM có đem lại giá trị hay chỉ tăng chi phí. |
| Đánh giá + hard gate | Deterministic Validation — kiểm chứng bằng code | Kiểm tra cấu trúc, hợp đồng công cụ, chính sách và hành vi quan sát được mà không gọi model. |

Direct, Hierarchical và Multi-Candidate tác động đến quá trình sinh. Selective và Judge-All là hai phạm vi dùng chung một Judge, không phải hai generator. B0–B5 là các cấu hình ghép lớp đánh giá; chữ B ở glossary và B0 ở cấu hình là hai hệ ký hiệu khác nhau. A–H trong tài liệu kỹ thuật cũng không phải tám generator độc lập.

| Ưu tiên | Điểm bắt đầu | Điều kiện và giới hạn |
|---|---|---|
| Độ tin cậy | D + E, thêm F cho khoảng trống đã biết | Hard gate và oracle độc lập; không chứng minh mọi đầu vào. |
| Tốc độ / CPU local | Xem report đã lưu hoặc kiểm chứng xác định; nếu cần sinh, lấy Direct làm mốc | Không có model vẫn đọc/chạy reference được. Không so cache lookup với inference mới. |
| Chi phí token | Kiểm tra bằng code trước, Judge chỉ khi cần và có evidence | Không có đo ghép cặp đủ để khẳng định Selective rẻ hơn Judge-All trong lần này. |
| Chất lượng nghiệp vụ | SOP rõ + hợp đồng + fixture + metamorphic trước khi tăng candidate | Chưa có workflow model hợp lệ trong bộ Direct chính; chưa có phương pháp tốt nhất tuyệt đối. |

## 3. Khái niệm cần biết

| Khái niệm | Giải thích và ví dụ trong lab |
|---|---|
| SOP (Standard Operating Procedure) | Quy trình nghiệp vụ: khi nào hỏi thiếu thông tin, khi nào chuyển người hỗ trợ. Giống tờ hướng dẫn xử lý một phiếu. |
| Workflow / graph | Định nghĩa luồng là graph có node (công việc/điều kiện) và edge (đường nối). Định nghĩa khác một lần chạy với dữ liệu cụ thể. |
| Capability / contract | Hàm đã đăng ký cùng kiểu tham số, input/output và precondition; request_approval và send_reply có vai trò khác nhau. Model không sinh Python để chạy. |
| Baseline / candidate | Baseline là mốc đối chiếu; candidate là một phương án được sinh. Có nhiều candidate không nghĩa chúng độc lập hoặc khác nhau. |
| Validator / rule | Code kiểm tra điều kiện cụ thể: chỉ một input, condition phải có true/false, gửi trả lời cần trạng thái approved. |
| Oracle / fixture | Oracle là kỳ vọng độc lập; fixture là ticket đầu vào cụ thể cùng state/action cần có. Ví dụ rejected → Manual Review và không send_reply. Kỳ vọng được xây trước sinh model, nhưng vẫn là diễn giải có giới hạn. |
| LLM Judge / rubric | Một model đọc evidence và checklist để chấm từng tiêu chí, giống người duyệt dùng phiếu kiểm. Nó có thể sai hoặc dẫn bằng chứng không tồn tại. |
| Metric / mẫu số | Đại lượng đo và đối tượng đếm. 0/2 candidate khác 0/1 nhóm chọn; 46/46 lỗi mutation khác 7 workflow model. |
| Schema / graph / nghiệp vụ | JSON đúng khung giống tờ đơn đủ ô; graph hợp lệ giống tuyến đường nối được; nghiệp vụ đúng là tuyến đường dẫn đến đúng hành động. Ba việc khác nhau. |
| Metamorphic / mutation | Metamorphic đổi input để kiểm tra quan hệ đầu ra; mutation sửa graph để kiểm tra validator. Ví dụ thêm message phải chuyển từ thiếu dữ liệu sang tạo ticket. |
| Cache / token / latency | Cache đọc lại phản hồi cũ; token là đơn vị model xử lý văn bản; latency là thời gian chờ. Cache không tạo thêm bằng chứng model mới. |

## 4. Phân tích từng phương pháp

### Direct Generation — sinh trực tiếp

**1. Mục đích.** Chuyển yêu cầu thành một định nghĩa workflow JSON bằng một lần gọi model, tạo mốc đối chiếu (baseline) ít công đoạn.

**2. Hoạt động từng bước.** Nhận yêu cầu gốc → chọn SOP và capability liên quan bằng code → gửi prompt cùng JSON Schema cho Ollama → giữ phản hồi đầu tiên → kiểm tra graph, hợp đồng và hành vi. Zero-shot ở đây là không đưa workflow mẫu đã giải vào prompt; SOP và hợp đồng công cụ vẫn được cung cấp.

**3. Lý do chọn và tình huống phù hợp.** Phù hợp làm điểm bắt đầu khi cần ít lần gọi và muốn nhìn rõ model sai ở đâu. Cấu trúc đơn giản giúp tách lỗi sinh khỏi lỗi của bộ kiểm chứng.

**4. Setup đặc thù.** Lần đo chính: qwen3:4b, prompt genie-zero-shot-v2, N=1 mỗi case, temperature=0, seed=17, num_ctx=8192, num_predict=2048, timeout=300 giây, retries=0, không Judge. Khác mặc định CLI: qwen3.5:9b, context 16384, completion cap 4096, timeout 120 giây. Không nhầm cấu hình mặc định với cấu hình đã đo.

**5. Kết quả tóm tắt.** Bảy phản hồi có hình dạng JSON hợp lệ nhưng không workflow nào đạt tính hợp lệ của graph. Vì vậy không có thành công hành vi được ghi nhận.

**6. Số liệu chi tiết và nguồn.** Trong generation_comparison của ../outputs/results.json: 7 case (5 en, 2 vi), 7 request, 7 workflow attempts, 7 gọi inference mới; schema 7/7, graph 0/7, contract/policy 0/7, behavioral 0/7; tổng latency 974147.127 ms ≈ 974.147 giây; prompt/completion tokens 10917/3810. Đây là tổng của cả 7 case, không phải thời gian một workflow. Lần qwen3.5:9b/v1 riêng ở intake-en timeout sau 180124.531 ms, 0 phản hồi, token null; không gộp với v2.

**7. Ưu điểm, hạn chế và trade-off.** Ưu: một gọi/candidate, ít điều phối, dễ lưu first-pass. Nhược: JSON Schema không đảm bảo đúng đường đi hoặc nghiệp vụ; kết quả hiện có chưa có graph hợp lệ. Latency phụ thuộc model, CPU, context và độ dài trả lời; temperature 0 không chứng minh độ ổn định qua nhiều lần chạy.

**8. Nên / không nên chọn.** Nên dùng làm baseline với validator bắt buộc. Không nên thực thi trực tiếp chỉ vì JSON parse được; chưa có dữ liệu để kết luận model/phương pháp này tốt nhất trên Helpdesk nói chung.

Nguồn chi tiết: [các phương pháp](04-evaluation-methods.md), [giao thức thí nghiệm](05-experiments.md); các đường dẫn JSON ở trên là vị trí dữ liệu, có thể mở từ bảng nguồn dưới đây.

### Hierarchical Generation — sinh phân cấp

**1. Mục đích.** Chia nhiệm vụ phức tạp thành các phần có thể kiểm tra trước khi ghép thành graph.

**2. Hoạt động từng bước.** Yêu cầu → high-level stages → detailed activities → capability mapping → workflow. Mỗi mục có ID, mục đích nghiệp vụ, input/output, dependency, capability dự kiến và requirement ID. Kiểm tra dependency/provenance trước khi tiếp tục; lỗi thì dừng, không tự sửa âm thầm.

**3. Lý do chọn và tình huống phù hợp.** Phù hợp khi phân rã giúp người đọc kiểm tra thứ tự và ánh xạ công cụ. Đây là giả thuyết thiết kế; lần chạy hiện tại chưa chứng minh tăng chất lượng.

**4. Setup đặc thù.** Subset intake-en dùng cùng qwen3:4b/v2 và cấu hình 8192/2048, temperature 0, timeout 300 giây, retries 0 như Direct. Planner/detail có thể chọn model riêng; mặc định cùng model. Pipeline đầy đủ dự kiến 3 gọi lập kế hoạch/ánh xạ + 1 gọi workflow, nhưng không được ghi rằng đã chạy cả 4 khi đã dừng sớm.

**5. Kết quả tóm tắt.** Dừng ngay tại high_level_stages vì PLAN_DEPENDENCY: I1; không sinh workflow cuối.

**6. Số liệu chi tiết và nguồn.** ../outputs/selected-methods/hierarchical.json: 1 candidate intent, 1 gọi model mới, 0 workflow attempts, 0 workflow trả về; 77289.103 ms ≈ 77.289 giây, 1181 prompt và 304 completion tokens. Mục I1 đặt dependency là validate_fields (tên operation) thay vì ID stage đã có. First-pass schema/graph của workflow là null vì chưa tới bước đó; behavioral success theo candidate request là 0/1.

**7. Ưu điểm, hạn chế và trade-off.** Ưu: phát hiện kế hoạch không nhất quán sớm, intermediate dễ giải thích. Đổi lại thêm prompt, token, điểm lỗi và điều phối; một kế hoạch đúng hình dạng chưa đảm bảo graph đúng. Cùng một model ở nhiều bước không tạo suy luận độc lập. So 77.289 giây dừng sớm với thời gian sinh graph hoàn chỉnh không phải bằng chứng nhanh hơn.

**8. Nên / không nên chọn.** Nên thử khi cần audit kế hoạch và chấp nhận chi phí nhiều bước. Không nên bật chỉ vì tên “phân cấp” nghe đáng tin hơn. Chưa có dữ liệu để kết luận pipeline hoàn chỉnh tăng tỷ lệ đúng hay ổn định hơn.

Nguồn chi tiết: [các phương pháp](04-evaluation-methods.md), [giao thức thí nghiệm](05-experiments.md); các đường dẫn JSON ở trên là vị trí dữ liệu, có thể mở từ bảng nguồn dưới đây.

### Multi-Candidate — sinh nhiều phương án và chọn

**1. Mục đích.** Tìm một candidate đạt yêu cầu trong nhiều phương án; không giả định phương án nào cũng đúng.

**2. Hoạt động từng bước.** Sinh hoặc đọc cache từng candidate → đánh giá độc lập → xếp tuple theo hard compliance, tỷ lệ test E+F pass, checklist coverage, Judge cho mục chưa rõ, rồi mới ưu tiên ít node+cạnh. Lấy chỉ số đứng đầu không đồng nghĩa chấp nhận; selection_accepted vẫn có thể false.

**3. Lý do chọn và tình huống phù hợp.** Phù hợp khi có khả năng tạo đa dạng và validator phân biệt được lỗi. Đây là lựa chọn trên cùng bộ fixture, không phải đánh giá tổng quát trên dữ liệu chưa thấy.

**4. Setup đặc thù.** Subset intake-en, N=2, qwen3:4b/v2; temperature 0, seed 17 và 18; cùng context/token cap/timeout với Direct. Candidate seed 17 lấy từ cache, seed 18 gọi mới. Mặc định generator N=1; CLI hỗ trợ N=2 hoặc 3 khi chọn rõ. Không có threshold điểm số hay ngưỡng tiền tệ để chấp nhận: các hard check quyết định, UNKNOWN được giữ.

**5. Kết quả tóm tắt.** Cả hai graph đều sai; selected_candidate_index=0 nhưng selection_accepted=false. Không có cải thiện sau chọn.

**6. Số liệu chi tiết và nguồn.** ../outputs/selected-methods/multi-candidate.json và generation_matched_subset trong ../outputs/results.json: 2/2 trả JSON, graph 0/2, behavioral 0/2; selected behavioral 0/1 nhóm chọn. Một gọi mới, một cache hit; latency tăng thêm 44820.954 ms, token mới 1347/319. Tổng chi phí gốc của hai phản hồi: 110988.021 ms và 2694/638 tokens. Cả hai graph có 4 node, 3 cạnh và cùng lỗi; seed khác không bảo đảm đa dạng.

**7. Ưu điểm, hạn chế và trade-off.** Ưu: giữ đầy đủ lựa chọn và lý do xếp hạng. Nhược: thêm inference, đánh giá và tài nguyên; cache làm latency tăng thêm thấp nhưng không chứng minh sinh hai phương án rẻ hơn một. Bộ test yếu có thể chọn nhầm; ít node chỉ là tie-break cuối, không thay thế đúng nghiệp vụ.

**8. Nên / không nên chọn.** Nên chọn khi lợi ích từ đa dạng được đo trên cùng setup và có kiểm chứng tốt. Không nên chọn nếu mọi candidate lặp lại lỗi, ngân sách hạn chế, hoặc định lấy winner làm workflow an toàn dù hard check fail.

Nguồn chi tiết: [các phương pháp](04-evaluation-methods.md), [giao thức thí nghiệm](05-experiments.md); các đường dẫn JSON ở trên là vị trí dữ liệu, có thể mở từ bảng nguồn dưới đây.

### Selective LLM-as-a-Judge — chỉ hỏi mục chưa rõ

**1. Mục đích.** Dành model cho yêu cầu code chưa kết luận được, tránh dùng LLM để kiểm tra những sự thật xác định được bằng code.

**2. Hoạt động từng bước.** Chạy checklist và execution → chọn mục UNKNOWN → gửi yêu cầu gốc, SOP, rubric, hợp đồng, graph và evidence cho Judge → kiểm tra đủ requirement ID và node/edge/trace refs → giữ verdict, lý do, uncertainty. FAIL xác định bởi code không bị Judge ghi đè.

**3. Lý do chọn và tình huống phù hợp.** Phù hợp với yêu cầu ngữ nghĩa thật sự có bằng chứng để đọc. Trong lab, lời thông báo chủ yếu là template ID nên chưa đủ đánh giá giọng điệu.

**4. Setup đặc thù.** qwen3:4b cùng model với cấu hình subset; case order-en, chỉ requirement O3 (ghi nhận ý định khách hàng). Một gọi, timeout 300 giây, không retry. Judge mặc định tắt; --judge bật phạm vi chọn lọc. Nếu không có mục chưa rõ, NOT_NEEDED có thể không gọi model.

**5. Kết quả tóm tắt.** Request timeout; O3 vẫn UNKNOWN. Không có verdict model đã trả về để chấm chất lượng ngữ nghĩa.

**6. Số liệu chi tiết và nguồn.** ../outputs/selected-methods/judge-selective.json: calls[0].status=ERROR, error=timed out, latency 300107.276 ms; prompt/completion tokens=null. judge.status=UNAVAILABLE_OR_INVALID; evidence chứa UNKNOWN thay thế, uncertainty=1. Đây là trạng thái thiếu evidence, không phải lời chấm thành công của model.

**7. Ưu điểm, hạn chế và trade-off.** Ưu thiết kế: thường ít mục và token hơn Judge-All nếu chỉ một phần chưa rõ. Lần này chưa đo được tiết kiệm tương đương vì khác case/scope và timeout; không thể coi token null là 0. Thêm độ trễ, thiên lệch cùng model và khả năng sai/thiếu bằng chứng. Tên template order_ack không chứng minh chất lượng lời nói.

**8. Nên / không nên chọn.** Nên dùng khi có tiêu chí ngữ nghĩa rõ và bằng chứng đủ. Không nên bật để chứng nhận mọi workflow hoặc thay hard gate. Chưa có dữ liệu để kết luận độ chính xác, tiết kiệm token hay ưu thế ngữ nghĩa của Selective.

Nguồn chi tiết: [các phương pháp](04-evaluation-methods.md), [giao thức thí nghiệm](05-experiments.md); các đường dẫn JSON ở trên là vị trí dữ liệu, có thể mở từ bảng nguồn dưới đây.

### Judge-All — đối chứng hỏi mọi mục checklist

**1. Mục đích.** Đo Judge khi hỏi cả các tiêu chí code đã giải được; đối chứng (ablation) để xem thêm LLM có đem lại giá trị hay chỉ tăng chi phí.

**2. Hoạt động từng bước.** Đưa toàn bộ rubric và evidence vào Judge → kiểm tra schema và tham chiếu → lưu verdict riêng của Judge → so với nhãn độc lập có kết luận → ghép hard gate mà không xóa FAIL. Đếm UNKNOWN riêng; không biến effective verdict của hệ thống thành kết quả riêng của Judge.

**3. Lý do chọn và tình huống phù hợp.** Phù hợp nghiên cứu độ đồng thuận và lỗi chấm; không phải một cách sinh workflow độc lập.

**4. Setup đặc thù.** qwen3:4b, temperature 0, seed 17, context 8192, cap 2048, timeout 300 giây; all_items=True/--judge-all. Hai đối tượng là reference intake-en và biến thể swapped_branches được tạo có kiểm soát; không phải hai workflow model sinh ra.

**5. Kết quả tóm tắt.** Một mục đồng thuận PASS; mục còn lại thành UNKNOWN sau kiểm tra evidence. Không có dữ liệu nhãn ngữ nghĩa do chuyên gia độc lập đánh giá.

**6. Số liệu chi tiết và nguồn.** ../outputs/selected-methods/judge-all-reference.json: 2194/144 tokens, 102457.963 ms, Judge I1=PASS và code=PASS. ../outputs/selected-methods/judge-all-swapped_branches.json: 1712/109 tokens, 46416.264 ms; raw model từng trả FAIL nhưng dùng trace_ref complete thiếu :step_index nên bộ kiểm tra đổi verdict Judge thành UNKNOWN. deterministic_verdict/effective_verdict vẫn FAIL. Tổng 2 gọi: 3906/253 tokens, 148874.227 ms. ../outputs/results.json → judge_agreement: agree=1, eligible_items=1, unknown_items=1; confusion riêng Judge: true accept 1, false accept 0, true reject 0, false reject 0, UNKNOWN 1. Không gọi đây là chính xác 100% trên hai mẫu.

**7. Ưu điểm, hạn chế và trade-off.** Ưu: phát hiện bất đồng và kiểm tra integrity của evidence model. Nhược: hỏi cả sự thật đã biết, tốn token/CPU; cùng-model bias và không có human calibration. Verdict item được chuẩn hóa có thể khác raw_response và khác effective_verdict; phải đọc cả ba.

**8. Nên / không nên chọn.** Nên dùng để audit/ablation có nhãn độc lập. Không nên bật mặc định cho mọi tiêu chí hay coi Judge là ground truth. Chưa có dữ liệu để kết luận tăng khả năng bắt lỗi so với code trên một mẫu rộng.

Nguồn chi tiết: [các phương pháp](04-evaluation-methods.md), [giao thức thí nghiệm](05-experiments.md); các đường dẫn JSON ở trên là vị trí dữ liệu, có thể mở từ bảng nguồn dưới đây.

### Deterministic Validation — kiểm chứng bằng code

**1. Mục đích.** Kiểm tra cấu trúc, hợp đồng công cụ, chính sách và hành vi quan sát được mà không gọi model.

**2. Hoạt động từng bước.** B: tìm thuật ngữ (tín hiệu yếu). C: checklist từng yêu cầu. D: schema, ID, edge/port, reachability, DAG, operation/args, data dependency, guard và policy. E: chạy fixture độc lập, kiểm tra state, required/forbidden actions, nhánh, thứ tự. F: đổi đầu vào theo quan hệ đã định trước rồi kiểm tra khác biệt. G là Judge tùy chọn. Chạy graph bị D chặn trả INVALID và trace rỗng; không thực thi để “thử xem”.

**3. Lý do chọn và tình huống phù hợp.** Phù hợp làm nền kiểm chứng có thể lặp lại và đọc được nguyên nhân. Ví dụ missing_field_metamorphic bỏ kiểm tra message: fixture gốc vẫn pass nhưng cặp thêm message của F bắt lỗi.

**4. Setup đặc thù.** Python >=3.11, không cần Ollama hoặc thư viện runtime ngoài standard library. Kỳ vọng, SOP, fixture và policy nằm trong data; chạy DAG một ticket, không API ngoài. Không có ngưỡng LLM hay điểm 1–10. Những lựa chọn như required email/message là giả định simulator đã ghi rõ, không phải chính sách chung của vendor.

**5. Kết quả tóm tắt.** Reference: 23/23 fixtures, 10/10 metamorphic relations pass. B4 bắt 46/46 lỗi được cố ý đưa vào, nhưng đó là bộ fault thiết kế nhỏ, không phải chất lượng sinh model.

**6. Số liệu chi tiết và nguồn.** ../outputs/results.json → references, mutations, evaluation_summary: 7 case ngôn ngữ / 5 kịch bản; 53 variants gồm 46 sai và 7 graph khác cấu trúc nhưng tương đương hành vi. B0/B1/B2/B3/B4 lần lượt từ chối 0/2/36/45/46 trong 46 lỗi; B4 không false reject, còn 3 UNKNOWN ngữ nghĩa trên các variant hợp lệ. B5 trong mutation suite không có Judge chạy, cùng số với B4 không chứng minh giá trị tăng thêm. 81 unit tests ở ../outputs/test-run.txt là kết quả lịch sử đã lưu, không được chạy lại trong lần viết tài liệu này.

**7. Ưu điểm, hạn chế và trade-off.** Ưu: không tiêu thụ token LLM, lỗi xác định, dễ port TypeScript, thích hợp CPU. Đổi lại phải xây hợp đồng/oracle; guard proof có giới hạn, fixture hữu hạn có thể bỏ sót; glossary có false positive; tên operation không chứng minh đường đi đúng. Token=0 không có nghĩa không tốn CPU/thời gian.

**8. Nên / không nên chọn.** Nên làm lớp nền cho mọi cách sinh. Không nên dùng 46/46 để khẳng định an toàn cho mọi Helpdesk hay tự đánh giá giọng điệu từ template ID. Chưa có dữ liệu để kết luận độ bao phủ ngoài bộ tình huống hiện tại.

Nguồn chi tiết: [các phương pháp](04-evaluation-methods.md), [giao thức thí nghiệm](05-experiments.md); các đường dẫn JSON ở trên là vị trí dữ liệu, có thể mở từ bảng nguồn dưới đây.

## 5. Kết quả tổng hợp: chỉ so trong cùng phạm vi

### Cùng intake-en, cùng qwen3:4b/v2

Đây là subset so sánh cùng yêu cầu, SOP và oracle. Cache và việc Hierarchical dừng sớm làm thời gian không phải phép đo thuần về tốc độ thuật toán. Nguồn: [generation_matched_subset](../outputs/results.json) và [selected-methods/results](../outputs/selected-methods/results.json).

| Cấu hình | Request / workflow trả về | API mới / cache | ms lần này | ms phản hồi gốc | Token mới input/output | Kết quả |
|---|---|---|---|---|---|---|
| direct | 1 / 1 | 0 / 1 | 4.447 | 66173.094 | 0/0 | Không graph hợp lệ |
| hierarchical | 1 / 0 | 1 / 0 | 77289.103 | 77289.103 | 1181/304 | Dừng ở plan; chưa có workflow |
| multi-candidate | 2 / 2 | 1 / 1 | 44820.954 | 110988.021 | 1347/319 | Không graph hợp lệ |

Direct cache có chi phí gốc 1347/319 tokens; N=2 có chi phí gốc hai phản hồi 2694/638 tokens, lần này chỉ phát sinh 1347/319. Không lấy 4.447 ms làm tốc độ sinh của Direct, không cộng cached Direct subset thành case model độc lập thứ tám.

### Cùng 53 variant được gán nhãn

Nhãn gồm 46 variant sai và 7 tương đương hợp lệ. Bảng sau đo **validator**, không đo generator. Nguồn: [results → evaluation_summary](../outputs/results.json).

| Lớp | True accept | False accept | True reject / 46 lỗi | False reject | UNKNOWN | Tổng ms thành phần |
|---|---|---|---|---|---|---|
| B0 | 7 | 46 | 0 | 0 | 0 | 51.380 |
| B1 | 7 | 44 | 2 | 0 | 0 | 65.117 |
| B2 | 0 | 0 | 36 | 0 | 17 | 164.182 |
| B3 | 4 | 1 | 45 | 0 | 3 | 410.075 |
| B4 | 4 | 0 | 46 | 0 | 3 | 601.586 |
| B5 | 4 | 0 | 46 | 0 | 3 | 601.586 |

B0: schema/graph; B1: B0 + glossary; B2: B0 + contract/policy/checklist chưa có execution; B3: thêm E; B4: thêm F; B5: thêm Judge tùy chọn cho phần chưa rõ. B1 là nhánh tín hiệu từ khóa, không bắt buộc đi qua glossary khi dùng B2. B2 có 17 UNKNOWN, không phải 17 lỗi đã được chấp nhận. B4 có 4 true accept và 3 UNKNOWN trên 7 variant hợp lệ; cả 7 vẫn pass D/E/F, ba trường hợp còn thiếu bằng chứng ngữ nghĩa. B5 ở mutation suite chưa chạy Judge: số giống B4 và tokens null không chứng minh Judge tăng detection hay miễn phí.

## 6. Kết quả chi tiết và ví dụ đọc bằng chứng

### Các nhóm dữ liệu phải giữ riêng

| Nhóm | Số liệu được xác minh | Nguồn |
|---|---|---|
| Reference tự xây | 7 case, 23/23 fixtures; 10/10 quan hệ F; 5 kịch bản. English 5 case/15 fixtures pass; Vietnamese 2 case/8 fixtures pass. | [references, language_comparison](../outputs/results.json) |
| Direct model chính | qwen3:4b/v2: 7 request, schema 7/7, graph/contract/behavior 0/7; tổng 974147.127 ms, tokens 10917/3810. | [generation_comparison](../outputs/results.json), [benchmark](../outputs/ollama-benchmark.json) |
| Model/config cũ | qwen3.5:9b/v1 intake-en: 1 attempt, 0 phản hồi, 180124.531 ms, tokens null; không phải đối chứng ngang cấu hình v2. | [generation_comparison](../outputs/results.json) |
| Judge-All | Hai nhãn I1: 1 đồng thuận quyết định, 1 UNKNOWN; 2 API calls, 148874.227 ms, tokens 3906/253. | [judge_agreement](../outputs/results.json) |
| Selective Judge | order-en/O3: 1 API call, timeout 300107.276 ms, tokens null; không có kết quả chấm model hợp lệ. | [judge-selective](../outputs/selected-methods/judge-selective.json) |

### Ví dụ điển hình

- **Reference thành công:** approval-en/approved tạo ticket, draft, hỏi approval, gửi rồi route; rejected không gửi và đi Manual Review. Đây là kết quả của graph reference, không phải thành công của generator. Xem [reference executions](../outputs/results.json).
- **Graph model thất bại:** intake-en có 4 node, 3 cạnh nhưng thiếu output; validate_fields (custom) phát cạnh true/false thay vì qua condition. Lỗi OUTPUT_MISSING và EDGE_PORTS trong [direct.json](../outputs/selected-methods/direct.json). call.status=OK chỉ nói phản hồi parse/schema được; candidate.status=INVALID_WORKFLOW mới phản ánh kiểm chứng graph.
- **Plan thất bại:** dependency validate_fields không phải stage ID đã có; guard dừng pipeline ở I1. Không tự suy rằng đã chi tiền/token cho cả bốn bước. Xem [hierarchical.json](../outputs/selected-methods/hierarchical.json).
- **Từ khóa không đủ:** approval-en/swapped_branches giữ B=PASS, D=PASS nhưng E=FAIL: đảo scope branch khiến ca approved đi notify out_of_scope, không tạo/gửi như kỳ vọng. Nút minh họa từ khóa của report hiện chọn ví dụ này. Xem [mutations](../outputs/results.json).
- **Giá trị thêm của F:** intake-en/missing_field_metamorphic có D=PASS, E=PASS, F=FAIL. Kiểm tra chỉ email đã bỏ qua message; relation message_added mới phát hiện. Không phải workflow do model sinh. Xem [mutations và incremental_value](../outputs/results.json).
- **Khác hình dạng vẫn hợp lệ:** các equivalent_graph thêm một điều kiện dư với hai nhánh cùng đích; D/E/F vẫn pass. Không so graph bằng nhau tuyệt đối. Xem [mutations](../outputs/results.json).
- **Judge có evidence sai:** ở [judge-all-swapped_branches.json](../outputs/selected-methods/judge-all-swapped_branches.json), calls[0].raw_response có FAIL nhưng trace_refs=["complete"] không đúng định dạng fixture:step_index. Sau kiểm tra, item.verdict=UNKNOWN; effective_verdict=FAIL được giữ từ code. Đây không phải một true rejection riêng của Judge.

### Setup thực tế và khả năng lặp lại

[configuration.json](../outputs/selected-methods/configuration.json) ghi host loopback, model qwen3:4b, timeout 300, context 8192, cap 2048, temperature 0, seed 17, retries 0, cache=true. [doctor.json](../outputs/selected-methods/doctor.json) ghi tên/digest/kích thước model đã cài. Có model không có nghĩa inference hoặc workflow thành công. Qwen3:8b được ghi nhận cài đặt nhưng chưa có thử nghiệm đối chiếu ở đây. Quan sát CPU và thời gian là dữ liệu trên máy chạy này, không suy ra RAM tối thiểu, tốc độ GPU hoặc chi phí điện cho máy khác. Lần viết tài liệu không probe lại Ollama.

## 7. Đọc từng khu vực của outputs/report.html

Báo cáo hiện có bằng tiếng Anh; đây là bản chú giải tiếng Việt đối chiếu trực tiếp. Mở [report](../outputs/report.html), có thể cuộn bảng ngang hoặc graph trong khung.

| Khu vực hiện có | Cách đọc và chỗ dễ nhầm |
|---|---|
| Evidence and boundaries | 7 reference language cases và 53 variants là hai nhóm khác nhau. Ollama availability mở metadata; không phải huy hiệu mọi model đã chạy thành công. |
| Evaluation comparison · B0–B5 | Dùng bảng nhãn 53 variant. Detected/invalid có mẫu số 46; true/false accept/reject và UNKNOWN phải đọc cùng nhau. Detection by injected error type đếm theo loại sửa; Incremental detections liệt kê ca mới bị từ chối khi thêm lớp. |
| Behavioral pass rate* trong bảng B0–B5 | Code của report lấy số controlled mutation E=PASS / toàn bộ controlled variants, cùng một tập graph cho mọi hàng. Giá trị hiển thị 0.151 là 8/53 làm tròn (7 tương đương + mutant thiếu message). Không phải độ chính xác B0, không phải tỷ lệ 46 lỗi lọt qua hay tỷ lệ model đúng. |
| Generation comparison · separate experiment | Đọc Strategy/model/prompt, Cases trước khi so. Requests, Returned workflows, Workflow attempts và New inference calls có mẫu số khác nhau. First-pass schema shape cao chưa đảm bảo First-pass graph cao. Behavioral dùng candidate; Selected behavioral dùng nhóm chọn. |
| Các details dưới generation | Matched-case strategy comparison chỉ intake-en; Exact generation configurations cho context/cap/model và coverage; Judge agreement and ablation cost là dữ liệu Judge riêng, không dùng nâng số B5 mutation khi chưa có đo tương ứng. |
| English and Vietnamese | Reference cases/fixtures/passed khác actual candidate requests/contract/behavior passes. Actual counts có thể gồm lịch sử timeout và nhóm sinh nhiều candidate; mở kết quả theo model/case/strategy trước khi so. Reference tiếng Việt dùng chung oracle, không chứng minh model tương đương giữa hai ngôn ngữ. |
| Inspect a workflow and execution | Chọn workflow rồi fixture. Xem kind (reference, controlled mutation, actual output), introduced error và responsible/affected nodes. Badge B0/B/C/C_static/D/E/F/G là verdict phương pháp; không nhầm badge B với cấu hình B1. |
| Graph / Validation issues | Node là bước; cạnh ghi next hoặc true/false. Node/cạnh xanh là đường đã thực thi với fixture chọn. Viền đỏ/dấu ! là finding gắn node; node điều kiện nền vàng nhạt. Đây là ký hiệu riêng của graph, không phải mọi nền vàng nghĩa UNKNOWN. Graph invalid có thể không có đường xanh vì runner chặn. |
| Expected and observed behavior | PASS/FAIL theo fixture; danh sách lỗi so state/actions/order. Final state là thực tế, Expected state là oracle (thường là subset). Không cần state bằng toàn bộ JSON từng byte. |
| Execution trace | Step, node/type, operation, changes, selected edge và error mô tả một lần chạy. INVALID trước chạy có trace rỗng; không được coi rỗng là mọi hành động thành công. |
| Checklist and source evidence | Mở requirement để đọc description, evidence và nguồn SOP. Template ID không phải lời nói đã được con người thẩm định; tone có thể UNKNOWN. |
| Keyword coverage can pass incorrect behavior | Nút Inspect this failure chọn ca B pass nhưng E fail. Kiểm tra branch/state thật thay vì chỉ đếm tên operation. |
| Sources and limitations | Nguồn, phạm vi đọc, biến đổi và giới hạn. Có citation không biến fixture tự tạo thành dữ liệu chính thức. WorkflowJudge còn unverified, không dùng làm bằng chứng phương pháp đã được chứng minh. |

### Từ điển metric và trạng thái


**Schema shape.** Tỷ lệ phản hồi đầu tiên có dạng JSON đúng schema / số candidate request trong nhóm, khi có workflow attempt. Tỷ lệ 0–1; cao hơn nghĩa là nhiều phản hồi đúng hình dạng hơn. Không chứng minh có một input, có output hay đúng nghiệp vụ. Qwen3:4b chính: 7/7=1. Nguồn: [generation_comparison; ../src/genie_eval/report.py → generation_comparison](../outputs/results.json).

**First-pass graph.** Số candidate có graph đầu tiên hợp lệ / số candidate request; kiểm tra schema và graph trước retry/selection. Tỷ lệ 0–1, cao tốt trong cùng setup. Direct chính 0/7. Hierarchical null vì không có workflow attempt. Nguồn: [generation_comparison; ../src/genie_eval/validators.py → validate](../outputs/results.json).

**Contract/policy.** Candidate pass D / số candidate request. D kiểm tra hợp đồng operation, dữ liệu và policy cùng cấu trúc. Tỷ lệ 0–1. Thất bại trước khi có graph không đóng góp success. Cao chỉ đảm bảo trong hợp đồng đã hỗ trợ. Nguồn: [generation_comparison](../outputs/results.json).

**Behavioral / Selected behavioral.** Behavioral: candidate pass toàn bộ fixture E / candidate request. Selected: nhóm có winner pass E / số nhóm chọn. Tỷ lệ 0–1; mẫu số khác nhau. N=2 hiện 0/2 trước chọn và 0/1 nhóm sau chọn. Đây là pass E, không tự bao gồm F hay mọi ngữ nghĩa. Nguồn: [generation_comparison; ../src/genie_eval/report.py → generation_comparison](../outputs/results.json).

**Detection rate.** Số variant sai bị verdict FAIL / tổng variant sai, gồm cả UNKNOWN trong mẫu số. Tỷ lệ 0–1; B4=46/46 trên lỗi thiết kế. Không phải generator accuracy. Mutation là graph sửa có chủ đích, không phải output model. Nguồn: [evaluation_summary; ../src/genie_eval/experiments.py → summarize](../outputs/results.json).

**True/false acceptance/rejection.** True accept: nhãn hợp lệ → PASS; false accept: sai → PASS; true reject: sai → FAIL; false reject: hợp lệ → FAIL. UNKNOWN là cột riêng. Đơn vị variant hoặc criterion tùy bảng. Mong muốn false accept/reject thấp; phải kiểm tra true accept và UNKNOWN, không chỉ nhìn số false accept=0. B2 có 17 UNKNOWN nên không được coi 0 false accept là mọi quyết định đều đúng. Nguồn: [evaluation_summary và judge_agreement.ablation_confusion](../outputs/results.json).

**PASS / FAIL / UNKNOWN.** PASS: đủ evidence trong phạm vi; FAIL: có bằng chứng trái yêu cầu; UNKNOWN: chưa đủ hoặc không hợp lệ. Tổng hợp ưu tiên FAIL rồi UNKNOWN rồi PASS. Nhãn, không phải điểm. UNKNOWN không phải 0, PASS hay FAIL. Ba UNKNOWN ở B4 là giới hạn ngữ nghĩa, không phải ba lỗi bị bỏ sót trong 46 lỗi. Nguồn: [mutations[*].evaluation; ../src/genie_eval/evaluators.py → aggregate](../outputs/results.json).

**Latency / ms.** Thời gian đã ghi theo perf_counter; giây = ms/1000. Bảng nhóm cộng các thành phần/call liên quan. Thấp hơn chỉ có ý nghĩa với cùng lượng việc, model, thiết bị, cache. Lớp B0–B5 tái sử dụng timing thành phần, không phải microbenchmark độc lập. Cache lookup 4.447 ms không phải thời gian inference gốc 66173.094 ms. Nguồn: [generation_metrics và calls[*].original_latency_ms; ../outputs/results.json → evaluation_summary](../outputs/selected-methods/direct.json).

**Prompt / completion tokens.** Prompt: số token input được Ollama báo; completion: eval_count của output. Token là đơn vị văn bản của model, không bằng số từ. Đơn vị token. Zero ở cache hit là không gọi inference mới; original_* giữ chi phí phản hồi gốc. null là chưa đo/không trả count, không phải miễn phí. Không quy đổi USD vì đây là Ollama local và không có dữ liệu giá điện/API. Nguồn: [generation_comparison và judge_agreement](../outputs/results.json).

**Requests / Attempts / Calls / Cache hits.** Requests là candidate được yêu cầu; workflow attempts là lần thử bước workflow (có thể gồm phản hồi cache); new inference calls là số API inference mới, có thể gồm planner; cache hits là lần đọc lại. Đơn vị lượt. Hierarchy: 1 request, 1 planner call, 0 workflow attempts. N=2: 2 candidate, chỉ 1 gọi mới và 1 cache. Không cộng bản cache thành mẫu model độc lập. Nguồn: [generation_runs[*].generation_metrics](../outputs/selected-methods/results.json).

**Complexity nodes/edges.** Số node / số cạnh của graph trả về. Đơn vị node/cạnh. Ít hơn chỉ là tie-break cuối; graph 4/3 vẫn có thể sai. Không có graph thì danh sách rỗng, không phải graph có 0 node. Nguồn: [generation_comparison.graph_complexity; ../src/genie_eval/experiments.py → rank_key](../outputs/results.json).

**Judge agreement / uncertainty.** Agreement: số mục Judge đồng thuận nhãn code độc lập / số mục cả hai có verdict quyết định. Uncertainty là số 0–1 Judge báo; fallback thiếu evidence dùng 1. Hiện 1/1 mục quyết định, một mục UNKNOWN ngoài mẫu số. Không phải 2/2, không phải xác suất đúng đã hiệu chỉnh. Không có threshold uncertainty dùng để tự động chứng nhận. Nguồn: [judge_agreement; ../outputs/selected-methods/judge-all-swapped_branches.json](../outputs/results.json).

**Trạng thái thực thi.** MEASURED: có dữ liệu đo, không nghĩa đúng. ATTEMPTED_NO_OUTPUT: đã thử nhưng không trả workflow. NO_WORKFLOW_OUTPUT: pipeline chưa tạo graph. OK ở call: parse/schema có thể đạt, graph vẫn sai. INVALID_WORKFLOW: graph/contract không đạt. RUN là Judge đã chạy, không đồng nghĩa PASS. ERROR/timed out là lỗi request. UNAVAILABLE_OR_INVALID là không lấy được Judge hợp lệ; DISABLED là chưa bật; NOT_NEEDED là không cần gọi; unmeasured/null là chưa có số. INVALID ở runner khác ERROR lúc chạy; trace rỗng khi bị chặn. Nguồn: [generation_comparison; ../outputs/selected-methods/judge-selective.json; ../src/genie_eval/runner.py](../outputs/results.json).

Màu nhãn: PASS xanh, FAIL đỏ, UNKNOWN vàng/nâu. Dùng cả chữ, không chỉ dựa vào màu. Report làm tròn số thập phân đến ba chữ số; số nguyên token/lượt là đếm. Null/undefined hiển thị unmeasured; biểu đồ trống không tương đương giá trị 0 thật. Trong START.html, trạng thái thiếu dữ liệu hiển thị “Không có dữ liệu”. Bảng ms của các lớp cộng thời gian thành phần dùng lại; không đủ để kết luận độ ổn định hay tốc độ thực tế khi triển khai.

## 8. Chọn theo nhu cầu

- **Ưu tiên đúng và có thể giải thích:** xác nhận SOP/oracle, dùng D/E; thêm F ở khoảng trống như message_added. Đó là suy luận triển khai dựa trên lỗi đã quan sát, không chứng minh bao phủ mọi quy tắc Helpdesk.
- **Ưu tiên tốc độ hoặc máy local CPU:** xem report đã lưu không cần model; đánh giá xác định không dùng token LLM. Nếu cần sinh, Direct ít công đoạn nhất theo thiết kế; chưa có đối chứng hoàn chỉnh chứng minh nhanh hơn mọi cách khác.
- **Ưu tiên chi phí:** không gọi Judge cho sự thật code đã kiểm tra. Chọn lọc có tiềm năng giảm số mục theo thiết kế, nhưng lần order-en timeout không cho số token để so tiết kiệm. Cache tiết kiệm lần chạy lặp, không làm tăng số mẫu độc lập.
- **Ưu tiên ngữ nghĩa tự nhiên:** cần evidence là lời nói thật và nhãn độc lập trước khi dựa vào Judge. Các template thông báo hiện tại không đủ. Judge-All hữu ích như ablation; không dùng thay hard gate.
- **Muốn tăng cơ hội bằng nhiều candidate:** chỉ bật khi ngân sách cho phép và bộ kiểm chứng đáng tin; N=2 hiện lặp lỗi và không tăng success. Chưa có dữ liệu để kết luận N=3 tốt hơn hoặc model khác tốt hơn.
- **Muốn audit phân rã:** có thể thử Hierarchical; phải chấp nhận dừng ở plan và thêm chi phí. Không coi nhiều bước/cùng model là nhiều nguồn suy luận độc lập.

## 9. Giới hạn và kết luận

Kết quả chứng minh các validator đã phát hiện những lỗi thiết kế cụ thể và chặn các graph model sai được quan sát; không chứng minh mọi workflow Helpdesk an toàn. Bốn điều cần giữ riêng: kiểm chứng reference, đánh giá validator trên mutation, chất lượng sinh first-pass, và chất lượng sau selection. 46/46 không biến thành generator accuracy 100%.

Chưa có dữ liệu để kết luận phương pháp tốt nhất tuyệt đối, độ ổn định nhiều lần chạy, tổng quát sang Helpdesk khác, ưu thế model/thiết bị, chất lượng tiếng Việt đã được thẩm định, hoặc độ chính xác ngữ nghĩa Judge so với chuyên gia. Các case en/vi liên quan với nhau, không độc lập. Hai call Judge không đủ calibration; timeout không có token được báo; các foreground invocation bị gián đoạn không có output lưu không được tính là thành công.

Khuyến nghị có giới hạn: đưa hợp đồng, policy, runner, fixture độc lập và quan hệ F có lý do sang TypeScript trước; giữ Direct làm mốc sinh; thêm hierarchy/candidate/Judge khi dữ liệu so sánh cùng điều kiện cho thấy giá trị. Xem [hạn chế](07-limitations.md), [kiểm chứng lịch sử](08-verification.md), [nguồn](02-sources-and-provenance.md) và [chuyển sang TypeScript](06-python-to-typescript.md).
