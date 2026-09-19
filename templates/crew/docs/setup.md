# setup — dựng, chỉnh ngưỡng, nâng cấp

## Những gì `/docs-kit:crew-init` đã đặt vào repo

| Chỗ | Thứ |
|---|---|
| `.docs-kit.json` → `crew` | config: lệnh test/typecheck, nhánh, resources, ngưỡng |
| `scripts/crew` | CLI: `new` · `done` · `executor` · `lock` · `status` · `report` · `name` · `role` |
| `.claude/crew/*.md` | bảy tệp luật vận hành (thư mục này) |
| `.claude/commands/*.md` | bảy tệp: sáu vai + thủ tục `release` |
| `docs/92_audit/reports/` | báo cáo tuần và kế hoạch tháng của navigator — sinh khi dùng, có commit |
| `CLAUDE.md` | một đoạn tóm tắt giữa marker `docs-kit:crew` (nếu bạn đồng ý chèn) |
| `../<repo>-crew/` | trạng thái runtime — tự sinh khi dùng, không commit |

Vắng key `crew` trong `.docs-kit.json` là tầng này TẮT: hook im lặng, CLI từ
chối lịch sự, không gì đổi hình dạng. Đó cũng là cách tắt nhanh nhất.

## Config mẫu

```json
"crew": {
  "test_cmd": "npm test",
  "typecheck_cmd": "npx tsc --noEmit",
  "dev_branch": "main",
  "prod_branch": "production",
  "copy": ["node_modules", ".env", "harness"],
  "link": ["vendor-cache"],
  "setup_cmd": "",
  "roles_absent": [],
  "resources": { "e2e-harness": { "patterns": ["playwright", "docker compose"] } },
  "reader_cap": 4,
  "wait_budget_min": 30,
  "enforce": false
}
```

## Hai luật cho phần cấp phát executor

- `link` chỉ dành cho thứ **chỉ-đọc**; thứ gì phiếu có sửa thì `copy`, còn
  repo lồng có sửa thì mở phiếu ở crew của chính repo đó (`worktrees.md`).
- Sản phẩm phụ của `setup_cmd` phải rơi vào vùng gitignored hoặc vào thư mục
  đã `copy`, vì `crew done` chỉ nhận ra những gì nó tự đắp vào — một tệp lạ
  chưa commit sẽ giữ executor lại trên nhánh và được nêu đích danh.

## `origin/HEAD` chỉ tồn tại trên máy này

`dev_branch` là nơi mọi phiếu đổ về, nhưng các công cụ ngoài crew lấy nhánh gốc
từ ref `refs/remotes/origin/HEAD`. Khi clone, git đặt ref này theo nhánh mặc
định (default branch) trên GitHub, và nhánh đó thường là `prod_branch`. Hậu quả
là màn diff của Claude Code hiện toàn bộ việc chưa release, còn dòng "Main
branch" nạp vào đầu mỗi phiên lại gợi ý mở PR vào nhánh không nhận commit trực
tiếp.

Lệnh sửa chỉ có một dòng và chạy ở cây chính:

```
git remote set-head origin <dev_branch>
```

| Điều cần biết | Hệ quả |
|---|---|
| Ref nằm trong thư mục git mà mọi worktree dùng chung | chạy một lần là đủ cho cả pool |
| Ref chỉ tồn tại trên máy này | clone mới hoặc `git remote set-head origin -a` đưa nó về nhánh mặc định trên GitHub |
| Git từ bản 2.48 có khoá `remote.origin.followRemoteHEAD` | khoá này đặt là `always` thì mỗi lần `git fetch` sẽ đặt lại ref |
| Nhánh mặc định trên GitHub không đổi | `gh pr create` không kèm `--base` vẫn nhắm vào nhánh đó |
| `set-head` từ chối nhánh chưa có trên remote | nhánh dev phải được push trước |

`crew status` in hàng `default` trong khối `main tree:` khi ref này lệch khỏi
`dev_branch` hoặc chưa được đặt, và hàng đó ghi sẵn lệnh sửa. Board không tự chạy
lệnh, vì đổi một ref mà mọi công cụ cùng đọc là quyết định của người dùng, nên
`crew-init` và `crew-update` hỏi trước khi chạy.

Muốn sửa tận gốc cho mọi bản clone thì đổi nhánh mặc định trên GitHub sang
`dev_branch`. Đây là cài đặt dùng chung của repo và CI cũng đọc nó, nên kit không
đụng tới mà để chủ repo tự quyết.

## Khi nào bật `enforce`

`enforce: true` biến lời nhắc của explain-gate thành deny thật, chỉ cho repo
này. Bật khi đủ hai điều kiện, đúng thứ tự đó: bộ test của kit đã chứng minh
hook đỏ-đúng-lý-do trên ca hỏng đã biết, và log cho thấy lời nhắc đang bị lờ.
Quyền chặn mua bằng số liệu, không mua bằng niềm tin. Resource-guard không có
đường enforce — giới hạn của nó nằm trong `resources.md`.

## Nhịp báo cáo không phải một ngưỡng

Không có khoá config nào cho nhịp của navigator, và đó là chủ đích. Tuần là nhịp
của cột `## Now` theo định nghĩa, còn "đến hạn hay chưa" thì suy ra từ việc thật:
bảng chỉ đòi một báo cáo khi cửa sổ có ít nhất một phiếu hạ cánh, và tuần không
có gì thì in `report : none due`. Mỗi khoá config là một chỗ điền sai lặng lẽ,
nên chỉ thêm khi có số đo đòi.

## Chỉnh ngưỡng theo số đo của chính repo

- `wait_budget_min` (mặc định 30): sau ~5 phiếu nặng, đọc
  `../<repo>-crew/log.tsv` — cột cuối của các dòng `ACQUIRE` là số giây từng
  phiếu phải chờ. Ngưỡng đúng là mức bạn thấy xót thời gian.
- `reader_cap` (mặc định 4): đổi theo số người thật sự đọc kết quả.
- Ngưỡng chẻ phiếu `S > 6`: các dòng `SIZE` trong log ghi `declared=` với
  `actual=` — khi hai cột này lệch nhau đều đặn, số 6 cần dời.

## Nâng cấp

Bản mới của docs-kit có thể đổi `scripts/crew` và các template ở đây. Hai
bước, không hơn:

```
claude plugin update docs-kit@archi-ai-labs
/docs-kit:crew-update
```

Lệnh sau chỉ chép tệp, không hỏi lại phần cấu hình. Nó phân biệt được tệp nào
là của chính nó nhờ sổ sha256 ở `.claude/crew/.stamp`: tệp bạn chưa đụng tới
thì thay thẳng, tệp bạn đã sửa thì đặt bản mới cạnh dưới tên `.new` để bạn tự
trộn. Không bao giờ ghi đè chỉnh sửa cục bộ.

Repo được stamp trước khi có sổ thì lần chạy đầu vẫn ra `.new` một lượt, và
chính lần đó sinh ra sổ.
