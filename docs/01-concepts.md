# Concepts before code

A Helpdesk turns a support request into an accountable response or human handoff. The domain matters: a JSON graph can be valid yet send an unapproved message. This lab separates the shape of the graph, executable tool contracts, observable behavior, and unresolved meaning.

| Term | Meaning and example in Genie | Vietnamese explanation |
|---|---|---|
| Helpdesk | A service for receiving, tracking and resolving support requests; retail order support is one example. | Bộ phận/hệ thống tiếp nhận và xử lý yêu cầu hỗ trợ. |
| SOP | Standard operating procedure: a scoped process with inputs, actions, decisions and exceptions. Our SOP files adapt published examples. | Quy trình thao tác chuẩn; bản trong lab là bản phỏng theo nguồn, không phải quy trình chính thức của hãng. |
| Business rule | A condition on permitted behavior, such as human approval before a customer reply. | Quy tắc nghiệp vụ quyết định khi nào được thực hiện hành động. |
| Workflow | A connected specification of activities and decisions. | Luồng công việc. |
| Workflow definition | The static JSON graph: nodes, edges and configurations. | Định nghĩa luồng; chưa phải một lần chạy. |
| Workflow execution | One traversal using a concrete ticket snapshot. | Lần thực thi với dữ liệu đầu vào cụ thể. |
| Node and edge | A node performs an action/decision; an edge identifies the successor and branch port. | Nút và cạnh; cạnh true/false chỉ rõ nhánh điều kiện. |
| Capability/tool contract | Declared argument shape, state inputs, outputs, preconditions and effects of an executable operation. | Hợp đồng của công cụ: dữ liệu cần có, kết quả và tác động được phép. |
| Zero-shot learning/generation | Generate without completed workflow demonstrations for the task. Supplying the request, SOP, tools and schema remains zero-shot here. There is no training. | Sinh trực tiếp không có ví dụ đầu vào–đầu ra đã giải; vẫn được cung cấp quy tắc và công cụ. |
| Structured output | A model response constrained by a JSON Schema. This constrains syntax and shape. | Đầu ra có cấu trúc; đúng cấu trúc chưa đảm bảo đúng nghiệp vụ. |
| Structural correctness | Valid node/edge shapes, IDs, reachability, branch ports and acyclicity. | Tính đúng về cấu trúc đồ thị. |
| Functional correctness | A registered operation receives valid arguments and can execute with the available state. | Hàm/công cụ chạy đúng hợp đồng kỹ thuật. |
| General semantic correctness | The workflow expresses the user's intended task rather than an unrelated task; natural language may require judgment. | Đúng ý nghĩa và ý định chung của yêu cầu. |
| Domain-specific semantic correctness | The task follows relevant Helpdesk rules, e.g. rejection routes to manual review without sending. | Đúng ngữ nghĩa nghiệp vụ của miền hỗ trợ. |
| LLM-as-a-Judge | A model evaluates explicit criteria with evidence and uncertainty. | Dùng mô hình làm giám khảo; kết luận vẫn có thiên lệch và sai sót. |
| Checklist-based evaluation | Resolve each requirement with its own verdict and supporting evidence. | Kiểm tra từng yêu cầu theo danh sách tiêu chí. |
| Scenario-based testing | Execute independent input fixtures and check final state plus trace. | Chạy tình huống cụ thể và đối chiếu kết quả/mạch hành động. |
| Metamorphic testing | Change a source-relevant input and assert the specified behavioral difference. | Kiểm thử quan hệ biến đổi: đổi đầu vào có chủ đích rồi kiểm tra quan hệ đầu ra. |
| Mutation testing | Inject a known error into a confirmed reference to measure validator detection. | Cố ý tạo lỗi đã biết để đánh giá bộ kiểm chứng. |
| Behavioral equivalence | Different graph structures satisfy the same tested behavior; redundant branching may be acceptable. | Tương đương hành vi trong phạm vi kiểm thử; không cần đồ thị giống hệt. |
| False acceptance | An invalid labeled variant receives PASS. | Chấp nhận nhầm luồng sai. |
| False rejection | A valid labeled variant receives FAIL. | Loại nhầm luồng đúng. |
| Verification coverage | Which requirements, branches, inputs and error types the evidence actually covers. | Phạm vi kiểm chứng; tỉ lệ cao trên bộ nhỏ không chứng minh mọi trường hợp. |
| Ground truth vs source-derived expectations | Vendor descriptions are evidence of example behavior. Our fixture labels are independent local interpretations, with documented assumptions, not universal truth. | Phân biệt nhãn chuẩn độc lập và kỳ vọng suy ra/phỏng theo nguồn; không đồng nhất dữ liệu tự tạo với bộ chuẩn công bố. |

`PASS` means a criterion has evidence within the stated scope. `FAIL` means evidence contradicts it. `UNKNOWN` means available evidence cannot settle it. A missing judge is not a zero-token successful judge. A template called `damage_empathy` is not proof that customer-facing language is empathetic.

A useful reading path is request → scoped SOP → capability contracts → graph → execution → assertions. The independent oracle comes before generation. [τ-bench](https://arxiv.org/abs/2406.12045) motivates examining goal state; our small single-snapshot simulator does not reproduce its dynamic conversations or reliability benchmark. [OMG BPMN](https://www.omg.org/bpmn/) and [DMN](https://www.omg.org/dmn/) motivate separating process flow from business decisions, without a standards-conformance claim.
