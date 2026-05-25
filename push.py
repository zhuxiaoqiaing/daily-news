import requests, smtplib, time, os
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.163.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
EMAIL_TO = os.environ.get("EMAIL_TO")

AI = ["AI","ai","人工智能","大模型","ChatGPT","GPT","Claude","Gemini","OpenAI","DeepSeek",
      "芯片","GPU","算力","自动驾驶","机器人","LLM","文心","通义","豆包","Kimi",
      "Sora","AIGC","生成式","智能体","Agent","英伟达","NVIDIA","多模态","MCP","NL2SQL"]
LH = ["民生","教育","健康","医疗","就业","房价","消费","养老","社保","医保",
      "高考","工资","住房","补贴","育儿","退休","养老金","医院","药品","学校","落户"]
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def fetch(urls):
    for u in urls:
        for i in range(3):
            try:
                r = requests.get(u, headers=H, timeout=15)
                d = r.json()
                if d.get("code") == 200 or d.get("data"):
                    return d
            except Exception as e:
                print(f"  请求失败 {u}: {e}")
            time.sleep(2)
    return None

def main():
    print(f"=== 每日资讯推送 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    items = []
    bd = fetch(["https://v2.xxapi.cn/api/baiduhot","https://api.pearktrue.cn/api/dailyhot/?title=百度"])
    if bd:
        for x in (bd.get("data") or [])[:30]:
            t = x.get("title","")
            if t:
                items.append({"title":t.strip(),"desc":x.get("desc","").strip(),"hot":str(x.get("hot","")),"source":"百度热搜"})
    wb = fetch(["https://v2.xxapi.cn/api/weibohot","https://api.pearktrue.cn/api/dailyhot/?title=微博热搜"])
    if wb:
        for x in (wb.get("data") or [])[:30]:
            t = x.get("title","")
            if t:
                items.append({"title":t.strip(),"desc":x.get("desc","").strip(),"hot":str(x.get("hot","")),"source":"微博热搜"})
    seen = set()
    uniq = []
    for it in items:
        k = it["title"][:10]
        if k not in seen and it["title"]:
            seen.add(k)
            uniq.append(it)
    print(f"获取热搜 {len(uniq)} 条（去重后）")

    ai, hot, lh = [], [], []
    for it in uniq:
        t = it["title"] + " " + it.get("desc","")
        if any(k.lower() in t.lower() for k in AI):
            ai.append(it)
            continue
        if any(k in t for k in LH):
            lh.append(it)
            continue
        hot.append(it)
    if len(ai) < 5:
        try:
            d = fetch(["https://api.pearktrue.cn/api/dailyhot/?title=36氪"])
            if d:
                for x in d.get("data",[]):
                    tt = x.get("title","") + " " + x.get("description","")
                    if any(k.lower() in tt.lower() for k in AI):
                        ai.append({"title":x.get("title","").strip(),"desc":x.get("description","").strip()[:80],"source":"36氪"})
                        if len(ai) >= 5: break
        except: pass
    while len(ai) < 5:
        ai.append({"title":"AI技术持续演进","desc":"人工智能领域发展","source":"综合"})
    while len(hot) < 5 and uniq: hot.append(uniq.pop(0))
    while len(lh) < 5 and uniq: lh.append(uniq.pop(0))
    ai, hot, lh = ai[:5], hot[:5], lh[:5]
    print(f"分类: AI={len(ai)}, 热点={len(hot)}, 民生={len(lh)}")

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

if __name__ == "__main__":
    ok = main()
    exit(0 if ok else 1)
