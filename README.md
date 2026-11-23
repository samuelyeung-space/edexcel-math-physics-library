# Edexcel Mathematics & Physics · 教学题库

此仓库是 **独立的 GitHub 教学题库**，为 AI 按课程、年份、卷别、题号检索提供入口。

**[查看完整课程目录](catalog/README.md)** · [机器索引](catalog/index.json)

## 已有真实题目索引

| 项目 | 逐题元数据 | 范围 |
| --- | ---: | --- |
| Edexcel IAL 数学 2026 Jan | 118 | P1–P4、FP1–FP3、M1–M3、S1–S3、D1 |
| Edexcel IAL 数学 P3 历史 | 134 | 2021–2025 |
| Edexcel IAL 物理 Unit 1 | 263 | 2021–2025 |
| UK Edexcel A Level 数学 | 43 | 2025 |
| **合计** | **558** | 16 个课程索引，46 份题组记录 |

保留了另 **1,541 条历史原卷/Mark Scheme 来源登记**（2016–2025 IAL 数学和物理、2021–2025 UK 数学和物理）。注意来源登记有重复或受限链接，**不等于全部卷子已下载或完整**。

## 给 AI 读取

先读取 [catalog/index.json](https://raw.githubusercontent.com/samuelyeung-space/edexcel-math-physics-library/main/catalog/index.json)，沿 `courses[].file` 进入课程列表，沿 `papers[].file` 进入试卷题号清单，随后按 `questions[].question_file` 获取逐题元数据及来源链接。

**重要区别：**2026 Jan 118 道题及官方 MS 的 PDF 已在用户私有档案中校验，但**PDF 文件本身没有放入本公开仓库**；另外 440 道题也仅镜像了元数据，原题 PDF、Mark Scheme 仍通过旧归档和官方原始来源取用。这不是可直接下载所有原题的题库，也不是完成数学内容审查的《小白书》。

请勿将未经授权的考试机构原卷公开再分发。
