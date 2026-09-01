# roles — năm vai, chia theo VIỆC không theo tầng

Vai là mũ, không phải đầu người: repo một người đội cả năm mũ và không mất gì.
Ràng buộc chỉ bắt đầu có nghĩa khi các mũ nằm trên các phiên khác nhau.

| Role | Làm | Ràng buộc đáng tiền nhất |
|---|---|---|
| `planner` | đo bug tại chỗ, viết phiếu, xếp lane + mức, khai `scope_files`, giao việc | **không sửa code** |
| `executor` | một phiếu – một cây – tới `done`; n phiên song song | tự gộp bằng `crew done`, không chờ ai duyệt |
| `tester` | nghiệm thu + test khám phá đóng vai khách | **không vá thứ mình phát hiện** — phát hiện viết thành Issue |
| `devops` | giữ nhánh production, quan sát bản đang chạy | không nhận phiếu code |
| `steward` | dựng/dọn cây mồ côi, giữ bảng trạng thái, ghi luật | **không giao việc, không nhận báo cáo** |

`release.md` trong `.claude/commands/` là một thủ tục devops chạy, không phải
vai thứ sáu.

## Vì sao planner không được sửa code

Đây là cơ chế duy nhất phát hiện xếp mức sai. Ca đo được ở repo gốc: một phiếu
xếp NHẸ ("một tệp, dưới 50 dòng") giữ khoá máy test **871 giây**, vì thứ nó sửa
là hành vi của một công cụ vận hành lúc môi trường hỏng. Executor báo ngược con
số đó thì mức mới được sửa; nếu người xếp cũng là người sửa thì con số không
đến tay ai.

## Vì sao tester không được vá

Một lượt kiểm tay đóng vai khách tìm ra **12 phát hiện trong khi bộ test tự
động vẫn xanh**. Giá trị của tester nằm ở con mắt ngoài, và vá ngay là đổi con
mắt ngoài lấy một bản vá. Phát hiện đi vào hệ bằng cửa nhận sẵn có: tester viết
Issue, planner triage thành Backlog và xếp mức.

## Vai chưa tồn tại thì khai vắng, đừng stamp ma

Test và deploy mỗi hệ mỗi khác, nên `crew-init` kiểm bằng chứng từng vai —
tester cần lệnh test thật hoặc một harness đáng khoá, devops cần nhánh
production tồn tại hoặc dấu vết deploy — và vai nào thiếu bằng chứng thì phải
hỏi thẳng người dùng, không được lặng lẽ stamp. Vai trả lời "chưa có" đi vào
`roles_absent` trong config, tệp lệnh của nó không được stamp, và
`scripts/crew status` nhắc khoảng trống đó cho tới khi ai đó đấu nối. Một tệp
vai cho một vai không tồn tại là một sự thật sai nằm trong repo.

## Tên phiên là phần nhìn thấy được của mũ

| Loại phiên | Tên | Ví dụ |
|---|---|---|
| phiên phiếu (executor) | `<repo> · b<nnn> · crew/executor` | `lop-hoc-zalo · b157 · crew/executor` |
| phiên mũ (bốn vai còn lại) | `<repo> · crew/<vai>` | `lop-hoc-zalo · crew/steward` |

Tên repo đứng trước để danh sách phiên tự gom theo dự án, và phiên phiếu giữ
nguyên token `b157` — đúng chuỗi mà cây làm việc và nhánh đang mang, nên gõ một
con số vẫn tra ra cả năm chỗ (`tickets.md`).

`scripts/crew name <vai> [<nnn>]` đọc **title** của phiên đang chạy rồi so với
hai dòng trên, và title chưa đúng thì vai chưa bắt đầu.

Một phiên mang hai nhãn khác nhau, và phép kiểm đọc nhãn nào là chuyện có hậu
quả thật. `name` nằm trong bản ghi phiên sống, còn title là thứ danh sách phiên
hiển thị. Đổi tên trong app chỉ ghi title, còn `/rename` gõ trong terminal ghi
cả hai. Bản đầu của phép kiểm đọc `name`, nên bốn phiên đã đổi tên trong app —
đặt đúng và nhìn thấy đúng ngay trong sidebar — đều báo đỏ. Vì vậy nó chuyển
sang đọc title: bản ghi `custom-title` cuối cùng trong transcript của phiên.

Luật này mua được cái gì và không mua được cái gì, nói thẳng ra: title không
duy nhất, nên nó **không** chặn được hai phiên cùng đội một mũ. Nó chỉ làm cái
mũ hiện ra, và người đọc danh sách mới là thứ bắt được trùng. Hiện chỉ
`steward.md` bắt buộc chạy phép kiểm; các vai khác mới dừng ở mức khai tên.

## Steward và cây bút luật

Phiên steward khi đề xuất một thay đổi luật **mở rộng quyền của chính nó** phải
nói thẳng điều đó trong lời xin duyệt. Chuyện này đã xảy ra thật và không cơ
chế nào chặn được, vì vậy luật được ghi ra đây để im lặng bị đọc là vi phạm
chứ không phải sơ suất.
