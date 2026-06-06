# 金融办公自动化多智能体系统

这是一个可运行、可演示、可扩展的 Agent 应用项目，用来对应“Agent 应用算法实习生”经历中的核心场景：银行结单自动化处理、监管资讯智能整理、分层记忆、自动化评测、金融数据安全合规。

项目不只是脚本 demo，而是按真实业务系统的方式拆成了编排层、技能层、记忆层、评测层、审计层、API 层。默认不需要外部大模型即可运行；如果配置 `OPENAI_API_KEY`，系统会优先调用 OpenAI Responses API，并在网络或接口异常时自动回退到本地规则模型。

## 项目能做什么

### 1. 银行结单自动化 Agent

输入银行结单文本或 PDF，自动完成：

- 文档解析：支持 `.txt`、`.pdf`，PDF 通过 `pypdf` 抽取文本。
- 字段抽取：账户名、账号、账期、期初余额、期末余额、交易明细。
- 交易分类：转账、服务费、工资、利息收入等。
- 风险标签：大额交易、托管账户转出、可疑关键词等。
- 合规校验：检查 `期初余额 + 交易净额 = 期末余额`。
- Excel 填报：生成 `outputs/filled_bank_statement.xlsx`。
- JSON 归档：生成结构化 `outputs/bank_result.json`。

对应简历表述：

> 落地银行结单自动化项目，实现 PDF 解析、信息抽取、Excel 自动填表全链路处理。

### 2. 监管资讯整理 Agent

输入 SFC/证监会类监管资讯 JSON，自动完成：

- 资讯加载：批量读取监管新闻条目。
- 分类：AML、enforcement、licensing、market conduct、general compliance。
- 摘要：输出每条资讯的业务摘要。
- 风险评级：high、medium、low。
- 义务抽取：根据分类生成后续合规动作清单。
- 责任分派：自动路由到 AML、交易合规、牌照团队等 owner。
- Word 归档：生成 `outputs/regulatory_digest.docx`。
- JSON 归档：生成 `outputs/regulatory_digest.json`。

对应简历表述：

> 开发 SFC 证监会监管资讯智能整理 Agent，自动抓取、分类摘要、规范归档 Word/PDF。

### 3. 多 Agent 编排流水线

主编排在 `src/agent_finance_automation/graph.py`。

银行结单流程：

```text
document_parser
  -> security_guard
  -> bank_extractor
  -> compliance_validator
  -> quality_gate
  -> excel_filler
```

监管资讯流程：

```text
news_loader
  -> classification_summarizer
  -> quality_gate
  -> word_archiver
```

项目里实现了 `MiniStateGraph`，用于在没有安装 LangGraph 时也能运行。实际生产环境可以把这层替换为 LangGraph `StateGraph`，业务节点和 state 结构不需要大改。

### 4. 分层 AgentMemory

记忆模块在 `src/agent_finance_automation/memory.py`。

- 短期记忆：保存本轮运行中的最近上下文。
- 长期记忆：把历史运行摘要写入 `.agent_memory/long_term_memory.json`。
- 向量检索：用轻量词袋向量 + cosine similarity 做本地检索。

这对应简历里的：

> 设计分层级 AgentMemory 架构（短期上下文记忆 + 长期向量库记忆），结合上下文学习动态调整 prompt 策略。

### 5. 安全合规与审计

安全相关代码在：

- `src/agent_finance_automation/security.py`
- `src/agent_finance_automation/audit.py`

实现内容：

- 文档指纹：对输入文本计算 SHA-256 短指纹，便于追踪但不暴露原文。
- 敏感信息脱敏：账号、token、secret 等在审计日志中自动 mask。
- 私有化部署标记：评测报告会输出 `private_deployment: true`。
- 文档大小限制：防止异常大文件进入流水线。
- 审计日志：每个 run 都生成 `outputs/audit_<scenario>_<run_id>.jsonl`。

这对应简历里的：

> 采用私有化部署方案，所有数据均在内网处理，不向外网传输敏感业务数据，满足金融行业合规要求。

### 6. 自动化评测基准

评测入口在 `src/agent_finance_automation/evaluation.py`。

评测报告包括：

- accuracy：字段抽取置信度、监管分类覆盖率、义务抽取覆盖率。
- compliance：银行余额校验、高风险监管资讯数量、交易风险标签数量。
- efficiency：人工耗时估算、Agent 耗时估算、效率提升。
- quality_gates：每个流程的质量门禁是否通过。
- artifacts：输出文件路径和审计日志路径。
- traces：每个 Agent 节点的执行链路。

对应简历里的：

> 设计智能体评测基准框架，针对不同业务场景自动化构建测试集，实现从准确率、合规性、效率多维度自动评估。

## 快速运行

如果本机有 Python 3.11+：

```powershell
python -m src.agent_finance_automation.cli demo
```

当前 Codex 环境可以使用内置 Python：

```powershell
C:\Users\Ronal\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m src.agent_finance_automation.cli demo
```

运行成功后会看到类似输出：

```json
{
  "accuracy": {
    "bank_extraction_confidence": 1.0,
    "regulatory_classification_coverage": 1.0,
    "regulatory_obligation_coverage": 1.0
  },
  "compliance": {
    "bank_compliance_passed": true,
    "high_risk_regulatory_items": 1,
    "private_deployment": true
  },
  "quality_gates": {
    "summary": {
      "total": 6,
      "passed": 6,
      "warning": 0,
      "failed": 0
    }
  }
}
```

## 单独运行某个场景

银行结单：

```powershell
python -m src.agent_finance_automation.cli bank --input data/sample_bank_statement.txt
```

监管资讯：

```powershell
python -m src.agent_finance_automation.cli regulatory --input data/sample_regulatory_news.json
```

评测：

```powershell
python -m src.agent_finance_automation.cli eval
```

Smoke Test：

```powershell
python scripts/smoke_test.py
```

## 启动 Web/API 服务

```powershell
python -m src.agent_finance_automation.api
```

打开：

```text
http://127.0.0.1:8088/
```

接口：

- `GET /health`
- `POST /run/bank`
- `POST /run/regulatory`
- `POST /run/demo`

请求示例：

```powershell
Invoke-WebRequest -UseBasicParsing `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"path":"data/sample_bank_statement.txt"}' `
  http://127.0.0.1:8088/run/bank
```

## 大模型接口说明

LLM 抽象在 `src/agent_finance_automation/llm.py`。

默认使用：

- `LocalHeuristicLLM`：本地确定性规则模型，方便无网络演示。

设置 API Key 后使用：

- `OpenAIResponsesClient`：调用 OpenAI Responses API。
- `HybridLLM`：优先远程模型，异常时自动回退本地模型。

配置方式：

```powershell
$env:OPENAI_API_KEY="sk-..."
$env:OPENAI_MODEL="gpt-4.1-mini"
$env:OPENAI_BASE_URL="https://api.openai.com/v1"
```

如果公司内部是私有化模型，可以把 `OPENAI_BASE_URL` 换成内网 OpenAI-compatible 网关，或直接实现一个新的 `BaseLLM` 子类。

## 输出文件说明

运行后 `outputs/` 下会生成：

```text
bank_result.json                 # 银行结单结构化结果
filled_bank_statement.xlsx       # 自动填报 Excel
regulatory_digest.json           # 监管资讯结构化整理结果
regulatory_digest.docx           # Word 归档文件
evaluation_report.json           # 多维评测报告
audit_bank_statement_*.jsonl     # 银行流程审计日志
audit_regulatory_digest_*.jsonl  # 监管资讯流程审计日志
```

## 项目结构

```text
.
├── data/
│   ├── sample_bank_statement.txt
│   └── sample_regulatory_news.json
├── outputs/
│   └── generated artifacts
├── scripts/
│   └── smoke_test.py
├── src/
│   └── agent_finance_automation/
│       ├── api.py
│       ├── audit.py
│       ├── cli.py
│       ├── config.py
│       ├── evaluation.py
│       ├── graph.py
│       ├── llm.py
│       ├── memory.py
│       ├── quality.py
│       ├── schemas.py
│       ├── security.py
│       └── skills/
│           ├── bank_statement.py
│           ├── document_parser.py
│           └── regulatory_digest.py
├── tests/
│   └── test_pipeline.py
├── requirements.txt
└── README.md
```

## 思路

可以按这条线讲：

1. 业务痛点：金融中后台有大量重复的文档解析、资料填报、监管资讯整理工作。
2. 技术方案：用 Agent Graph 把任务拆成解析、抽取、校验、评测、归档等节点。
3. 准确性：结构化抽取后做余额校验、质量门禁、评测报告。
4. 合规性：输入只在本地处理，审计日志脱敏，保留文档指纹。
5. 可扩展性：新增场景只需要新增 Skill 节点，然后接入 graph。
6. 成本控制：无 API 时可用本地规则模型；接入小模型或蒸馏模型时只替换 LLM 层。

## 可以继续扩展的方向

- 接入真正的 LangGraph `StateGraph` 和 checkpoint。
- 接入 OCR，对扫描版 PDF 做版面识别。
- 增加 FastAPI + React 前端。
- 增加真实向量库，如 FAISS、Milvus、pgvector。
- 增加模型蒸馏数据生成脚本，把真实业务轨迹转成 SFT/RLAIF 数据。
- 增加 Excel 模板映射，把不同银行或券商格式配置化。
- 增加监管资讯爬虫，把 SFC/HKEX/CSRC/RSS 接入到同一条流水线。

