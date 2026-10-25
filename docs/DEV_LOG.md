# Nhật Ký Phát Triển & Quản Lý Vấn Đề Kỹ Thuật (Development Log)
Dự án: Bloxorz Solver - Project 1 (CSC14003 - Nhập môn Trí tuệ Nhân tạo)  
Nhánh: feat/member-3-dfs (Member 3)  
Cập nhật lần cuối: 25/10/2026  

---

## 1. Những công việc đã làm

Phần này tóm tắt ngắn gọn các hạng mục công việc mà Member 3 đã thực hiện và hoàn thành trên nhánh:

1. Thuật toán tìm kiếm DFS (bloxorz/solvers/dfs.py):
   - Cài đặt thuật toán tìm kiếm theo chiều sâu (Depth-First Search) để giải quyết các màn chơi Bloxorz.
   - Quản lý tập các trạng thái đã duyệt (visited) dựa trên khóa chuẩn hóa (canonical_key) kết hợp trạng thái khối và trạng thái các cây cầu, giúp tránh lặp vô tận trên đồ thị có chu trình.
   - Hỗ trợ đầy đủ các bước đi hợp lệ: lăn khối bình thường, kích hoạt các loại công tắc và cầu, chuyển đổi điều khiển giữa hai khối lập phương (SWITCH_CUBE), và đi qua cổng dịch chuyển.

2. Cơ chế phân tách khối và dịch chuyển (Split Block & Teleport):
   - Xây dựng lớp trạng thái SplitBlockState (trong bloxorz/core/block/split.py và bloxorz/core/split.py).
   - Mô phỏng chính xác các quy tắc vật lý khi khối bị tách thành hai khối lập phương 1x1x1:
     + Kích hoạt công tắc chữ X (Soft switch).
     + Đứng an toàn trên các ô màu cam (Fragile tile) mà không làm sập ô.
     + Di chuyển qua ô đích (Goal tile) an toàn (không bị rơi nhưng không chiến thắng một mình; chỉ thắng khi hai khối đã ghép lại thành khối 1x1x2 đứng thẳng trên ô đích).
     + Tự động ghép lại (Merge) thành khối 1x1x2 khi hai khối 1x1x1 di chuyển đến vị trí kề sát nhau.

3. Phân loại bộ dữ liệu kiểm thử (Test Cases Catalog):
   - Xây dựng tệp dữ liệu data/test_cases_catalog.json, phân loại 33 màn chơi theo 5 nhóm độ khó để đánh giá hiệu năng và tính đúng đắn của thuật toán.

4. Bộ kiểm thử tự động (Unit Tests):
   - Viết các ca kiểm thử tự động trong tests/test_dfs.py và tests/test_split.py, đảm bảo kiểm thử toàn diện thuật toán DFS, cơ chế phân tách và các tương tác đặc thù. Toàn bộ 26/26 ca kiểm thử đều vượt qua.

5. Tài liệu kỹ thuật và kịch bản mô phỏng:
   - Soạn thảo báo cáo kỹ thuật chi tiết tại docs/MEMBER_3_DFS_SPLIT.md và xây dựng tệp demo.py để chạy thử nghiệm các màn chơi tiêu biểu.

---

## 2. Các lỗi đã xảy ra và đề xuất xử lý

Phần này ghi nhận các lỗi kỹ thuật và vấn đề trải nghiệm phát sinh trong quá trình phát triển, nguyên nhân, giải pháp gợi ý, cũng như tình trạng thực hiện (đã sửa hay chưa sửa).

### Vấn đề 1: Lỗi mất trạng thái cầu khi nhân bản bàn cờ (Board.clone())
- Mô tả vấn đề:
  Trong các màn chơi có công tắc và cầu (như Stage 05, Stage 14, Stage 20), khi thuật toán tìm kiếm rẽ nhánh và gọi lệnh sao chép trạng thái bàn cờ (board.clone()), cây cầu vừa mở lại bị đặt lại về trạng thái ban đầu của màn chơi. Do đó, thuật toán không thể đi qua cây cầu vừa mở và kết luận là không tìm được đường đi.
- Nguyên nhân:
  Hàm khởi tạo Board.__init__() tự động gọi lệnh self.reset(). Khi gọi clone(), bàn cờ mới được tạo ra và vô tình chạy lại hàm reset(), làm đè mất các thay đổi công tắc trước đó.
- Giải pháp gợi ý:
  Bổ sung tham số auto_reset=False vào hàm khởi tạo Board.__init__(). Trong hàm Board.clone(), truyền tham số này để không reset bàn cờ, đồng thời sao chép chính xác thuộc tính is_open của từng cây cầu và đồng bộ lại các ô sàn liên quan.
- Tình trạng xử lý:
  Đã sửa xong trong mã nguồn của Member 3 (tại bloxorz/core/board.py trên nhánh feat/member-3-dfs). Các thành viên khác có thể trực tiếp tham khảo cách xử lý này để đưa vào nhánh của mình.

### Vấn đề 2: Lỗi không hiển thị đầy đủ hai khối khi phân tách (Stage 08)
- Mô tả vấn đề:
  Khi khối đi vào ô phân tách (Teleport), khối được tách thành hai khối lập phương 1x1x1 độc lập. Tuy nhiên, trên giao diện đồ họa, người chơi không nhìn thấy được cả hai khối đang ở đâu trên bàn cờ. Hệ thống chỉ vẽ duy nhất khối đang được chọn để điều khiển, còn khối thụ động còn lại bị ẩn đi, khiến người chơi không thể nắm bắt được toàn bộ bàn cờ.
- Giải pháp gợi ý:
  Cập nhật tầng đồ họa 3D để render đồng thời cả hai khối khi trạng thái khối là SplitBlockState, đồng thời gắn phím Space (hoặc nút bấm trên giao diện) để người chơi có thể chuyển đổi qua lại giữa hai khối.
- Tình trạng xử lý:
  - Tầng logic và thuật toán: Member 3 đã cài đặt hoàn chỉnh và hỗ trợ đầy đủ.
  - Tầng giao diện 3D: Đã được bổ sung trong bản cập nhật mới nhất trên nhánh main. Nhánh feat/member-3-dfs đã tích hợp thành công. Các thành viên khác cần đồng bộ mã nguồn mới từ main về để có phần hiển thị đầy đủ cả hai khối.

### Vấn đề 3: Lời giải thuật toán DFS quá dài và thiếu công cụ điều khiển trên giao diện
- Mô tả vấn đề:
  Thuật toán DFS duyệt theo chiều sâu nên không đảm bảo tìm được đường đi ngắn nhất. Ở một số màn chơi (như Stage 09), DFS tìm ra chuỗi hành động dài tới 762 bước (trong khi đường đi tối ưu chỉ khoảng 24 bước). Khi giao diện diễn hoạt từng bước, người chơi phải chờ gần 3 phút và hoàn toàn không thể dừng lại hay đẩy nhanh tiến độ.
- Giải pháp gợi ý cho giao diện (GUI):
  1. Thêm nút Dừng AI (Stop / Cancel): Cho phép người chơi dừng diễn hoạt ngay lập tức bằng nút bấm hoặc phím tắt.
  2. Thêm thanh chỉnh tốc độ diễn hoạt: Cung cấp các mức tốc độ (ví dụ 1x, 2x, 5x, 10x) để người chơi có thể tua nhanh.
  3. Thêm nút Bỏ qua (Skip to End): Lập tức đưa khối đến vị trí kết thúc mà không cần xem từng bước.
  4. Cho phép người chơi lựa chọn thuật toán phù hợp trên giao diện: Giúp người chơi linh hoạt chọn giữa DFS, BFS, hay A* tùy theo đặc điểm màn chơi.
- Tình trạng xử lý:
  Chưa làm trên giao diện (đây là phần việc thuộc về tầng giao diện người dùng của Member 1; đã được ghi nhận vào danh sách công việc tồn đọng để phối hợp hoàn thiện).

### Vấn đề 4: Bị khóa các phím điều hướng (Menu / Chơi lại / Cài đặt) khi đang diễn hoạt
- Mô tả vấn đề:
  Khi hoạt cảnh di chuyển của khối hoặc diễn hoạt lời giải của AI đang chạy, hệ thống khóa nhận tín hiệu để bảo vệ khung hình. Điều này khiến các phím chức năng như R (chơi lại màn), O (mở cài đặt), ESC (quay về menu chính) không phản hồi, tạo cảm giác game bị đơ.
- Giải pháp gợi ý cho giao diện (GUI):
  Trong hàm xử lý sự kiện phím, nếu người chơi bấm ESC hoặc R trong lúc đang diễn hoạt, hệ thống cần tự động ngắt diễn hoạt an toàn trước khi chuyển màn hình hoặc nạp lại màn chơi.
- Tình trạng xử lý:
  Chưa làm trên giao diện (đây là phần việc thuộc về tầng giao diện người dùng của Member 1; đã được ghi nhận vào danh sách công việc tồn đọng để phối hợp hoàn thiện).
