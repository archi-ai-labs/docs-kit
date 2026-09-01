---
description: "Thủ tục release — đưa nhánh dev lên production. Devops chạy; không phải một vai."
disable-model-invocation: true
---

Đây là **thủ tục**, không phải vai: devops chạy nó, từng bước, không sáng tạo
thêm. Nhánh lấy từ `.docs-kit.json` → `crew.dev_branch` / `crew.prod_branch`.

## Checklist

1. **Trạng thái sạch trước đã**: `scripts/crew status` — không cây mồ côi,
   không khoá đang giữ quá hạn, không phiếu `in-progress` định lên chuyến này.
2. **Backlog khớp thực tế**: mọi phiếu của chuyến này `status: done`, audit
   có dòng dẫn sha (`docs_close` đã chạy qua `crew done`; thiếu thì chạy
   `/docs-kit:docs-sync` trước).
3. **Xanh trên dev**: chạy đúng lệnh test + typecheck trong config, trên cây
   chính, nhánh dev.
4. **Gộp sang production**:

   ```
   git checkout <prod_branch>
   git merge --ff-only <dev_branch>
   git tag <version>
   git push origin <prod_branch> <version>
   git checkout <dev_branch>
   ```

   `--ff-only` là chủ đích: production không bao giờ có commit riêng, nên lịch
   sử của nó là một đoạn tiền tố của dev. Không ff được nghĩa là production đã
   bị sửa tay — dừng lại và điều tra, đừng ép merge.
5. **Quan sát sau release**: log và health của bản mới; bất thường → Issue kèm
   số đo, và quyết định rollback theo lane test câu 3 — thao tác không lùi
   được đã lên chuyến này thì rollback không phải nút bấm vô hại.
6. Nối một dòng vào `docs/92_audit/`: ngày, version, sha, khác thường nếu có.
