# Errors Log

---

<!-- Errors will be logged here when commands fail or unexpected behavior occurs -->

## [ERR-20260409-001] xlsx-recalc-soffice-missing

**Logged**: 2026-04-09T16:30:00+08:00
**Priority**: medium
**Status**: pending
**Area**: config

### Summary
`xlsx` 技能的 `recalc.py` 在当前 macOS 环境无法执行，因为系统中没有可用的 `soffice`。

### Error
```
FileNotFoundError: [Errno 2] No such file or directory: 'soffice'
```

### Context
- 尝试命令：`python3 '.codebuddy/skills/xlsx/scripts/recalc.py' '10_Work/海克斯大乱斗/海克斯大乱斗_符文标签.xlsx'`
- 场景：更新 Excel 后，希望重算 `英雄汇总` Sheet 中的占比公式缓存
- 环境：macOS / zsh / 当前工作区未安装 LibreOffice CLI

### Suggested Fix
为本机安装 LibreOffice，或让 `recalc.py` 在缺少 `soffice` 时优先检查 macOS 应用路径并提供数值回填兜底方案。

### Metadata
- Reproducible: yes
- Related Files: .codebuddy/skills/xlsx/scripts/recalc.py, 10_Work/海克斯大乱斗/海克斯大乱斗_符文标签.xlsx

---
