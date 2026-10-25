# UCS cho Bloxorz

## Mục tiêu và luật chơi

UCS tìm lời giải có tổng chi phí nhỏ nhất từ đầu màn. Solver dùng chung hàm sinh
trạng thái và kiểm tra thắng của core, chạy không cần mở Ursina. Phần này chưa
bao gồm benchmark hay các thuật toán khác.

Trạng thái được nhận diện bằng vị trí/hướng của khối và cấu hình mọi nhóm cầu:

```text
(BlockState(x, y, orientation), ((bridge_id, is_open), ...))
```

Khối đứng chiếm một ô; nằm theo X hoặc Y chiếm hai ô. Các bước ra ngoài bàn,
qua void/cầu không thể đi, hoặc đứng trên fragile đều bị core loại. Soft switch
nhận tiếp xúc ở mọi hướng; heavy switch yêu cầu khối đứng. Cấu hình cầu phải
được giữ sau khi khối rời công tắc. Chỉ khối lớn đứng tại đích mới thắng.

Đề và FAQ của môn học là căn cứ cho bài nộp. Hướng dẫn đối chiếu:
[Bloxorz trên Coolmath](https://www.coolmathgames.com/0-bloxorz).

## Cost function

Hàm dùng chung `fragile_cost(block, board, successor)` trong `bloxorz.solvers.costs`:

```text
cost(s, action, s_next) = 1 + 2 * I(s_next tiếp xúc ít nhất một ô fragile)
```

- Mỗi bước hợp lệ thông thường có cost 1, kể cả đi qua cầu hoặc công tắc.
- Tiếp xúc một hay hai ô fragile đều có cost 3.
- Còn tiếp xúc fragile sau lượt lăn tiếp theo thì tiếp tục chịu khoản cộng thêm.
- Rời fragile tới ô thường hoặc đích có cost 1.
- Bước gây thua bị loại trước khi tính cost.

Đây là quy ước ưu tiên tránh nền yếu, không phải luật tính điểm gốc hoặc xác suất
thua. Nằm đúng cách trên fragile vẫn an toàn trong game tất định. Hệ số 2 là lựa
chọn thiết kế: sẵn sàng chấp nhận một đường dài hơn để giảm tiếp xúc fragile.

Stage 03 có đường 8 bước với cost 10:

```text
DOWN, RIGHT, RIGHT, DOWN, RIGHT, RIGHT, RIGHT, RIGHT
```

UCS tìm được đường 9 bước có cost 9. Vì vậy số bước và tổng cost cần được đọc
riêng. Ở màn không có fragile, cost mặc định bằng số bước. Người làm A* có thể
nhập lại cùng hàm cost và kiểm chứng heuristic với mục tiêu đó.

## Thuật toán và giao diện

`UCSSolver(cost_fn=fragile_cost)` kế thừa `BaseSolver`. Hàm cost tùy chỉnh nhận
`(source_block, source_board, successor)` và phải trả số hữu hạn, không âm.
Cost 0 được chấp nhận; cost âm, NaN, vô cực hoặc tổng cost tràn số gây `ValueError`.
Hàm cost cần tất định và không thay đổi các trạng thái đầu vào.

1. Đưa trạng thái xuất phát vào min-heap với tổng cost 0.
2. Lấy trạng thái có tổng cost nhỏ nhất ra; bỏ bản ghi có cost đã lỗi thời.
3. Nếu là đích, lần theo chuỗi cha để trả danh sách `Direction`.
4. Nếu chưa thắng, sinh các bước hợp lệ bằng `BaseSolver.get_successors()`.
5. Chỉ thêm trạng thái nếu đường vừa tìm rẻ hơn chi phí tốt nhất đã biết.
6. Hàng đợi hết mà chưa đến đích thì trả kết quả không có lời giải theo core hiện tại.

Một bộ đếm tăng dần xử lý trường hợp bằng cost, tránh so sánh trực tiếp Board
hoặc BlockState. Giữ thứ tự sinh hướng của core: UP, RIGHT, DOWN, LEFT.
Phải kiểm tra đích khi lấy ra khỏi heap, không dừng ngay khi vừa sinh ra đích.
Trên không gian hữu hạn với cost không âm, UCS tìm được lời giải tối ưu nếu có.

Tài liệu tham khảo:
[UCS trong Berkeley CS188](https://inst.eecs.berkeley.edu/~cs188/textbook/search/uninformed.html#133-uniform-cost-search),
[hàng đợi ưu tiên của Python](https://docs.python.org/3/library/heapq.html#priority-queue-implementation-notes).

`solve(board)` trả `SolverResult`; gọi trực tiếp `solver(board)` trả danh sách
hướng để giữ tương thích callback GUI. Bàn đầu vào không bị thay đổi.

| Trường kết quả | Quy ước |
| --- | --- |
| `moves` | Danh sách hướng; độ dài lời giải là `len(moves)` khi `is_solved=True` |
| `solution_cost` | Tổng cost; 0 nếu xuất phát đã ở đích, `None` nếu không có lời giải |
| `visited_count` | Số khóa trạng thái đã phát hiện, gồm xuất phát và đích đã phát hiện |
| `expanded_nodes` | Số lần sinh trạng thái kế tiếp; bỏ qua nút đích và bản ghi lỗi thời |
| `max_depth` | Độ sâu lớn nhất của các nút đã mở rộng, không phải độ dài lời giải |
| `execution_time_ms` | Thời gian do wrapper `BaseSolver.solve()` đo |

Hai trường mới của `SolverResult` có mặc định và được thêm ở cuối, giữ tương
thích cách khởi tạo cũ. Solver khác cần tự điền chỉ số mở rộng/tổng cost khi tích hợp.
Lượt tìm kiếm đã thắng tại spawn có danh sách rỗng và `is_solved=True`; không
được chỉ dùng `moves == []` để kết luận tìm kiếm thất bại.

## Chạy thử và kiểm thử

Từ thư mục chứa `run.py`, sau khi kích hoạt môi trường:

```bash
python - <<'PY'
from pathlib import Path
from bloxorz.core.level_loader import load_level_from_file
from bloxorz.solvers import UCSSolver

board = load_level_from_file(Path("bloxorz/levels/stage_03.json"))
result = UCSSolver().solve(board)
print(result.summary())
print([move.name for move in result.moves])
PY

python -m pytest tests/ -v
```

Để xem animation của UCS:

```bash
python run.py
```

Lệnh chạy thông thường đã đăng ký UCS. Nhấn P để tự đưa màn về trạng thái ban đầu
và chạy lời giải. Restart hoặc đổi màn sẽ hủy lời giải cũ, kể cả bước đang chờ chạy.
Nếu không tìm được đường, GUI hiện `SOLVER FOUND NO SOLUTION`; màn split chưa được
hỗ trợ sẽ có thông báo riêng. Khi dùng API `launch(solver=...)`, callback tùy chỉnh
vẫn được giữ nguyên.

API tìm kiếm hiện chỉ nhận Board, không nhận vị trí khối đang chơi dở; luôn dùng
bàn mới nạp với `solve(board)`.

Các test kiểm tra cost, tối ưu chi phí, cập nhật đường rẻ hơn, heap bằng cost,
bản ghi lỗi thời, chu trình cost 0, dữ liệu không hỗ trợ, phát lại lời giải qua
`Game.roll()` và việc không thay đổi đầu vào. Các đồ thị nhỏ có cost biết trước
kiểm tra thuật toán độc lập với cơ chế lăn; Stage 03 kiểm tra lựa chọn cost trong game thật.

## Phụ thuộc core còn tồn tại

- `Board.clone()` hiện reset cờ cầu về ban đầu nhưng lại sao chép ô cầu hiện tại.
  Điều này làm khóa trạng thái và trạng thái đi lại không nhất quán. Stage 02 có
  lời giải phát lại được, nhưng chưa thể chứng nhận chung các màn có cầu.
- Stage 04 hiện bị UCS báo không có lời giải do lỗi clone; không dùng kết quả đó
  để khẳng định map vô nghiệm. Việc sửa core do thành viên khác phụ trách.
- Hai test hồi quy clone/Stage 04 được đánh dấu `xfail(strict=True)` kèm lý do.
  Khi nhóm sửa core, gỡ marker sau khi xác nhận các test qua; XPASS sẽ khiến suite
  thất bại để nhắc cập nhật tình trạng phụ thuộc.
- Test hành trình qua switch/cầu thay `clone` bằng `deepcopy` chỉ trong fixture
  để kiểm chứng UCS với snapshot đúng. Không có workaround trong mã sản phẩm.
- Core đang coi nằm qua đích là `FELL_HALF_GOAL`. UCS tuân theo core; nhóm cần
  thống nhất luật này với đề trước khi dùng làm kết quả cuối cùng.
- `TELEPORT` gây `NotImplementedError`. Cơ chế split cần core cung cấp trạng thái
  hai khối, khối đang điều khiển, hành động đổi khối và luật ghép lại trước khi
  tích hợp UCS. Theo FAQ, khối nhỏ đứng trên fragile không làm vỡ ô.
- Stage 05 không có lời giải theo core hiện tại và được dùng kiểm tra trường hợp thất bại.
