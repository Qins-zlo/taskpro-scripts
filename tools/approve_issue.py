#!/usr/bin/env python3
"""
TaskPro 脚本市场审核工具
把用户通过 GitHub Issue 提交的脚本审核通过后, 合并进 scripts/ 目录并更新 index.json。

用法:
    python3 approve_issue.py <issue_number> [--approve|--reject] [--reason "理由"]

流程:
1. 读取指定 Issue, 解析脚本元数据(name/type/ver/note/author) + 代码内容
2. --approve: 把脚本写入 scripts/<name>/index.json, 更新 index.json, 提交推送
            并在 Issue 上加 [merged] 标记 (App 的"我的提交"会识别为已上架), 关闭 Issue
3. --reject:  关闭 Issue (App 的"我的提交"会识别为已驳回)

需要环境变量 GH_TOKEN (GitHub personal access token, 有 taskpro-scripts 仓库写权限)
"""
import sys, os, json, base64, re, subprocess, urllib.request

REPO = "Qins-zlo/taskpro-scripts"
API = f"https://api.github.com/repos/{REPO}"
TOKEN = os.environ.get("GH_TOKEN", "")
ISSUE_PREFIX = "[script] "

def gh(method, path, data=None):
    req = urllib.request.Request(API + path, method=method,
        headers={"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json"})
    body = json.dumps(data).encode() if data is not None else None
    try:
        resp = urllib.request.urlopen(req, body, timeout=30)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print("HTTP错误", e.code, e.read().decode()[:500])
        sys.exit(1)

def parse_issue(num):
    """解析 Issue body, 提取脚本元数据与代码"""
    it = gh("GET", f"/issues/{num}")
    title = it.get("title", "")
    body = it.get("body", "")
    if not title.startswith(ISSUE_PREFIX):
        print(f"Issue #{num} 不是脚本提交(标题不以 {ISSUE_PREFIX} 开头)")
        sys.exit(1)
    def field(name):
        m = re.search(rf"\*\*{name}\*\*:\s*(.*)", body)
        return m.group(1).strip() if m else ""
    name = field("名称")
    typ = field("类型")
    ver = field("版本")
    note = field("说明")
    author = field("作者")
    # 提取代码块 (支持动态长度围栏, 如 ``` 或 `````)
    content = ""
    fence_m = re.search(r"^(`{3,})\w*\s*\n", body, re.MULTILINE)
    if fence_m:
        fence = fence_m.group(1)
        # 匹配同长度的闭合围栏
        m = re.search(re.escape(fence) + r"\w*\s*\n(.*?)\n" + re.escape(fence), body, re.DOTALL)
        if m: content = m.group(1)
    if not name or not content:
        print("解析失败: 缺少名称或代码内容")
        sys.exit(1)
    return {"name": name, "type": typ or "py", "ver": ver or "1.0",
            "note": note, "author": author, "content": content, "issue": num}

def approve(meta):
    name = meta["name"]
    # 写入 scripts/<name>/index.json
    dirpath = f"scripts/{name}"
    os.makedirs(dirpath, exist_ok=True)
    with open(f"{dirpath}/index.json", "w", encoding="utf-8") as f:
        json.dump({"name": name, "type": meta["type"], "ver": meta["ver"],
                   "note": meta["note"], "author": meta["author"],
                   "content": meta["content"]}, f, ensure_ascii=False, indent=2)
    # 更新 index.json
    with open("index.json", "r", encoding="utf-8") as f:
        idx = json.load(f)
    scripts = idx.get("scripts", [])
    # 覆盖同名的旧条目
    scripts = [s for s in scripts if s.get("name") != name]
    scripts.append({"name": name, "type": meta["type"], "ver": meta["ver"],
                    "note": meta["note"], "author": meta["author"]})
    idx["scripts"] = scripts
    with open("index.json", "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    # git 提交推送
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "-c", f"user.name={REPO.split('/')[0]}",
                    "-c", f"user.email={REPO.split('/')[0]}@users.noreply.github.com",
                    "commit", "-m", f"approve script: {name} v{meta['ver']} (issue #{meta['issue']})"],
                   check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)
    # 在 Issue 上追加 [merged] 标记并关闭 (保留原始 body 以便 App 按 UID 识别)
    cur = gh("GET", f"/issues/{meta['issue']}")
    orig_body = cur.get("body", "")
    merged_body = orig_body + "\n\n[merged]\n\n已通过审核并上架。感谢贡献!"
    gh("PATCH", f"/issues/{meta['issue']}",
       {"state": "closed", "body": merged_body})
    print(f"✅ 已通过并上架: {name} v{meta['ver']} (Issue #{meta['issue']})")

def reject(num, reason=""):
    gh("PATCH", f"/issues/{num}",
       {"state": "closed", "body": f"未通过审核{(': ' + reason) if reason else ''}"})
    print(f"❌ 已驳回 Issue #{num}{': ' + reason if reason else ''}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    if not TOKEN:
        print("缺少 GH_TOKEN 环境变量"); sys.exit(1)
    num = int(sys.argv[1])
    mode = "--approve"
    reason = ""
    for a in sys.argv[2:]:
        if a == "--reject": mode = "--reject"
        elif a == "--approve": mode = "--approve"
        elif a.startswith("--reason"): reason = sys.argv[sys.argv.index(a)+1]
    if mode == "--reject":
        reject(num, reason)
    else:
        meta = parse_issue(num)
        approve(meta)
