"""
模块 · LLM 路由分类
使用 DeepSeek API 智能判断邮件品类，低置信度自动降级到正则规则。

用法：
    from phase2.llm_classify import classify_email

设计：
    - API Key 未配置 → 直接走规则引擎（compat）
    - LLM 返回低置信度 → 降级到正则
    - LLM 成功 → 返回品类 + 置信度
"""

import os
import json
import re
import sys

try:
    from .llm_options import structured_output_options
except ImportError:
    from llm_options import structured_output_options

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.rules import DOMAIN_RULES, KEYWORD_RULES, SPAM_DOMAINS

# ---------- 品类列表 ----------
CATEGORIES = ['机票', '火车票', '酒店', '网约车', '发票', '门票', '不相关']

# ---------- LLM 客户端（延迟初始化，兼容 DeepSeek 旧变量名做向下兼容）----------
_client = None


def _get_client():
    """获取 OpenAI 客户端，未配置 API Key 返回 None。支持任何 OpenAI 兼容服务商。"""
    global _client
    if _client is not None:
        return _client

    # 优先用 LLM_API_KEY，向下兼容 DEEPSEEK_API_KEY
    api_key = os.getenv('LLM_API_KEY', '') or os.getenv('DEEPSEEK_API_KEY', '')
    if not api_key or api_key.startswith('sk-your-'):
        _client = False
        return None

    base_url = os.getenv('LLM_BASE_URL', '') or os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
    try:
        from openai import OpenAI
    except ImportError:
        _client = False
        return None

    _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client


def _get_model():
    return os.getenv('LLM_MODEL', '') or os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')


# ---------- LLM 分类 ----------

CLASSIFY_PROMPT = """判断以下邮件是否与出差/旅行相关，并归类。

邮件标题：{subject}
发件人：{sender}
邮件正文前500字：{body_preview}

分类选项（7选1）：机票、火车票、酒店、网约车、发票、门票、不相关

判断标准：
- 机票：航班确认、电子客票行程单、登机提醒
- 火车票：12306购票通知、车票确认
- 酒店：酒店预订确认、入住通知
- 网约车：打车行程单、网约车电子发票
- 发票：增值税发票、电子发票、通行费发票
- 门票：演出/景点/活动门票
- 不相关：广告、社交、电商、银行通知等非出行邮件

严格按以下 JSON 格式输出，不要输出其他内容：
{{"category": "机票", "confidence": 0.95}}"""


def llm_classify(subject, sender, body_preview):
    """
    LLM 分类单封邮件。
    返回: dict with category, confidence or None（API未配置/调用失败）
    """
    client = _get_client()
    if client is None:
        return None

    model = _get_model()

    try:
        prompt = CLASSIFY_PROMPT.format(
            subject=subject,
            sender=sender,
            body_preview=body_preview[:500]
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.0,
            max_tokens=100,
            **structured_output_options(model),
        )
        raw = resp.choices[0].message.content.strip()

        # 尝试提取 JSON
        m = re.search(r'\{[^}]+\}', raw)
        if m:
            result = json.loads(m.group(0))
            if result.get('category') in CATEGORIES and isinstance(result.get('confidence'), (int, float)):
                return {
                    'category': result['category'],
                    'confidence': float(result['confidence']),
                    'method': 'LLM'
                }
    except Exception:
        pass

    return None


# ---------- 降级规则（复用 Phase 1 逻辑，轻量版）----------

def rule_classify(sender, subject):
    """正则降级分类"""
    sl = sender.lower()
    subject_lower = subject.lower()

    # 黑名单
    if any(d in sl for d in SPAM_DOMAINS):
        return {'category': '不相关', 'confidence': 1.0, 'method': '黑名单'}

    # 主题证据优先。平台域名只能增强置信度，不能单独证明它是报销邮件。
    for cat, keywords in KEYWORD_RULES.items():
        for kw in keywords:
            if kw.lower() in subject_lower:
                domains = DOMAIN_RULES.get(cat, [])
                method = '域名+关键词' if any(domain in sl for domain in domains) else '关键词匹配'
                confidence = 0.9 if method == '域名+关键词' else 0.7
                return {'category': cat, 'confidence': confidence, 'method': method}

    return {'category': '不相关', 'confidence': 0.5, 'method': '无匹配'}


# ---------- 主入口 ----------

CONFIDENCE_THRESHOLD = 0.7


def classify_email(subject, sender, body_preview, use_llm=True):
    """
    分类单封邮件。

    策略：
    1. 规则能可靠识别时直接返回
    2. 规则无法识别时才调用 LLM
    3. 返回统一格式
    """
    rule_result = rule_classify(sender, subject)
    if rule_result['method'] != '无匹配':
        return rule_result

    llm_result = llm_classify(subject, sender, body_preview) if use_llm else None
    if llm_result and llm_result['confidence'] >= CONFIDENCE_THRESHOLD:
        return llm_result

    if llm_result:
        return {**rule_result, 'llm_category': llm_result['category'], 'llm_confidence': llm_result['confidence']}

    return rule_result


def has_api_key():
    """检查是否配置了有效的 API Key 且安装了 LLM 客户端依赖"""
    key = os.getenv('LLM_API_KEY', '') or os.getenv('DEEPSEEK_API_KEY', '')
    if not key or key.startswith('sk-your-'):
        return False
    try:
        import openai  # noqa: F401
    except ImportError:
        return False
    return True


if __name__ == '__main__':
    # 简单测试
    test_sender = 'service@qunar.com'
    test_subject = '【去哪儿网】机票电子发票-行程单'
    test_body = '您的机票已出票，航班 CA1234，北京→上海，金额1280.00元'

    result = classify_email(test_subject, test_sender, test_body)
    print(f'分类结果: {result}')
    print(f'API Key 配置: {"已配置" if has_api_key() else "未配置（纯规则模式）"}')
