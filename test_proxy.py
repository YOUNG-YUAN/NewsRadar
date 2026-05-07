import requests

# 替换为你代理软件的真实 HTTP 端口
proxy = "http://127.0.0.1:10808" 
proxies = {"http": proxy, "https": proxy}

test_url = "https://www.google.com" # 或者某个 RSS 地址

try:
    print(f"正在尝试通过代理 {proxy} 访问...")
    resp = requests.get(test_url, proxies=proxies, timeout=10)
    print(f"✅ 成功！状态码: {resp.status_code}")
except Exception as e:
    print(f"❌ 失败！错误信息: {e}")