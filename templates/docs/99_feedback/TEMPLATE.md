---
id: FEEDBACK-NNN
about: docs-kit            # docs-kit | crew
kind: bug                  # bug | doc | gap | friction
severity: blocks           # silent | blocks | friction
status: open               # open | sent | fixed
fixed_in:                  # phiên bản kit đã sửa — điền khi nó về

# Bên dưới do docs_feedback.sh điền. Không sửa tay: một báo cáo không tái hiện
# được thì bối cảnh là thứ duy nhất còn lại của nó.
seen_on: {{FEEDBACK_DATE}}
kit_version: "{{KIT_VERSION}}"
crew: {{CREW_STATE}}
repo: {{REPO_NAME}}
profile: "{{REPO_PROFILE}}"
rev: {{REPO_REV}}
platform: "{{PLATFORM}}"
---

# <một câu: kit đã làm gì, không phải bạn thấy thế nào>

> Copy **toàn bộ** file này, kể cả frontmatter, rồi dán vào một phiên làm việc
> trên repo docs-kit. Frontmatter ở trên là bối cảnh máy đọc được, nên không cần
> viết lại nó thành câu.

## What I ran

```bash
<lệnh, skill, hoặc thao tác — nguyên văn, không diễn giải>
```

## What happened

```
<output nguyên văn. Dài thì cắt phần giữa và đánh dấu chỗ cắt bằng […]>
```

## What I expected — and what says so

<Kỳ vọng, kèm chỗ nó được viết ra: STANDARD §7, EXECUTION §6, hay dòng nào trong
skills/docs-sync/SKILL.md. Không trích được nguồn nào thì đây là `kind: gap`, chứ
không phải `bug`.>

## Why it costs something

<Cái giá đo được: mất bao nhiêu phút, sai ở chỗ nào, ai là người không nhìn thấy
cái sai đó. "Khó chịu" chưa phải một cái giá.>

## Smallest repro

<Các bước từ một repo trống. Không tái hiện được ngoài repo này thì nói thẳng như
vậy, và mô tả điều gì ở repo này khiến nó khác.>

## What I did instead

<Cách đã lách để xong việc, hoặc "không có — dừng lại ở đây". Phần này quan trọng
với người bảo trì: nó cho biết mọi người đang làm gì thay cho cái kit định bắt làm.>

## The ask

<Một câu: kit nên làm khác đi thế nào.>

## Seen again

<!-- Mỗi lần gặp lại nối MỘT dòng, không sửa dòng cũ, không tạo file thứ hai:
     YYYY-MM-DD | ở đâu | lần này khác gì lần đầu -->
