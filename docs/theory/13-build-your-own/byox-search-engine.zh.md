---
id: byox-search-engine
category: 13-build-your-own
level: 高级
name_zh: 从零写搜索引擎(Build Your Own Search Engine)
name_en: Build Your Own Search Engine
one_liner_zh: 倒排索引 + TF-IDF + BM25;懂检索 + RAG 测试根
one_liner_en: Inverted index + TF-IDF + BM25; foundation for retrieval + RAG testing
authority:
  - "Manning《Introduction to Information Retrieval》(Stanford)"
  - "Lucene in Action"
confidence: medium
last_reviewed: 2026-05-12
reviewer: agent-curator
estimated_time_hours: 25
when_to_use: RAG 测试 / 搜索结果质量评测 / 推荐相关性 / KB 检索准确率
common_pitfall: ["仅 TF-IDF 不学 BM25 → 长文档惩罚错", "不学 Vector → 跟不上 RAG 时代"]
example: |
  Python 100 行倒排索引 + BM25;100 文档检索 top-3
related_to: [byox-database]
reading_zh: ["阿里巴巴搜索学院文档"]
reading_en: ["https://nlp.stanford.edu/IR-book/"]
---

# 对测试工作

-**RAG 测试**:理解检索召回率/精度 → 设计 Jaccard@k / nDCG eval
-**混合检索**(本项目 §24):懂 BM25 + vector 才能融合 fork
-**KB 测试**:本项目 docs/theory KB 检索质量评测
-**gbrain 精髓**§ 1.3 混合检索 4 路落地的理论基础
