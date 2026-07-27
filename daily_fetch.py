#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日自动采集 + AI 改写脚本
- 抓取抖音/B站/全网热榜
- 抓取指定微信专辑文章
- 调用 AI 改写成 10 条选题灵感 + 10 条二创角度
- 推送到 GitHub Gist
用法: python3 daily_fetch.py
环境变量:
  GITHUB_TOKEN   - GitHub Personal Access Token (需 gist 权限)
  GIST_ID        - 目标 Gist ID (首次运行可不填,会自动创建并打印)
  AI_API_KEY     - AI 服务密钥 (默认用 DeepSeek,也支持 OpenAI 兼容接口)
  AI_BASE_URL    - AI 接口地址 (默认 DeepSeek: https://api.deepseek.com)
  AI_MODEL       - 模型名 (默认 deepseek-chat)
  TRACK_KEYWORDS - 赛道关键词 (用 | 分隔多行)
  WECHAT_ACCOUNTS- 公众号名 (用 | 分隔,用于搜索/提示)
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

# ============ 配置 ============
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GIST_ID = os.environ.get("GIST_ID", "")
GIST_FILE = "creator-data.json"
GIST_DESC = "宝妈创作工作台 - 每日数据"

AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://api.deepseek.com")
AI_MODEL = os.environ.get("AI_MODEL", "deepseek-chat")

TRACK_KEYWORDS = os.environ.get("TRACK_KEYWORDS", "02年早婚宝妈日常|新手育儿经验|年轻妈妈情绪共鸣|亲子养育|夫妻相处|全职宝妈自我成长|普通人婚后真实生活感悟|母婴生活短视频文案创作")
WECHAT_ACCOUNTS = os.environ.get("WECHAT_ACCOUNTS", "C妈养育|大J小D|少女心诊所|李筱懿|潘幸知|洞见")

# 6 个公众号 + 搜索关键词
WECHAT_SOURCES = WECHAT_ACCOUNTS.split("|")
TRACK_LIST = [k.strip() for k in TRACK_KEYWORDS.split("|") if k.strip()]

# 北京时间
BJT = timezone(timedelta(hours=8))
TODAY = datetime.now(BJT).strftime("%Y-%m-%d")
TODAY_CN = datetime.now(BJT).strftime("%m月%d日")

# ============ 热榜采集 ============
def fetch_douyin_hot():
    """抖音热榜 - 通过公开接口"""
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
                # 不同接口结构兼容
                items = data.get("word_list") or data.get("data", {}).get("word_list") or []
                if items:
                    return [{"title": it.get("word", ""), "hot": str(it.get("hot_value", "")), "source": "抖音热榜"} for it in items[:20]]
        except Exception as e:
            print(f"  抖音接口 {url} 失败: {e}", file=sys.stderr)
    return []

def fetch_bili_hot():
    """B站热门"""
    try:
        r = requests.get("https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all", timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", {}).get("list", [])
            return [{"title": v.get("title", ""), "hot": str(v.get("stat", {}).get("view", ""))+"播放", "source": "B站热门", "owner": v.get("owner", {}).get("name", "")} for v in data[:20]]
    except Exception as e:
        print(f"  B站接口失败: {e}", file=sys.stderr)
    return []

def fetch_weibo_hot():
    """微博热搜作为全网热点补充"""
    try:
        r = requests.get("https://weibo.com/ajax/side/hotSearch", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", {}).get("realtime", [])
            return [{"title": it.get("note", ""), "hot": str(it.get("num", "")), "source": "微博热搜"} for it in data[:20]]
    except Exception as e:
        print(f"  微博接口失败: {e}", file=sys.stderr)
    return []

def fetch_zhihu_hot():
    """知乎热榜"""
    try:
        r = requests.get("https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=20",
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", [])
            return [{"title": it.get("target", {}).get("title", ""), "hot": str(it.get("detail_text", "")), "source": "知乎热榜"} for it in data[:20]]
    except Exception as e:
        print(f"  知乎接口失败: {e}", file=sys.stderr)
    return []

def fetch_all_hot():
    print("[1/4] 采集热榜...")
    all_hot = []
    all_hot.extend(fetch_douyin_hot())
    all_hot.extend(fetch_bili_hot())
    all_hot.extend(fetch_weibo_hot())
    all_hot.extend(fetch_zhihu_hot())
    # 去重
    seen = set()
    unique = []
    for it in all_hot:
        key = it["title"][:20]
        if key not in seen and it["title"]:
            seen.add(key)
            unique.append(it)
    print(f"  共采集 {len(unique)} 条热点")
    return unique[:40]

# ============ 微信文章采集 ============
def fetch_wechat_articles():
    """从搜狗微信搜索抓取指定公众号最新文章"""
    print("[2/4] 采集微信文章...")
    all_articles = []
    headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"}
    for account in WECHAT_SOURCES:
        try:
            # 搜狗微信搜索接口
            url = f"https://weixin.sogou.com/weixin?type=2&query={account}&ie=utf8"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                # 解析搜索结果页
                html = r.text
                # 提取文章链接(简易解析,实际可能需要处理反爬)
                titles = re.findall(r'<em[^>]*>(.*?)</em>', html)
                links = re.findall(r'href="(https?://mp\.weixin\.qq\.com[^"]+)"', html)
                for i, (title, link) in enumerate(zip(titles[:3], links[:3])):
                    clean_title = re.sub(r'<[^>]+>', '', title)
                    all_articles.append({
                        "title": clean_title,
                        "url": link,
                        "account": account,
                        "source": "微信"
                    })
            time.sleep(1)  # 避免频率限制
        except Exception as e:
            print(f"  公众号 {account} 采集失败: {e}", file=sys.stderr)
    print(f"  共采集 {len(all_articles)} 篇微信文章")
    return all_articles[:15]

def fetch_article_content(url):
    """抓取微信文章正文"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            html = r.text
            # 提取标题
            title_match = re.search(r'id="activity-name"[^>]*>(.*?)</h1>', html, re.S)
            title = title_match.group(1).strip() if title_match else ""
            # 提取正文
            content_match = re.search(r'id="js_content"[^>]*>(.*?)</div>\s*<script', html, re.S)
            if content_match:
                content = re.sub(r'<[^>]+>', '', content_match.group(1)).strip()
            else:
                content = re.sub(r'<[^>]+>', '', html)[:500]
            return title, content[:800]
    except Exception as e:
        print(f"  文章抓取失败: {e}", file=sys.stderr)
    return "", ""

# ============ AI 改写 ============
def ai_chat(prompt, max_tokens=4000):
    """调用 AI 接口"""
    if not AI_API_KEY:
        print("  [警告] 未配置 AI_API_KEY,使用模板生成", file=sys.stderr)
        return None
    url = f"{AI_BASE_URL.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": "你是一位资深母婴短视频内容策划,擅长把热点话题改编成贴合02年早婚宝妈赛区的选题。输出必须是严格的 JSON 格式。"},
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
            print(f"  AI 接口错误 {r.status_code}: {r.text[:200]}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"  AI 调用失败: {e}", file=sys.stderr)
        return None

def generate_inspire(hot_list, wechat_articles):
    """生成 10 条选题灵感"""
    print("[3/4] AI 生成选题灵感...")
    hot_text = "\n".join([f"- {h['title']} ({h['source']}, {h.get('hot','')})" for h in hot_list[:15]])
    wechat_text = "\n".join([f"- {w['title']} (来自公众号{w['account']})" for w in wechat_articles[:8]]) or "暂无"
    track_str = "、".join(TRACK_LIST)

    prompt = f"""我是一名02年早婚宝妈,做母婴短视频,赛道方向:{track_str}

今天的热点话题:
{hot_text}

参考公众号文章选题:
{wechat_text}

请基于以上信息,为我生成10条今日选题灵感。要求:
1. 每条选题都要贴合"02年早婚宝妈"人设和母婴赛区
2. 标题要有吸引力、有情绪共鸣,适合抖音/B站短视频
3. 标签从[爆款,情绪共鸣,日常,干货,争议,成长,痛点,夫妻,副业]中选1-2个
4. 说明要讲清楚这条选题为什么适合我、怎么拍

输出 JSON 格式:
{{"date":"{TODAY_CN}","list":[{{"title":"","tags":[],"desc":""}}]}}

必须输出10条,严格 JSON。"""

    result = ai_chat(prompt)
    if result:
        try:
            # 尝试提取 JSON
            result = result.strip()
            if result.startswith("```"):
                result = re.sub(r'^```json?\n?', '', result)
                result = re.sub(r'\n?```$', '', result)
            data = json.loads(result)
            if "list" in data and len(data["list"]) >= 5:
                print(f"  AI 生成 {len(data['list'])} 条选题灵感")
                return data
        except json.JSONDecodeError as e:
            print(f"  JSON 解析失败: {e}", file=sys.stderr)

    # fallback: 模板生成
    print("  使用模板生成选题灵感")
    return generate_inspire_fallback(hot_list)

def generate_inspire_fallback(hot_list):
    """无 AI 时用模板生成"""
    templates = [
        ("02年宝妈看{hot}:这就是当代年轻妈妈的真实想法", ["情绪共鸣", "爆款"], "结合热点话题,从02年宝妈视角发表真实看法,容易引发同频宝妈讨论"),
        ("{hot}火了,但全职妈妈看到的却是另一面", ["争议", "成长"], "反向解读热点,讲宝妈视角的不同观点,制造话题"),
        ("新手妈妈如何应对{hot}?这3点建议很实用", ["干货", "实用"], "把热点转化为育儿干货,收藏率高"),
        ("02年早婚宝妈的一天:从{hot}说起", ["日常", "共鸣"], "用热点切入,记录真实带娃日常"),
        ("关于{hot},我和老公吵了一架", ["夫妻", "情绪"], "把热点嫁接到夫妻关系话题,引发讨论"),
        ("全职宝妈省钱指南:看完{hot}我悟了", ["干货", "副业"], "从热点延伸到省钱/副业话题"),
        ("宝宝教会我的事:从{hot}想到的", ["情绪共鸣", "成长"], "把热点转化为亲子成长感悟"),
        ("02年宝妈真实感受:{hot}背后的真相", ["痛点", "爆款"], "讲热点背后的真实痛点"),
        ("新手妈妈崩溃瞬间:{hot}让我破防了", ["情绪", "痛点"], "记录热点引发的崩溃瞬间"),
        ("带娃也能关注{hot}?宝妈时间管理术", ["干货", "成长"], "讲宝妈如何兼顾带娃和关注自我")
    ]
    lst = []
    for i, (tpl, tags, desc) in enumerate(templates):
        hot_title = hot_list[i % len(hot_list)]["title"] if hot_list else "今日热点"
        # 截断热点标题
        hot_short = hot_title[:15] + "…" if len(hot_title) > 15 else hot_title
        lst.append({
            "title": tpl.replace("{hot}", hot_short),
            "tags": tags,
            "desc": desc + f"(关联热点:{hot_title})"
        })
    return {"date": TODAY_CN, "list": lst}

def generate_hot_angles(hot_list):
    """生成 10 条二创角度"""
    print("[4/4] AI 生成二创角度...")
    hot_text = "\n".join([f"{i+1}. {h['title']} ({h['source']}, {h.get('hot','')})" for i, h in enumerate(hot_list[:15])])
    track_str = "、".join(TRACK_LIST)

    prompt = f"""我是一名02年早婚宝妈,做母婴短视频,赛道方向:{track_str}

今日热点榜单:
{hot_text}

请从这些热点中挑选10个,为每个热点设计一个适合我赛区的二创改编角度。要求:
1. 改编角度要贴合"02年早婚宝妈"人设
2. 要讲清楚怎么把热点改编成我的内容
3. 角度要有差异化,不能直接搬运

输出 JSON 格式:
{{"date":"{TODAY_CN}","list":[{{"title":"热点标题","source":"来源","hot":"热度","angle":"改编角度说明"}}]}}

必须输出10条,严格 JSON。"""

    result = ai_chat(prompt)
    if result:
        try:
            result = result.strip()
            if result.startswith("```"):
                result = re.sub(r'^```json?\n?', '', result)
                result = re.sub(r'\n?```$', '', result)
            data = json.loads(result)
            if "list" in data and len(data["list"]) >= 5:
                print(f"  AI 生成 {len(data['list'])} 条二创角度")
                return data
        except json.JSONDecodeError:
            pass

    # fallback
    print("  使用模板生成二创角度")
    angles_pool = [
        "从02年宝妈视角评论热点,讲自己作为年轻妈妈的真实感受,用对比手法引发共鸣",
        "把热点话题嫁接到带娃日常,记录宝宝对热点的反应,制造反差萌",
        "反向解读热点,讲宝妈看到的不同角度,提出有争议但真诚的观点",
        "做热点话题的平替版,聚焦月入3千宝妈也能做到的方案,差异化定位",
        "结合夫妻关系讲热点,记录和老公对热点的不同看法,引发讨论",
        "把热点转化为育儿干货,讲新手妈妈如何应对类似情况,提高收藏率",
        "用情绪共鸣手法讲热点,记录热点引发的崩溃或感动瞬间",
        "做热点话题的省钱版,讲全职宝妈的低成本应对方案",
        "从成长视角讲热点,分享带娃期间关注热点的自我成长感悟",
        "把热点和副业结合,讲宝妈如何把热点变成内容创作素材"
    ]
    lst = []
    for i in range(10):
        h = hot_list[i % len(hot_list)] if hot_list else {"title": f"今日热点{i+1}", "source": "全网", "hot": "热度上升"}
        lst.append({
            "title": h["title"],
            "source": h.get("source", ""),
            "hot": h.get("hot", ""),
            "angle": angles_pool[i % len(angles_pool)]
        })
    return {"date": TODAY_CN, "list": lst}

# ============ Gist 推送 ============
def push_to_gist(data):
    """推送数据到 GitHub Gist"""
    print("推送数据到 Gist...")
    if not GITHUB_TOKEN:
        print("  [警告] 未配置 GITHUB_TOKEN,跳过推送", file=sys.stderr)
        print(f"  数据已保存到本地: daily_output_{TODAY}.json", file=sys.stderr)
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
        # 更新已有 Gist
        url = f"https://api.github.com/gists/{GIST_ID}"
        r = requests.patch(url, headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            print(f"  Gist 已更新: https://gist.github.com/{GIST_ID}")
            return True
        else:
            print(f"  Gist 更新失败 {r.status_code}: {r.text[:200]}", file=sys.stderr)
            return False
    else:
        # 创建新 Gist
        payload["public"] = True
        r = requests.post("https://api.github.com/gists", headers=headers, json=payload, timeout=30)
        if r.status_code == 201:
            gist_id = r.json()["id"]
            print(f"\n{'='*50}")
            print(f"✅ Gist 创建成功!")
            print(f"GIST_ID = {gist_id}")
            print(f"网址: https://gist.github.com/{gist_id}")
            print(f"请把 GIST_ID={gist_id} 加到自动化环境变量中")
            print(f"{'='*50}\n")
            # 保存到文件供后续使用
            with open("gist_id.txt", "w") as f:
                f.write(gist_id)
            return True
        else:
            print(f"  Gist 创建失败 {r.status_code}: {r.text[:200]}", file=sys.stderr)
            return False

# ============ 主流程 ============
def main():
    print(f"\n{'='*50}")
    print(f"宝妈创作工作台 - 每日采集任务")
    print(f"时间: {TODAY} {TODAY_CN}")
    print(f"赛道: {TRACK_KEYWORDS}")
    print(f"���众号: {WECHAT_ACCOUNTS}")
    print(f"{'='*50}\n")

    # 1. 采集热榜
    hot_list = fetch_all_hot()

    # 2. 采集微信文章
    wechat_articles = fetch_wechat_articles()

    # 3. AI 生成选题灵感
    inspire_data = generate_inspire(hot_list, wechat_articles)

    # 4. AI 生成二创角度
    hot_data = generate_hot_angles(hot_list)

    # 5. 组装数据
    output = {
        "date": TODAY,
        "updated": datetime.now(BJT).isoformat(),
        "inspire": inspire_data,
        "hot": hot_data,
        "wechat_articles": wechat_articles[:5]  # 顺便推送几篇微信文章供速算/申论模块用
    }

    # 6. 推送到 Gist
    ok = push_to_gist(output)

    # 本地备份
    with open(f"daily_output_{TODAY}.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n本地备份: daily_output_{TODAY}.json")

    if ok:
        print("\n✅ 任务完成!")
    else:
        print("\n⚠️ 任务完成(但 Gist 推送失败,数据已存本地)")

    return ok

if __name__ == "__main__":
    main()
