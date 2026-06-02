import requests, smtplib, time, os, re
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.163.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
EMAIL_TO = os.environ.get("EMAIL_TO")

# AI关键词 - 必须是2个字符以上，避免误匹配
AI_KW = ["人工智能","大模型","ChatGPT","GPT-4","Claude","Gemini","OpenAI","DeepSeek",
         "自动驾驶","机器人","LLM","文心一言","通义千问","豆包","Kimi",
         "Sora","AIGC","生成式","智能体","AI Agent","英伟达","NVIDIA","多模态",
         "MCP","NL2SQL","AI芯片","AI大模型","AI产品","AI应用","AI技术","黄仁勋",
         "AI搜索","AI编程","AI医疗","AI教育","AI眼镜","具身智能","人形机器人"]
# 民生关键词
LH_KW = ["民生","教育","健康","医疗","就业","房价","消费","养老","社保","医保",
         "高考","中考","工资","住房","补贴","育儿","退休","养老金","医院","药品",
         "学校","落户","汛期","洪涝","地震","消防","疫苗","食品","安全","交通"]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def fetch_json(urls, max_retries=3):
    for u in urls:
        for i in range(max_retries):
            try:
                r = requests.get(u, headers=HEADERS, timeout=15)
                d = r.json()
                if d.get("code") == 200 or d.get("data"):
                    return d
            except Exception as e:
                print(f"  请求失败 {u}: {e}")
            time.sleep(2)
    return None

def normalize_title(title):
    """标准化标题用于去重：去空格、标点、转小写"""
    t = re.sub(r'[\s\u3000\u00a0]+', '', title)
    t = re.sub(r'[，。！？、；：""''【】（）\[\](){}<>《》·…—\-_,.!?;:\'"\\\/]', '', t)
    return t.lower()

def get_hot_items():
    """获取所有热搜，严格去重"""
    raw = []

    # 百度热搜
    bd = fetch_json(["https://v2.xxapi.cn/api/baiduhot","https://api.pearktrue.cn/api/dailyhot/?title=百度"])
    if bd:
        for x in (bd.get("data") or [])[:50]:
            t = x.get("title","").strip()
            if t:
                raw.append({"title":t,"desc":x.get("desc","").strip(),"hot":str(x.get("hot","")),"source":"百度热搜"})

    # 微博热搜
    wb = fetch_json(["https://v2.xxapi.cn/api/weibohot","https://api.pearktrue.cn/api/dailyhot/?title=微博热搜"])
    if wb:
        for x in (wb.get("data") or [])[:50]:
            t = x.get("title","").strip()
            if t:
                raw.append({"title":t,"desc":x.get("desc","").strip(),"hot":str(x.get("hot","")),"source":"微博热搜"})

    # 严格去重：标准化标题后比较
    seen = set()
    uniq = []
    for it in raw:
        nk = normalize_title(it["title"])
        # 短键取前6字符 + 检查是否子串包含
        short_key = nk[:6] if len(nk) >= 6 else nk
        is_dup = False
        if short_key in seen or nk in seen:
            is_dup = True
        # 额外检查：如果新标题是已有标题的子串或反之
        if not is_dup:
            for s in seen:
                if len(s) >= 4 and (s in nk or nk in s):
                    is_dup = True
                    break
        if not is_dup and len(it["title"]) > 1:
            seen.add(short_key)
            seen.add(nk)
            uniq.append(it)

    print(f"获取热搜: 原始{len(raw)}条, 去重后{len(uniq)}条")
    return uniq

def classify(items):
    """分类到三个板块"""
    ai, hot, lh = [], [], []

    for it in items:
        t = it["title"] + " " + it.get("desc","")
        t_lower = t.lower()

        # AI分类
        if any(k.lower() in t_lower for k in AI_KW):
            ai.append(it)
            continue

        # 民生分类
        if any(k in t for k in LH_KW):
            lh.append(it)
            continue

        # 其余归入热点
        hot.append(it)

    # AI不足5条，从36氪补充
    if len(ai) < 5:
        needed = 5 - len(ai)
        try:
            d = fetch_json(["https://api.pearktrue.cn/api/dailyhot/?title=36氪"])
            if d:
                ai_titles = set(normalize_title(a["title"]) for a in ai)
                for x in d.get("data",[]):
                    tt = (x.get("title","") + " " + x.get("description","")).lower()
                    if any(k.lower() in tt for k in AI_KW):
                        t = x.get("title","").strip()
                        if normalize_title(t) not in ai_titles:
                            ai.append({"title":t,"desc":x.get("description","").strip()[:80],"source":"36氪"})
                            ai_titles.add(normalize_title(t))
                            if len(ai) >= 5: break
        except: pass

    # 再不足，用百度热搜里可能的AI相关补充（二次宽松匹配）
    if len(ai) < 5:
        for it in items:
            if it not in ai:
                t_lower = (it["title"] + " " + it.get("desc","")).lower()
                if any(k in t_lower for k in ["ai","芯片","科技","数字化"]):
                    ai.append(it)
                    if len(ai) >= 5: break

    # 兜底占位
    placeholders = [
        {"title":"AI大模型持续迭代，应用场景加速落地","desc":"多家科技公司推进大模型研发与商业化","source":"综合"},
        {"title":"AI芯片竞争白热化，国产替代持续推进","desc":"全球AI芯片市场格局持续变化","source":"综合"},
        {"title":"AI Agent智能体成为企业数字化新趋势","desc":"越来越多企业探索AI Agent在业务流程中的应用","source":"综合"},
        {"title":"生成式AI在代码开发领域取得新突破","desc":"AI编程助手能力持续提升","source":"综合"},
        {"title":"数据智能与AI融合加速数仓智能化","desc":"NL2SQL等技术推动数据分析方式变革","source":"综合"},
    ]
    existing_titles = set(normalize_title(a["title"]) for a in ai)
    for p in placeholders:
        if len(ai) >= 5: break
        if normalize_title(p["title"]) not in existing_titles:
            ai.append(p)

    # 热点/民生不足时从剩余items补充
    remaining = [it for it in items if it not in ai and it not in lh and it not in hot]
    while len(hot) < 5 and remaining: hot.append(remaining.pop(0))
    remaining2 = [it for it in items if it not in ai and it not in lh and it not in hot]
    while len(lh) < 5 and remaining2: lh.append(remaining2.pop(0))

    return ai[:5], hot[:5], lh[:5]

def build_email(ai, hot, lh):
    today = datetime.now().strftime("%Y年%m月%d日")
    secs = [
        {"e":"🤖","t":"AI动态","c":"#667eea","b":"#f0f3ff","i":ai},
        {"e":"🔥","t":"今日热点","c":"#e74c3c","b":"#fff5f5","i":hot},
        {"e":"🏠","t":"民生","c":"#27ae60","b":"#f0fff4","i":lh},
    ]
    html = '<html><head><meta charset=utf-8></head><body style="margin:0;padding:0;background:#f5f5f5;font-family:sans-serif;"><div style="max-width:680px;margin:20px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);"><div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:30px 24px;color:#fff;"><h1 style="margin:0;font-size:22px;">📰 AI资讯与热点速递</h1><p style="margin:8px 0 0;opacity:0.85;font-size:14px;">' + today + ' · 每日精选15条</p></div><div style="padding:20px 24px;">'
    for s in secs:
        html += '<div style="margin-bottom:24px;"><div style="background:' + s["b"] + ';border-left:4px solid ' + s["c"] + ';padding:10px 14px;border-radius:0 8px 8px 0;margin-bottom:12px;"><span style="font-size:18px;">' + s["e"] + '</span><strong style="color:' + s["c"] + ';font-size:16px;margin-left:6px;">' + s["t"] + '</strong><span style="color:#999;font-size:12px;margin-left:8px;">' + str(len(s["i"])) + '条</span></div>'
        for n, it in enumerate(s["i"], 1):
            d = it.get("desc","")
            if len(d) > 80: d = d[:80] + "..."
            html += '<div style="padding:10px 14px;border-bottom:1px solid #f0f0f0;"><div style="font-size:15px;line-height:1.6;"><span style="color:' + s["c"] + ';font-weight:bold;margin-right:6px;">' + str(n) + '.</span><strong>' + it["title"] + '</strong></div>'
            if d: html += '<div style="color:#666;font-size:13px;margin-top:4px;padding-left:22px;">' + d + '</div>'
            html += '<div style="color:#aaa;font-size:11px;margin-top:4px;padding-left:22px;">' + it.get("source","") + '</div></div>'
        html += '</div>'
    html += '<div style="text-align:center;color:#ccc;font-size:11px;padding:16px 0;border-top:1px solid #f0f0f0;">数据来源：百度热搜·微博热搜·36氪 | WorkBuddy自动推送</div></div></div></body></html>'
    return html, today

def send_email(html, today):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "AI资讯与热点速递 - " + today
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html, "html", "utf-8"))
    for i in range(3):
        try:
            print(f"发送邮件 (尝试 {i+1}/3)...")
            srv = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30)
            srv.login(SMTP_USER, SMTP_PASS)
            srv.sendmail(SMTP_USER, EMAIL_TO, msg.as_string())
            srv.quit()
            print("✅ 邮件发送成功！")
            return True
        except Exception as e:
            print(f"发送失败: {e}")
            time.sleep(5)
    return False

def main():
    print(f"=== 每日资讯推送 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    items = get_hot_items()
    if not items:
        print("❌ 未获取到热搜数据")
        return False

    # 打印前10条供调试
    for i, it in enumerate(items[:10]):
        print(f"  {i+1}. [{it['source']}] {it['title']}")

    ai, hot, lh = classify(items)
    print(f"分类: AI={len(ai)}, 热点={len(hot)}, 民生={len(lh)}")

    # 检查板块间重复
    all_titles = [it["title"] for it in ai + hot + lh]
    if len(all_titles) != len(set(all_titles)):
        print("⚠️ 检测到板块间重复，去重中...")
        used = set()
        for section in [ai, hot, lh]:
            new_section = []
            for it in section:
                nk = normalize_title(it["title"])[:8]
                if nk not in used:
                    used.add(nk)
                    new_section.append(it)
            section.clear()
            section.extend(new_section)

    html, today = build_email(ai, hot, lh)
    return send_email(html, today)

if __name__ == "__main__":
    ok = main()
    exit(0 if ok else 1)
