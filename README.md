# 宝妈创作工作台

一个为 02 年早婚宝妈赛道定制的移动端创作工作台，单文件网页 + GitHub Actions 自动化。

## 功能模块

| 模块 | 说明 |
|------|------|
| 📋 每日计划 | 进度条 + 可勾选清单，按天存储 |
| 💡 选题每日灵感 | 每天 10 条 AI 生成选题，一键跳抖音/B站 |
| 🔥 爆款热点二创 | 每日热点 + 贴合赛道的改编角度 |
| 📊 内容复盘 | 播放/点赞/评论/转发数据 + 亮点/问题/优化 |
| 📝 备忘录 | 默认 5 行，可勾选可加行 |
| 🔢 速算练习 | 粘贴微信文章链接自动抓取正文 |
| 📚 申论积累 | 粘贴微信文章链接自动抓取正文 |

## 快速开始

### 1. 部署网页（GitHub Pages）

```bash
# 在 GitHub 创建仓库 creator-desk 后
git init
git add .
git commit -m "初始化创作工作台"
git branch -M main
git remote add origin https://github.com/你的用户名/creator-desk.git
git push -u origin main
```

然后在仓库 **Settings → Pages → Source** 选择 `main` 分支，保存后 1-2 分钟会得到：
`https://你的用户名.github.io/creator-desk/`

### 2. 配置自动化密钥

在仓库 **Settings → Secrets and variables → Actions** 添加以下 Secrets：

| Secret 名 | 说明 | 示例 |
|-----------|------|------|
| `GH_TOKEN` | GitHub Token（需 gist 权限） | `ghp_xxxxxxxx` |
| `GIST_ID` | 首次运行后从日志获取，先留空 | （自动创建） |
| `AI_API_KEY` | AI 服务密钥（推荐 DeepSeek） | `sk-xxxxxx` |
| `AI_BASE_URL` | AI 接口地址 | `https://api.deepseek.com` |
| `AI_MODEL` | 模型名 | `deepseek-chat` |
| `TRACK_KEYWORDS` | 赛道关键词（竖线分隔） | `02年早婚宝妈日常\|新手育儿经验\|...` |
| `WECHAT_ACCOUNTS` | 公众号名（竖线分隔） | `C妈养育\|大J小D\|少女心诊所\|...` |

### 3. 首次运行获取 GIST_ID

在仓库 **Actions** 页面找到「每日采集任务」→ 点击 **Run workflow** 手动触发一次。

运行完成后在日志里会看到：
```
✅ Gist 创建成功!
GIST_ID = abc123xxxx
```

把这个 ID 填回 `GIST_ID` Secret，并填到 `index.html` 的 `CONFIG.gistId` 字段。

### 4. 配置网页读取 Gist

编辑 `index.html`，找到：
```javascript
const CONFIG = {
  gistId: '',  // ← 填入你的 GIST_ID
```

填入后重新 push 即可。

## 文件结构

```
creator-desk/
├── index.html                      # 网页主体（七个模块）
├── daily_fetch.py                  # 每日采集+AI改写脚本
├── .github/workflows/daily-fetch.yml  # 定时任务配置
└── README.md                       # 本文档
```

## 定时任务

每天自动运行 3 次（北京时间）：
- **08:00** - 早间选题
- **14:00** - 午间补充
- **20:00** - 晚间热点

也可在 Actions 页面手动触发。

## 数据存储

- 网页数据：浏览器 localStorage（按设备存储）
- 每日数据：GitHub Gist（公开，可跨设备同步）
- 本地备份：Actions 运行日志（保留 30 天）

## 关于微信文章采集

公众号没有官方 API，采集策略：
1. **搜狗微信搜索**（脚本内置，但易被反爬）
2. **手动粘贴链接**（网页支持，最稳定）
3. **RSS 镜像**（预留接口，接 WeRSS 后可填）

建议重要文章用手动粘贴方式。

## 技术栈

- 前端：原生 HTML/CSS/JS，无依赖，单文件
- 自动化：Python + GitHub Actions
- AI：DeepSeek / OpenAI 兼容接口
- 数据：GitHub Gist + localStorage

## 常见问题

**Q: 网页打不开？**
A: 检查 GitHub Pages 是否开启，仓库是否公开。

**Q: 刷新按钮没数据？**
A: 检查 `gistId` 是否填对，Gist 是否公开。

**Q: 定时任务没跑？**
A: GitHub Actions 的 cron 可能有 5-15 分钟延迟，属于正常现象。

**Q: 抖音/B站按钮没唤起 App？**
A: 手机浏览器需允许弹窗，会先尝试唤起 App，1.5 秒未跳转则打开网页版。
