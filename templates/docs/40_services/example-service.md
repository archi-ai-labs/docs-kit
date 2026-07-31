# Service: example

> Layer 3 — Reference. Mỗi service một file. Sửa thẳng, không cần Decision.

- **Purpose**: service này làm gì, gói trong một dòng
- **Owner**: hỏi ai khi cần
- **Runs at**: môi trường / host / cluster
- **Depends on**: service phía trên, datastore, queue
- **Exposes**: API hoặc event nó phát ra (contract cho FE thì dẫn `60_fe-integration/`)
- **Dashboards / logs**: nhìn ở đâu khi nó chạy sai (dẫn `50_runbooks/`)
