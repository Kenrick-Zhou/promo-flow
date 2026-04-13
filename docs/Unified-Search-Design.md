# PromoFlow 统一搜索架构设计

## 1. 背景与目标

当前 PromoFlow 的 Web 搜索与 Bot 对话式搜索，底层都建立在同一条“查询文本生成 embedding → pgvector 相似度排序”的链路上。该实现具备基础的语义检索能力，但在实际业务体验上存在明显不足：

- 过度依赖单一路径的向量相似度，缺少传统关键词命中能力。
- 搜索 `视频`、`短视频`、`图片`、`图` 等类型词时，无法稳定转化为精准过滤条件。
- 搜索词命中素材标签（人工标签或 AI 关键词）时，结果排序缺少显著加权。
- 搜索 `玻璃瓶`、`食品` 等内容实体词时，无法充分利用标题、描述、标签、类目和 AI 摘要的综合信息。
- Web 搜索与 Bot 搜索虽然复用了同一个基础语义检索函数，但缺少统一的“查询理解、混合召回、融合排序、LLM 重排”能力。

本设计文档的目标是建设一套**统一的搜索服务体系**，同时服务于：

- Web 应用中的列表搜索、筛选与结果排序
- 飞书 Bot 的对话式素材检索与问答

并满足以下要求：

1. 同时兼顾**关键词精确命中**与**自然语言语义理解**。
2. 对类型词、标签词、类目词、实体词具备稳定且符合业务直觉的表现。
3. 支持轻量级 LLM 参与 **Query 理解** 与 **Top-K 重排**，LLM 模型可通过配置快速切换，不依赖昂贵或过慢的大模型。
4. Web 与 Bot **必须共用同一套 search service 及其背后的检索/排序系统**，禁止出现两套独立搜索实现。
5. 所有可调参数（权重、模型名称、功能开关）**必须通过环境变量管理**，禁止硬编码在业务代码中。
6. 每次搜索的各阶段耗时**必须结构化记录**，支持通过配置将耗时附加在 API 响应中，便于性能对比与调优。

---

## 2. 设计原则

### 2.1 单一搜索内核

无论是 Web 页面搜索还是 Bot 对话式搜索，都应调用统一的搜索应用服务，统一使用：

- 相同的查询理解能力
- 相同的召回逻辑
- 相同的融合排序逻辑
- 相同的轻量 LLM 重排能力

区别仅体现在：

- Web：返回素材列表与解释性元信息
- Bot：在同一套检索结果基础上，进一步调用 LLM 生成对话回答

### 2.2 混合检索优先于纯向量检索

向量检索是必要能力，但不是唯一能力。最终系统应采用混合检索：

- 结构化过滤（content type / category 等）
- 关键词检索（标题 / 描述 / 标签 / AI 关键词 / 类目）
- 标签精确命中与实体词命中
- 向量召回（语义理解）
- 轻量 LLM 重排（只处理 Top-K）

### 2.3 业务直觉优先

对营销素材搜索而言，以下信号应被认为比抽象向量语义更强：

- 人工标签直接命中
- AI 关键词直接命中
- 标题直接命中
- 类型词触发的素材类型过滤
- 类目词直接命中

因此排序策略采用**方案 A：业务加权分数**，而不是完全依赖无解释的单一相似度分数。

### 2.4 轻量 LLM，配置驱动

LLM 在该场景中的定位：

- 做 Query 理解
- 做 Top-K 重排
- 做 Bot 最终回答生成

LLM 的使用通过功能开关控制，模型名称通过环境变量配置，可以在不修改代码的情况下快速切换或临时关闭，以便对比不同模型的延迟与效果表现。两处 LLM 调用均有超时降级机制，确保 LLM 异常时搜索仍能返回结果。

### 2.5 可观测性内建

每次 `search_contents()` 调用均应记录各阶段耗时（Query 理解、各路召回、RRF 融合、业务评分、LLM 重排），写入结构化日志。调试模式下该耗时同时附加在 API 响应中，便于对比不同模型与参数配置下的性能差异。

---

## 3. 当前实现概览与主要问题

### 3.1 当前搜索流程

当前实现中：

1. 用户输入查询文本
2. 后端直接为该文本生成 embedding
3. 对 `contents.embedding` 执行 pgvector cosine similarity 排序
4. 返回排序结果

Bot 对话搜索的流程是在上述检索结果之上，再额外调用 LLM 生成自然语言回答。

### 3.2 当前实现的核心问题

#### 3.2.1 召回路径单一

当前主要依赖向量相似度，缺少：关键词召回、标签精确命中召回、类目精确命中召回、类型词解析、业务排序加权。

#### 3.2.2 结构化信息未充分参与检索

虽然内容实体中存在如下信息：

- 标题
- 描述
- 人工标签
- AI 关键词
- 一级/二级类目
- 内容类型（image / video）

但这些信息在当前搜索排序中并未被系统性使用。

#### 3.2.3 Web 与 Bot 只共享“最底层检索函数”，未共享完整搜索系统

当前共享的是基础 `semantic_search`，但未共享：

- 查询理解
- 多路召回
- 融合排序
- 重排策略

这会导致两个入口在后续演进中容易分叉，最终形成两套行为不一致的搜索体验。

#### 3.2.4 embedding 文本构造范围窄，存量数据无补算机制

当前 embedding 文本仅由 `title + ai_summary + ai_keywords` 组成，未包含人工标签、类目、内容类型等关键业务信息，导致向量召回对业务字段的覆盖度不足。embedding 文本构造策略变更后，存量数据缺乏重算触发机制，需要提供手动补算脚本。

#### 3.2.5 所有搜索参数硬编码

限制条数、相似度阈值等参数直接写在业务代码中，无法在不修改代码的情况下快速调优。

---

## 4. 目标能力

统一搜索系统应满足以下业务能力：

### 4.1 类型词理解

当用户输入以下词语时，应优先转化为结构化过滤条件：

- `视频` / `短视频` / `视频素材` → `content_type = video`
- `图片` / `图` / `海报` / `照片` → `content_type = image`

### 4.2 标签优先

当查询词直接命中：

- 人工标签
- AI 关键词

相关素材应在排序上得到显著提升。

### 4.3 实体词高可用

当用户搜索：

- `玻璃瓶`
- `食品`
- `礼盒`
- `胶原蛋白`

系统应综合利用：

- 标题
- 描述
- 标签
- AI 关键词
- AI 摘要
- 类目
- 向量语义

使真正包含该实体内容的素材尽量排在前列。

### 4.4 对话式检索复用同一内核

Bot 对话式搜索不应有独立召回系统。Bot 只是在统一搜索结果上追加对检索结果的解释、多条结果摘要整合和最终自然语言回答生成。

### 4.5 快速参数调优

更换 LLM 模型、调整各信号权重、开关 LLM 功能，均可通过修改环境变量实现，无需修改代码并重新部署。

---

## 5. 统一搜索总体架构

统一搜索处理流水线：

```
用户输入
  │
  ▼
[1] Query 预处理
  │   - 去除前后空白，长度截断
  │   - 大小写归一（英文）
  │
  ▼
[2] Query 理解（规则 + 可选 LLM）              ← stage: query_parse
  │   - 类型词识别 → parsed_content_type
  │   - 关键词提取 → must_terms / should_terms
  │   - 同义词扩展
  │   - (可选 SEARCH_ENABLE_LLM_QUERY_PARSE) LLM 补充解析
  │   - LLM 超时则降级为纯规则结果
  │
  ▼
[3] 多路召回                                    ← stage: vector_recall / fts_recall / tag_recall
  │   - 路径一：结构化过滤（content_type 等）作为 WHERE 前置条件
  │   - 路径二：FTS 全文召回（zhparser + to_tsvector）
  │   - 路径三：标签/关键词精确命中召回
  │   - 路径四：pgvector 向量召回
  │
  ▼
[4] RRF 融合去重                                ← stage: rrf_merge
  │   - Reciprocal Rank Fusion 合并各路召回结果
  │   - 去重，得到统一候选集
  │
  ▼
[5] 业务加权评分                                ← stage: scoring
  │   - score_filter + score_exact + score_lexical + score_semantic + score_freshness
  │   - 记录 matched_signals（命中信号列表）
  │
  ▼
[6] Top-K LLM 重排（可选 SEARCH_ENABLE_LLM_RERANK） ← stage: llm_rerank
  │   - 超时则降级为业务评分结果
  │
  ▼
[7] 统一结果输出
  │   - SearchOutput（results + timing + query_info）
  │   - 各阶段耗时写入结构化日志；SEARCH_DEBUG_TIMING=true 时附加在响应中
  │
  ▼
[8] （Bot 专有）生成自然语言回答
```

---

## 6. 服务边界与模块划分

### 6.1 统一服务模块

在 `backend/app/services/search/` 内建立以下模块：

| 文件 | 职责 |
|------|------|
| `core.py` | 统一编排入口，对外暴露 `search_contents()` |
| `query_parser.py` | Query 预处理与理解（规则 + 可选 LLM） |
| `retriever.py` | 多路召回（FTS、向量、标签精确命中） |
| `ranker.py` | RRF 融合 + 业务加权评分 |
| `reranker.py` | Top-K LLM 重排 |
| `errors.py` | 搜索领域异常 |

统一对外暴露一个主入口：

`search_contents(command: SearchContentCommand, db: AsyncSession) -> SearchOutput`

并让以下调用方共享该入口：

- `backend/app/routers/search.py` — Web API
- `backend/app/bot/handlers.py` — Bot 消息处理（**必须重构为调用此入口，当前直接调用 `semantic_search` 的方式须废弃**）

### 6.2 Web 与 Bot 的职责分工

#### Web 搜索

调用统一 `search_contents(...)`，返回：

- 结果列表
- 分数
- 可选命中说明（后续可扩展）

#### Bot 搜索

先调用统一 `search_contents(...)`，拿到同一份候选结果，再：

- 拼接上下文摘要
- 交给轻量 LLM 生成对话式回答

即：

- **共享检索与排序**
- **分离展示与回答层**

这样既统一底层逻辑，也保证不同入口能输出适合自身交互形态的结果。

---

## 7. 搜索配置体系

**所有可调参数必须通过环境变量管理，文件路径：`.env`（本地/生产）、`.env.test`（测试）。** 代码中通过统一的 `SearchConfig` 对象读取，禁止在业务逻辑中直接调用 `os.environ` 或硬编码数值。

### 7.1 完整配置清单

```dotenv
# ── Query 理解 ────────────────────────────────────────────────
# 是否启用 LLM 做 Query 理解
SEARCH_ENABLE_LLM_QUERY_PARSE=false
# LLM Query 理解所用模型（DashScope model id）
SEARCH_LLM_QUERY_PARSE_MODEL=qwen-turbo
# LLM Query 理解超时（秒），超时则降级为纯规则结果
SEARCH_LLM_QUERY_PARSE_TIMEOUT_S=3

# ── 多路召回 ──────────────────────────────────────────────────
# 向量召回最大候选数（进入 RRF 融合前）
SEARCH_VECTOR_RECALL_LIMIT=50
# 全文召回最大候选数（进入 RRF 融合前）
SEARCH_FTS_RECALL_LIMIT=50
# 标签精确命中召回最大候选数
SEARCH_TAG_RECALL_LIMIT=30
# RRF 融合参数 k（推荐初始值 60）
SEARCH_RRF_K=60

# ── 业务加权分数 ──────────────────────────────────────────────
SEARCH_SCORE_CONTENT_TYPE_MATCH=80
SEARCH_SCORE_TAG_EXACT=100
SEARCH_SCORE_TAG_PHRASE=85
SEARCH_SCORE_AI_KEYWORD_EXACT=70
SEARCH_SCORE_AI_KEYWORD_PHRASE=55
SEARCH_SCORE_TITLE_EXACT=60
SEARCH_SCORE_TITLE_PHRASE=45
SEARCH_SCORE_CATEGORY_EXACT=40
SEARCH_SCORE_CATEGORY_PHRASE=30
# must_term 每次出现在描述中的加分
SEARCH_SCORE_MUST_TERM_DESC=20
# must_term 每次出现在 AI 摘要中的加分
SEARCH_SCORE_MUST_TERM_SUMMARY=15
# FTS 分归一化上限（FTS 原始分 → 线性归一到 [0, 此值]）
SEARCH_SCORE_FTS_MAX=30
# 向量相似度归一化上限（相似度 [0,1] → 线性归一到 [0, 此值]）
SEARCH_SCORE_VECTOR_MAX=25
# 新鲜度补充分上限
SEARCH_SCORE_FRESHNESS_MAX=5

# ── LLM 重排 ──────────────────────────────────────────────────
# 是否启用 LLM 重排（生产可先关闭，评估后开启）
SEARCH_ENABLE_LLM_RERANK=false
# LLM 重排所用模型（DashScope model id），修改此项即可切换模型，无需改代码
SEARCH_LLM_RERANK_MODEL=qwen-turbo
# 参与重排的候选数（Top-K）
SEARCH_LLM_RERANK_TOP_K=10
# LLM 重排超时（秒），超时则降级为业务评分排序结果
SEARCH_LLM_RERANK_TIMEOUT_S=8

# ── 可观测性 ──────────────────────────────────────────────────
# 是否在 API 响应中附带各阶段耗时（生产建议 false，调试建议 true）
SEARCH_DEBUG_TIMING=false
```

### 7.2 SearchConfig 读取方式

在 `backend/app/core/config.py` 的 `Settings` 类中新增上述字段（`pydantic-settings` 自动从环境变量读取），并在 `services/search/core.py` 中按功能分组使用：

```python
# 示例：在 service 层读取配置
from app.core.config import settings

enable_rerank: bool = settings.search_enable_llm_rerank
rerank_model: str   = settings.search_llm_rerank_model
score_tag_exact: float = settings.search_score_tag_exact
```

所有 service 层代码通过注入的 `settings` 对象读取配置，不直接访问 `os.environ`，也不硬编码任何数值。

---

## 8. Query 理解设计

Query 理解分为两层：**规则解析优先，轻量 LLM 补充**。

### 8.1 规则解析

对高频、稳定、成本敏感的模式，优先使用规则和词典处理。规则词典以 Python 文件形式维护，路径：`backend/app/services/search/dictionaries/`。

#### 8.1.1 类型词识别

```python
# backend/app/services/search/dictionaries/content_type.py
CONTENT_TYPE_DICT = {
    "video": ["视频", "短视频", "视频素材", "小视频"],
    "image": ["图片", "图", "海报", "照片", "图像", "banner"],
}
```

若 Query 中出现明确类型词，则产出 `parsed_content_type`，并从 Query 文本中移除类型词后再做关键词提取。

#### 8.1.2 强关键词提取

对 Query 做基础分词与归一化，提取：

- 去噪后的关键词列表
- 保留原词顺序
- 去除明显停用词（维护在 `dictionaries/stopwords.py`）
- 字符长度 ≥ 2 的词视为有效词

#### 8.1.3 同义词扩展

```python
# backend/app/services/search/dictionaries/synonyms.py
SYNONYM_DICT = {
    "图": "图片",
    "短视频": "视频",
    "产品展示": "产品",
}
```

同义词归一仅用于扩展 `should_terms`，不修改用户原始 Query 语义。

### 8.2 轻量 LLM 理解

**触发条件**（需 `SEARCH_ENABLE_LLM_QUERY_PARSE=true`，且满足以下至少一条）：

- Query 字符数 > 10
- 规则解析后 `must_terms` 数量 > 2
- Query 包含模糊自然语言结构

**LLM 输入 Prompt 示例：**

```
你是一个营销素材搜索系统的查询理解模块。
请分析用户的查询意图，输出以下 JSON 结构，不要输出其他内容：
{
  "normalized_query": "归一化后的检索表达",
  "content_type": "video | image | null",
  "must_terms": ["强约束词1", "强约束词2"],
  "should_terms": ["软约束词1"],
  "intent": "意图简述"
}

用户输入：{query}
```

**超时处理**：LLM 调用超过 `SEARCH_LLM_QUERY_PARSE_TIMEOUT_S` 秒时，**降级使用规则解析结果**，不中断搜索流程，`ParsedQuery.llm_used` 标记为 `false`。

**示例**（用户输入：`找一些适合朋友圈宣传的玻璃瓶食品短视频`）：

- `content_type = video`
- `must_terms = [玻璃瓶, 食品]`
- `should_terms = [朋友圈, 宣传]`
- `intent = 查找食品类玻璃瓶包装的宣传短视频素材`

### 8.3 Query 理解输出结构

```python
@dataclass
class ParsedQuery:
    raw_query: str
    normalized_query: str          # 归一化后用于 embedding
    parsed_content_type: str | None
    must_terms: list[str]          # 强约束词
    should_terms: list[str]        # 软约束词（含同义扩展）
    query_embedding_text: str      # 用于生成 embedding 的文本
    need_llm_rerank: bool          # 是否建议触发 LLM 重排
    llm_used: bool                 # 是否实际调用了 LLM
```

---

## 9. 多路召回设计

### 9.1 路径一：结构化过滤

针对 `ParsedQuery.parsed_content_type`，在发起任何检索之前，先对候选集施加结构化约束（SQL `WHERE` 条件）：

- 默认仅检索 `status = approved` 的内容
- 若 `parsed_content_type` 非空，加入 `content_type = :type` 过滤
- 结构化过滤作为**强制前置过滤**，在各路召回的 SQL 中直接加入 `WHERE`，而不是 RRF 后置过滤

后续可扩展 `category_id`、`primary_category_id` 等过滤条件。

### 9.2 路径二：全文召回（FTS）

#### 9.2.1 技术选型

**采用 PostgreSQL FTS + `zhparser` 中文分词插件**。

- `zhparser` 已安装于生产环境阿里云 RDS PostgreSQL，无需额外申请
- 使用 `to_tsvector('zhparser', search_document)` **实时计算**，不存储持久化 `tsvector` 列
- 替代方案：本地开发环境若未安装 `zhparser`，可通过 `SEARCH_FTS_BACKEND=ilike` 配置项降级为 `ILIKE` 多字段匹配

FTS 查询示意：

```sql
SELECT id,
       ts_rank_cd(
           to_tsvector('zhparser', search_document),
           plainto_tsquery('zhparser', :query)
       ) AS fts_rank
FROM contents
WHERE status = 'approved'
  AND to_tsvector('zhparser', search_document)
      @@ plainto_tsquery('zhparser', :query)
ORDER BY fts_rank DESC
LIMIT :fts_recall_limit;   -- SEARCH_FTS_RECALL_LIMIT
```

#### 9.2.2 search_document 字段权重说明

`search_document` 按字段重要性拼接，高权重字段靠前，使 `ts_rank_cd` 的位置权重发挥正向作用：

| 权重 | 字段 |
|------|------|
| A（最高） | 标题、人工标签 |
| B | AI 关键词、类目名、内容类型中文标签 |
| C | 描述、AI 摘要 |

`content_type_label` 双写中文别名（`image` → `图片 图像`，`video` → `视频 短视频`），覆盖更多查询变体。

#### 9.2.3 GIN 索引

```sql
CREATE INDEX CONCURRENTLY idx_contents_search_fts
    ON contents
    USING gin(to_tsvector('zhparser', search_document))
    WHERE search_document IS NOT NULL;
```

### 9.3 路径三：标签精确命中召回

独立执行标签精确命中查询，不依赖 FTS。查询逻辑：

1. **人工标签完全命中**：JOIN `content_tags`，`tag.name = any(:must_terms)`
2. **人工标签短语命中**：`tag.name ILIKE '%' || :term || '%'`
3. **AI 关键词完全命中**：`:term = any(ai_keywords)`（JSONB 数组操作）
4. **AI 关键词短语命中**：`EXISTS (SELECT 1 FROM jsonb_array_elements_text(ai_keywords) kw WHERE kw ILIKE '%' || :term || '%')`

此路径结果独立收集，参与 RRF 融合，并在业务评分阶段记录 matched_signals。

### 9.4 路径四：向量召回

```sql
SELECT id,
       1 - (embedding <=> :query_embedding) AS vector_score
FROM contents
WHERE status = 'approved'
  AND embedding IS NOT NULL
ORDER BY embedding <=> :query_embedding
LIMIT :vector_recall_limit;   -- SEARCH_VECTOR_RECALL_LIMIT
```

向量召回结果参与 RRF 融合，不再作为最终排序的唯一依据。

---

## 10. RRF 融合策略

### 10.1 算法选择

采用 **Reciprocal Rank Fusion（RRF）** 作为多路召回的融合策略。

RRF 优点：
- 无需对各路分数做归一化，对量纲差异天然免疫
- 参数少（仅 `k`），效果稳健，便于通过 `SEARCH_RRF_K` 快速调优

### 10.2 融合公式

$$
RRF\_score(d) = \sum_{r \in \{fts,\;vector,\;tag\}} \frac{1}{k + rank_r(d)}
$$

其中：

- $rank_r(d)$ 为内容 $d$ 在召回路径 $r$ 中的排名（从 1 开始，未被该路径召回则不参与求和）
- $k$ 由 `SEARCH_RRF_K` 配置，推荐初始值 `60`

**示例（k=60）：**

| 内容 | FTS 排名 | 向量排名 | 标签命中排名 | RRF 分数 |
|------|---------|---------|------------|---------|
| A    | 1       | 3       | 1          | 1/61 + 1/63 + 1/61 ≈ 0.049 |
| B    | 2       | 1       | —          | 1/62 + 1/61 ≈ 0.033 |
| C    | —       | 2       | 2          | 1/62 + 1/62 ≈ 0.032 |

### 10.3 融合后候选集规模

实际参与业务评分的候选集通常在 30～150 条之间，足够支撑后续打分与重排。

---

## 11. 搜索文档与 embedding 文本设计

### 11.1 search_document（供 FTS 使用）

`search_document` 是 `contents` 表上的 `TEXT` 列，内容为各字段按权重顺序拼接：

```
{title} {tag_names} {ai_keywords} {category_name} {primary_category_name} {content_type_label} {description} {ai_summary}
```

- **重要字段靠前**：标题和标签排在最前，使 `ts_rank_cd` 位置权重发挥正向作用
- **字段分隔符**：空格（对中文分词友好）
- `content_type_label`：`image` → `图片 图像`，`video` → `视频 短视频`（双写，覆盖更多查询变体）
- 任何字段为空时直接跳过，不插入占位符

### 11.2 embedding_text（供向量召回使用）

embedding 文本应全面覆盖内容的业务语义，相比旧版新增 `description`、`tag_names`（人工标签）、`primary_category_name`、`content_type_label`：

```
{title} {description} {tag_names} {ai_keywords} {ai_summary} {primary_category_name} {category_name} {content_type_label}
```

### 11.3 AI 失败 fallback

若 AI 分析失败（`ai_status = failed`），不应生成空文本 embedding。Fallback 规则（按优先级）：

1. `title`（用户填写）
2. `description`（用户填写）
3. `tag_names`（人工标签）
4. `category_name` + `primary_category_name`
5. `content_type_label`

当且仅当拼接后有效文本长度 ≥ 4 字时才生成 embedding；否则跳过，待 AI 重试完成后再补算。

### 11.4 search_document 同步策略

`search_document` 和 `embedding_text` 在以下场景下保持同步：

#### 场景一：AI 分析完成（主路径）

AI 后台任务（`workers/`）分析完成后，在更新 `ai_summary`、`ai_keywords`、`ai_status` 的**同一事务**中，同步更新 `search_document`、`embedding_text`，并重新生成 embedding。这是大多数内容的正常写入路径。

#### 场景二：人工标签变更

`content_tags` 关联表发生 INSERT 或 DELETE 时，在内容标签管理的 service 方法中，标签变更后**通过 `BackgroundTasks` 异步触发** `rebuild_search_document(content_id)` 任务，同时重建 `search_document` 并重算 embedding（人工标签同时包含在 `embedding_text` 中）。

#### 场景三：类目变更

content 的 `category_id` 变更时，同场景二的处理，触发 `rebuild_search_document(content_id)`。

#### 场景四：存量数据手动补算

针对已有数据，通过手动脚本执行全量重建：

```bash
# 脚本路径：scripts/backfill_search_documents.py

# 只打印，不写入（dry run）
cd backend && uv run python ../scripts/backfill_search_documents.py --dry-run

# 全量补算
cd backend && uv run python ../scripts/backfill_search_documents.py

# 只处理指定 content
cd backend && uv run python ../scripts/backfill_search_documents.py --content-id 42

# 只处理 AI 分析已完成的内容
cd backend && uv run python ../scripts/backfill_search_documents.py --ai-status-filter completed
```

脚本要求：批量处理（每批 20 条）避免 embedding API 限速；支持断点续算（记录最后处理的 `content_id`）；执行完毕后打印成功/失败统计。

---

## 12. 业务加权评分

RRF 融合后，对统一候选集进行业务加权评分，得到最终排序依据。

### 12.1 总分公式

$$
score_{final} = score_{filter} + score_{exact} + score_{lexical} + score_{semantic} + score_{freshness}
$$

| 组成部分 | 含义 |
|---------|------|
| `score_filter` | 类型词命中 content_type 的加分 |
| `score_exact` | 标签精确/短语命中、标题精确/短语命中、类目命中加分 |
| `score_lexical` | FTS rank 归一化分 |
| `score_semantic` | 向量相似度归一化分 |
| `score_freshness` | 基于上传时间的轻量新鲜度补充分 |

### 12.2 各信号分值（通过 env 配置，初始值见第 7 节）

| 信号 | 配置键 | 初始值 |
|------|--------|-------|
| 类型词命中 content_type | `SEARCH_SCORE_CONTENT_TYPE_MATCH` | 80 |
| 人工标签完全命中 | `SEARCH_SCORE_TAG_EXACT` | 100 |
| 人工标签短语命中 | `SEARCH_SCORE_TAG_PHRASE` | 85 |
| AI 关键词完全命中 | `SEARCH_SCORE_AI_KEYWORD_EXACT` | 70 |
| AI 关键词短语命中 | `SEARCH_SCORE_AI_KEYWORD_PHRASE` | 55 |
| 标题完全命中 | `SEARCH_SCORE_TITLE_EXACT` | 60 |
| 标题短语命中 | `SEARCH_SCORE_TITLE_PHRASE` | 45 |
| 类目完全命中 | `SEARCH_SCORE_CATEGORY_EXACT` | 40 |
| 类目短语命中 | `SEARCH_SCORE_CATEGORY_PHRASE` | 30 |
| must term 出现在描述中（每个） | `SEARCH_SCORE_MUST_TERM_DESC` | 20 |
| must term 出现在 AI 摘要中（每个） | `SEARCH_SCORE_MUST_TERM_SUMMARY` | 15 |
| FTS 分归一化上限 | `SEARCH_SCORE_FTS_MAX` | 30 |
| 向量相似度归一化上限 | `SEARCH_SCORE_VECTOR_MAX` | 25 |
| 新鲜度补充分上限 | `SEARCH_SCORE_FRESHNESS_MAX` | 5 |

### 12.3 排序优先级

1. **人工标签命中最高**
2. **AI 关键词命中次高**
3. **标题 / 类型 / 类目命中优先于纯向量相似度**
4. 向量分值作为补充，不压过结构化和精确命中的主排序依据

### 12.4 FTS 与向量分的归一化

$$
score_{lexical} = \frac{fts\_rank}{max\_fts\_rank\_in\_batch} \times SEARCH\_SCORE\_FTS\_MAX
$$

$$
score_{semantic} = vector\_similarity \times SEARCH\_SCORE\_VECTOR\_MAX
$$

### 12.5 Must Terms 约束

若 `ParsedQuery.must_terms` 非空：

- 候选结果完全不包含任何 must term：`score_final *= 0.3`（显著降权，保留兜底）
- 命中多个 must term：按每个命中词进行加分累计

---

## 13. Top-K 轻量 LLM 重排

### 13.1 何时触发

LLM 重排受以下条件共同约束：

1. `SEARCH_ENABLE_LLM_RERANK=true`
2. `ParsedQuery.need_llm_rerank=true`（Query 理解阶段判断）

两个条件同时满足时才执行重排。`need_llm_rerank` 触发条件（规则判断）：Query 字符数 > 8，或 `must_terms` 数量 ≥ 2。

### 13.2 LLM 重排目标

用于解决：Query 是复杂自然语言表达、多个结果都命中关键词但"真正符合意图"的排序仍不稳定的场景。只处理业务评分后的 Top-K 候选（`SEARCH_LLM_RERANK_TOP_K`），不扫描全库。

### 13.3 模型配置与切换

模型名称通过 `SEARCH_LLM_RERANK_MODEL` 配置，修改后无需改代码即可切换。推荐选项：

| 模型 | 特点 |
|------|------|
| `qwen-turbo` | 响应快（通常 1~3s），成本低，适合首期 |
| `qwen-plus` | 效果更佳，延迟相对更高，评估后可切换 |

### 13.4 LLM 输入格式

```
你是一个营销素材搜索结果重排模块。
用户查询：{query}
查询意图：{intent}

请从以下候选素材中，按照与用户查询的相关性从高到低重新排序。
输出格式为 JSON 数组，只包含素材 id，例如：[3, 1, 5, 2, 4]
不要输出其他内容。

候选素材：
{candidates}
```

`candidates` 为 JSON 数组，每项包含：id、title、content_type、tags、ai_keywords、category、description（截断至 100 字）、ai_summary（截断至 100 字）、initial_score。

### 13.5 超时降级

LLM 调用超过 `SEARCH_LLM_RERANK_TIMEOUT_S` 秒时，**降级使用业务评分排序结果**，`SearchResultOutput.reranked` 标记为 `false`，不中断请求。

### 13.6 Web 与 Bot 的差异

- **Web**：使用重排后的结果顺序
- **Bot**：在相同重排结果上进一步生成自然语言回答

---

## 14. 统一搜索结果模型

### 14.1 SearchResultOutput（领域层）

```python
@dataclass
class SearchResultOutput:
    content: ContentOutput
    final_score: float
    lexical_score: float
    semantic_score: float
    matched_signals: list[str]   # 命中信号列表，用于调试与解释
    reranked: bool               # 是否经过 LLM 重排
```

`matched_signals` 可能包含的值：

| 值 | 含义 |
|----|------|
| `content_type_filter` | 命中类型词过滤 |
| `tag_exact:{tag}` | 人工标签完全命中 |
| `tag_phrase:{tag}` | 人工标签短语命中 |
| `ai_keyword_exact:{kw}` | AI 关键词完全命中 |
| `ai_keyword_phrase:{kw}` | AI 关键词短语命中 |
| `title_exact` | 标题完全命中 |
| `title_phrase` | 标题短语命中 |
| `category_match:{name}` | 类目命中 |
| `must_term:{term}` | must term 命中 |
| `fts_match` | FTS 全文召回命中 |
| `vector_match` | 向量召回命中 |

### 14.2 SearchTimingOutput（可观测性）

```python
@dataclass
class SearchTimingOutput:
    query_parse_ms: float
    vector_recall_ms: float
    fts_recall_ms: float
    tag_recall_ms: float
    rrf_merge_ms: float
    scoring_ms: float
    llm_rerank_ms: float | None   # None 表示未触发重排
    total_ms: float
```

**无论 `SEARCH_DEBUG_TIMING` 是否开启，`SearchTimingOutput` 都写入结构化日志。** 当 `SEARCH_DEBUG_TIMING=true` 时，同时附加在 API 响应中。

### 14.3 SearchOutput（统一出口）

```python
@dataclass
class SearchOutput:
    results: list[SearchResultOutput]
    timing: SearchTimingOutput | None   # SEARCH_DEBUG_TIMING=true 时非 None
    query_info: ParsedQuery             # 调试用，含 LLM 是否被调用
```

---

## 15. 数据库与索引设计

### 15.1 contents 表新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `search_document` | `TEXT` | FTS 检索文本，由服务层维护 |
| `embedding_text` | `TEXT` | 用于生成 embedding 的文本（可选，调试用） |

迁移文件命名示例：`xxx_add_search_document_to_contents.py`

### 15.2 索引建议

```sql
-- FTS GIN 索引（zhparser）
CREATE INDEX CONCURRENTLY idx_contents_search_fts
    ON contents
    USING gin(to_tsvector('zhparser', search_document))
    WHERE search_document IS NOT NULL;

-- pgvector 索引（已有，确认存在即可）
CREATE INDEX CONCURRENTLY idx_contents_embedding
    ON contents
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- 过滤索引（content_type + status 复合，覆盖多路召回的 WHERE 条件）
CREATE INDEX idx_contents_type_status
    ON contents (content_type, status)
    WHERE status = 'approved';
```

### 15.3 标签检索

人工标签通过关联表 JOIN 查询（精确命中路径），AI 关键词通过 JSONB 数组操作查询，两者同时聚合写入 `search_document` 以统一 FTS 检索入口。

---

## 16. API 设计

### 16.1 Web 搜索 API

**端点**：`POST /api/v1/search`（保持现有路径不变）

**请求体（SearchQueryIn）：**

```json
{
  "query": "适合朋友圈的食品类短视频",
  "limit": 10,
  "content_type": null,
  "enable_rerank": null
}
```

- `content_type`：前端显式筛选器传入时使用；若同时 Query 理解也识别出类型词，前端传值优先
- `enable_rerank`：保留字段，实际由 `SEARCH_ENABLE_LLM_RERANK` 决定，客户端传值仅供调试参考

**响应体（SearchResultsOut）：**

```json
{
  "results": [
    {
      "content": { "...": "..." },
      "final_score": 195.5,
      "lexical_score": 22.3,
      "semantic_score": 18.7,
      "matched_signals": ["content_type_filter", "tag_exact:食品", "fts_match"],
      "reranked": false
    }
  ],
  "timing": {
    "query_parse_ms": 1245.2,
    "vector_recall_ms": 38.1,
    "fts_recall_ms": 22.4,
    "tag_recall_ms": 5.3,
    "rrf_merge_ms": 0.8,
    "scoring_ms": 3.2,
    "llm_rerank_ms": null,
    "total_ms": 1316.4
  },
  "query_info": {
    "parsed_content_type": "video",
    "must_terms": ["食品"],
    "should_terms": ["朋友圈", "宣传"],
    "llm_used": true
  }
}
```

注：`timing` 和 `query_info` 字段仅在 `SEARCH_DEBUG_TIMING=true` 时出现在响应中。`timing` 在任何情况下都写入结构化日志。

### 16.2 Bot 调用方式

Bot `handlers.py` 重构为：

```python
result = await search_contents(
    SearchContentCommand(query=user_text, limit=5),
    db=db,
)
# 取 result.results 前 N 条，构造上下文，调用 LLM 生成回答
```

---

## 17. 实施路线

建议分阶段实施，每个 Phase 可独立上线。

### Phase 0：配置基础设施（前置，所有 Phase 共同依赖）

- 在 `backend/app/core/config.py` 中添加所有 `SEARCH_*` 环境变量字段
- 更新 `.env.example` 和 `.env.test` 中的配置项
- 确认阿里云 RDS 已安装 `zhparser`（执行 `CREATE TEXT SEARCH CONFIGURATION zhparser (PARSER = zhparser)` 验证）

### Phase 1：修正基础数据质量

- 新增 `contents.search_document` 和 `contents.embedding_text` 列（Alembic 迁移）
- 重构 embedding 文本构造逻辑（扩展为 8 个字段）
- 重构 `search_document` 构造逻辑（高权重字段靠前）
- 修复 AI 失败时的 fallback 策略
- 创建 FTS GIN 索引
- 编写并执行 `scripts/backfill_search_documents.py` 存量补算

### Phase 2：引入统一 Query 理解

- 创建 `dictionaries/` 目录，维护类型词、停用词、同义词词典
- 实现 `query_parser.py`（规则解析）
- 接入 LLM Query 理解（开关 `SEARCH_ENABLE_LLM_QUERY_PARSE`，默认 `false`）
- 单元测试覆盖各类 Query 场景

### Phase 3：实现多路召回 + RRF 融合

- 实现 FTS 全文召回（`retriever.py`）
- 实现标签精确命中召回
- 保留向量召回
- 实现 RRF 融合（`ranker.py`，参数 `SEARCH_RRF_K`）

### Phase 4：实现业务加权评分 + 可观测性

- 落地业务加权分数模型（所有权重从 `settings` 读取）
- 输出 `matched_signals`
- 实现 `SearchTimingOutput` 结构化日志记录
- 开启 `SEARCH_DEBUG_TIMING=true` 观测各阶段耗时基线

### Phase 5：LLM 重排 + Bot 重构

- 实现 `reranker.py`（开关 `SEARCH_ENABLE_LLM_RERANK`，默认 `false`）
- 重构 `bot/handlers.py`，改为调用统一 `search_contents()`
- 验证 Web 与 Bot 结果一致性

### Phase 6：评估与迭代

- 建立典型查询评测集（覆盖类型词、标签词、实体词、复杂意图四类）
- 开启 LLM 重排（`SEARCH_ENABLE_LLM_RERANK=true`），对比耗时与效果
- 切换模型（修改 `SEARCH_LLM_RERANK_MODEL`），对比不同模型表现
- 根据评测结果调整权重（修改 `SEARCH_SCORE_*`），持续迭代

---

## 18. 评估指标

### 18.1 查询类别

| 类别 | 示例 |
|------|------|
| 类型词查询 | `视频`、`短视频`、`图片` |
| 标签词查询 | `胶原蛋白`、`女性营养` |
| 类目词查询 | `食品`、`保健品` |
| 实体词查询 | `玻璃瓶`、`礼盒` |
| 复杂意图查询 | `适合朋友圈宣传的食品类短视频` |

### 18.2 检索效果指标

- Top 1 / Top 3 / Top 10 命中率
- 精确命中结果平均排名
- LLM 重排前后 Top 3 命中率提升幅度

### 18.3 性能指标（来自 SearchTimingOutput）

| 阶段 | 目标耗时 |
|------|---------|
| query_parse（规则） | < 5ms |
| query_parse（LLM） | < 3000ms（超时降级） |
| vector_recall | < 50ms |
| fts_recall | < 30ms |
| tag_recall | < 10ms |
| rrf_merge + scoring | < 10ms |
| llm_rerank | < 8000ms（超时降级） |
| **total（无 LLM）** | **< 120ms** |
| **total（含 LLM Query 理解）** | **< 3200ms** |
| **total（含 LLM 重排）** | **< 700ms**（不含 Query 理解） |

---

## 19. 风险与注意事项

### 19.1 不能把 LLM 当主检索引擎

LLM 应用于理解与重排，而不是替代数据库检索。两处 LLM 调用均有超时降级机制，确保 LLM 异常时搜索仍能返回结果。

### 19.2 不允许 Web 与 Bot 分叉演进

Web 搜索与 Bot 搜索必须共用 `search_contents()` 入口。Bot `handlers.py` 重构为调用统一入口是 Phase 5 的强制要求，不可跳过。

### 19.3 权重通过配置持续调优

首期权重按文档初始值上线，通过 `SEARCH_DEBUG_TIMING=true` 收集线上查询日志，结合评测集结果逐步调优。调优只需修改 env，无需修改代码。

### 19.4 search_document 同步一致性

当内容标签或类目发生变更时，`search_document` 更新是**异步**的（`BackgroundTasks`），在极短时间窗口内 FTS 结果可能基于旧数据。这个一致性延迟在营销素材搜索场景下是可接受的。

### 19.5 zhparser 扩展依赖

FTS 强依赖 `zhparser` 扩展：

- **生产环境**：阿里云 RDS 已安装，无需额外操作
- **本地开发**：Docker 镜像可能未含此扩展；可通过 `SEARCH_FTS_BACKEND=ilike` 配置项降级为 `ILIKE` 多字段匹配（性能较低，仅限开发调试）

---

## 20. 结论

PromoFlow 的目标搜索系统不应是"纯向量相似度排序"，而应是一个**统一的、可解释的、可配置的混合式智能搜索系统**。

该系统的核心特征：

- **Web 与 Bot 共用一套搜索内核**，Bot 只是在统一结果上追加回答生成
- **规则 + 可选 LLM** 做 Query 理解，规则降级保障可用性
- **四路召回（结构化过滤 + FTS/zhparser + 标签精确命中 + 向量）+ RRF 融合**，覆盖精确与语义两类需求
- **业务加权评分**，所有权重通过 env 配置，可在不修改代码的情况下快速调优
- **可选 LLM Top-K 重排**，模型可配置，超时自动降级
- **各阶段耗时结构化记录**，调试模式下附加在 API 响应中，便于快速对比不同模型与参数的性能差异
- **search_document 明确同步策略**，包含 AI worker 主路径、异步触发和手动补算脚本三条路径
