import os
import json
import sys

# ==========================================
# 📂 动态挂载运行路径
# ==========================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, 'data')
RAW_DIR = os.path.join(DATA_DIR, 'raw_news')
FAILED_DIR = os.path.join(DATA_DIR, 'failed_news')
RESULTS_DIR = os.path.join(BASE_DIR, 'results')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
FONTS_DIR = os.path.join(BASE_DIR, 'fonts')
# 🌟 新增：数据湖目录，存放每日抓取的 JSON 原始数据
DB_DIR = os.path.join(DATA_DIR, 'database')

# 自动创建所有必要的物理目录
for d in [DATA_DIR, RAW_DIR, FAILED_DIR, RESULTS_DIR, LOGS_DIR, FONTS_DIR, DB_DIR]:
    os.makedirs(d, exist_ok=True)

CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')
SOURCES_FILE = os.path.join(DATA_DIR, 'sources.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')

VERSION = "v2.2.3" 

# ==========================================
# ⚙️ 默认初始配置
# ==========================================
DEFAULT_CONFIG = {
    "save_path": RESULTS_DIR,
    "ai_provider": "Google Gemini", 
    "providers": {
        "Google Gemini": {"url": "https://generativelanguage.googleapis.com/v1beta/models/", "model": "gemini-1.5-flash", "api_key": ""},
        "OpenAI": {"url": "https://api.openai.com/v1", "model": "gpt-4o-mini", "api_key": ""},
        "Claude": {"url": "https://api.anthropic.com/v1/messages", "model": "claude-3-haiku-20240307", "api_key": ""},
        "DeepSeek": {"url": "https://api.deepseek.com", "model": "deepseek-chat", "api_key": ""},
        "Qwen (通义千问)": {"url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus", "api_key": ""},
        "Local Ollama": {"url": "http://localhost:11434/v1", "model": "qwen2.5:7b", "api_key": "ollama"}
    },
    
    "is_multi_mode": False,
    "multi_apis": [],
    
    "listen_freq": "12h", 
    "total_tokens": 0,
    "ai_use_proxy": False,
    "ai_proxy_server": "http://127.0.0.1",
    "ai_proxy_port": "10808",
    "rss_use_proxy": False,
    "rss_proxy_server": "http://127.0.0.1",
    "rss_proxy_port": "10808",
    "fetch_all": False,
    
    "batch_size": "30",
    "user_prompt": "",
    
    "export_md": True,
    "export_pdf": True,
    
    # 🌟 新增：周报与月报自动生成开关
    "enable_weekly": True,
    "enable_monthly": True,

    "language": "zh", # 底层保留语言接口，默认中文

    # 🌟 预留字体接口：默认为空，程序运行时将自动回退至系统默认黑体
    # 用户可以在 fonts/ 文件夹放入 ttf 文件并在 config.json 中指定文件名
    "font_header": "msyhbd.ttc",              # 大标题与栏目：微软雅黑粗体
    "font_article": "msyhl.ttc",              # 新闻标题：鸿蒙黑体
    "font_body": "msyhl.ttc",                 # 情报摘要正文：华文中宋
    "font_keywords": "msyhbd.ttc",             # 🌟 关键词专用字体 (推荐使用微软雅黑粗体)
    "font_accent": "consola.ttf",             # 元数据、时间、链接、关键词：Consolas等宽
}

# 🌟 全球新闻订阅源配置矩阵
DEFAULT_SOURCES = [
    # === 🏛️ 英国广播公司 (BBC News) 全矩阵 (23个频道) ===
    {"checked": True, "name": "BBC - Top Stories",      "url": "http://feeds.bbci.co.uk/news/rss.xml",                    "note": "BBC/头条精华"},
    {"checked": True, "name": "BBC - World",            "url": "http://feeds.bbci.co.uk/news/world/rss.xml",              "note": "BBC/国际综合"},
    {"checked": True, "name": "BBC - Africa",           "url": "http://feeds.bbci.co.uk/news/world/africa/rss.xml",       "note": "BBC/非洲地区"},
    {"checked": True, "name": "BBC - Asia",             "url": "http://feeds.bbci.co.uk/news/world/asia/rss.xml",         "note": "BBC/亚洲地区"},
    {"checked": True, "name": "BBC - Europe",           "url": "http://feeds.bbci.co.uk/news/world/europe/rss.xml",       "note": "BBC/欧洲地区"},
    {"checked": True, "name": "BBC - Latin America",    "url": "http://feeds.bbci.co.uk/news/world/latin_america/rss.xml","note": "BBC/拉丁美洲"},
    {"checked": True, "name": "BBC - Middle East",      "url": "http://feeds.bbci.co.uk/news/world/middle_east/rss.xml",  "note": "BBC/中东地区"},
    {"checked": True, "name": "BBC - US & Canada",      "url": "http://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml","note": "BBC/美国与加拿大"},
    {"checked": True, "name": "BBC - UK",               "url": "http://feeds.bbci.co.uk/news/uk/rss.xml",                 "note": "BBC/英国国内"},
    {"checked": True, "name": "BBC - England",          "url": "http://feeds.bbci.co.uk/news/england/rss.xml",            "note": "BBC/英格兰"},
    {"checked": True, "name": "BBC - Northern Ireland", "url": "http://feeds.bbci.co.uk/news/northern_ireland/rss.xml",   "note": "BBC/北爱尔兰"},
    {"checked": True, "name": "BBC - Scotland",         "url": "http://feeds.bbci.co.uk/news/scotland/rss.xml",           "note": "BBC/苏格兰"},
    {"checked": True, "name": "BBC - Wales",            "url": "http://feeds.bbci.co.uk/news/wales/rss.xml",              "note": "BBC/威尔士"},
    {"checked": True, "name": "BBC - Business",         "url": "http://feeds.bbci.co.uk/news/business/rss.xml",           "note": "BBC/商业财经"},
    {"checked": True, "name": "BBC - Politics",         "url": "http://feeds.bbci.co.uk/news/politics/rss.xml",           "note": "BBC/政治"},
    {"checked": True, "name": "BBC - Health",           "url": "http://feeds.bbci.co.uk/news/health/rss.xml",             "note": "BBC/健康"},
    {"checked": True, "name": "BBC - Education",        "url": "http://feeds.bbci.co.uk/news/education/rss.xml",          "note": "BBC/教育与家庭"},
    {"checked": True, "name": "BBC - Science & Env",    "url": "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml","note": "BBC/科学与环境"},
    {"checked": True, "name": "BBC - Technology",       "url": "http://feeds.bbci.co.uk/news/technology/rss.xml",         "note": "BBC/科技"},
    {"checked": True, "name": "BBC - Arts",             "url": "http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml","note": "BBC/娱乐与艺术"},
    {"checked": True, "name": "BBC - Magazine",         "url": "http://feeds.bbci.co.uk/news/magazine/rss.xml",           "note": "BBC/深度杂志"},

    # === 🏛️ 纽约时报 (NYT) 全矩阵 (30个频道) ===
    {"checked": True, "name": "NYT - Home Page",      "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",      "note": "纽约时报/主页精华"},
    {"checked": True, "name": "NYT - World",          "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",          "note": "纽约时报/国际综合"},
    {"checked": True, "name": "NYT - Africa",         "url": "https://rss.nytimes.com/services/xml/rss/nyt/Africa.xml",         "note": "纽约时报/非洲地区"},
    {"checked": True, "name": "NYT - Americas",       "url": "https://rss.nytimes.com/services/xml/rss/nyt/Americas.xml",       "note": "纽约时报/美洲地区"},
    {"checked": True, "name": "NYT - Asia Pacific",   "url": "https://rss.nytimes.com/services/xml/rss/nyt/AsiaPacific.xml",    "note": "纽约时报/亚太地区"},
    {"checked": True, "name": "NYT - Europe",         "url": "https://rss.nytimes.com/services/xml/rss/nyt/Europe.xml",         "note": "纽约时报/欧洲地区"},
    {"checked": True, "name": "NYT - Middle East",    "url": "https://rss.nytimes.com/services/xml/rss/nyt/MiddleEast.xml",     "note": "纽约时报/中东地区"},
    {"checked": True, "name": "NYT - U.S.",           "url": "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",             "note": "纽约时报/美国国内"},
    {"checked": True, "name": "NYT - Education",      "url": "https://rss.nytimes.com/services/xml/rss/nyt/Education.xml",      "note": "纽约时报/教育"},
    {"checked": True, "name": "NYT - Politics",       "url": "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",       "note": "纽约时报/政治"},
    {"checked": True, "name": "NYT - The Upshot",     "url": "https://rss.nytimes.com/services/xml/rss/nyt/Upshot.xml",         "note": "纽约时报/数据新闻与分析"},
    {"checked": True, "name": "NYT - NY Region",      "url": "https://rss.nytimes.com/services/xml/rss/nyt/NYRegion.xml",       "note": "纽约时报/纽约本地"},
    {"checked": True, "name": "NYT - Business",       "url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",       "note": "纽约时报/商业"},
    {"checked": True, "name": "NYT - Energy & Env",   "url": "https://rss.nytimes.com/services/xml/rss/nyt/EnergyEnvironment.xml","note": "纽约时报/能源与环境"},
    {"checked": True, "name": "NYT - Small Business", "url": "https://rss.nytimes.com/services/xml/rss/nyt/SmallBusiness.xml",  "note": "纽约时报/小微企业"},
    {"checked": True, "name": "NYT - Economy",        "url": "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml",        "note": "纽约时报/宏观经济"},
    {"checked": True, "name": "NYT - DealBook",       "url": "https://rss.nytimes.com/services/xml/rss/nyt/Dealbook.xml",       "note": "纽约时报/交易与并购(专栏)"},
    {"checked": True, "name": "NYT - Media & Adv",    "url": "https://rss.nytimes.com/services/xml/rss/nyt/MediaandAdvertising.xml","note": "纽约时报/传媒与广告"},
    {"checked": True, "name": "NYT - Your Money",     "url": "https://rss.nytimes.com/services/xml/rss/nyt/YourMoney.xml",      "note": "纽约时报/个人理财"},
    {"checked": True, "name": "NYT - Technology",     "url": "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",     "note": "纽约时报/科技"},
    {"checked": True, "name": "NYT - Personal Tech",  "url": "https://rss.nytimes.com/services/xml/rss/nyt/PersonalTech.xml",   "note": "纽约时报/个人数码科技"},
    {"checked": True, "name": "NYT - Sports",         "url": "https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml",         "note": "纽约时报/体育综合"},
    {"checked": True, "name": "NYT - Science",        "url": "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",        "note": "纽约时报/科学"},
    {"checked": True, "name": "NYT - Space",          "url": "https://rss.nytimes.com/services/xml/rss/nyt/Space.xml",          "note": "纽约时报/太空与天文"},
    {"checked": True, "name": "NYT - Health",         "url": "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml",         "note": "纽约时报/健康与医疗"},
    {"checked": True, "name": "NYT - Climate",        "url": "https://rss.nytimes.com/services/xml/rss/nyt/Climate.xml",        "note": "纽约时报/气候危机"},
    {"checked": True, "name": "NYT - Arts",           "url": "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml",           "note": "纽约时报/文化艺术"},
    {"checked": True, "name": "NYT - Fashion & Style","url": "https://rss.nytimes.com/services/xml/rss/nyt/FashionandStyle.xml","note": "纽约时报/时尚与风格"},
    {"checked": True, "name": "NYT - Travel",         "url": "https://www.nytimes.com/services/xml/rss/nyt/Travel.xml",         "note": "纽约时报/旅行"},
    {"checked": True, "name": "NYT - Sunday Opinion", "url": "https://rss.nytimes.com/services/xml/rss/nyt/sunday-review.xml",  "note": "纽约时报/周日深度评论"},

    # === 🏛️ 华尔街日报 (WSJ) 全矩阵 (15个频道) ===
    {"checked": True, "name": "WSJ - World News",     "url": "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",       "note": "华尔街日报/国际新闻"},
    {"checked": True, "name": "WSJ - U.S.",           "url": "https://feeds.content.dowjones.io/public/rss/RSSUSnews",          "note": "华尔街日报/美国国内"},
    {"checked": True, "name": "WSJ - Politics",       "url": "https://feeds.content.dowjones.io/public/rss/socialpoliticsfeed", "note": "华尔街日报/政治新闻"},
    {"checked": True, "name": "WSJ - Economy",        "url": "https://feeds.content.dowjones.io/public/rss/socialeconomyfeed",  "note": "华尔街日报/宏观经济"},
    {"checked": True, "name": "WSJ - U.S. Business",  "url": "https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness",   "note": "华尔街日报/美国商业"},
    {"checked": True, "name": "WSJ - Markets News",   "url": "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",     "note": "华尔街日报/市场与金融"},
    {"checked": True, "name": "WSJ - Technology",     "url": "https://feeds.content.dowjones.io/public/rss/RSSWSJD",            "note": "华尔街日报/科技动态"},
    {"checked": True, "name": "WSJ - Real Estate",    "url": "https://feeds.content.dowjones.io/public/rss/latestnewsrealestate","note": "华尔街日报/房地产"},
    {"checked": True, "name": "WSJ - Pers. Finance",  "url": "https://feeds.content.dowjones.io/public/rss/RSSPersonalFinance", "note": "华尔街日报/个人理财"},
    {"checked": True, "name": "WSJ - Opinion",        "url": "https://feeds.content.dowjones.io/public/rss/RSSOpinion",         "note": "华尔街日报/观点与专栏"},
    {"checked": True, "name": "WSJ - Lifestyle",      "url": "https://feeds.content.dowjones.io/public/rss/RSSLifestyle",       "note": "华尔街日报/生活"},
    {"checked": True, "name": "WSJ - Arts",           "url": "https://feeds.content.dowjones.io/public/rss/RSSArtsCulture",     "note": "华尔街日报/文化艺术"},
    {"checked": True, "name": "WSJ - Style",          "url": "https://feeds.content.dowjones.io/public/rss/RSSStyle",           "note": "华尔街日报/时尚潮流"},
    {"checked": True, "name": "WSJ - Health",         "url": "https://feeds.content.dowjones.io/public/rss/socialhealth",       "note": "华尔街日报/医疗健康"},
    {"checked": True, "name": "WSJ - Sports",         "url": "https://feeds.content.dowjones.io/public/rss/rsssportsfeed",      "note": "华尔街日报/体育"},

    # === 📈 彭博社 (Bloomberg) 全矩阵 (15个频道) ===
    {"checked": True, "name": "Bloomberg - Markets",       "url": "https://feeds.bloomberg.com/markets/news.rss",       "note": "彭博社/全球市场与交易"},
    {"checked": True, "name": "Bloomberg - Economics",     "url": "https://feeds.bloomberg.com/economics/news.rss",     "note": "彭博社/宏观经济与央行"},
    {"checked": True, "name": "Bloomberg - Industries",    "url": "https://feeds.bloomberg.com/industries/news.rss",    "note": "彭博社/全球产业与供应链"},
    {"checked": True, "name": "Bloomberg - Technology",    "url": "https://feeds.bloomberg.com/technology/news.rss",    "note": "彭博社/科技与互联网"},
    {"checked": False,"name": "Bloomberg - AI",            "url": "https://feeds.bloomberg.com/ai/news.rss",            "note": "彭博社/人工智能前沿"},
    {"checked": True, "name": "Bloomberg - Politics",      "url": "https://feeds.bloomberg.com/politics/news.rss",      "note": "彭博社/全球政治与政策"},
    {"checked": True, "name": "Bloomberg - Green",         "url": "https://feeds.bloomberg.com/green/news.rss",         "note": "彭博社/气候与绿色经济"},
    {"checked": True, "name": "Bloomberg - Crypto",        "url": "https://feeds.bloomberg.com/crypto/news.rss",        "note": "彭博社/加密货币与区块链"},
    {"checked": True, "name": "Bloomberg - Wealth",        "url": "https://feeds.bloomberg.com/wealth/news.rss",        "note": "彭博社/全球财富与家族办公室"},
    {"checked": True, "name": "Bloomberg - Pursuits",      "url": "https://feeds.bloomberg.com/pursuits/news.rss",      "note": "彭博社/顶级奢侈品与生活方式"},
    {"checked": True, "name": "Bloomberg - Businessweek",  "url": "https://feeds.bloomberg.com/businessweek/news.rss",  "note": "彭博社/商业周刊深度报道"},
    {"checked": True, "name": "Bloomberg - CityLab",       "url": "https://feeds.bloomberg.com/citylab/news.rss",            "note": "彭博社/城市发展与建筑设计"},
    {"checked": False,"name": "Bloomberg - Sports",        "url": "https://feeds.bloomberg.com/business-of-sports/news.rss",  "note": "彭博社/体育商业"},
    {"checked": True, "name": "Bloomberg - Equality",      "url": "https://feeds.bloomberg.com/equality/news.rss",            "note": "彭博社/职场平等与多样性"},
    {"checked": False,"name": "Bloomberg - Management & Work", "url": "https://feeds.bloomberg.com/management-work/news.rss", "note": "彭博社/企业管理与职场"},

    # === 🏛️ 金融时报 (Financial Times) 全矩阵 (40个频道) ===
    # --- World (世界) ---
    {"checked": True, "name": "FT - World",                   "url": "https://www.ft.com/world?format=rss",                     "note": "金融时报/世界综合"},
    {"checked": True, "name": "FT - Middle East war",         "url": "https://www.ft.com/middle-east-war?format=rss",           "note": "金融时报/中东战争"},
    {"checked": True, "name": "FT - Global Economy",          "url": "https://www.ft.com/global-economy?format=rss",            "note": "金融时报/全球经济"},
    {"checked": True, "name": "FT - UK",                      "url": "https://www.ft.com/uk?format=rss",                        "note": "金融时报/英国"},
    {"checked": True, "name": "FT - US",                      "url": "https://www.ft.com/us?format=rss",                        "note": "金融时报/美国"},
    {"checked": True, "name": "FT - China",                   "url": "https://www.ft.com/china?format=rss",                     "note": "金融时报/中国"},
    {"checked": True, "name": "FT - Africa",                  "url": "https://www.ft.com/africa?format=rss",                    "note": "金融时报/非洲"},
    {"checked": True, "name": "FT - Asia Pacific",            "url": "https://www.ft.com/asia-pacific?format=rss",              "note": "金融时报/亚太地区"},
    {"checked": True, "name": "FT - Emerging Markets",        "url": "https://www.ft.com/emerging-markets?format=rss",          "note": "金融时报/新兴市场"},
    {"checked": True, "name": "FT - Europe",                  "url": "https://www.ft.com/europe?format=rss",                    "note": "金融时报/欧洲"},
    {"checked": True, "name": "FT - War in Ukraine",          "url": "https://www.ft.com/war-in-ukraine?format=rss",            "note": "金融时报/乌克兰战争"},
    {"checked": True, "name": "FT - Americas",                "url": "https://www.ft.com/americas?format=rss",                  "note": "金融时报/美洲"},
    {"checked": True, "name": "FT - Middle East & N Africa",  "url": "https://www.ft.com/middle-east-north-africa?format=rss",  "note": "金融时报/中东及北非"},
    {"checked": True, "name": "FT - Visual & Data Journalism","url": "https://www.ft.com/visual-and-data-journalism?format=rss","note": "金融时报/视觉与数据新闻"},
    {"checked": True, "name": "FT - Moral Money",             "url": "https://www.ft.com/moral-money?format=rss",               "note": "金融时报/ESG与道德投资"},
    {"checked": True, "name": "FT - Tech Asia",               "url": "https://www.ft.com/tech-asia?format=rss",                 "note": "金融时报/亚洲科技专栏"},
    {"checked": True, "name": "FT - Schools",                 "url": "https://www.ft.com/ft-schools?format=rss",                "note": "金融时报/教育与校园精选"},

    # --- US (美国子频道) ---
    {"checked": True, "name": "FT - US Economy",             "url": "https://www.ft.com/us-economy?format=rss",             "note": "金融时报/美国经济"},
    {"checked": True, "name": "FT - US Companies",           "url": "https://www.ft.com/us-companies?format=rss",           "note": "金融时报/美国企业"},
    {"checked": True, "name": "FT - US Politics & Policy",   "url": "https://www.ft.com/us-politics-policy?format=rss",     "note": "金融时报/美国政治与政策"},

    # --- Companies (公司) ---
    {"checked": True, "name": "FT - Companies",              "url": "https://www.ft.com/companies?format=rss",              "note": "金融时报/公司综合"},
    {"checked": True, "name": "FT - Energy",                 "url": "https://www.ft.com/energy?format=rss",                 "note": "金融时报/能源公司"},
    {"checked": True, "name": "FT - Financials",             "url": "https://www.ft.com/financials?format=rss",             "note": "金融时报/金融公司"},
    {"checked": True, "name": "FT - Health",                 "url": "https://www.ft.com/health?format=rss",                 "note": "金融时报/医疗健康公司"},
    {"checked": True, "name": "FT - Industrials",            "url": "https://www.ft.com/industrials?format=rss",            "note": "金融时报/工业公司"},
    {"checked": True, "name": "FT - Media",                  "url": "https://www.ft.com/media?format=rss",                  "note": "金融时报/传媒公司"},
    {"checked": True, "name": "FT - Prof. Services",         "url": "https://www.ft.com/professional-services?format=rss",  "note": "金融时报/专业服务公司"},
    {"checked": True, "name": "FT - Retail & Consumer",      "url": "https://www.ft.com/retail-consumer?format=rss",        "note": "金融时报/零售与消费公司"},
    {"checked": True, "name": "FT - Tech Sector",            "url": "https://www.ft.com/technology-sector?format=rss",      "note": "金融时报/科技板块"},
    {"checked": True, "name": "FT - Telecoms",               "url": "https://www.ft.com/telecoms?format=rss",               "note": "金融时报/电信公司"},
    {"checked": True, "name": "FT - Transport",              "url": "https://www.ft.com/transport?format=rss",              "note": "金融时报/交通运输公司"},

    # --- Tech (科技) ---
    {"checked": True, "name": "FT - Tech",                   "url": "https://www.ft.com/tech?format=rss",                   "note": "金融时报/科技综合"},
    {"checked": True, "name": "FT - AI",                     "url": "https://www.ft.com/artificial-intelligence?format=rss","note": "金融时报/人工智能"},
    {"checked": True, "name": "FT - Semiconductors",         "url": "https://www.ft.com/semiconductors?format=rss",         "note": "金融时报/半导体"},
    {"checked": True, "name": "FT - Cyber Security",         "url": "https://www.ft.com/cyber-security?format=rss",         "note": "金融时报/网络安全"},
    {"checked": True, "name": "FT - Social Media",           "url": "https://www.ft.com/social-media?format=rss",           "note": "金融时报/社交媒体"},

    # --- Markets (市场) ---
    {"checked": True, "name": "FT - Markets",                "url": "https://www.ft.com/markets?format=rss",                "note": "金融时报/市场综合"},
    {"checked": True, "name": "FT - Alphaville",             "url": "https://www.ft.com/alphaville?format=rss",             "note": "金融时报/著名金融博客"},
    {"checked": True, "name": "FT - Private Markets",        "url": "https://www.ft.com/private-markets?format=rss",        "note": "金融时报/私募市场"},
    {"checked": True, "name": "FT - Equities",               "url": "https://www.ft.com/equities?format=rss",               "note": "金融时报/股票"},
    {"checked": True, "name": "FT - Bonds",                  "url": "https://www.ft.com/bonds?format=rss",                  "note": "金融时报/债券"},
    {"checked": True, "name": "FT - Currencies",             "url": "https://www.ft.com/currencies?format=rss",             "note": "金融时报/外汇"},
    {"checked": True, "name": "FT - Commodities",            "url": "https://www.ft.com/commodities?format=rss",            "note": "金融时报/大宗商品"},
    {"checked": True, "name": "FT - Crypto",                 "url": "https://www.ft.com/crypto?format=rss",                 "note": "金融时报/加密货币"},
    {"checked": True, "name": "FT - Wealth Management",      "url": "https://www.ft.com/wealth-management?format=rss",      "note": "金融时报/财富管理"},
    {"checked": True, "name": "FT - Moral Money",            "url": "https://www.ft.com/moral-money?format=rss",            "note": "金融时报/ESG与道德投资"},
    {"checked": True, "name": "FT - ETF Hub",                "url": "https://www.ft.com/etf-hub?format=rss",                "note": "金融时报/ETF中心"},

    # --- Climate & Opinion (气候与观点) ---
    {"checked": True, "name": "FT - Climate",                "url": "https://www.ft.com/climate?format=rss",                "note": "金融时报/气候变化"},
    {"checked": True, "name": "FT - Opinion",                "url": "https://www.ft.com/opinion?format=rss",                "note": "金融时报/观点评论"},
    {"checked": True, "name": "FT - The FT View",            "url": "https://www.ft.com/ft-view?format=rss",                "note": "金融时报/社论"},
    {"checked": True, "name": "FT - The Big Read",           "url": "https://www.ft.com/the-big-read?format=rss",           "note": "金融时报/深度阅读"},
    {"checked": True, "name": "FT - Lex",                    "url": "https://www.ft.com/lex?format=rss",                    "note": "金融时报/Lex老牌专栏"},
    {"checked": True, "name": "FT - Obituaries",             "url": "https://www.ft.com/obituaries?format=rss",             "note": "金融时报/讣告"},
    {"checked": True, "name": "FT - Letters",                "url": "https://www.ft.com/letters?format=rss",                "note": "金融时报/读者来信"},

    # --- Work & Careers, Life & Arts (工作、生活与艺术) ---
    {"checked": True, "name": "FT - Work & Careers",         "url": "https://www.ft.com/work-careers?format=rss",           "note": "金融时报/工作与职场"},
    {"checked": True, "name": "FT - Business School Rankings","url": "https://www.ft.com/business-school-rankings?format=rss","note": "金融时报/商学院排名"},
    {"checked": True, "name": "FT - Business Education",     "url": "https://www.ft.com/business-education?format=rss",     "note": "金融时报/商业教育"},
    {"checked": True, "name": "FT - Entrepreneurship",       "url": "https://www.ft.com/entrepreneurship?format=rss",       "note": "金融时报/创业"},
    {"checked": True, "name": "FT - Recruitment",            "url": "https://www.ft.com/recruitment?format=rss",            "note": "金融时报/招聘"},
    {"checked": True, "name": "FT - Business Books",         "url": "https://www.ft.com/business-books?format=rss",         "note": "金融时报/商业书籍"},
    {"checked": True, "name": "FT - Business Travel",        "url": "https://www.ft.com/business-travel?format=rss",        "note": "金融时报/商务旅行"},
    {"checked": True, "name": "FT - Working It",             "url": "https://www.ft.com/working-it?format=rss",             "note": "金融时报/职场指南"},
    {"checked": True, "name": "FT - Life & Arts",            "url": "https://www.ft.com/life-arts?format=rss",              "note": "金融时报/生活与艺术"},
    {"checked": True, "name": "FT - Arts",                   "url": "https://www.ft.com/arts?format=rss",                   "note": "金融时报/艺术"},
    {"checked": True, "name": "FT - Books",                  "url": "https://www.ft.com/books?format=rss",                  "note": "金融时报/书籍"},
    {"checked": True, "name": "FT - Food & Drink",           "url": "https://www.ft.com/food-drink?format=rss",             "note": "金融时报/美食与饮品"},
    {"checked": True, "name": "FT - FT Magazine",            "url": "https://www.ft.com/magazine?format=rss",               "note": "金融时报/周末杂志"},
    {"checked": True, "name": "FT - House & Home",           "url": "https://www.ft.com/house-home?format=rss",             "note": "金融时报/家居"},
    {"checked": True, "name": "FT - Style",                  "url": "https://www.ft.com/style?format=rss",                  "note": "金融时报/时尚"},
    {"checked": True, "name": "FT - Puzzles",                "url": "https://www.ft.com/puzzles?format=rss",                "note": "金融时报/智力游戏"},
    {"checked": True, "name": "FT - Travel",                 "url": "https://www.ft.com/travel?format=rss",                 "note": "金融时报/旅行"},
    {"checked": True, "name": "FT - FT Globetrotter",        "url": "https://www.ft.com/globetrotter?format=rss",           "note": "金融时报/全球旅行家"},

    # --- Personal Finance, How To Spend It, Special Reports (个人理财、消费、特别报道) ---
    {"checked": True, "name": "FT - Personal Finance",       "url": "https://www.ft.com/personal-finance?format=rss",       "note": "金融时报/个人理财"},
    {"checked": True, "name": "FT - Property & Mortgages",   "url": "https://www.ft.com/mortgages?format=rss",     "note": "金融时报/房地产与房贷"},
    {"checked": True, "name": "FT - Investments",            "url": "https://www.ft.com/investments?format=rss",            "note": "金融时报/投资"},
    {"checked": True, "name": "FT - Pensions",               "url": "https://www.ft.com/pensions?format=rss",               "note": "金融时报/养老金"},
    {"checked": True, "name": "FT - Tax",                    "url": "https://www.ft.com/tax?format=rss",                    "note": "金融时报/税务"},
    {"checked": True, "name": "FT - Banking & Savings",      "url": "https://www.ft.com/banking-savings?format=rss",        "note": "金融时报/银行与储蓄"},
    {"checked": True, "name": "FT - Advice & Comment",       "url": "https://www.ft.com/advice-comment?format=rss",         "note": "金融时报/理财建议与评论"},
    {"checked": True, "name": "FT - How To Spend It",        "url": "https://www.ft.com/htsi?format=rss",                   "note": "金融时报/高端消费(HTSI)"},
    {"checked": True, "name": "FT - Special Reports",        "url": "https://www.ft.com/special-reports?format=rss",        "note": "金融时报/特别报道"},

    # === 📻 美国全国公共广播电台 (NPR) 提纯矩阵 (20个常青频道) ===
    {"checked": True,  "name": "NPR - News",             "url": "https://feeds.npr.org/1001/rss.xml", "note": "美国NPR/新闻滚动头条"},
    {"checked": True,  "name": "NPR - Top Stories",      "url": "https://feeds.npr.org/1002/rss.xml", "note": "美国NPR/主页精选头条"},
    {"checked": True,  "name": "NPR - National",         "url": "https://feeds.npr.org/1003/rss.xml", "note": "美国NPR/美国国内热点"},
    {"checked": True,  "name": "NPR - World",            "url": "https://feeds.npr.org/1004/rss.xml", "note": "美国NPR/国际风云"},
    {"checked": True,  "name": "NPR - Business",         "url": "https://feeds.npr.org/1006/rss.xml", "note": "美国NPR/商业与企业"},
    {"checked": True,  "name": "NPR - Economy",          "url": "https://feeds.npr.org/1017/rss.xml", "note": "美国NPR/宏观经济"},
    {"checked": True,  "name": "NPR - Technology",       "url": "https://feeds.npr.org/1019/rss.xml", "note": "美国NPR/科技与互联网"},
    {"checked": True,  "name": "NPR - Science",          "url": "https://feeds.npr.org/1007/rss.xml", "note": "美国NPR/科学发现"},
    {"checked": True,  "name": "NPR - Health",           "url": "https://feeds.npr.org/1027/rss.xml", "note": "美国NPR/医疗健康"},
    {"checked": True,  "name": "NPR - Politics",         "url": "https://feeds.npr.org/1014/rss.xml", "note": "美国NPR/美国政治"},
    {"checked": True,  "name": "NPR - Law",              "url": "https://feeds.npr.org/1070/rss.xml", "note": "美国NPR/法律与司法"},
    {"checked": True,  "name": "NPR - Middle East",      "url": "https://feeds.npr.org/1009/rss.xml", "note": "美国NPR/中东局势"},
    {"checked": True,  "name": "NPR - Environment",      "url": "https://feeds.npr.org/1025/rss.xml", "note": "美国NPR/环境与生态"},
    {"checked": True,  "name": "NPR - Space",            "url": "https://feeds.npr.org/1026/rss.xml", "note": "美国NPR/太空与天文"},
    {"checked": True,  "name": "NPR - Global Health",    "url": "https://feeds.npr.org/1031/rss.xml", "note": "美国NPR/全球公共卫生"},
    {"checked": True,  "name": "NPR - Race",             "url": "https://feeds.npr.org/1015/rss.xml", "note": "美国NPR/种族与社会问题"},
    {"checked": True,  "name": "NPR - Education",        "url": "https://feeds.npr.org/1013/rss.xml", "note": "美国NPR/教育"},
    {"checked": True,  "name": "NPR - Media",            "url": "https://feeds.npr.org/1020/rss.xml", "note": "美国NPR/传媒与舆论"},
    {"checked": True,  "name": "NPR - Opinion",          "url": "https://feeds.npr.org/1057/rss.xml", "note": "美国NPR/评论与专栏"},
    {"checked": True,  "name": "NPR - Analysis",         "url": "https://feeds.npr.org/1059/rss.xml", "note": "美国NPR/深度分析"},
    
    # === 🌍 卫报 (The Guardian) 全矩阵 (5个频道) ===
    {"checked": True, "name": "The Guardian - News",       "url": "https://www.theguardian.com/international/rss",       "note": "卫报/国际头条与深度新闻"},
    {"checked": True, "name": "The Guardian - Opinion",    "url": "https://www.theguardian.com/uk/commentisfree/rss",    "note": "卫报/名家专栏与自由评论"},
    {"checked": True, "name": "The Guardian - Culture",    "url": "https://www.theguardian.com/uk/culture/rss",          "note": "卫报/文化与艺术前沿"},
    {"checked": True, "name": "The Guardian - Lifestyle",  "url": "https://www.theguardian.com/uk/lifeandstyle/rss",     "note": "卫报/英伦生活方式"},
    {"checked": True, "name": "The Guardian - Sport",      "url": "https://www.theguardian.com/uk/sport/rss",            "note": "卫报/全球体育赛事"},

    # === 🇭🇰 南华早报 (SCMP) 全矩阵 (30个频道) ===
    # --- News (新闻综合) ---
    {"checked": True,  "name": "SCMP - News",                "url": "https://www.scmp.com/rss/91/feed",     "note": "南华早报/新闻头条"},
    {"checked": True,  "name": "SCMP - Hong Kong",           "url": "https://www.scmp.com/rss/2/feed",      "note": "南华早报/香港本地"},
    {"checked": True,  "name": "SCMP - China",               "url": "https://www.scmp.com/rss/4/feed",      "note": "南华早报/中国新闻"},
    {"checked": True,  "name": "SCMP - Asia",                "url": "https://www.scmp.com/rss/3/feed",      "note": "南华早报/亚洲新闻"},
    {"checked": True,  "name": "SCMP - World",               "url": "https://www.scmp.com/rss/5/feed",      "note": "南华早报/世界新闻"},
    {"checked": True,  "name": "SCMP - People & Culture",    "url": "https://www.scmp.com/rss/318202/feed", "note": "南华早报/人文与文化"},

    # --- China (中国深度) ---
    {"checked": True,  "name": "SCMP - China Politics",      "url": "https://www.scmp.com/rss/318198/feed", "note": "南华早报/中国政治与政策"},
    {"checked": True,  "name": "SCMP - China Diplomacy",     "url": "https://www.scmp.com/rss/318199/feed", "note": "南华早报/中国外交与防务"},
    {"checked": True,  "name": "SCMP - China Economy",       "url": "https://www.scmp.com/rss/318421/feed", "note": "南华早报/中国宏观经济"},
    {"checked": True,  "name": "SCMP - China Society",       "url": "https://www.scmp.com/rss/318202/feed", "note": "南华早报/中国社会焦点"},

    # --- World (世界区域) ---
    {"checked": True,  "name": "SCMP - US & Canada",         "url": "https://www.scmp.com/rss/322262/feed", "note": "南华早报/美国与加拿大"},
    {"checked": True,  "name": "SCMP - Europe",              "url": "https://www.scmp.com/rss/322263/feed", "note": "南华早报/欧洲"},
    {"checked": True,  "name": "SCMP - Middle East",         "url": "https://www.scmp.com/rss/322264/feed", "note": "南华早报/中东"},

    # --- This Week In Asia (本周亚洲深度) ---
    {"checked": True,  "name": "SCMP - TWIA Politics",       "url": "https://www.scmp.com/rss/323046/feed", "note": "南华早报/本周亚洲·政治"},
    {"checked": True,  "name": "SCMP - TWIA Geopolitics",    "url": "https://www.scmp.com/rss/323047/feed", "note": "南华早报/本周亚洲·地缘政治"},
    {"checked": True,  "name": "SCMP - TWIA Business",       "url": "https://www.scmp.com/rss/323048/feed", "note": "南华早报/本周亚洲·商业"},

    # --- Business (商业与经济) ---
    {"checked": True,  "name": "SCMP - Business",            "url": "https://www.scmp.com/rss/92/feed",     "note": "南华早报/商业综合"},
    {"checked": True,  "name": "SCMP - Companies",           "url": "https://www.scmp.com/rss/10/feed",     "note": "南华早报/企业动态"},
    {"checked": True,  "name": "SCMP - Global Economy",      "url": "https://www.scmp.com/rss/12/feed",     "note": "南华早报/全球经济"},

    # --- Tech (科技) ---
    {"checked": True,  "name": "SCMP - Tech",                "url": "https://www.scmp.com/rss/36/feed",     "note": "南华早报/科技综合"},
    {"checked": True,  "name": "SCMP - China Tech",          "url": "https://www.scmp.com/rss/320663/feed", "note": "南华早报/中国科技前沿"},
    {"checked": True,  "name": "SCMP - Tech Enterprises",    "url": "https://www.scmp.com/rss/318218/feed", "note": "南华早报/科技巨头"},
    {"checked": False,  "name": "SCMP - Tech Start-ups",      "url": "https://www.scmp.com/rss/318220/feed", "note": "南华早报/创投与初创"},
    {"checked": True,  "name": "SCMP - Science & Research",  "url": "https://www.scmp.com/rss/318224/feed", "note": "南华早报/科研突破"},

    # --- Opinion (观点评论) ---
    {"checked": True,  "name": "SCMP - Opinion",             "url": "https://www.scmp.com/rss/6/feed",      "note": "南华早报/名家专栏与评论"},
    {"checked": True,  "name": "SCMP - Insight & Opinion",   "url": "https://www.scmp.com/rss/17/feed",     "note": "南华早报/深度观察"},

    {"checked": True, "name": "ProPublica",         "url": "https://www.propublica.org/feeds/propublica/main",         "note": "普利策奖级深度调查报道"},
    {"checked": True, "name": "Al Jazeera",         "url": "https://www.aljazeera.com/xml/rss/all.xml",                "note": "半岛电视台/非西方视角"},

    # === 💻 科技、互联网与创投 ===
    {"checked": True, "name": "TechCrunch",          "url": "https://techcrunch.com/feed/",                            "note": "硅谷创投与早期科技公司"},
    {"checked": True, "name": "VentureBeat",         "url": "https://venturebeat.com/feed/",                           "note": "重点关注AI突破与商业动态"},
    {"checked": True, "name": "Wired",               "url": "https://www.wired.com/feed/rss",                          "note": "连线杂志/科技与人文探讨"},
    {"checked": True, "name": "The Verge",           "url": "https://www.theverge.com/rss/index.xml",                  "note": "前沿消费电子与互联网文化"},
    {"checked": True, "name": "Ars Technica",        "url": "https://feeds.arstechnica.com/arstechnica/index",         "note": "极客最爱/IT与科技政策"},

    # === 🔬 顶尖科学、学术与工程 ===
    {"checked": True, "name": "Nature",              "url": "https://www.nature.com/nature.rss",                       "note": "自然/全球顶尖综合科学期刊"},
    {"checked": True, "name": "Cell Press",          "url": "https://www.cell.com/cell/current.rss",                   "note": "细胞/生命科学与医学顶刊"},
    {"checked": True, "name": "Science News",        "url": "https://www.sciencenews.org/feed",                        "note": "前沿科学发现与研究追踪"},
    {"checked": True, "name": "MIT Tech Review",     "url": "https://www.technologyreview.com/feed/",                  "note": "麻省理工科技评论"},
    {"checked": True, "name": "IEEE Spectrum",       "url": "https://spectrum.ieee.org/feeds/feed.rss",                "note": "全球最大工程师协会权威报道"},

    # === 🇨🇳 中国国际电视台 (CGTN) 全矩阵 (12个频道 满血版) ===
    {"checked": True, "name": "CGTN - China",         "url": "https://www.cgtn.com/subscribe/rss/section/china.xml",       "note": "CGTN/国内社会与热点"},
    {"checked": True, "name": "CGTN - World",         "url": "https://www.cgtn.com/subscribe/rss/section/world.xml",       "note": "CGTN/全球视野与各洲动态"},
    {"checked": True, "name": "CGTN - Politics",      "url": "https://www.cgtn.com/subscribe/rss/section/politics.xml",    "note": "CGTN/大国政治与中国外交"},
    {"checked": True, "name": "CGTN - Business",      "url": "https://www.cgtn.com/subscribe/rss/section/business.xml",    "note": "CGTN/经济趋势与市场分析"},
    {"checked": True, "name": "CGTN - Tech&Sci",      "url": "https://www.cgtn.com/subscribe/rss/section/tech-sci.xml",    "note": "CGTN/科技创新与环境健康"},
    {"checked": True, "name": "CGTN - Opinion",       "url": "https://www.cgtn.com/subscribe/rss/section/opinion.xml",     "note": "CGTN/中国立场与社论观点"},
    {"checked": True, "name": "CGTN - Culture",       "url": "https://www.cgtn.com/subscribe/rss/section/culture.xml",     "note": "CGTN/文化艺术与东方视角"},
    {"checked": True, "name": "CGTN - Sports",        "url": "https://www.cgtn.com/subscribe/rss/section/sports.xml",      "note": "CGTN/国内外体坛要闻"},
    {"checked": True, "name": "CGTN - Travel",        "url": "https://www.cgtn.com/subscribe/rss/section/travel.xml",      "note": "CGTN/旅游文化与风土人情"},
    {"checked": True, "name": "CGTN - Nature",        "url": "https://www.cgtn.com/subscribe/rss/section/nature.xml",      "note": "CGTN/自然探索与行星故事"},
    {"checked": True, "name": "CGTN - Video",         "url": "https://www.cgtn.com/subscribe/rss/section/video.xml",       "note": "CGTN/重大突发新闻视频报道"},
    {"checked": True, "name": "CGTN - Documentary",   "url": "https://www.cgtn.com/subscribe/rss/section/documentary.xml", "note": "CGTN/中国故事高质量纪录片"},
    {"checked": True, "name": "CGTN - G-Stringer",    "url": "https://www.cgtn.com/subscribe/rss/section/gstringer.xml",   "note": "CGTN/全球独家通讯员报道网络"},
    {"checked": True, "name": "CGTN - Live",          "url": "https://www.cgtn.com/subscribe/rss/section/live.xml",        "note": "CGTN/沉浸式新闻现场直播"},

    # === 🇨🇳 中国官方与外宣媒体 ===
    {"checked": True, "name": "People's Daily",      "url": "http://www.people.com.cn/rss/world.xml",                  "note": "人民网国际版/中国官方权威发声"}
]

class ConfigManager:
    @staticmethod
    def load_config():
        if not os.path.exists(CONFIG_FILE):
            ConfigManager.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
        
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)

        if "providers" not in config:
            config["providers"] = DEFAULT_CONFIG["providers"]
            config["ai_provider"] = "Google Gemini"

        if "rss_use_proxy" not in config:
            config["rss_use_proxy"] = False
            config["rss_proxy_server"] = "http://127.0.0.1"
            config["rss_proxy_port"] = "10808"

        changed = False
        for key, default_val in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = default_val
                changed = True
            
        if changed:
            ConfigManager.save_config(config)
            
        return config

    @staticmethod
    def save_config(config):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

    @staticmethod
    def load_sources():
        if not os.path.exists(SOURCES_FILE):
            ConfigManager.save_sources(DEFAULT_SOURCES)
            return DEFAULT_SOURCES
        with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def save_sources(sources):
        with open(SOURCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(sources, f, indent=4, ensure_ascii=False)

    @staticmethod
    def load_history():
        if not os.path.exists(HISTORY_FILE): return []
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def add_to_history(url):
        history = ConfigManager.load_history()
        if url not in history:
            history.append(url)
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False)