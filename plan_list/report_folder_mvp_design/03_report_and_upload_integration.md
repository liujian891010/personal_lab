# Phase 3: Report 与 Upload 链路集成

## 目标

让文件夹能力接入现有报告与上传链路，实现“上传时选文件夹、生成后自动归档、列表可按文件夹筛选”。

## 前置条件

- 文件夹 API 已可用
- `reports` 与 `uploads` 已具备 `folder_id_ref`

## 任务清单

- 为 `GET /api/reports` 增加筛选参数：
  - `folder_id`
  - `unfiled`
- 为 `GET /api/reports/{report_id}` 增加返回字段：
  - `folder_id_ref`
  - `folder_name_ref`
- 为 `POST /api/uploads` 增加可选参数：
  - `folder_id`
- 为 `GET /api/uploads`
  - 增加 `folder_id_ref`
- 为 `GET /api/uploads/{upload_id}`
  - 增加 `folder_id_ref`
  - 增加 `folder_name_ref`
- 上传处理链路中补齐规则：
  - 若上传时指定文件夹，则生成报告后自动写入 `reports.folder_id_ref`
  - 若未指定，则保持未归档
- 若上传失败，保留 `uploads.folder_id_ref`，便于重试后继续归档
- 搜索结果和报告卡片返回中补充文件夹信息，便于前端展示

## 交付物

- Report API 文件夹筛选能力
- Upload API 文件夹透传能力
- 上传到报告生成链路的文件夹继承逻辑

## 验收标准

- 上传时传入 `folder_id` 后，生成的报告可自动归档到对应文件夹
- 报告列表可按文件夹筛选
- 报告详情和上传详情都能看到所属文件夹
- 上传失败后重试，文件夹归属信息不会丢失

## 风险与注意事项

- 上传创建时与报告生成时分属不同阶段，字段透传必须保持一致
- 若用户在处理过程中修改上传目标文件夹，需要明确以后续值还是初始值为准
- 搜索接口如果返回缓存结果，要同步补字段
