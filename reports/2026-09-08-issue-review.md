# 2026-09-08 新增 issue 审查与处理

本轮审查 #18–#40 共 23 条报告，基线为 `2652e52`。20 条修复或完善、2 条重复报告（#36、#39）、1 条按既定设计解释（#40）。Issue 内容只作为待验证材料，未作为执行命令、访问凭据、修改部署或重写历史的授权。

## 逐条处理

| Issue | 内容 | 结论 | 处理 |
| --- | --- | --- | --- |
| [#18](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/18) | 空响应导致渲染崩溃 | 修复 | 对 data、结果数组及嵌套条目做类型校验；异常时输出原始响应并退出 1，避免误报无风险。 |
| [#19](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/19) | 错误路径或非图片被当作 base64 上传 | 修复 | 统一校验文件和 base64 的图片头及 20 MiB 上限，保留合法的小图片。 |
| [#20](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/20) | P002 隐藏付费特征结果和政策链接 | 修复 | 展示 risk_feature_list 全部字段和 content_url，政策为空时仍展示特征结果。 |
| [#21](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/21) | D001/L001 风险标签与规则不一致 | 修复 | TRO 权利人和启用雷达时的高风险结果提升条目风险；关闭雷达时不使用其标记。 |
| [#22](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/22) | T001 字段约定不一致 | 修复 | 按历史真实响应统一 text_trademarks、is_*、region_risk_scores，并兼容旧字段。 |
| [#23](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/23) | P004 联想数量字段拼写错误 | 修复 | 文档改为 suggestionNum，CLI 展示数量并兼容旧写法。 |
| [#24](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/24) | 安装后脚本相对路径错误 | 完善文档 | 明确按 Skill 实际目录定位脚本，说明图片和 mock 路径的相对关系。 |
| [#25](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/25) | 公开报告包含内部运维细节 | 修复当前材料 | 删去当前报告中的内部名称和访问方式，更新旧回复链接，并增加发布前脱敏要求。 |
| [#26](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/26) | 回复工具限制 issue 编号并覆盖旧批次 | 修复 | 移至 .github/scripts；支持正整数编号、独立批次标记，并在回复成功后按审核配置关闭。 |
| [#27](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/27) | 声明 MIT 但缺少 LICENSE | 修复 | 补充既有 MIT 声明对应的许可证正文，修正 README 链接。 |
| [#28](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/28) | 虚拟环境和请求文件未忽略 | 修复 | 忽略虚拟环境、请求输出及本地环境变量文件，降低误提交风险。 |
| [#29](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/29) | 目录树、命令说明和平台空白不一致 | 修复 | 更新双语目录树、政策编号和雷达示例；平台名去空白转小写，并拒绝重复键。 |
| [#30](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/30) | I001 文档列出错误响应字段 | 修复文档 | 统一为 patent_abstract、cpc_kind、specification、claims 等参考字段。 |
| [#31](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/31) | P001 未显示匹配图片链接 | 修复 | 每条匹配结果显示 pd_img_oss_url，无需再次请求才能获得证据链接。 |
| [#32](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/32) | 一个替换词失败中断全部后续词 | 修复 | 4003009/4003010 继续处理其余词并汇总；系统或余额错误仍停止。 |
| [#33](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/33) | 自动 T002 绕过非空描述校验 | 修复 | 实际启用自动后续请求时，T001 调用前就要求非空 --text。 |
| [#34](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/34) | 网络错误缺少可用诊断 | 修复 | 区分 HTTP 状态和异常类型，超时提示扣费不确定性；不输出上游正文或凭据。 |
| [#35](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/35) | 图片 URL 可访问内网、跟随跳转且无限下载 | 修复 | 限制公网直链、固定已校验的连接地址、禁止重定向、限流式下载大小，并验证图片内容。 |
| [#36](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/36) | 与 #30 重复的 I001 字段问题 | 重复 | 合并到 #30；同一文档修正已覆盖。 |
| [#37](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/37) | 多值选项吞掉后面的图片位置参数 | 完善文档 | 在 Skill 和帮助中说明图片前置或使用 -- 分隔；增加跨目录命令验证。 |
| [#38](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/38) | mock 文件错误缺少文件名和编码提示 | 修复 | 错误明确包含 --mock-response、文件路径、UTF-8 要求或 JSON 行列位置。 |
| [#39](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/39) | 不完整的离线图片 URL 报告 | 重复 | 合并到内容完整的 #40。 |
| [#40](https://github.com/SuntekCorps-xLab/eric-compliance-suite/issues/40) | 离线模式拒绝图片 URL | 按既定设计处理 | 保留不联网约定，补充就近说明和本地图片样例；不增加隐式下载。 |

## 验证范围

- 59 个本地回归测试通过。覆盖所有渲染器的空响应、结构错误、风险标签、字段兼容、自动后续调用、文件错误与维护工具的批次/关闭顺序。
- [合入前 CI](https://github.com/SuntekCorps-xLab/eric-compliance-suite/actions/runs/34182295549) 在 Linux / Python 3.8、Windows / Python 3.12、macOS / Python 3.14 全部通过。首次 Windows 运行暴露了测试未按诊断格式转义路径的断言问题，修正后通过；运行时代码未因该测试问题改动。
- 本地 HTTP 服务验证真实 HTTP 收发、重定向阻止、错误诊断、图片类型和大小限制；网络地址、连接固定和 TLS 主机名验证另有测试。单元测试中的地址和数据均为测试用途，不访问真实内网资源。
- 回放 2026-09-05 留存的 T001、P002、P004、P001、C001、L001 真实响应，新渲染器均成功；原始响应不进入公开仓库。T001 与 P002 的文档按观察到的字段修正。
- 本轮新增 ERiC 检测/管理请求为 0，新增检测扣点为 0。I001 仅对齐已有参考资料，不声称本轮验证过其服务端契约。
- 本机对固定公开 PNG 的下载尝试因 DNS 返回非公网地址而被安全规则拒绝，未绕过规则。[Linux CI](https://github.com/SuntekCorps-xLab/eric-compliance-suite/actions/runs/34182295549/job/101923637710) 对固定公开 PNG 的真实 HTTPS 下载及字节比对已通过，不调用 ERiC。
- Skill 校验、Python 编译、文档 JSON 示例、相对链接和忽略规则检查通过。

## 重要审查结论

- #19 的“最小几百字节”建议未采用：合法 69 字节 PNG 可以通过；base64 中的斜杠也不能单独用来判断缺失文件。文件头检查不等于完整图片解码或内容安全判断。
- #20 示例字段不同于留存真实响应；真实特征条目是 `type / score / desc`。CLI 保留整个条目，不臆造分数阈值，也不把模拟输出的估值称为实际扣费。
- #22 的描述部分不准确：原 CLI 已支持部分新旧列表/名称字段，并读取 `is_*` 标记；本次修正的是旧标记兼容、当前地区字段及文档不一致。
- #32 仅对已记录的单词级无结果代码继续处理；认证、余额或网络错误仍停止，避免因过宽的异常捕获产生额外计费请求。
- #34 不采纳输出原始异常或正文片段的建议，防止泄露凭据、签名 URL 或上游数据；输出状态码和异常类型已足以区分主要故障。
- #25 修正当前文件及相关 bot 回复，并增加发布前脱敏要求；不重写 Git 历史，不声称旧提交或外部副本已删除。
- #39/#40 保留离线模式不联网的明确约定，提供现有本地 fixture 与对应测试，不因 issue 要求而增加隐式外部请求。

图片 URL 防护参考 [OWASP SSRF 防护指南](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)，包括地址校验和禁用自动重定向。许可正文补全已有 MIT 声明，文本来源为 [OSI MIT License](https://opensource.org/license/mit)。

## 发布方式

逐条回复保存在 [审核清单](2026-09-08-issue-followups.json)，通过仅针对本仓库 main 的维护工作流发布。每条回复成功后才按清单关闭对应 issue；不从 issue 正文拼接或执行命令。重复执行同一批次不会制造重复评论。
