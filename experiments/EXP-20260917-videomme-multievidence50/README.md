# Video-MME long：全量 caption 搜索多证据题

开始：2026-09-17。状态：**2026-09-17 按用户要求暂停**，不再追加 API 调用。已保存 **11 道确认题、36 个必要组（平均 3.27 组/题）**；原目标至少 50 道未达成。暂停原因是处理效率过低，见 [暂停记录](pause_record.json) 和 [结果分析](analysis.md)。

用户要求：搜索 long 全部问题，候选题的定位直接输入对应视频**全部 caption**，取消40条上限；定位、观察、核验及删组调用均使用 `qwen3.8-flash`。原有[60题时间分组](../EXP-20260917-videomme-evidence-groups/README.md)及其结果保持不变。本轮只做数据处理，不运行存取方法对比。

## 暂停时的结果

900 题已完成题目级优先级筛选。816 题有处理结果：170 题得到非技术失败判定，646 题技术失败；48 题处于 API 多证据候选通过状态，仅 11 题经逐题源复核确认。确认题才纳入部分数据集，不把候选或失败计作完成验证。

- [统计与用量](summary.json)、[源完整性检查](validation.json)、[暂停交付检查](delivery_checks.json)。
- [已确认题目与复核清单](confirmed_manifest.json)保留题号、必要组 ID、结果哈希和具体复核理由。
- [本机逐题证据浏览](/mnt/raid5-01/baorui/visual-memory/EXP-20260917-videomme-multievidence50/run-001/final/index.html)、[题目数据](/mnt/raid5-01/baorui/visual-memory/EXP-20260917-videomme-multievidence50/run-001/final/multievidence.jsonl)。目录名 `final/` 沿用导出器命名，仅表示已确认部分，不表示目标完成。
- 暂停前的旧导出及统计保存在本机 `run-001/pause_archive_20260917/`；原响应、失败、源包及修订历史继续保留。

## 流程与准入

1. 对900题做仅题目级优先级筛选，保留所有优先级和理由。优先处理正向的顺序/跨事件比较题，再处理其他正向题及穷尽/否定题；按已完成筛选的最高优先级逐批启动，保存每次实际批次，精确重放以这些固定批次为准。同时对上一轮8个多组样例做同协议先导复核；它们必须从全量caption重新定位，不继承旧准入。后续按900题的优先级补足，每批题目清单固定归档。
2. 对候选题提交该视频全部原始10秒caption及全部可用原字幕，记录输入条数、ID与哈希；没有BM25预筛或caption截断。
3. 定位独立事件/章节，忠实保留原题语义与官方答案，形成最小评分事实。连续制作、一个训练日、一段对话或一个魔术的步骤不拆成多组。
4. 解码原视频，保留实际PTS、JPEG哈希，补抽区间内部及边界上下文帧，投射原字幕。caption只用于定位，不进入观察或源核验。
5. 独立上下文中做不见答案的观察；另一次调用核验题意、评分事实、源支持和分组边界。必要时基于完整时间线修订一次，保留原调用。
6. 原始源证据的全集必须充分；逐个候选单组必须不充分；逐组删除冗余后，保留集合充分且每次再删一组都不充分。被删组、caption及其摘要不进入删组调用。
7. 再用全部caption与字幕反查独立摘要/回顾是否单组即可回答，以及是否人为拆组或额外添加评分要求。存疑不计入目标；补处理后续候选。
8. 最终逐题复查、导出证据组和复现记录，并校验全部caption确实进入定位请求、源引用合法、组边界与删组隔离正确。

“多证据”仅表示当前源证据与核验器下的必要多组，不是全视频最少组数的数学证明。API采用独立上下文但同一模型，存在共同偏差；不是人工金标。计数/否定/极值题不能用几个局部正例证明完整范围。

## 运行与产物

- 代码：[code/run.py](code/run.py)；规则：[protocol.json](protocol.json)；提示：[code/prompts](code/prompts)。源投射/隔离工具从上一轮复制为本实验的`group_base.py`，不修改旧实现。
- 输入：`/mnt/raid5-01/baorui/visual-memory/EXP-20260916-memory-data-prep/run-001-inventory/`，900题、300视频、74,136条caption。
- 原视频和原字幕：`/mnt/raid5-01/baorui/Video-MME`，只读。
- 本轮产物：`/mnt/raid5-01/baorui/visual-memory/EXP-20260917-videomme-multievidence50/run-001/`。
- 凭据仍读取忽略的`tmp/api.json`；模型由冻结协议指定，不改凭据文件、不保存密钥。请求/响应、失败、代码快照均归档。
- 网络：本机现有HTTP代理`http://127.0.0.1:7892`可连通该API；本轮在命令环境显式设置`HTTPS_PROXY`，不改系统配置。直连失败记录与代理探针保留于产物父目录`connectivity/`。
- Python沿用`/home/baorui/projects/WorldMM/.venv/bin/python`。`py_compile`及全量caption保留、删组隔离、单组替代、相邻独立区间保留等逻辑检查已通过；暂停时11题离线导出与交付检查通过，50题数量要求未通过（未达标）。
- 分支`work/motivation-data-prep`，本次随暂停归档纳入本地提交，未推送。基础revision及依赖见[environment.json](environment.json)。实施修订及原因见[execution_amendments.json](execution_amendments.json)，各版冻结协议保存在`protocol-history/`。

以下为历史执行命令，**暂停期间不要执行**。恢复须获得用户明确指示，先记录新执行方案、归档暂停状态并显式处理 `run-001/pause_queue`；旧命令不是恢复授权。

```bash
export HTTPS_PROXY=http://127.0.0.1:7892
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260917-videomme-multievidence50/code/run.py screen
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260917-videomme-multievidence50/code/consume.py
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260917-videomme-multievidence50/code/run.py summary
```

精确重放依赖归档模型输出；新的API调用不保证同样结果。已接触视频仍不得用作后续未见视频测试；本轮会单独导出新增接触清单。失败与不合格题保留，不为达到数量降低准入。

传输更新：v1.3使用流式返回，完整收齐JSON与finish_reason后才接受；模型仍为qwen3.8-flash。失败与超时保留，超时请求的提供方实际用量未知，日志中已返回的token不能代表这些请求的全部费用。v1.0/1.1互不重叠的旧核心以其原有闭区间输入重放，v1.2起用半开区间避免相邻章节边界帧混入；最终每组包标明区间语义。

评分修订：对原题含编号列表的顺序题，用原始题项与官方排列确定相邻先后关系；共同器材按每个训练日分别验证。复合事实中有任何事件未被源支持就不能通过。若复查发现评分过宽/过严或边界错误，保留旧结果，冻结修订输入并重新做相关原源验证；详见`rubric_refinements/`与`code/revalidate.py`。单个API返回通过不等于最终入选。

暂停期间可执行以下离线检查，不调用模型：

```bash
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260917-videomme-multievidence50/code/export.py
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260917-videomme-multievidence50/code/check_delivery.py --min-count 11
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260917-videomme-multievidence50/code/check_pipeline.py
```

`--min-count 11` 只验证暂停部分的完整性，不替代默认 50 题验收。v1.6–v1.8 的连续事件规则、关系两端独立引用、快照锁及尾帧处理见实施修订记录；`formal_order_rubrics.json` 保留 v1.5 历史生成结果，实际评分以逐题结果和对应代码快照为准。616-3 的旧版单事实负例省略逐事实状态，导出器仅在整体明确不充分且列出缺失证据时容许原记录，不能据此推断正例。
