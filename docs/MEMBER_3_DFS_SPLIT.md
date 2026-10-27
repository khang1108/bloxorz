# Báo Cáo Kỹ Thuật: DFS Solver & Cơ Chế Khối Phân Tách (Split Mechanics)
**Phân công thực hiện: Member 3**  
**Học phần:** CSC14003 - Nhập môn Trí tuệ Nhân tạo (Introduction to Artificial Intelligence)  
**Đồ án:** Project 1 - Bloxorz Solver  

---

## 1. Tổng quan nhiệm vụ của Member 3
Theo phân công công việc của nhóm, Member 3 chịu trách nhiệm các hạng mục cốt lõi sau:
1. **Hiện thực hóa cơ chế nâng cao 2 (Advanced Mechanics 2 - `split.py`)**:
   - Công tắc phân tách (`Split switch` / `Teleport`).
   - Tách khối chuẩn $1 \times 1 \times 2$ thành hai khối lập phương nhỏ $1 \times 1 \times 1$ và dịch chuyển đến 2 tọa độ chỉ định.
   - Cơ chế điều khiển luân phiên hai khối (`Switch active cube`).
   - Tương tác vật lý của khối nhỏ với các ô đặc biệt (ô Fragile không bị vỡ, không kích hoạt Heavy switch, không thể một mình về Goal).
   - Cơ chế tự động hợp nhất (`Rejoining / Merging`) khi 2 khối nằm ở 2 ô liền kề trực giao.
2. **Cài đặt thuật toán tìm kiếm DFS (`dfs.py`)**:
   - Hiện thực hóa **Depth-First Search (DFS)** với cấu trúc dữ liệu ngăn xếp hiển thị (Explicit LIFO Stack) tránh tràn bộ nhớ đệm đệ quy (`RecursionError`).
   - Kỹ thuật chống chu trình lặp (Cycle Detection) thông qua bảng băm chữ ký trạng thái (`visited set`).
   - Đo đạc đầy đủ 4 chỉ số thực nghiệm: **Thời gian tìm kiếm (Search Time)**, **Bộ nhớ đỉnh (Peak Memory)** thông qua thư viện `tracemalloc`, **Số nút mở rộng (Expanded Nodes)** và **Độ dài lời giải (Solution Length)**.
3. **Thiết kế & Phân cấp bộ Test Cases JSON từ cơ bản đến nâng cao**:
   - Phân loại toàn bộ hệ thống màn chơi thành **5 nhóm độ khó** theo đúng yêu cầu mục 3.6 của đề bài và giải đáp Q&A của Giảng viên.
   - Xây dựng file danh mục dữ liệu thực nghiệm chuẩn hóa (`data/test_cases_catalog.json`).
4. **Kiểm thử hồi quy (Regression Testing) & Tài liệu hóa**:
   - Xây dựng bộ kiểm thử tự động `tests/test_split.py` và `tests/test_dfs.py`.
   - Cung cấp mô tả toán học và phân tích thuật toán chi tiết để đưa vào Báo cáo cuối kỳ.

---

## 2. Mô hình hóa Toán học Cơ chế Khối Phân Tách (`bloxorz/core/split.py`)

### 2.1. Biểu diễn trạng thái bất biến (`SplitBlockState`)
Để tương thích với các thuật toán tìm kiếm không gian trạng thái, trạng thái của khối phân tách được định nghĩa bằng cấu trúc bất biến (`@dataclass(frozen=True)`):
```python
@dataclass(frozen=True)
class SplitBlockState:
    cube1: Tuple[int, int]   # Tọa độ (x, y) của khối 1
    cube2: Tuple[int, int]   # Tọa độ (x, y) của khối 2
    active_cube: int = 0     # 0: đang điều khiển cube1, 1: đang điều khiển cube2
```
- **Tính bất biến (Immutability)**: Thuộc tính `frozen=True` tự động sinh hàm băm `__hash__` và hàm so sánh `__eq__`, cho phép đưa trực tiếp `SplitBlockState` vào các tập hợp `set` và từ điển `dict` của thuật toán tìm kiếm mà không sợ biến đổi dữ liệu.
- **Tính tương thích đa hình (Polymorphism)**: Cả `BlockState` và `SplitBlockState` đều cung cấp thuộc tính `is_split: bool`, `occupied_cells: Set[Tuple[int, int]]`, `get_center_3d()` và phương thức chuyển tiếp `roll(direction: Direction)`.

### 2.2. Không gian hành động của Khối Phân Tách
Khi ở trạng thái phân tách, không gian hành động mở rộng từ 4 hướng di chuyển sang **5 hành động**:
$$\mathcal{A}_{\text{split}} = \{\text{UP}, \text{RIGHT}, \text{DOWN}, \text{LEFT}, \text{SWITCH\_CUBE}\}$$
- **Hành động di chuyển (`UP`, `RIGHT`, `DOWN`, `LEFT`)**: Chỉ làm thay đổi tọa độ của khối đang nhận quyền điều khiển (`active_cube`):
  $$(x_{\text{active}}', y_{\text{active}}') = (x_{\text{active}} + dx, y_{\text{active}} + dy)$$
  Khối không được chọn (`inactive_cube`) giữ nguyên vị trí.
- **Hành động chuyển đổi điều khiển (`SWITCH_CUBE` / phím Space / ký hiệu `_`)**:
  Hoán đổi chỉ số điều khiển:
  $$\text{active\_cube}' = 1 - \text{active\_cube}$$
  Hành động này không làm dịch chuyển khối trên bản đồ, do đó không kích hoạt công tắc và không làm tăng bộ đếm số bước di chuyển vật lý của màn chơi.

### 2.3. Quy tắc tương tác với các loại ô đặc biệt
Theo đặc tả đồ án và phần giải đáp thắc mắc (Q&A của Giảng viên):
1. **Ô dễ vỡ (`Fragile tile` / ô màu cam)**:
   - *Luật*: Khối nhỏ $1 \times 1 \times 1$ có trọng lượng nhẹ (1 đơn vị diện tích tiếp xúc với 1 đơn vị khối lượng), do đó **đứng trên ô Fragile KHÔNG làm sập ô** (Q&A câu 16: *"với cube 1x1x1 đang tách: đứng trên ô fragile có làm ô vỡ và thua không ạ -> Không á em"*).
2. **Công tắc mềm (`Soft switch` / hình tròn)**:
   - Bất kỳ khối nhỏ nào chạm vào ô công tắc mềm đều kích hoạt đóng/mở cầu liên kết.
3. **Công tắc nặng (`Heavy switch` / hình chữ X)**:
   - Khối nhỏ $1 \times 1 \times 1$ **KHÔNG kích hoạt** được công tắc nặng (chỉ có khối chuẩn $1 \times 1 \times 2$ đứng thẳng mới kích hoạt được).
4. **Ô đích (`Goal hole`)**:
   - Một khối nhỏ đơn độc **không thể hoàn thành màn chơi**. Nếu khối nhỏ bước vào ô Goal, nó sẽ rơi xuống hố rỗng (`FELL_VOID`) dẫn đến thất bại.

### 2.4. Cơ chế Kích hoạt Phân tách (`trigger_teleport`)
- Công tắc phân tách (`TileType.TELEPORT`, ký hiệu `( )` hoặc số `8` trong file JSON) chỉ kích hoạt khi khối chuẩn $1 \times 1 \times 2$ **đứng thẳng (STANDING)** trên ô đó.
- Khi kích hoạt, khối lập tức tách ra và dịch chuyển đến hai tọa độ mục tiêu:
  $$\text{BlockState}(x, y, \text{STANDING}) \xrightarrow{\text{Split}} \text{SplitBlockState}(\text{target}_1, \text{target}_2, \text{selected})$$

### 2.5. Cơ chế Tự Động Hợp Nhất (Rejoining / Merging)
Sau mỗi bước di chuyển của khối đang active, hệ thống kiểm tra điều kiện kề cận trực giao (Orthogonal Adjacency theo khoảng cách Manhattan):
$$D_{\text{Manhattan}}(c_1, c_2) = |x_1 - x_2| + |y_1 - y_2|$$
- **Nếu $y_1 = y_2$ và $|x_1 - x_2| = 1$ (Kề cận theo phương ngang)**:
  Hai khối tự động hợp nhất thành khối chuẩn $1 \times 1 \times 2$ ở tư thế nằm ngang:
  $$\text{BlockState}(\min(x_1, x_2), y_1, \text{BlockOrientation.LYING\_X})$$
- **Nếu $x_1 = x_2$ and $|y_1 - y_2| = 1$ (Kề cận theo phương dọc)**:
  Hai khối tự động hợp nhất thành khối chuẩn $1 \times 1 \times 2$ ở tư thế nằm dọc:
  $$\text{BlockState}(x_1, \min(y_1, y_2), \text{BlockOrientation.LYING\_Y})$$
- **Nếu $D_{\text{Manhattan}} \neq 1$**: Khối tiếp tục duy trì trạng thái phân tách `SplitBlockState`.

---

## 3. Thuật toán Tìm kiếm DFS (`bloxorz/solvers/dfs.py`)

Trong bài toán Bloxorz, không gian trạng thái chứa vô số chu trình (ví dụ: lăn phải rồi lăn trái trở về vị trí cũ). Nếu áp dụng DFS ngây thơ không có cơ chế phát hiện lặp, thuật toán sẽ rơi vào vòng lặp vô tận.

#### Cấu trúc thuật toán DFS đã hiện thực:
1. **Ngăn xếp hiện thị (Explicit Stack)**: Thay vì dùng hàm đệ quy của Python (dễ bị giới hạn bởi `sys.getrecursionlimit()` dẫn đến `RecursionError`), thuật toán sử dụng cấu trúc `list` làm ngăn xếp LIFO lưu trữ `(current_block, current_board, path_moves)`.
2. **Chữ ký trạng thái chuẩn hóa (Canonical State Signature)**:
   Để kiểm tra chu trình hoàn hảo, chữ ký trạng thái $K$ bao gồm:
   $$K = (\text{block\_state}, \text{bridge\_configuration})$$
   Trong đó `bridge_configuration` là tuple sắp xếp trạng thái mở/đóng của toàn bộ các cầu trên bản đồ:
   $$((\text{bridge\_id}_1, \text{is\_open}_1), (\text{bridge\_id}_2, \text{is\_open}_2), \dots)$$
3. **Cơ chế tránh chu trình (`visited set`)**:
   Khi một nút con được sinh ra, nếu chữ ký $K$ đã tồn tại trong `visited`, bước đi đó bị cắt tỉa (pruning) ngay lập tức.
4. **Kiểm tra đích sớm (Early Goal Test)**:
   Ngay khi sinh nút con, nếu nút con đạt trạng thái `VICTORY`, thuật toán lập tức dừng và trả về đường đi, giúp tiết kiệm thời gian duyệt không cần thiết.

---

## 4. Hệ thống Phân Cấp Test Cases từ Cơ Bản đến Nâng Cao

Để phục vụ cho phần thực nghiệm và so sánh của đồ án (đặc biệt hỗ trợ Member 4 chạy benchmark), toàn bộ các màn chơi đã được chuẩn hóa và phân thành **5 nhóm độ khó tăng dần** trong file `data/test_cases_catalog.json`:

| STT | Nhóm màn chơi | Mã Stage | Kích thước Grid | Số bước tối ưu | Đặc điểm kỹ thuật kiểm thử |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | **Nhóm 1: Cơ bản (Basic)** | `stage_01.json` | $6 \times 10$ | **7** | Địa hình chuẩn, kiểm tra chuyển đổi tư thế cơ bản và đích đến. |
| **2** | **Nhóm 1: Cơ bản (Basic)** | `stage_03.json` | $6 \times 15$ | **19** | Đường đi hẹp dài, ngõ cụt, kiểm tra khả năng quay đầu khối. |
| **3** | **Nhóm 1: Cơ bản (Basic)** | `stage_06.json` | $10 \times 15$ | **35** | Mê cung rộng, hệ số phân nhánh cao, kiểm tra khả năng cắt tỉa chu trình. |
| **4** | **Nhóm 2: Ô dễ vỡ (Fragile)** | `stage_04.json` | $9 \times 14$ | **28** | Dải ô cam dễ vỡ, bắt buộc căn chỉnh khối luôn ở tư thế nằm ngang/dọc. |
| **5** | **Nhóm 2: Ô dễ vỡ (Fragile)** | `stage_13.json` | $10 \times 14$ | **46** | Mạng lưới ô dễ vỡ đan xen, kiểm tra tính toán chẵn lẻ bước đi. |
| **6** | **Nhóm 3: Công tắc & Cầu** | `stage_02.json` | $6 \times 15$ | **17** | Làm quen với công tắc mềm (tròn) và công tắc nặng (chữ X). |
| **7** | **Nhóm 3: Công tắc & Cầu** | `stage_05.json` | $10 \times 15$ | **33** | Mạng lưới 3 cầu, 4 công tắc liên kết phụ thuộc lẫn nhau. |
| **8** | **Nhóm 3: Công tắc & Cầu** | `stage_07.json` | $8 \times 15$ | **44** | Cần kích hoạt công tắc từ xa rồi quay lại đi qua cây cầu vừa mở. |
| **9** | **Nhóm 4: Phân tách khối** | `stage_08.json` | $9 \times 15$ | **10** | Công tắc phân tách, teleport ra 2 khối $1 \times 1 \times 1$, hợp nhất theo trục đứng. |
| **10** | **Nhóm 4: Phân tách khối** | `stage_09.json` | $5 \times 15$ | **24** | Điều phối 2 khối nhỏ đi qua hẻm hẹp và hợp nhất theo trục ngang. |
| **11** | **Nhóm 5: Kết hợp phức tạp** | `stage_10.json` | $10 \times 14$ | **57** | Kết hợp phân tách khối, ô dễ vỡ, công tắc mềm và 3 cây cầu. |
| **12** | **Nhóm 5: Kết hợp phức tạp** | `stage_23.json` | $10 \times 15$ | **75** | Màn chơi đỉnh cao: 6 cầu, 4 công tắc, ô dễ vỡ và công tắc phân tách. |

---

## 5. Kết quả Kiểm thử Tự động (Regression Verification)

Tất cả các mô-đun được xây dựng đều tuân thủ 100% tài liệu hướng dẫn [CONTRIBUTING.md](file:///d:/AIOnClass/bloxorz/CONTRIBUTING.md), chạy hoàn toàn độc lập trong môi trường headless (không phụ thuộc engine đồ họa), tuân thủ định dạng PEP 8 (độ dài dòng $\le 120$ ký tự) và đạt tỷ lệ vượt qua **24/24 unit tests (100% Pass)**:

```text
Ran 24 tests in 0.080s
OK
```

### Chi tiết các test case đã kiểm thử thành công:
1. `tests/test_split.py`:
   - `test_split_block_state_properties`: Kiểm tra khởi tạo và hoán đổi điều khiển giữa 2 khối nhỏ.
   - `test_split_movement_without_merge`: Kiểm tra di chuyển độc lập khối active.
   - `test_split_merge_horizontal`: Kiểm tra tự động gộp thành `LYING_X` khi kề cận ngang.
   - `test_split_merge_vertical`: Kiểm tra tự động gộp thành `LYING_Y` khi kề cận dọc.
   - `test_split_on_fragile_is_safe`: Kiểm tra khối nhỏ đứng trên ô fragile không làm sập ô (theo Q&A 16).
   - `test_split_on_goal_fails`: Kiểm tra khối nhỏ rơi vào ô Goal sẽ thua (không thể tự về đích).
   - `test_split_switches_interaction`: Kiểm tra khối nhỏ bật được Soft switch và không bật được Heavy switch.
   - `test_stage_08_ground_truth_solution`: Chạy diễn hoạt chính xác chuỗi bước đi chuẩn `RRDDDD_UURR` trên Stage 08 và đạt `VICTORY` tuyệt đối.
2. `tests/test_dfs.py`:
   - `test_dfs_solves_stage_01`: DFS giải thành công Stage 01, đo đạc đầy đủ thời gian và Peak Memory.
   - `test_dfs_solves_bridge_stage_02`: DFS giải thành công màn chơi có mạng lưới cầu và công tắc (Stage 02).
   - `test_dfs_solves_split_stage_08`: DFS tự động tìm đường giải thành công màn chơi có phân tách khối (Stage 08).
   - `test_dfs_cycle_prevention`: Kiểm tra thuật toán phát hiện chu trình trên bản đồ vòng tròn, kết thúc an toàn không bị treo.
3. `tests/test_core.py` & `tests/test_levels.py`:
   - Toàn bộ 12 test case nền tảng về vật lý khối và nạp 33 màn chơi đều duy trì hoạt động hoàn hảo.

---

## 6. Kết luận & Hướng bàn giao cho các thành viên còn lại
- **Mở đường cho Member 2 (BFS)**: Đã có sẵn cấu trúc `SplitBlockState` và hàm `get_successors()` hoàn chỉnh, Member 2 chỉ cần gọi hàm sinh kế tiếp là BFS tự động giải được cả các màn có phân tách khối.
- **Mở đường cho Member 4 (UCS & Benchmark)**: 
  - File danh mục `data/test_cases_catalog.json` đã sẵn sàng để script `benchmark.py` của Member 4 nạp tự động chạy vòng lặp đo đạc trên 12 test cases tiêu chuẩn.
  - Thuộc tính `peak_memory_kb` và `expanded_nodes` đã được tích hợp sẵn vào `SolverResult` và lớp cơ sở `BaseSolver`.
- **Tài liệu cho Báo cáo**: Toàn bộ nội dung toán học và bảng phân loại màn chơi trong tài liệu này có thể đưa trực tiếp vào Báo cáo PDF cuối kỳ của nhóm.
