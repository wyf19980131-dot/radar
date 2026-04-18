import requests
import time
import json

# ==========================================
# 1. 核心配置区
# ==========================================
GEMINI_API_KEY = "AIzaSyAWEZReCFalz7NvsaoRKZrfORpjA4iqfkU"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1494204147770331136/qSKkHw9q1jKxdklhmBcoxXzUsdnvku71XLex6MZcr82uvWNaGAyXj81r6zRwWOsR0CuX"
NEWS_API_KEY = "pub_a89fdc173fbd42ad90a9a8e43cbfe07f"
FINNHUB_API_KEY = "d7g83t1r01qqb8rim0tgd7g83t1r01qqb8rim0u0"

# ==========================================
# 2. 宏观引擎：全球新闻抓取
# ==========================================
def fetch_macro_news():
    print("📡 正在扫描全球宏观与科技新闻流...")
    url = f"https://newsdata.io/api/1/news?apikey={NEWS_API_KEY}&category=business,technology&language=en"
    try:
        res = requests.get(url).json()
        articles = res.get('results', [])[:8]
        if not articles:
            print("📭 当前时段暂无重大宏观新闻。")
            return None
        context = ""
        for i, art in enumerate(articles):
            context += f"{i+1}. {art.get('title')}\n摘要: {art.get('description')}\n\n"
        return context
    except Exception as e:
        print(f"❌ 宏观新闻网络异常: {e}")
        return None

# ==========================================
# 3. 财报引擎：极简 5 股狙击雷达
# ==========================================
def fetch_earnings_data():
    print("📊 正在锁定今日美股财报核心焦点 (Top 5)...")
    today = time.strftime("%Y-%m-%d", time.localtime())
    url = f"https://finnhub.io/api/v1/calendar/earnings?from={today}&to={today}&token={FINNHUB_API_KEY}"
    try:
        res = requests.get(url).json()
        earnings = res.get('earningsCalendar', [])

        # 严格限制：只抓取前 5 家已公布实际业绩的公司
        published = [e for e in earnings if e.get('epsActual') is not None][:5]

        if not published:
            print("📭 当前暂无已公布财报的焦点公司。")
            return None

        context = ""
        for e in published:
            symbol = e.get('symbol')
            est = e.get('epsEstimate') or 0.01
            act = e.get('epsActual') or 0
            diff_pct = ((act - est) / abs(est)) * 100 if est != 0 else 0

            context += f"【{symbol}】EPS预期:{est}, 实际:{act} (超预期 {diff_pct:.1f}%) | 营收实际:{e.get('revenueActual')}\n"

        return context
    except Exception as e:
        print(f"❌ 财报流网络异常: {e}")
        return None

# ==========================================
# 4. AI 处理与跨平台推送逻辑 (抗压重试版)
# ==========================================
def ai_process_and_push(content, mode="Macro"):
    if not content: return

    prompts = {
        "Macro": f"你是一个宏观对冲基金分析师。分析以下新闻，过滤噪音，只挑出最影响全球大类资产趋势的 2 件事并给出冷酷的逻辑判断。总字数 150 字内。\n\n{content}",
        "Earnings": f"你是一个极其冷酷的量化交易员。以下是最新公布的 5 家美股核心财报数据：\n{content}\n请执行狙击任务：1. 用一句话给今日盈利质量定调。2. 只锁定预期差最极端的 1-2 家公司点评。3. 给出量化策略（IV Crush、杀估值等）。严控在 150 字以内。"
    }

    # 获取可用模型并构建请求 URL（已修复截断风险）
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1/models?key={GEMINI_API_KEY}"
        auth_check = requests.get(list_url).json()
        available_models = [m['name'] for m in auth_check.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        best_model = "models/gemini-1.5-flash" if "models/gemini-1.5-flash" in available_models else available_models[0]
        gen_url = f"https://generativelanguage.googleapis.com/v1/{best_model}:generateContent?key={GEMINI_API_KEY}"
    except:
        # 回退模型，代码已修复闭合
        best_model = "models/gemini-pro"
        gen_url = f"https://generativelanguage.googleapis.com/v1/{best_model}:generateContent?key={GEMINI_API_KEY}"

    payload = {"contents": [{"parts": [{"text": prompts[mode]}]}]}

    # 增加最大 3 次重试机制
    max_retries = 3
    for attempt in range(max_retries):
        try:
            res = requests.post(gen_url, headers={'Content-Type': 'application/json'}, json=payload).json()

            # 如果服务器返回了 error
            if 'error' in res:
                error_msg = res['error']['message']
                print(f"⚠️ 第 {attempt + 1} 次请求被拦截: {error_msg}")
                if attempt < max_retries - 1:
                    print("⏳ 触发重试机制，程序休眠 10 秒后再次冲锋...")
                    time.sleep(10)
                    continue
                else:
                    print("❌ 已达到最大重试次数 (3次)，放弃本轮生成。")
                    return

            # 如果成功拿到数据
            ai_thought = res['candidates'][0]['content']['parts'][0]['text']

            # 拆解参数，彻底防止代码超长截断
            header_text = "🌐 【半小时宏观雷达】" if mode == "Macro" else "🎯 【Top 5 财报狙击】"
            bot_name = "AI 宏观分析仪" if mode == "Macro" else "AI 财报粉碎机"
            bot_avatar = "https://cdn-icons-png.flaticon.com/512/1907/1907152.png" if mode == "Macro" else "https://cdn-icons-png.flaticon.com/512/2933/2933116.png"

            discord_payload = {
                "content": f"{header_text}\n\n{ai_thought}",
                "username": bot_name,
                "avatar_url": bot_avatar
            }

            d_res = requests.post(DISCORD_WEBHOOK_URL, json=discord_payload)

            if d_res.status_code in [200, 204]:
                print(f"✅ {mode} 简报已成功推送到 iPad。")
            else:
                print(f"❌ Discord 推送失败，状态码: {d_res.status_code}")

            break # 成功推送后，必须 break 跳出重试循环

        except Exception as e:
            print(f"❌ 发生不可预知的网络异常: {e}")
            break

# ==========================================
# 5. 自动化心跳引擎 (每30分钟)
# ==========================================
print("🚀 [全天候抗压双引擎] 重新挂载！已装备【3次不死重试护甲】...")
while True:
    print(f"\n[{time.strftime('%H:%M:%S')}] 触发扫描周期...")

    ai_process_and_push(fetch_macro_news(), "Macro")
    ai_process_and_push(fetch_earnings_data(), "Earnings")

    print("💤 扫描完毕。进入 30 分钟战术静默期...")
    time.sleep(1800)
