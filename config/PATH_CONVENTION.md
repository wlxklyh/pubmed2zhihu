# 路径约定文档

## 项目目录结构

```
projects/
  └── {timestamp}_{query_slug}/
      ├── project_summary.json          # 项目元数据
      ├── step1_search/
      │   └── search_results.json       # 搜索结果
      ├── step2_details/
      │   ├── papers_details.json       # 论文详情
      │   └── pdfs/                     # PDF文件和提取的文本
      ├── step3_figures/
      │   ├── figures_info.json         # 图片信息
      │   └── images/                   # 图片文件
      ├── step4_prompts/
      │   ├── prompts_info.json         # Prompt信息
      │   └── prompt_{pmid}.txt         # 单篇论文Prompt
      ├── step5_overview/
      │   ├── overview_info.json        # 综述信息
      │   ├── merged_prompt.txt         # 合并的Prompt
      │   ├── papers_list.json          # 论文列表
      │   └── llm_response.json         # LLM返回的JSON结果 ⚠️
      ├── step6_report/
      │   └── report_info.json          # 报告生成信息（兼容旧版本）
      └── FinalOutput/                  # 最终输出目录 ✨
          ├── report_info.json          # 报告生成信息（主要位置）
          ├── overview_report.html      # 综述主报告
          └── {pmid}_{slug}.html        # 论文详情页（20个）
```

## 关键路径说明

### 1. LLM响应文件
- **位置**: `step5_overview/llm_response.json`
- **作用**: 存储LLM生成的综述和论文解读内容
- **格式**: JSON，包含 `overview` 和 `papers` 两部分
- **生成方式**: 手动将LLM输出保存到此文件

### 2. 报告信息文件
- **主要位置**: `FinalOutput/report_info.json`
- **兼容位置**: `step6_report/report_info.json`
- **内容**: 包含生成状态、时间、文件列表等元数据
- **读取优先级**: 优先读取 FinalOutput，不存在则读取 step6_report

### 3. HTML报告文件
- **综述主页**: `FinalOutput/overview_report.html`
- **论文详情**: `FinalOutput/{pmid}_{slug}.html`
- **访问方式**: 通过Flask路由 `/project/<name>/report/<filename>`

## Web路由映射

| URL | 文件路径 | 说明 |
|-----|---------|------|
| `/project/<name>/report` | `FinalOutput/overview_report.html` | 综述主页（默认） |
| `/project/<name>/report/overview_report.html` | `FinalOutput/overview_report.html` | 综述主页（显式） |
| `/project/<name>/report/{pmid}_{slug}.html` | `FinalOutput/{pmid}_{slug}.html` | 论文详情页 |
| `/project/<name>/images/<filename>` | `step3_figures/images/<filename>` | 图片文件 |

## 注意事项

1. **路径分隔符**: Windows使用 `\`，建议使用 `os.path.join()` 构建路径
2. **相对路径**: HTML中的图片使用相对路径 `../step3_figures/images/`
3. **URL编码**: 项目名称中的特殊字符需要正确编码
4. **文件存在性检查**: 访问文件前必须检查 `os.path.exists()`

## 更新日志

- 2026-01-01: 统一 `report_info.json` 路径，同时保存到两个位置以兼容
- 2026-01-01: 添加通配符路由支持子路径访问

