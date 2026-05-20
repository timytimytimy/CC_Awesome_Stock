# 交易日记

记录你自己的每一笔交易，以及定期复盘。这是整个知识库中**权重最高**的部分——skill 在做决策时会优先参考你自己的教训。

## 目录结构

```
journal/
├── trades/       # 单笔交易日记（每笔一个文件）
├── reviews/
│   ├── weekly/   # 每周复盘
│   └── monthly/  # 每月复盘
└── lessons/      # 提炼的可复用教训（skill 启动时强制加载）
```

## 使用方式

1. **建仓时**：用 `_template.md` 创建 `trades/YYYY-MM-DD-TICKER.md`，填写建仓逻辑
2. **离场时**：回到该文件，填写"实际结果"和"事后反思"
3. **定期**：每周写 `reviews/weekly/YYYY-Www.md`，每月写 `reviews/monthly/YYYY-MM.md`
4. **提炼**：发现可复用的教训时，写入 `lessons/<slug>.md`

## Lessons 命名约定

`lessons/<slug>.md` 的 slug 应清晰描述教训：
- `do-not-buy-breakout-in-bear-market.md`
- `validate-revenue-before-buying-concept.md`
- `no-averaging-down-without-new-evidence.md`
