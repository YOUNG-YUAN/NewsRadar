# 📡 NewsRadar (AI 新闻雷达) v1.0.0

![Python Version](assets/img-001.svg)
![License](assets/img-002.svg)
![Platform](assets/img-003.svg)
![GUI](assets/img-004.svg)
![AI Models](assets/img-005.svg)

**NewsRadar (AI 新闻雷达)** 是一款基于 Python 和 CustomTkinter 开发的现代化桌面端自动化情报聚合工具。
它能够全天候、多线程地监听全球主流外媒与科研期刊的 RSS 源，截获最新资讯，并利用目前最先进的 AI 大语言模型（LLMs）对海量外文新闻进行智能翻译、分类、提炼和总结，最终自动生成排版精美的 Markdown 情报简报。

无论你是密切关注地缘政治的分析师、追踪科技巨头动态的极客，还是需要每日获取顶刊论文摘要的科研工作者，NewsRadar 都能成为你最得力的私人情报官。

---

## ✨ 核心特性 (Core Features)

### 🤖 1. 全平台 AI 大模型矩阵支持
不再被单一服务商绑定！项目底层完全重构了 API 调用逻辑，动态兼容主流平台的原生接口与 OpenAI 格式接口。
* **支持云端模型**：Google Gemini (1.5 Pro/Flash), OpenAI (GPT-4o), Anthropic Claude 3, DeepSeek (V3/R1), 阿里云通义千问 (Qwen)。
* **支持本地部署**：完美兼容 **Ollama**，支持在断网或极度隐私环境下调用本地的 Qwen2.5, Llama3 等模型。
* **深度思考优化**：针对 `DeepSeek-R1` 等推理模型，代码层面对 `reasoning_effort` 做了专属适配，可完美处理带有 `<think>` 思维链的返回结果。

### ⚡ 2. 高性能“获取-分析”双引擎架构
* **流水线分离**：采用生产者-消费者模型，`FetcherThread`（爬虫抓取）与 `AnalyzerThread`（AI 分析）完全解耦，利用线程池（ThreadPoolExecutor）并发处理数据，绝不阻塞主 UI 界面。
* **响应式暂停/恢复**：引入了极低延迟的挂起拦截器，点击“暂停”按钮可瞬间挂起所有后台轮询，并在恢复时自动执行**时间补偿算法**，确保运行时长统计严丝合缝。

### 🛡️ 3. 工业级 3-Retry 容错机制
网络波动是自动化的天敌。NewsRadar 在三个最容易崩溃的环节植入了严格的 `for attempt in range(1, 4)` 三次重试机制：
* **RSS 抓取层**：遇到墙外订阅源 DNS 污染或连接超时，自动等待并重试，最高容忍 3 次彻底断连。
* **AI 解析层**：遇到 API 频率限制 (Rate Limit) 或大模型未按严格 JSON 格式输出时，自动拦截报错并重新发起生成请求。
* **I/O 读写层**：写入最终 Markdown 报告时，如遇系统文件夹权限锁死或杀毒软件占用，会延时排队写入，确保数据绝不丢失。

### 🔒 4. 物理隔离的“双轨制”网络代理设置
由于 RSS 源（往往需要翻墙）与 AI 接口（有时需要直连或使用特定节点）的网络环境大不相同，程序实现了**代理的彻底解绑**：
* **AI 代理**：基于 `os.environ` 挂载，专门为大模型 API 服务。
* **RSS 代理**：基于 `requests` 的 `proxies` 字典进行底层流量路由，绝不污染全局环境变量。

### 🎨 5. 现代化交互体验 (UX)
* 基于 **CustomTkinter** 构建的深色/浅色自适应界面。
* **密码保护与试探**：API Key 输入框加入了 👁️/🔒 动态视觉遮盖逻辑，焦点移开时固定显示 20 个黑点，防止旁人偷窥长度。
* **实时监控**：提供极具极客感的实时命令行日志（Queue 线程安全）、运行耗时统计以及 Token 消耗计数器。

---

## 🌍 内置全球信息源矩阵 (Built-in Sources)

程序默认内置了经过精细归类的高质量 RSS 订阅源（超过 120 个节点），支持在界面中“一键全选”或自定义增删：
* **国际顶级综合大报**：BBC News (全矩阵), 纽约时报 (NYT), 华尔街日报 (WSJ), 金融时报 (FT), 卫报 (The Guardian), 半岛电视台 (Al Jazeera), 南华早报 (SCMP)。
* **商业与金融**：彭博社 (Bloomberg), ProPublica 深度调查。
* **科技与前沿风投**：TechCrunch, Wired, The Verge, Ars Technica。
* **科研与学术顶刊**：Nature (自然), Cell Press (细胞), Science News, MIT Tech Review, IEEE Spectrum。
* **中国官方与外宣**：人民网国际版 (People's Daily), CGTN 全矩阵。

> 💡 **分析引擎大类**：AI 会自动将杂乱的新闻精准归入：中国、美国、亚洲、欧洲、科技、商业金融、AI与机器人、科学、健康、能源气候 等 16 个标准化栏目。

---

## 🛠️ 安装与运行 (Installation & Usage)

### 选项 A：使用打包好的可执行文件 (仅限 Windows)
如果您不想配置 Python 环境，可以直接在 GitHub 的 [Releases](../../releases) 页面下载最新版的 `NewsRadar_v1.0.0.zip`。
1. 解压到任意文件夹。
2. 双击运行 `NewsRadar.exe` 即可（程序完全绿色，配置文件保存在同级 `data` 目录下）。

### 选项 B：从源码运行 (Windows / macOS / Linux)

**1. 克隆仓库**
```bash
git clone [https://github.com/YourUsername/NewsRadar.git](https://github.com/YourUsername/NewsRadar.git)
cd NewsRadar

```
**2. 安装依赖**
建议使用 Python 3.8 或更高版本。推荐创建虚拟环境后执行：

```bash
pip install -r requirements.txt

```
*(注：requirements.txt 应包含：requests, feedparser, beautifulsoup4, google-generativeai, openai, customtkinter, python-dateutil)*
**3. 启动程序**

```bash
python main.py

```

---

## 📖 使用指南 (Quick Start)

1. **配置 AI 模型**：
  - 点击主界面上的 **[AI模型选择]**。
  - 从下拉菜单中选择你的服务商（如 DeepSeek 或 OpenAI）。
  - 填入你的 `API Key`（支持点击 👁️ 图标查看或编辑）。
  - （可选）如果你使用的 API 需要翻墙，请开启底部的**网络代理**并配置端口。
  - 点击 **[连接测试]**，如果显示绿色的 `✅ 成功!`，点击保存即可。
2. **配置监听源与频率**：
  - 点击主界面上的 **[监听设置]**。
  - 勾选你感兴趣的媒体平台。
  - 在右上角设置**监听频率**（如设为 `1h`，则每次拉取只获取各平台过去 1 小时内发布的新闻；如果打开“RSS下所有新闻”开关，则进行全量回溯）。
  - （关键）如果某些外媒 RSS 需要翻墙才能访问，请点击上方的 **[网络代理]** 按钮，单独为 RSS 爬虫开启代理。
3. **开始截获情报**：
  - 回到主界面，点击绿色的 **[开始获取]** 按钮。
  - 此时雷达正式启动，你可以在日志框中实时看到抓取、分包、AI 解析的进度。
  - 任务完成后，前往你设置的**保存位置**，即可查阅由 AI 精心排版、带有中英对照和重点摘要的 `.md` 简报文件。

---

## 📦 开发者说明与打包打包指导
项目根目录提供了一个写好的 `build_exe.bat` 脚本，用于在 Windows 下快速将 Python 源码编译为独立的 EXE 桌面程序。
**打包要求：**

1. 请确保你在虚拟环境中安装了 `pyinstaller`。
2. 确保项目根目录下存在 `icon.ico` 图标文件。
3. 运行 `build_exe.bat`。脚本会自动使用 `--add-data` 挂载图标，并收集 customtkinter 的依赖。最终生成的程序将位于 `dist/NewsRadar` 文件夹中。

### 常见问题排查 (Troubleshooting)

- **Q: 测试 API 时提示 401 Unauthorized 报错？**
  - **A:** 请检查 API Key 是否复制完整（前后是否有不可见的空格）。同时，请注意在下拉菜单选择正确的服务商，不要在“云端 Gemini”下填入“DeepSeek”的密钥，这会导致认证协议不匹配。
- **Q: 日志提示抓取源失败，一直 Retry？**
  - **A:** RSS 源地址可能被防火墙屏蔽。请进入 `[监听设置] -> [网络代理]`，确保开启了代理并填入了正确的代理软件本地端口（如 v2ray/clash 默认通常是 10808 或 7890）。
- **Q: 我自己打包的 EXE，修改了 icon.ico 为什么图标还是默认的或者没变化？**
  - **A:** 这是 Windows 的系统图标缓存机制导致的，清除系统系统图标缓存即可。

---

## 🤝 参与贡献 (Contributing)
非常欢迎任何形式的贡献！无论你是想添加新的 RSS 新闻源、优化大模型的 Prompt 提示词，还是改进 UI，都可以通过提交 Pull Request (PR) 或开启一个 Issue 来参与。

1. Fork 本仓库。
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)。
3. 提交您的修改 (`git commit -m 'Add some AmazingFeature'`)。
4. 推送到分支 (`git push origin feature/AmazingFeature`)。
5. 开启一个 Pull Request。

---

## 📄 许可证 (License)
本项目基于 MIT License 开源。您可以自由地使用、修改和分发本项目的代码，但请保留原作者的版权声明。

---

## 🙏 致谢 (Acknowledgments)

- 感谢 CustomTkinter 提供优雅的现代 UI 框架。
- 感谢 feedparser 为 RSS 解析提供的强大支持。
- 感谢各大新闻媒体与科研机构提供的开放 RSS 订阅服务。

```

### 给你的后续建议（发布 GitHub 前的准备）：
1. **替换仓库链接**：将文档中的 `https://github.com/YourUsername/NewsRadar.git` 替换成你实际的 GitHub URL。
2. **准备一张截图**：强烈建议你在 README 中插入 1-2 张程序的实际运行截图。你可以将软件跑起来，截个图命名为 `screenshot.png` 放在项目里，然后在 README 的开头加入代码 `![软件截图](screenshot.png)`，这会让你的仓库吸引力暴增。
3. **准备 requirements.txt**：在项目根目录下建一个 `requirements.txt` 文件，里面写上：
   ```text
   requests
   feedparser
   beautifulsoup4
   google-generativeai
   openai
   customtkinter
   python-dateutil

```

1. **提交代码**：通过 git init -> add -> commit -> push 就可以大功告成啦！
祝你的开源项目大受欢迎，收获满满的 Star！如果后续还有需要迭代新功能，随时找我！

---

*Exported from [Voyager](https://github.com/Nagi-ovo/gemini-voyager)*  
*Generated on May 8, 2026 at 02:03 AM*