# 东华倪家 — 家庭门户网站 运营手册

## 🌐 域名信息

| 项目 | 详情 |
|------|------|
| 域名 | `donghuani.xyz` |
| 注册商 | 阿里云（万网） |
| DNS 管理 | Cloudflare（免费计划） |
| Cloudflare 账号 | `535929481@qq.com` |

---

## 🚀 日常使用

### 启动网站

双击 `family-portal/start.bat`，自动完成：
1. 启动 Cloudflare Tunnel
2. 获取公网 URL
3. 启动 Flask 服务器

启动后会显示：
```
[OK] Tunnel: https://xxx.trycloudflare.com
  Local:   http://localhost:5000
  Domain:  https://donghuani.xyz
```

### 停止网站

按 `Ctrl+C` 即可。

---

## 🔄 Tunnel URL 变更处理

**什么时候会变：** 电脑重启、手动停止 Tunnel、网络断开重连

**变更后操作（1 分钟）：**

1. 打开 [Cloudflare 后台](https://dash.cloudflare.com)
2. 选择 `donghuani.xyz`
3. 左侧 → **规则** → **页面规则**
4. 编辑唯一的那条规则
5. 把目标 URL 改成新的 `https://新地址.trycloudflare.com/$1`
6. 保存

启动脚本会显示当前 URL，直接复制即可。

---

## 📋 网站功能

### 任务看板（首页）
- 发布任务：填写标题 + 描述 → 发布
- 认领任务：点击「我来做」
- 完成任务：点击「完成」
- 删除任务：点击垃圾桶图标

### 劳动统计（统计页）
- 总任务数 / 已完成 / 进行中
- 家庭贡献排行榜
- 积分规则：完成 10 分 + 发布 3 分

### 成员管理
- 右上角头像切换身份
- 下拉菜单添加新成员

---

## 🗂️ 文件结构

```
家庭项目/
├── .gitignore           # Git 忽略规则
├── README.md            # 本文件
└── family-portal/
    ├── start.bat         # 启动脚本（双击运行）
    ├── start.py          # 自动启动逻辑
    ├── server.py         # Flask 后端
    ├── requirements.txt  # Python 依赖
    ├── .cftoken          # Cloudflare API Token（不要泄露）
    ├── cloudflared.exe   # Cloudflare Tunnel 客户端
    ├── Dockerfile        # Docker 部署配置
    ├── fly.toml          # Fly.io 配置（备用）
    ├── render.yaml       # Render.com 配置（备用）
    ├── data/             # 数据库和密钥（不要提交到 Git）
    │   ├── family.db     # SQLite 数据库
    │   └── .secret_key   # Session 加密密钥
    ├── uploads/          # 上传文件（已废弃）
    └── public/           # 前端文件
        ├── index.html    # 任务看板
        ├── stats.html    # 统计页面
        ├── login.html    # 登录页面
        ├── app.js        # 前端公共逻辑
        └── style.css     # 样式表
```

---

## 🔑 重要凭据

| 凭据 | 位置 | 用途 |
|------|------|------|
| Cloudflare API Token | `family-portal/.cftoken` | 域名自动更新 |
| 网站管理员密码 | 数据库 `family_users` 表 | 登录网站 |
| Session 密钥 | `data/.secret_key` | 用户登录状态 |

> ⚠️ 以上文件已加入 `.gitignore`，不会被提交到 GitHub。

---

## 🛠️ 故障排查

| 问题 | 解决方案 |
|------|----------|
| 网站打不开 | 检查电脑是否开机、是否运行 `start.bat` |
| 域名无法访问 | 检查 Tunnel URL 是否变了，更新 Page Rule |
| 页面加载空白 | 刷新浏览器，重新选择成员身份 |
| 任务数据不显示 | 重新选择成员身份（右上角） |
| Tunnel 启动失败 | 检查网络连接，重试 `start.bat` |

---

## 📦 备份建议

定期备份数据库文件：
```
family-portal/data/family.db
```

复制到安全位置即可，包含所有任务和成员数据。

---

## 🔄 Git 仓库

- 地址：`https://github.com/Neehou/-`
- 分支：`master`
- 推送代码：`git push origin master`

> 注意：数据库、密钥、Token 不会上传到 GitHub。

---

## 📝 更新日志

- 2026-06-17：域名 `donghuani.xyz` 绑定、修复数据加载 Bug、删除照片功能、绿色主题、自动启动脚本
- 2026-06-16：项目初始化
