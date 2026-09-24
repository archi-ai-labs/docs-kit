# roles — sáu vai, chia theo VIỆC không theo tầng

Vai là mũ, không phải đầu người: repo một người đội cả sáu mũ và không mất gì.
Ràng buộc chỉ bắt đầu có nghĩa khi các mũ nằm trên các phiên khác nhau.

| Role | Làm | Ràng buộc đáng tiền nhất |
|---|---|---|
| `planner` | đo bug tại chỗ, viết phiếu, xếp lane + mức, khai `scope_files`, giao việc, quyết định cỡ pool | **không sửa code** |
| `executor` | một phiếu – một nhánh – tới `done`; một phiên mở bằng `crew new --chain` mang một chuỗi phiếu trong một executor | tự gộp bằng `crew done`, không chờ ai duyệt |
| `tester` | nghiệm thu + test khám phá đóng vai khách | **không vá thứ mình phát hiện** — phát hiện viết thành Issue |
| `devops` | giữ nhánh production, quan sát bản đang chạy | không nhận phiếu code |
| `steward` | dọn executor mồ côi, giữ bảng trạng thái, ghi luật | **không giao việc, không nhận báo cáo** |
| `navigator` | giữ cột `## Now` khớp Backlog, viết báo cáo tuần và kế hoạch tháng vào `docs/92_audit/reports/`, phát hiện thành Issue | **không viết phiếu, không nhận phiếu** |

`release.md` trong `.claude/commands/` là một thủ tục devops chạy, không phải
vai thứ bảy.

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

## Vì sao navigator không viết phiếu

Cơ chế được bảo vệ là: **người đo độ lệch không được là người xoá được độ lệch
bằng cách viết lại phiếu.** Nếu navigator vừa xếp lộ trình vừa cắt phiếu thì
lộ trình thành một hệ phiếu thứ hai, và cỡ một phiếu do chính người muốn nó
xong quyết định — đúng chỗ mà luật "người xếp mức ≠ người sửa" của planner tồn
tại để chặn.

Số đo ở repo gốc ngày 2026-09-10, một repo một ngày nên nói rõ là một điểm dữ
liệu: `docs/00_roadmap/roadmap.md` không đổi suốt **10 ngày**, trong khi 10
commit mang trailer `Closes: BACKLOG-`, 29 dòng audit dẫn id phiếu và 5 dòng
`DONE` vào `log.tsv`. Cột `## Now` gọi tên 4 phiếu, **cả 4 đã `done`** và đã
nằm trong `_archive/`, còn **cả 2 phiếu đang mở không xuất hiện ở cột nào**.
Không phép kiểm nào đỏ, vì trước 0.34.0 không có gì so hai tài liệu ấy với
nhau. Mũ planner đã được đội suốt mười ngày đó và vẫn không ai báo, nên gộp
việc này vào planner là phương án đã bị chính số đo bác bỏ.

Số đo thứ hai, cho vế "không nhận phiếu": `BACKLOG-017` ở repo ấy là việc định
hướng (khảo sát thị trường, lộ trình 6 tháng) bị đẩy qua Backlog thành một
phiếu code — `scope_files: 0`, ba deliverable nằm trong `briefs/` đã gitignore,
và chính phiếu ghi rằng executor **không được đóng** nó vì report cần chủ dự án
duyệt. Đó là một phiếu mà hệ phiếu không đóng được, chiếm một chỗ trong cửa
nhận đơn, và kết quả thì hết phiên là mất. Có navigator thì cùng việc ấy là
`docs/92_audit/reports/2026-09.md` cộng một lượt làm mới cột `## Next`, không
phiếu nào cả.

## Ai cầm bút trên roadmap.md

Một tài liệu một người viết, đúng như `docs/23_backlog/` là của planner:
`docs/00_roadmap/roadmap.md` là của navigator. Planner **đọc** cột `## Next` từ
trên xuống để chọn phiếu tiếp theo, nhưng không sửa tệp; executor và `crew done`
chỉ lật `status:` của phiếu, và bảng biến cái lật đó thành một dòng nhìn thấy
được cho tới khi navigator đồng bộ lại.

Lý do không cho executor tự sửa cột `## Now` lúc đóng phiếu: n nhánh `work/`
chạy song song sẽ cùng sửa một tệp Layer 1, đúng va chạm mà kit đã từ chối
`merge=union` để tránh — và vai có ít bối cảnh về hướng đi nhất lại là vai sửa.

Luật này là kỷ luật, không phải khoá. Thứ làm một người viết thứ hai lộ ra là
title phiên và khối `direction:` trên bảng, giống hệt luật tự khai của steward.

## Vai chưa tồn tại thì khai vắng, đừng stamp ma

Test và deploy mỗi hệ mỗi khác, nên `crew-init` kiểm bằng chứng từng vai —
tester cần lệnh test thật hoặc một harness đáng khoá, devops cần nhánh
production tồn tại hoặc dấu vết deploy — và vai nào thiếu bằng chứng thì phải
hỏi thẳng người dùng, không được lặng lẽ stamp. Vai trả lời "chưa có" đi vào
`roles_absent` trong config, tệp lệnh của nó không được stamp, và
`scripts/crew status` nhắc khoảng trống đó cho tới khi ai đó đấu nối. Một tệp
vai cho một vai không tồn tại là một sự thật sai nằm trong repo.

## Tên phiên là phần nhìn thấy được của mũ

Văn phạm chung là `<repo> · <vai> · <nhiệm vụ>`: tên project, rồi vai, rồi việc
đang làm. Mũ không có việc cụ thể thì dừng ở vai.

| Loại phiên | Tên | Ví dụ |
|---|---|---|
| phiên executor trong pool | `<repo> · executor · b<nnn> · <gốc> · e<k> · <trạng thái>` | `lop-hoc-zalo · executor · b157 · d009 · e1 · processing` |
| phiên executor mang chuỗi | `<repo> · executor · b<nnn> · <gốc> · <đầu>→<cuối> · e<k> · <trạng thái>` | `lop-hoc-zalo · executor · b334 · d009 · 332→336 · e1 · processing` |
| phiên executor fast-pair | `<repo> · executor · b<nnn> · <gốc> · main · <trạng thái>` | `lop-hoc-zalo · executor · b010 · i020 · main · processing` |
| planner chủ đề | `<repo> · planner · <gốc> <mô tả>` | `lop-hoc-zalo · planner · d009 layer-1-noi-dung-su-that` |
| phiên mũ không có việc cụ thể | `<repo> · <vai>` | `lop-hoc-zalo · navigator` |

Tên repo đứng trước để danh sách phiên tự gom theo dự án. Các phần còn lại đều
đọc từ git và từ phiếu chứ không gõ tay: nhánh cho biết phiếu nào, `source_ref`
của phiếu cho biết **gốc** (tài liệu mà phiếu phục vụ: `d009` là DECISION-009,
`i020` là ISSUE-020), tên cây cho biết executor nào, trailer cho biết trạng
thái. Số phiếu đứng ngay sau vai, vì danh sách phiên cắt title dài ở cuối, và
phần đứng trước là phần còn đọc được. Ô chỗ là **nơi session đang ngồi**: `e<k>`
khi nó ở một cây trong pool, `main` khi đó là phiếu fast-pair làm thẳng ở cây chính.
Phiếu không có `source_ref` đọc được thì title bỏ ô gốc, chứ lệnh không từ chối.

**Ô gốc là đường quay về planner.** Planner lo một chủ đề lớn mang cùng token đó
trong title, kèm phần mô tả lấy từ tên file của tài liệu gốc
(`scripts/crew name planner d009`). Nhìn `b157 · d009` là biết phải quay lại
planner nào; không planner nào mang token đó thì quay về planner chung
`<repo> · planner`.
Mỗi chuỗi phiếu có một phiên riêng, và phiếu không nằm trong chuỗi nào là chuỗi
một phần tử (`tickets.md`). Phiên sinh ra ở `processing`, kết thúc ở `finished`,
và title luôn chỉ đúng một phiếu, là phiếu cây đang giữ.
Executor rảnh thì không có phiên nào để đặt tên, và một phiên executor không có
số phiếu cũng vậy, nên `crew name` báo lỗi thay vì bịa ra một cái title.

`scripts/crew name <vai>` đọc **title** của phiên đang chạy rồi so với bảng
trên, và title chưa đúng thì vai chưa bắt đầu.

Một phiên mang hai nhãn khác nhau, và phép kiểm đọc nhãn nào là chuyện có hậu
quả thật. `name` nằm trong bản ghi phiên sống, còn title là thứ danh sách phiên
hiển thị. Đổi tên trong app chỉ ghi title, còn `/rename` gõ trong terminal ghi
cả hai. Bản đầu của phép kiểm đọc `name`, nên bốn phiên đã đổi tên trong app —
đặt đúng và nhìn thấy đúng ngay trong sidebar — đều báo đỏ. Vì vậy nó chuyển
sang đọc title: bản ghi `custom-title` cuối cùng trong transcript của phiên.

Luật này mua được cái gì và không mua được cái gì, nói thẳng ra: title không
duy nhất, nên nó **không** chặn được hai phiên cùng đội một mũ. Nó chỉ làm cái
mũ hiện ra, và người đọc danh sách mới là thứ bắt được trùng. Hiện
`steward.md` và `navigator.md` bắt buộc chạy phép kiểm — hai vai ghi thẳng vào
cây chính dùng chung; các vai khác mới dừng ở mức khai tên.

## Nhóm sidebar — chỉ trong app desktop, và chỉ khi người dùng đã dùng nhóm

App desktop cho xếp phiên vào nhóm tự tạo. Kit không chạm được vào sidebar, nên
việc này do chính phiên làm, theo đúng các bước sau:

1. Chạy `scripts/crew name <vai> [<số phiếu>|<gốc>] --group`. Lệnh in một hoặc
   hai tên nhóm, nhóm hợp nhất đứng đầu: nhóm của chủ đề (`<repo> · d009 …`),
   rồi nhóm của project (`<repo>`).
2. Liệt kê các nhóm đang có bằng công cụ của app, rồi chuyển **chính phiên này**
   vào nhóm đầu tiên trong danh sách lệnh in ra mà đã tồn tại.
3. Không nhóm nào tồn tại thì bỏ qua bước này. Đừng tạo nhóm project: nếu người
   dùng đang xếp sidebar theo project, việc chuyển phiên vào nhóm sẽ bật cả
   sidebar sang chế độ nhóm, và họ mất cách xếp theo project.
4. Phiên đang được ghim thì để nguyên, vì chuyển vào nhóm sẽ làm nó mất ghim.

Chỉ planner chủ đề được tạo nhóm, và chỉ khi nhóm project đã có (`planner.md`).
Ngoài app, ví dụ trong terminal, không có công cụ nào cho việc này, nên bỏ qua
toàn bộ mục này. Title và `crew status` vẫn là nguồn sự thật; nhóm chỉ là cách
hiển thị.

## Steward và cây bút luật

Phiên steward khi đề xuất một thay đổi luật **mở rộng quyền của chính nó** phải
nói thẳng điều đó trong lời xin duyệt. Chuyện này đã xảy ra thật và không cơ
chế nào chặn được, vì vậy luật được ghi ra đây để im lặng bị đọc là vi phạm
chứ không phải sơ suất.
