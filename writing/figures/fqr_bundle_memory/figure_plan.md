# FQR Bundle Memory：Figure 1 规划

## 完整性说明

- 已分析材料：`research/ideas/fqr_candidate_motivation_and_nearest_work_2026-09-02.md`、`research/ideas/fqr_mem_cvpr_motivation_and_refined_proposal_2026-09-01.md`、`research/literature/fqr_mem_2026_literature_evidence.md`、`writing/drafts/fqr_bundle_memory_cvpr/main.tex`
- 当前输出类型：阶段性
- 高置信信息：论文主问题是固定预算、问题未知、原视频不可回看的 pre-query 记忆；核心结构是 bundle 内 AND、替代 bundle 间 OR；训练问题只能连接训练期 teacher，不能进入部署 writer
- 待确认信息：最终事件胶囊形式、选用的开源骨干、真实数据上的替代证据路径数量、实验结果
- 建议补充材料：1）确定后的 memory backbone 接口；2）首批真实 bundle 标注示例；3）phenomenon study 的首轮结果

## 论文概览

- 研究问题：未知未来问题到达前，系统能否在固定持久字节内保留至少一条完整的最小充分证据路径，而不是只保留许多彼此不完整的相关片段？
- 方法主张：训练期用问题与 grounded evidence 构造或验证 evidence bundle，再把集合级完整路径覆盖蒸馏给测试时不见 query 的 set critic；部署 writer 只做固定预算的 skip、insert、replace。
- 证据计划：可精确枚举的 Video Memory Gym、同预算 post-query / offline-pre-query / causal-pre-query oracle、同骨干 objective replacement、store/access/use 分层干预。
- 版面约束：CVPR 双栏；Figure 1 使用双栏宽度 183 mm，建议 3:2 横向构图。

## Figure 1：Overall Framework（must）

一句话沟通目标：读者看完图后应立即理解，单条证据召回高不等于完整路径存活，而 BundleMem 只在训练期使用问题生成集合监督，部署 writer 始终看不到未来问题。

建议采用三段不对称横向叙事，而不是普通模块流水线：

1. **左侧主视觉：失败反例。** 同一段视频产生两份同预算记忆。上方记忆保留多条路径的零散片段，item recall 较高，但所有路径都有缺口；下方记忆保留更少的总片段，却完整保住一条路径。用连续实线连接完整路径，用虚线和缺口表示断裂路径。
2. **中部：训练期 teacher。** 训练问题、答案与 grounded evidence 进入 bundle teacher；同一个 memory coalition 做完整/删一项对照，得到 group-wise complete-path coverage 标签。训练 query 的箭头必须在 teacher 边界内终止。
3. **右侧：部署 writer。** 视频事件、当前 memory、ASR/OCR side information 进入 query-free set critic；critic 给 skip / insert / replace 后的候选 memory 打分，选择不超预算的更新。右上角明确画出被阻断的 future query，不允许有任何隐含箭头进入 writer。

必须出现的节点：

- `video_stream`
- `event_capsules`
- `fragmented_memory`
- `complete_path_memory`
- `training_queries`
- `grounded_evidence`
- `bundle_teacher`
- `coalition_labels`
- `query_free_set_critic`
- `current_memory`
- `side_information`
- `online_allocator`
- `future_query_blocked`

必须出现的连接：

- `video_stream -> event_capsules: causal candidate generation`
- `event_capsules -> fragmented_memory: item-wise proxy selection`
- `event_capsules -> complete_path_memory: bundle-aware selection`
- `training_queries -> bundle_teacher: training-only supervision`
- `grounded_evidence -> bundle_teacher: training-only supervision`
- `bundle_teacher -> coalition_labels: sufficiency/minimality tests`
- `coalition_labels -> query_free_set_critic: distillation`
- `current_memory -> query_free_set_critic: set context`
- `side_information -> query_free_set_critic: replaceability context`
- `query_free_set_critic -> online_allocator: action utility`
- `online_allocator -> current_memory: skip/insert/replace under B bytes`

权限边界：

- `training_only_boundary`：包含 training queries、answers、grounded evidence、bundle teacher 和 coalition labels。
- `deployment_boundary`：包含当前流、当前 memory、side information、set critic 和 allocator。
- `future_query` 位于 deployment boundary 之外；只能在 memory 冻结后连接 query-time reader，Figure 1 可不画 reader 细节。

禁止暗示：

- 不得暗示 BundleMem 在部署时看到、生成或猜测真实测试问题。
- 不得暗示保留一个完整 observed bundle 就构成对任意 consumer 的形式化可回答性证明。
- 不得暗示原视频仍可回放或存在未计费冷存储。
- 不得把图、层次 memory、codec 或 reader 画成核心创新。
- 不得在图中写入尚未产生的性能数字或 “SOTA”。

次要内容（空间不足时删除）：group balance、side-information corruption、store/access/use audit、三类 oracle frontier。

文字预算：面板标题不超过 5 个英文词；节点标签不超过 4 个英文词；解释性细节放入 caption。

## 结果触发的后续图（当前不进入正式 Figure Plan）

只有在结果文件存在后再决定是否加入：answerability--budget frontier、bundle geometry 热图、store/access/use 失败分解、一个 grounded 定性案例。当前不预设它们的趋势、数量或版面。

## Figure Plan v1

```json
{
  "schema": "academic-figure/FigurePlan@1",
  "source_revision": "work/fqr-paper-draft@initial-draft-2026-09-02",
  "venue": "CVPR",
  "sources": [
    "research/ideas/fqr_candidate_motivation_and_nearest_work_2026-09-02.md",
    "research/ideas/fqr_mem_cvpr_motivation_and_refined_proposal_2026-09-01.md",
    "research/literature/fqr_mem_2026_literature_evidence.md",
    "writing/drafts/fqr_bundle_memory_cvpr/main.tex"
  ],
  "figures": [
    {
      "figure_id": "fig1",
      "figure_type": "Overall Framework",
      "priority": "must",
      "communication_goal": "Show that high item recall can leave every sufficient evidence path broken, and that bundle supervision is distilled from training-only queries into a deployed writer that never sees the future query.",
      "claim_scope": [
        "Answerability requires every member of at least one minimal sufficient evidence bundle to survive.",
        "Training questions supervise bundle labels but are not inputs to the deployed writer.",
        "The deployed writer changes only fixed-budget admission and replacement, not the shared codec or reader."
      ],
      "hero_element": "asymmetric contrast plus training/deployment boundary",
      "required_nodes": [
        "video_stream",
        "event_capsules",
        "fragmented_memory",
        "complete_path_memory",
        "training_queries",
        "grounded_evidence",
        "bundle_teacher",
        "coalition_labels",
        "query_free_set_critic",
        "current_memory",
        "side_information",
        "online_allocator",
        "future_query_blocked"
      ],
      "required_connections": [
        "video_stream -> event_capsules: causal candidate generation",
        "event_capsules -> fragmented_memory: item-wise proxy selection",
        "event_capsules -> complete_path_memory: bundle-aware selection",
        "training_queries -> bundle_teacher: training-only supervision",
        "grounded_evidence -> bundle_teacher: training-only supervision",
        "bundle_teacher -> coalition_labels: sufficiency/minimality tests",
        "coalition_labels -> query_free_set_critic: distillation",
        "current_memory -> query_free_set_critic: set context",
        "side_information -> query_free_set_critic: replaceability context",
        "query_free_set_critic -> online_allocator: action utility",
        "online_allocator -> current_memory: skip/insert/replace under fixed bytes"
      ],
      "authority_boundaries": [
        "training_only_boundary: queries, answers, grounded evidence, teacher, and coalition labels",
        "deployment_boundary: stream, current memory, side information, critic, and allocator",
        "future query is outside the deployment writer boundary"
      ],
      "secondary_context": [
        "group balance",
        "side-information corruption",
        "storage-access-use audit",
        "oracle frontiers"
      ],
      "forbidden_claims": [
        "deployment writer sees or predicts the held-out question",
        "observed-bundle survival is a universal semantic certificate",
        "raw video can be replayed without cost",
        "unmeasured state-of-the-art performance"
      ],
      "forbidden_connections": [
        "future_query_blocked -> query_free_set_critic",
        "test_answers -> query_free_set_critic",
        "deleted_raw_video -> online_allocator"
      ],
      "aspect_ratio": "3:2",
      "final_width_mm": 183,
      "style_profile_hint": "classic-technical with one dominant failure contrast and restrained color",
      "reference_assets": [],
      "open_questions": [
        "Which backbone determines the final capsule appearance?",
        "How many alternative real-video bundles survive human verification?",
        "Whether group balance belongs in Figure 1 after the first ablation?"
      ],
      "confidence": "high",
      "review_status": "pending"
    }
  ]
}
```
