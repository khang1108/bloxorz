# Nhật Ký Phát Triển & Quản Lý Vấn Đề Kỹ Thuật (Development Log & Issue Backlog)
**Dự án:** Bloxorz Solver - Project 1 (CSC14003 - Nhập môn Trí tuệ Nhân tạo)  
**Nhánh:** `feat/member-3-dfs` (Member 3)  
**Cập nhật lần cuối:** 25/10/2026  

---

## 1. Tổng quan mục đích
Tài liệu này đóng vai trò là sổ ghi nhận kỹ thuật (Dev Log) tập trung cho toàn nhóm, ghi lại:
- Các lỗi phát sinh trong mã nguồn gốc (Root Cause & Solution).
- Trạng thái giải quyết trên các nhánh làm việc.
- Các vấn đề trải nghiệm người dùng (UX/UI Backlog) được phát hiện để các thành viên liên quan tham khảo và hoàn thiện.

---

## 2. Danh sách các vấn đề kỹ thuật (Technical Issues & Backlog)

### 📌 Vấn đề 1: Lỗi "Mất trí nhớ trạng thái cầu" trong nhân bản bàn cờ (`Board.clone()`)
* **Mức độ nghiêm trọng:** Nghiêm trọng (Critical Bug) - Ảnh hưởng trực tiếp đến kết quả tìm kiếm của tất cả các thuật toán AI (BFS, DFS, IDS, UCS, A*).
* **Mô tả triệu chứng:**
  - Ở các màn chơi có mạng lưới công tắc và cầu liên kết (như Stage 05, Stage 14, Stage 20), khi thuật toán tìm kiếm rẽ nhánh, khối dẫm lên công tắc làm cầu chuyển trạng thái (Mở $\leftrightarrow$ Đóng).
  - Tuy nhiên, ngay bước tính toán kế tiếp, thuật toán không thể đi qua cây cầu vừa mở và kết luận là không tìm được đường đi (hoặc rơi vào bế tắc lặp lại).
* **Nguyên nhân kỹ thuật (Root Cause):**
  - Trong tệp `bloxorz/core/board.py`, hàm khởi tạo `Board.__init__()` tự động gọi lệnh `self.reset()`.
  - Khi thuật toán tìm kiếm gọi `new_board = board.clone()` để tạo trạng thái mới, hàm `reset()` vô tình đè lại toàn bộ thuộc tính `bridge.is_open = bridge.initially_open` (trạng thái lúc mới vào màn). Cầu bị đưa về trạng thái xuất phát, làm mất trí nhớ mọi thay đổi công tắc trước đó.
* **Phân công trách nhiệm:**
  - Nghiệp vụ Cầu & Công tắc thuộc trách nhiệm của **Member 2**.
  - Khung kiến trúc bàn cờ và lớp `Board` thuộc trách nhiệm của **Member 1**.
* **Trạng thái xử lý:**
  - ✅ **ĐÃ SỬA XONG TRONG CODE CỦA BRANCH MEMBER 3 (`feat/member-3-dfs`)**.
  - **Giải pháp kỹ thuật đã áp dụng:**
    1. Bổ sung tham số `auto_reset: bool = True` vào `Board.__init__()`. Khi `Board.clone()` được gọi, truyền `auto_reset=False` để bỏ qua việc reset cầu.
    2. Trong `Board.clone()`, khôi phục chính xác trạng thái thực tế `new_board.bridges[b_id].is_open = bridge.is_open` và gọi `_sync_bridge_tiles()` để cập nhật ma trận ô sàn.
  - **Ghi chú cho nhóm:** Các thành viên (Member 1, Member 2, Member 4) có thể trực tiếp tham khảo cách sửa trong `bloxorz/core/board.py` trên branch này để tích hợp vào nhánh của mình.

---

### 📌 Vấn đề 2: Tối ưu trải nghiệm khi AI chạy lời giải có số bước lớn (Ví dụ: Stage 9 có 762 bước)
* **Mức độ:** Cải thiện trải nghiệm người dùng (UX Enhancement).
* **Mô tả triệu chứng:**
  - Thuật toán DFS thuần túy tìm kiếm theo chiều sâu đầu tiên nên không đảm bảo tính tối ưu độ dài. Ở một số màn chơi (như Stage 09), DFS tìm ra chuỗi lời giải dài tới 762 bước (trong khi số bước tối ưu của IDS chỉ là 24 bước).
  - Với tốc độ diễn hoạt đồ họa mặc định (khoảng 0.15s - 0.25s / bước), 762 bước khiến hoạt cảnh diễn ra kéo dài gần 3 phút, người chơi không thể can thiệp hay thoát ra được.
* **Đề xuất giải pháp (Backlog cho Member 1 - Phụ trách GUI):**
  1. **Nút "Dừng AI" (Stop / Cancel Solver):** Bổ sung nút bấm trên HUD hoặc gán phím tắt `ESC` / `Space` để người chơi có thể hủy ngang diễn hoạt (`app.stop_solution()`) bất cứ lúc nào.
  2. **Thanh chỉnh tốc độ (Playback Speed):** Cung cấp các mức tốc độ `1x`, `2x`, `5x`, `10x` trong lúc AI diễn hoạt để người chơi tua nhanh.
  3. **Nút "Bỏ qua diễn hoạt" (Skip to End):** Lập tức đưa khối về trạng thái chiến thắng mà không cần chờ diễn hoạt từng bước.
  4. **Ưu tiên giải pháp tối ưu:** Trong menu chọn thuật toán, khuyến nghị người dùng chọn **IDS** (của Member 3), **BFS** (của Member 2) hoặc **A\*** (của Member 1) đối với các màn chơi có không gian trạng thái rộng.
* **Trạng thái:** 📋 **ĐANG LƯU LOG / CHỜ TRIỂN KHAI TẦNG GUI (Backlog)** (Chưa sửa trực tiếp vào code GUI theo yêu cầu giữ nguyên hiện trạng).

---

### 📌 Vấn đề 3: Khóa tương tác Menu / Reset / Settings trong lúc đang diễn hoạt hoạt cảnh
* **Mức độ:** Cải thiện logic giao diện (UI Logic).
* **Mô tả triệu chứng:**
  - Khi khối đang lăn hoặc khi AI Solver đang diễn hoạt, hệ thống kích hoạt cờ `self.block_view.is_animating = True` để bảo vệ đồng bộ khung hình đồ họa.
  - Tuy nhiên, điều này vô tình chặn luôn các phím điều hướng hệ thống như `R` (Restart), `O` (Settings), `ESC` (Chọn màn / Pause). Người chơi có cảm giác game bị treo hoặc không bấm được gì khi màn chơi đang diễn hoạt.
* **Đề xuất giải pháp (Backlog cho Member 1):**
  - Trong hàm `handle_input()`, nếu nhận phím `ESC` hoặc `R` trong lúc `self._is_playing_solution == True`, hệ thống cần tự động gọi `self.stop_solution()` để ngắt hoạt cảnh an toàn trước khi chuyển qua hiển thị menu hoặc khởi động lại màn chơi.
* **Trạng thái:** 📋 **ĐANG LƯU LOG / CHỜ TRIỂN KHAI TẦNG GUI (Backlog)**.

---

### 📌 Vấn đề 4: Hiển thị cả 2 khối và chuyển đổi điều khiển khi phân tách khối (Stage 08)
* **Mô tả:**
  - Ở màn chơi có công tắc phân tách (Teleport), khối tách thành 2 khối lập phương $1 \times 1 \times 1$.
  - Người chơi cần nhìn thấy cả 2 khối trên bản đồ và dùng phím `Space` để đổi quyền điều khiển giữa 2 khối.
* **Trạng thái xử lý:**
  - ✅ **ĐÃ HOÀN TẤT VÀ TÍCH HỢP**:
    - Tầng Core & Thuật toán: Member 3 đã cài đặt đầy đủ cấu trúc `SplitBlockState`, lệnh `Direction.SWITCH_CUBE`, kiểm tra an toàn trên ô fragile và cơ chế tự động hợp nhất khi kề cận.
    - Tầng Đồ họa 3D & Phím Space: Member 1 (bạn Khang) đã cập nhật trong commit `332344a` trên `main` và nhánh `feat/member-3-dfs` đã kéo về tích hợp thành công.

---

## 3. Lịch sử đồng bộ Git (Git Sync History)
- **Commit `7b3f9a0`:** Lưu trữ toàn bộ mã nguồn DFS/IDS Solver, Split mechanics, Test catalog và bản vá lỗi `Board.clone()`.
- **Cập nhật từ `origin/main` (commit `332344a`):** Kéo các cập nhật đồ họa 3D, animation phân tách khối và tái cấu trúc module `block/` từ bạn Khang về nhánh.
- **Commit `8b89f9f` & Merge:** Giải quyết xung đột hợp nhất, đảm bảo toàn bộ mã nguồn và bài test của Member 3 (cùng bản vá lỗi cầu) hoạt động hài hòa 100% với phiên bản mới nhất từ `main`.
