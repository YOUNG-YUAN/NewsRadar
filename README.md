# 📡 NewsRadar (AI 新闻雷达) v2.2.0
**NewsRadar** 是一款基于 Python 开发的自动化情报聚合与 AI 分析工具。系统通过多线程监听全球主流媒体及科研期刊的 RSS 订阅源，利用大语言模型（LLMs）执行多维度情报提炼，并生成标准化的 Markdown/PDF 简报。

**v2.2.0 版本在异构多服务商并发架构的基础上，引入了革命性的“数据湖与时序自动化出版引擎”，实现了从“单次抓取工具”向“工业级情报管理底座”的跨代升级。**

---

## 🛠️ v2.2.0 核心更新说明 (Changelog)

### 1. 异构多服务商并发引擎 (Heterogeneous Multi-Provider Engine)

- **架构转型**：废弃单一 URL 的密钥池机制，升级为支持不同服务商、独立模型及不同 Base URL 的并发矩阵。
- **交互创新**：引入基于“推拉门”逻辑的单/多模式切换组件，支持 2*N 矩阵式服务节点管理。
- **状态闭环**：建立接口连通性验证系统，通过三色状态（白/绿/红）实时反馈各节点可用性，支持全局一键并行测试。

### 2. 个性化排版与实时预览系统 (Typography Engine)

- **WYSIWYG 渲染**：新增个性化排版弹窗，集成所见即所得（WYSIWYG）的渲染预览引擎。
- **缩放算法**：支持预览区域 0.5x - 3.0x 的动态缩放，确保高分辨率屏幕下的视觉一致性。
- **字体逻辑优化**：增强了对 TTF/TTC 字体的解析能力，支持粗体、斜体后缀的精准识别。

### 3. 极客级交互体验 (Geek-Level UX & Interaction)

- **三合一状态引擎**：将“暂停 / 恢复 / 中止”三大高频操作无缝融合至单一动态控件，大幅提升主界面的空间利用率与视觉平衡感。
- **长按防误触机制 (Long-Press Abort)**：独创“1秒触发 + 3秒读条”的物理级安全中止机制。长按按钮时将触发平滑的红色遮罩推移，并伴随像素级的文字反色截断（Text Masking）视觉特效。
- **工业级事件侦听**：采用系统绝对坐标系（Absolute Coordinates）追踪指针，彻底解决高分屏（DPI 缩放）下控件嵌套带来的事件穿透与边缘漏色问题，提供极致丝滑的阻尼手感。

### 4. 数据湖与时序自动化出版系统 (Data Lake & Automated Publishing)

- **增量拼装引擎 (Incremental Splicing)**：引入本地 JSON 数据湖作为中间态存储，按发布日期自动归槽新截获的情报。实现“只发新数据给 AI”，将 Token 消耗降至最低的同时，保证了排版的 100% 统一无痕。
- **全自动周期简报 (Periodic Reports)**：内置智能时序状态机。系统将在每周一 16:00 之后自动聚合生成上周《周报》，每月 5 日 08:00 之后自动聚合生成上月《月报》。
- **超时补签预警 (Red Alert)**：当历史报告发生“时光倒流”式的漏抓数据追加时，系统将拦截并在日志区触发动态加粗红字警报，同时静默级联重绘所有受影响的日报、周报与月报。

### 5. 模块化重构与性能优化

- **核心解耦**：将 `pipelines.py` 与 `dialogs.py` 拆解为 `exporter.py`、`dialog_sys.py`、`dialog_ai.py` 等独立模块，提升代码可维护性。
- **高密度 UI**：重新校准控件间距与容器约束，实现 750x620 的高密度紧凑布局，解决小分辨率屏幕下的组件溢出问题。

---

## ✨ 核心特性 (Features)

- **全协议兼容**：原生支持 Google Gemini, OpenAI, Anthropic, DeepSeek, 阿里云通义千问及本地化部署的 Ollama。
- **物理代理隔离**：实现 RSS 抓取层与 AI 调用层的网络代理彻底解绑。
- **容错鲁棒性**：植入工业级 3-Retry 机制，覆盖网络请求、JSON 解析及文件 I/O 环节。
- **分发合规性**：遵循开源版权规范，通过 `.gitignore` 排除商业字体，提供占位符式引导配置。

---

## 🚀 安装与配置 (Installation)

### 1. 准备环境
建议使用虚拟环境运行：

```bash
# 克隆仓库
git clone [https://github.com/YourUsername/NewsRadar.git](https://github.com/YourUsername/NewsRadar.git)
cd NewsRadar

# 安装依赖
pip install -r requirements.txt

```

### 2. 字体配置 (重要)
出于版权保护原因，本仓库不附带任何商业字体。

1. 进入项目根目录下的 `fonts/` 文件夹。
2. 请自行从 Windows 系统或其他合法渠道拷贝所需字体文件（如 `msyh.ttc`, `consola.ttf` 等）至该目录。
3. 程序启动后，在 **[个性化]** 设置中即可识别并启用。

### 3. 启动程序

```bash
python main.py

```

---

## 📋 依赖列表 (Requirements)

- `customtkinter==5.2.2` (GUI 框架)
- `requests==2.33.1` (网络请求)
- `feedparser==6.0.12` (RSS 解析)
- `beautifulsoup4==4.14.3` (HTML 处理)
- `openai==2.33.0` (AI 接口)
- `google-generativeai==0.8.6` (Gemini 接口)
- `Markdown==3.10.2` (报告转换)

---

## 📦 打包指南 (Distribution)
项目提供 `build.bat` 脚本，支持在 Windows 环境下一键编译为独立 EXE 程序。

- 打包过程会自动清理构建缓存。
- 脚本会物理创建 `fonts/` 外部资源目录并同步占位符文件，确保分发包结构完整。

---

## 📄 许可证 (License)
本项目基于 **MIT License** 开源。使用商业字体时请务必遵守相关厂商的最终用户许可协议（EULA）。

---

## 🙏 致谢 (Acknowledgments)

- 感谢 **CustomTkinter** 提供的现代化 UI 架构。
- 感谢 **feedparser** 在 RSS 协议解析方面的支持。

---