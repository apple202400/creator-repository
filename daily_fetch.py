#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
æ¯æ¥èªå¨éé + AI æ¹åèæ¬
- æåæé³/Bç«/å¨ç½ç­æ¦
- æåæå®å¾®ä¿¡ä¸è¾æç« 
- è°ç¨ AI æ¹åæ 10 æ¡éé¢çµæ + 10 æ¡äºåè§åº¦
- æ¨éå° GitHub Gist
ç¨æ³: python3 daily_fetch.py
ç¯å¢åé:
  GITHUB_TOKEN   - GitHub Personal Access Token (é gist æé)
  GIST_ID        - ç®æ  Gist ID (é¦æ¬¡è¿è¡å¯ä¸å¡«,ä¼èªå¨åå»ºå¹¶æå°)
  AI_API_KEY     - AI æå¡å¯é¥ (é»è®¤ç¨ DeepSeek,ä¹æ¯æ OpenAI å¼å®¹æ¥å£)
  AI_BASE_URL    - AI æ¥å£å°å (é»è®¤ DeepSeek: https://api.deepseek.com)
  AI_MODEL       - æ¨¡åå (é»è®¤ deepseek-chat)
  TRACK_KEYWORDS - èµéå³é®è¯ (ç¨ | åéå¤è¡)
  WECHAT_ACCOUNTS- å¬ä¼å·å (ç¨ | åé,ç¨äºæç´¢/æç¤º)
"""

import os
import sys
import json
import time
import hashlib
import re
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests

# ============ éç½® ============
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GIST_ID = os.environ.get("GIST_ID", "")
GIST_FILE = "creator-data.json"
GIST_DESC = "å®å¦åä½å·¥ä½å° - æ¯æ¥æ°æ®"

AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://api.deepseek.com")
AI_MODEL = os.environ.get("AI_MODEL", "deepseek-chat")

TRACK_KEYWORDS = os.environ.get("TRACK_KEYWORDS", "02年宝妈|早婚宝妈|年轻妈妈|02年当妈|二十岁宝妈|年轻全职妈妈|早婚感悟|同龄人当妈|两岁宝宝|2岁宝宝叛逆期|两岁育儿经验|幼儿早教|宝宝日常|亲子养育|两岁宝宝沟通|宝宝好习惯培养|全职宝妈日常|宝妈情绪|婚后生活|夫妻相处|宝妈自我成长|新手妈妈|宝妈内心独白|不做焦虑妈妈|母婴好物|宝宝平价好物|母婴用品|幼童穿搭|宝妈居家好物|带娃好物")
WECHAT_ACCOUNTS = os.environ.get("WECHAT_ACCOUNTS", "Cå¦å»è²|å¤§Jå°D|å°å¥³å¿è¯æ|æç­±æ¿|æ½å¹¸ç¥|æ´è§")

# 6 ä¸ªå¬ä¼å· + æç´¢å³é®è¯
WECHAT_SOURCES = WECHAT_ACCOUNTS.split("|")
TRACK_LIST = [k.strip() for k in TRACK_KEYWORDS.split("|") if k.strip()]

# åäº¬æ¶é´
BJT = timezone(timedelta(hours=8))
TODAY = datetime.now(BJT).strftime("%Y-%m-%d")
TODAY_CN = datetime.now(BJT).strftime("%mæ%dæ¥")

# ============ ç­æ¦éé ============
def fetch_douyin_hot():
    """æé³ç­æ¦ - éè¿å¬å¼æ¥å£"""
    urls = [
        "https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/",
        "https://aweme.snssdk.com/aweme/v1/hot/search/list/",
    ]
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"}
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                # ä¸åæ¥å£ç»æå¼å®¹
                items = data.get("word_list") or data.get("data", {}).get("word_list") or []
                if items:
                    return [{"title": it.get("word", ""), "hot": str(it.get("hot_value", "")), "source": "æé³ç­æ¦"} for it in items[:20]]
        except Exception as e:
            print(f"  æé³æ¥å£ {url} å¤±è´¥: {e}", file=sys.stderr)
    return []

def fetch_bili_hot():
    """Bç«ç­é¨"""
    try:
        r = requests.get("https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all", timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", {}).get("list", [])
            return [{"title": v.get("title", ""), "hot": str(v.get("stat", {}).get("view", ""))+"æ­æ¾", "source": "Bç«ç­é¨", "owner": v.get("owner", {}).get("name", "")} for v in data[:20]]
    except Exception as e:
        print(f"  Bç«æ¥å£å¤±è´¥: {e}", file=sys.stderr)
    return []

def fetch_weibo_hot():
    """å¾®åç­æä½ä¸ºå¨ç½ç­ç¹è¡¥å"""
    try:
        r = requests.get("https://weibo.com/ajax/side/hotSearch", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", {}).get("realtime", [])
            return [{"title": it.get("note", ""), "hot": str(it.get("num", "")), "source": "å¾®åç­æ"} for it in data[:20]]
    except Exception as e:
        print(f"  å¾®åæ¥å£å¤±è´¥: {e}", file=sys.stderr)
    return []

def fetch_zhihu_hot():
    """ç¥ä¹ç­æ¦"""
    try:
        r = requests.get("https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=20",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", [])
            return [{"title": it.get("target", {}).get("title", ""), "hot": str(it.get("detail_text", "")), "source": "ç¥ä¹ç­æ¦"} for it in data[:20]]
    except Exception as e:
        print(f"  ç¥ä¹æ¥å£å¤±è´¥: {e}", file=sys.stderr)
    return []

def fetch_all_hot():
    print("[1/4] ééç­æ¦...")
    all_hot = []
    all_hot.extend(fetch_douyin_hot())
    all_hot.extend(fetch_bili_hot())
    all_hot.extend(fetch_weibo_hot())
    all_hot.extend(fetch_zhihu_hot())
    # å»é
    seen = set()
    unique = []
    for it in all_hot:
        key = it["title"][:20]
        if key not in seen and it["title"]:
            seen.add(key)
            unique.append(it)
    print(f"  å±éé {len(unique)} æ¡ç­ç¹")
    return unique[:40]

# ============ å¾®ä¿¡æç« éé ============
def fetch_wechat_articles():
    """ä»æçå¾®ä¿¡æç´¢æåæå®å¬ä¼å·ææ°æç« """
    print("[2/4] ééå¾®ä¿¡æç« ...")
    all_articles = []
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"}
    for account in WECHAT_SOURCES:
        try:
            # æçå¾®ä¿¡æç´¢æ¥å£
            url = f"https://weixin.sogou.com/weixin?type=2&query={account}&ie=utf8"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                # è§£ææç´¢ç»æé¡µ
                html = r.text
                # æåæç« é¾æ¥(ç®æè§£æ,å®éå¯è½éè¦å¤çåç¬)
                titles = re.findall(r'<em[^>]*>(.*?)</em>', html)
                links = re.findall(r'href="(https?://mp\.weixin\.qq\.com[^"]+)"', html)
                for i, (title, link) in enumerate(zip(titles[:3], links[:3])):
                    clean_title = re.sub(r'<[^>]+>', '', title)
                    all_articles.append({
                        "title": clean_title,
                        "url": link,
                        "account": account,
                        "source": "å¾®ä¿¡"
                    })
            time.sleep(1)  # é¿åé¢çéå¶
        except Exception as e:
            print(f"  å¬ä¼å· {account} ééå¤±è´¥: {e}", file=sys.stderr)
    print(f"  å±éé {len(all_articles)} ç¯å¾®ä¿¡æç« ")
    return all_articles[:15]

def fetch_article_content(url):
    """æåå¾®ä¿¡æç« æ­£æ"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            html = r.text
            # æåæ é¢
            title_match = re.search(r'id="activity-name"[^>]*>(.*?)</h1>', html, re.S)
            title = title_match.group(1).strip() if title_match else ""
            # æåæ­£æ
            content_match = re.search(r'id="js_content"[^>]*>(.*?)</div>\s*<script', html, re.S)
            if content_match:
                content = re.sub(r'<[^>]+>', '', content_match.group(1)).strip()
            else:
                content = re.sub(r'<[^>]+>', '', html)[:500]
            return title, content[:800]
    except Exception as e:
        print(f"  æç« æåå¤±è´¥: {e}", file=sys.stderr)
    return "", ""

# ============ AI æ¹å ============
def ai_chat(prompt, max_tokens=4000):
    """è°ç¨ AI æ¥å£"""
    if not AI_API_KEY:
        print("  [è­¦å] æªéç½® AI_API_KEY,ä½¿ç¨æ¨¡æ¿çæ", file=sys.stderr)
        return None
    url = f"{AI_BASE_URL.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": "ä½ æ¯ä¸ä½èµæ·±æ¯å©´ç­è§é¢åå®¹ç­å,æé¿æç­ç¹è¯é¢æ¹ç¼æè´´å02å¹´æ©å©å®å¦èµåºçéé¢ãè¾åºå¿é¡»æ¯ä¸¥æ ¼ç JSON æ ¼å¼ã"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.85,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"}
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            print(f"  AI æ¥å£éè¯¯ {r.status_code}: {r.text[:200]}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"  AI è°ç¨å¤±è´¥: {e}", file=sys.stderr)
        return None

def generate_inspire(hot_list, wechat_articles):
    """çæ 10 æ¡éé¢çµæ"""
    print("[3/4] AI çæéé¢çµæ...")
    hot_text = "\n".join([f"- {h['title']} ({h['source']}, {h.get('hot','')})" for h in hot_list[:15]])
    wechat_text = "\n".join([f"- {w['title']} (æ¥èªå¬ä¼å·{w['account']})" for w in wechat_articles[:8]]) or "ææ "
    track_str = "ã".join(TRACK_LIST)

    prompt = f"""ææ¯ä¸å02å¹´æ©å©å®å¦,åæ¯å©´ç­è§é¢,èµéæ¹å:{track_str}

ä»å¤©çç­ç¹è¯é¢:
{hot_text}

åèå¬ä¼å·æç« éé¢:
{wechat_text}

è¯·åºäºä»¥ä¸ä¿¡æ¯,ä¸ºæçæ10æ¡ä»æ¥éé¢çµæãè¦æ±:
1. æ¯æ¡éé¢é½è¦è´´å"02å¹´æ©å©å®å¦"äººè®¾åæ¯å©´èµåº
2. æ é¢è¦æå¸å¼åãææç»ªå±é¸£,éåæé³/Bç«ç­è§é¢
3. æ ç­¾ä»[çæ¬¾,æç»ªå±é¸£,æ¥å¸¸,å¹²è´§,äºè®®,æé¿,çç¹,å¤«å¦»,å¯ä¸]ä¸­é1-2ä¸ª
4. è¯´æè¦è®²æ¸æ¥è¿æ¡éé¢ä¸ºä»ä¹éåæãæä¹æ

è¾åº JSON æ ¼å¼:
{{"date":"{TODAY_CN}","list":[{{"title":"","tags":[],"desc":""}}]}}

å¿é¡»è¾åº10æ¡,ä¸¥æ ¼ JSONã"""

    result = ai_chat(prompt)
    if result:
        try:
            # å°è¯æå JSON
            result = result.strip()
            if result.startswith("```"):
                result = re.sub(r'^```json?\n?', '', result)
                result = re.sub(r'\n?```$', '', result)
            data = json.loads(result)
            if "list" in data and len(data["list"]) >= 5:
                print(f"  AI çæ {len(data['list'])} æ¡éé¢çµæ")
                return data
        except json.JSONDecodeError as e:
            print(f"  JSON è§£æå¤±è´¥: {e}", file=sys.stderr)

    # fallback: æ¨¡æ¿çæ
    print("  ä½¿ç¨æ¨¡æ¿çæéé¢çµæ")
    return generate_inspire_fallback(hot_list)

def generate_inspire_fallback(hot_list):
    """æ  AI æ¶ç¨æ¨¡æ¿çæ"""
    templates = [
        ("02å¹´å®å¦ç{hot}:è¿å°±æ¯å½ä»£å¹´è½»å¦å¦ççå®æ³æ³", ["æç»ªå±é¸£", "çæ¬¾"], "ç»åç­ç¹è¯é¢,ä»02å¹´å®å¦è§è§åè¡¨çå®çæ³,å®¹æå¼ååé¢å®å¦è®¨è®º"),
        ("{hot}ç«äº,ä½å¨èå¦å¦çå°çå´æ¯å¦ä¸é¢", ["äºè®®", "æé¿"], "ååè§£è¯»ç­ç¹,è®²å®å¦è§è§çä¸åè§ç¹,å¶é è¯é¢"),
        ("æ°æå¦å¦å¦ä½åºå¯¹{hot}?è¿3ç¹å»ºè®®å¾å®ç¨", ["å¹²è´§", "å®ç¨"], "æç­ç¹è½¬åä¸ºè²å¿å¹²è´§,æ¶èçé«"),
        ("02å¹´æ©å©å®å¦çä¸å¤©:ä»{hot}è¯´èµ·", ["æ¥å¸¸", "å±é¸£"], "ç¨ç­ç¹åå¥,è®°å½çå®å¸¦å¨æ¥å¸¸"),
        ("å³äº{hot},æåèå¬åµäºä¸æ¶", ["å¤«å¦»", "æç»ª"], "æç­ç¹å«æ¥å°å¤«å¦»å³ç³»è¯é¢,å¼åè®¨è®º"),
        ("å¨èå®å¦çé±æå:çå®{hot}ææäº", ["å¹²è´§", "å¯ä¸"], "ä»ç­ç¹å»¶ä¼¸å°çé±/å¯ä¸è¯é¢"),
        ("å®å®æä¼æçäº:ä»{hot}æ³å°ç", ["æç»ªå±é¸£", "æé¿"], "æç­ç¹è½¬åä¸ºäº²å­æé¿ææ"),
        ("02å¹´å®å¦çå®æå:{hot}èåççç¸", ["çç¹", "çæ¬¾"], "è®²ç­ç¹èåççå®çç¹"),
        ("æ°æå¦å¦å´©æºç¬é´:{hot}è®©æç ´é²äº", ["æç»ª", "çç¹"], "è®°å½ç­ç¹å¼åçå´©æºç¬é´"),
        ("å¸¦å¨ä¹è½å³æ³¨{hot}?å®å¦æ¶é´ç®¡çæ¯", ["å¹²è´§", "æé¿"], "è®²å®å¦å¦ä½å¼é¡¾å¸¦å¨åå³æ³¨èªæ")
    ]
    lst = []
    for i, (tpl, tags, desc) in enumerate(templates):
        hot_title = hot_list[i % len(hot_list)]["title"] if hot_list else "ä»æ¥ç­ç¹"
        # æªæ­ç­ç¹æ é¢
        hot_short = hot_title[:15] + "â¦" if len(hot_title) > 15 else hot_title
        lst.append({
            "title": tpl.replace("{hot}", hot_short),
            "tags": tags,
            "desc": desc + f"(å³èç­ç¹:{hot_title})"
        })
    return {"date": TODAY_CN, "list": lst}

def generate_hot_angles(hot_list):
    """çæ 10 æ¡äºåè§åº¦"""
    print("[4/4] AI çæäºåè§åº¦...")
    hot_text = "\n".join([f"{i+1}. {h['title']} ({h['source']}, {h.get('hot','')})" for i, h in enumerate(hot_list[:15])])
    track_str = "ã".join(TRACK_LIST)

    prompt = f"""ææ¯ä¸å02å¹´æ©å©å®å¦,åæ¯å©´ç­è§é¢,èµéæ¹å:{track_str}

ä»æ¥ç­ç¹æ¦å:
{hot_text}

è¯·ä»è¿äºç­ç¹ä¸­æé10ä¸ª,ä¸ºæ¯ä¸ªç­ç¹è®¾è®¡ä¸ä¸ªéåæèµåºçäºåæ¹ç¼è§åº¦ãè¦æ±:
1. æ¹ç¼è§åº¦è¦è´´å"02å¹´æ©å©å®å¦"äººè®¾
2. è¦è®²æ¸æ¥æä¹æç­ç¹æ¹ç¼ææçåå®¹
3. è§åº¦è¦æå·®å¼å,ä¸è½ç´æ¥æ¬è¿

è¾åº JSON æ ¼å¼:
{{"date":"{TODAY_CN}","list":[{{"title":"ç­ç¹æ é¢","source":"æ¥æº","hot":"ç­åº¦","angle":"æ¹ç¼è§åº¦è¯´æ"}}]}}

å¿é¡»è¾åº10æ¡,ä¸¥æ ¼ JSONã"""

    result = ai_chat(prompt)
    if result:
        try:
            result = result.strip()
            if result.startswith("```"):
                result = re.sub(r'^```json?\n?', '', result)
                result = re.sub(r'\n?```$', '', result)
            data = json.loads(result)
            if "list" in data and len(data["list"]) >= 5:
                print(f"  AI çæ {len(data['list'])} æ¡äºåè§åº¦")
                return data
        except json.JSONDecodeError:
            pass

    # fallback
    print("  ä½¿ç¨æ¨¡æ¿çæäºåè§åº¦")
    angles_pool = [
        "ä»02å¹´å®å¦è§è§è¯è®ºç­ç¹,è®²èªå·±ä½ä¸ºå¹´è½»å¦å¦ççå®æå,ç¨å¯¹æ¯ææ³å¼åå±é¸£",
        "æç­ç¹è¯é¢å«æ¥å°å¸¦å¨æ¥å¸¸,è®°å½å®å®å¯¹ç­ç¹çååº,å¶é åå·®è",
        "ååè§£è¯»ç­ç¹,è®²å®å¦çå°çä¸åè§åº¦,æåºæäºè®®ä½çè¯çè§ç¹",
        "åç­ç¹è¯é¢çå¹³æ¿ç,èç¦æå¥3åå®å¦ä¹è½åå°çæ¹æ¡,å·®å¼åå®ä½",
        "ç»åå¤«å¦»å³ç³»è®²ç­ç¹,è®°å½åèå¬å¯¹ç­ç¹çä¸åçæ³,å¼åè®¨è®º",
        "æç­ç¹è½¬åä¸ºè²å¿å¹²è´§,è®²æ°æå¦å¦å¦ä½åºå¯¹ç±»ä¼¼æåµ,æé«æ¶èç",
        "ç¨æç»ªå±é¸£ææ³è®²ç­ç¹,è®°å½ç­ç¹å¼åçå´©æºææå¨ç¬é´",
        "åç­ç¹è¯é¢ççé±ç,è®²å¨èå®å¦çä½ææ¬åºå¯¹æ¹æ¡",
        "ä»æé¿è§è§è®²ç­ç¹,åäº«å¸¦å¨æé´å³æ³¨ç­ç¹çèªææé¿ææ",
        "æç­ç¹åå¯ä¸ç»å,è®²å®å¦å¦ä½æç­ç¹åæåå®¹åä½ç´ æ"
    ]
    lst = []
    for i in range(10):
        h = hot_list[i % len(hot_list)] if hot_list else {"title": f"ä»æ¥ç­ç¹{i+1}", "source": "å¨ç½", "hot": "ç­åº¦ä¸å"}
        lst.append({
            "title": h["title"],
            "source": h.get("source", ""),
            "hot": h.get("hot", ""),
            "angle": angles_pool[i % len(angles_pool)]
        })
    return {"date": TODAY_CN, "list": lst}

# ============ Gist æ¨é ============
def push_to_gist(data):
    """æ¨éæ°æ®å° GitHub Gist"""
    print("æ¨éæ°æ®å° Gist...")
    if not GITHUB_TOKEN:
        print("  [è­¦å] æªéç½® GITHUB_TOKEN,è·³è¿æ¨é", file=sys.stderr)
        print(f"  æ°æ®å·²ä¿å­å°æ¬å°: daily_output_{TODAY}.json", file=sys.stderr)
        with open(f"daily_output_{TODAY}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return False

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    content = json.dumps(data, ensure_ascii=False, indent=2)
    payload = {
        "description": GIST_DESC,
        "files": {
            GIST_FILE: {"content": content}
        }
    }

    if GIST_ID:
        # æ´æ°å·²æ Gist
        url = f"https://api.github.com/gists/{GIST_ID}"
        r = requests.patch(url, headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            print(f"  Gist å·²æ´æ°: https://gist.github.com/{GIST_ID}")
            return True
        else:
            print(f"  Gist æ´æ°å¤±è´¥ {r.status_code}: {r.text[:200]}", file=sys.stderr)
            return False
    else:
        # åå»ºæ° Gist
        payload["public"] = True
        r = requests.post("https://api.github.com/gists", headers=headers, json=payload, timeout=30)
        if r.status_code == 201:
            gist_id = r.json()["id"]
            print(f"\n{'='*50}")
            print(f"â Gist åå»ºæå!")
            print(f"GIST_ID = {gist_id}")
            print(f"ç½å: https://gist.github.com/{gist_id}")
            print(f"è¯·æ GIST_ID={gist_id} å å°èªå¨åç¯å¢åéä¸­")
            print(f"{'='*50}\n")
            # ä¿å­å°æä»¶ä¾åç»­ä½¿ç¨
            with open("gist_id.txt", "w") as f:
                f.write(gist_id)
            return True
        else:
            print(f"  Gist åå»ºå¤±è´¥ {r.status_code}: {r.text[:200]}", file=sys.stderr)
            return False

# ============ ä¸»æµç¨ ============
def main():
    print(f"\n{'='*50}")
    print(f"å®å¦åä½å·¥ä½å° - æ¯æ¥ééä»»å¡")
    print(f"æ¶é´: {TODAY} {TODAY_CN}")
    print(f"èµé: {TRACK_KEYWORDS}")
    print(f"ï¿½ï¿½ï¿½ä¼å·: {WECHAT_ACCOUNTS}")
    print(f"{'='*50}\n")

    # 1. ééç­æ¦
    hot_list = fetch_all_hot()

    # 2. ééå¾®ä¿¡æç« 
    wechat_articles = fetch_wechat_articles()

    # 3. AI çæéé¢çµæ
    inspire_data = generate_inspire(hot_list, wechat_articles)

    # 4. AI çæäºåè§åº¦
    hot_data = generate_hot_angles(hot_list)

    # 5. ç»è£æ°æ®
    output = {
        "date": TODAY,
        "updated": datetime.now(BJT).isoformat(),
        "inspire": inspire_data,
        "hot": hot_data,
        "wechat_articles": wechat_articles[:5]  # é¡ºä¾¿æ¨éå ç¯å¾®ä¿¡æç« ä¾éç®/ç³è®ºæ¨¡åç¨
    }

    # 6. æ¨éå° Gist
    ok = push_to_gist(output)

    # æ¬å°å¤ä»½
    with open(f"daily_output_{TODAY}.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\næ¬å°å¤ä»½: daily_output_{TODAY}.json")

    if ok:
        print("\nâ ä»»å¡å®æ!")
    else:
        print("\nâ ï¸ ä»»å¡å®æ(ä½ Gist æ¨éå¤±è´¥,æ°æ®å·²å­æ¬å°)")

    return ok

if __name__ == "__main__":
    main()
