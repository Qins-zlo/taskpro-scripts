# TaskPro Scripts

TaskPro (定时任务Pro) 官方脚本市场仓库。

## 目录结构

- `index.json` - 脚本索引（脚本元数据列表）
- `scripts/<name>/` - 每个脚本一个目录
  - `index.json` - 脚本元数据 + 内容

## 脚本格式

每个脚本位于 `scripts/<name>/index.json`：

```json
{
  "name": "脚本名",
  "type": "py|js|sh",
  "ver": "1.0",
  "note": "说明",
  "author": "作者",
  "content": "脚本代码"
}
```

## 提交脚本

用户通过 TaskPro App 提交脚本后，会以 GitHub Issue 形式出现在本仓库的 Issues 中，经审核通过后合并入 `scripts/` 目录。
