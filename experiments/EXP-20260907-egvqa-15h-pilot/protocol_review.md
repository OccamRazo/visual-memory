# 本轮科学协议审阅

审阅对象为[15 小时方案 v1.1](../../docs/plan/egvqa_15h_single_gpu_validation_plan.md)及本轮实现。本文记录代码与检查的适用范围；E1/E2 模型结果、D0 吞吐准入和人工审核结论以独立 run 的最终产物为准。

## 已核实的可执行部分

[protocol.py](../../src/egvqa_pilot/protocol.py)已实现严格重叠区间合并、余弦检索及 ID 平局规则、R2 至多 8 个候选的 3 条组合枚举、保守时间覆盖和 R* 位掩码动态规划。R2 每题至多枚举 56 个组合，不产生额外 VLM 请求。账本在调用前预留输入与完整生成上限，执行 8,192 单请求、12,288 每题每方法累计 token 约束及调用次数约束；失败、重试和缓存命中均保留逻辑费用，judge 单独计评估成本。

本审阅直接执行了以下检查，均通过：

| 检查 | 实际结果与范围 |
|---|---|
| [test_egvqa_pilot_protocol.py](../../tests/test_egvqa_pilot_protocol.py) | 28 项 CPU 测试；包括独立枚举/穷举对照、重复 PTS 与填充、预算边界、失败与缓存计费、缺失/重复结果、匿名 judge、视频聚类 bootstrap、成本公平与人工校准门槛。 |
| [test_egvqa_runner.py](../../tests/test_egvqa_runner.py) | 3 项 fakebackend 集成测试；验证单方法准备失败不取消其他方法、judge 失败仍保留全部题目、未知生成失败保守计费与恢复、正常提示无金标答案及控制器答案提示、R* 使用独立诊断入口。 |

复现命令为 `.venv/bin/python -m unittest discover -s tests -p test_egvqa_pilot_protocol.py -v` 和 `.venv/bin/python -m unittest discover -s tests -p test_egvqa_runner.py -v`。这 31 项检查不构成 GPU 推理、实际跨题 VLM 重放或人工 grounding 已通过的证据。[前端测试](../../tests/test_egvqa_data.py)和[真实快照检查脚本](../../scripts/check_egvqa_pilot.py)另行覆盖 writer、像素、字节与文件访问；最终通过范围须引用对应 run 的检查日志。

## 覆盖指标中的结构性限制

**由本轮定义可直接推出：`Stored_ann == Feasible_ann`。** 合并后最多有 `m≤4` 个标注组；若快照已覆盖所有组，每组选一个能独立覆盖该组的 capsule，去重后至多 `m≤4` 条，即已满足 6 条读取上限。因此，本轮“快照有覆盖，但 6 条装不下”的失败类别必为空集；这不是运行得到的零失败率，也不能用来论证读取预算充裕。

实现仍保留两个指标和一般读取上限的动态规划，并用随机小快照穷举验证最小覆盖。该推论依赖“一个 capsule 内至少两个不同有效 PTS 即覆盖该组”的定义；不意味着四条就一定包含关键动作，也不意味着消费者能答对。R* 保持标注辅助参考的含义，不是数学性能上界。

## 分母与评价限制

[analysis.py](../../src/egvqa_pilot/analysis.py)拒绝同一逻辑条件的重复最终行。E1 主干预差值仅在完整有效配对题上计算，同时保留原计划题数、可构造题数、缺失条件和无效原因；人工确认比例使用冻结的 `Nplan`，不能换成 Full 正确子集。E2 四种方法共享全部预定题目，失败与缺失按未成功计，未知覆盖和未知费用另列。`uncertain` 在主表计 0，另报比例和排除后的敏感性结果。主要差值按视频成对 bootstrap 2,000 次、seed=43；同视频多题不是独立样本。

回答与文本 judge 使用同一冻结模型，因此 A 仅是本地 pilot 指标，不能称官方评分或独立评价。D0 的 32 条匿名答案仍须由实际人工核验，至少 28 条一致才通过该门槛；AI 复核不能替代人工校准。E1 自动联合候选、E2 自动增益案例均不直接计为人工确认。人工尚未完成时，工程执行完成与科学有效性必须分开报告。时间段覆盖、合法引用和 `J_ann` 也不能替代实际证据使用的人工判断。

## 本设备的隔离实现及边界

设备不提供本轮所需的 mount/unshare 权限，采用[isolation.py](../../src/egvqa_pilot/isolation.py)的 Linux Landlock 文件访问白名单。[reader.py](../../src/egvqa_pilot/reader.py)用 `spawn` 启动正常 reader，在打开快照前施加限制，仅允许当前封存快照及 Python 运行库目录的文件读取；原视频、全候选审计目录和金标文件不在白名单。不存在 Landlock 支持时直接拒绝正常 reader 启动。R* 的包加载使用独立诊断进程，金标选择出的 ID 不送入正常 reader。

已读取的本地 `run-20260907T0206+0800/isolation_probe.json` 记录内核 ABI 为 **1**，两个真实存在的白名单外文件均返回访问拒绝。该 run 的阶段性 `protocol_checks.json` 已记录 **13 个真实快照**的检查；这不代表全部计划视频已经完成检查。真实检查会验证原视频、eval 金标和完整候选文件均存在且被拒绝，并检查已淘汰 ID 被拒绝、取回像素 hash 与查询顺序不变性。最终范围以完整运行后的日志为准。

这种实现针对本实验正常 reader 的**文件读访问限制**达到“不开放原视频、全历史及金标”的隔离目的，没有创建独立 mount namespace。Landlock 的 ABI 1 不提供网络访问控制，本轮实现也没有网络规则；当前固定 reader 只实现本地检索、取包与访问探针，没有下载或网络请求接口。因此不能称为完整容器隔离或内核级网络隔离。Landlock 还不撤销限制前已打开文件的读取能力，所以需要保持 `spawn` 启动和禁止传入特权文件句柄的实现约束。[Linux 官方 Landlock 文档](https://docs.kernel.org/userspace-api/landlock.html)明确说明了文件访问权、已打开句柄的边界及网络控制从后续 ABI 引入的区别。

## 冻结前最终检查补记

上文 31 项测试、13 个快照是早期审阅时的范围，保留为阶段记录。最终 `protocol_checks.json` 已覆盖全部 **24 个真实快照**，六类机械检查均为 PASS；`tests.log` 记录完整 **61 项测试通过**。其中协议测试已增至 36 项，另有 runner 3 项、前端 8 项、下载器 14 项。正常 reader 在施加 Landlock 前还要求只有一个 OS 线程，并通过单线程环境的 `spawn` 确保限制施加于实际读取线程。

eval 开始前冻结了 10 个源码文件的 SHA、模型与 prompt identity、12 视频 / 48 QA 清单和预算。此后仅完善报告与审计材料，不更改消费者、读取规则或评分源码。该 smoke 全部条件有终止记录时，可记注册执行 COMPLETE；原标准规模的 ≥60 题 / ≥15 视频门槛仍不满足，不能修改门槛使验收通过。
