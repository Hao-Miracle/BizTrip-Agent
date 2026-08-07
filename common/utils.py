"""
公共工具函数
- decode_str: 邮件标题/发件人解码
- get_email_config: 邮箱配置读取（自动推断 IMAP 服务器）
"""

import os
from datetime import datetime
from email.header import decode_header


def decode_str(s):
    """解码邮件标题等字段"""
    if not s:
        return ''
    parts = decode_header(s)
    result = []
    for content, charset in parts:
        if isinstance(content, bytes):
            try:
                result.append(content.decode(charset or 'utf-8', errors='replace'))
            except Exception:
                result.append(content.decode('utf-8', errors='replace'))
        else:
            result.append(content)
    return ''.join(result)


def get_email_config():
    """获取邮箱配置，支持通用变量 + 向后兼容旧 QQ_EMAIL 变量"""
    account = os.getenv('EMAIL_ACCOUNT', '') or os.getenv('QQ_EMAIL', '')
    password = os.getenv('EMAIL_PASSWORD', '') or os.getenv('QQ_AUTH_CODE', '')
    server = os.getenv('EMAIL_IMAP_SERVER', '') or os.getenv('QQ_IMAP_SERVER', '')
    port = int(os.getenv('EMAIL_IMAP_PORT', '') or os.getenv('QQ_IMAP_PORT', '0'))

    if not server:
        if '@qq.com' in account:
            server = 'imap.qq.com'
        elif '@163.com' in account:
            server = 'imap.163.com'
        elif '@126.com' in account:
            server = 'imap.126.com'
        elif '@gmail.com' in account:
            server = 'imap.gmail.com'
        elif '@outlook.com' in account or '@hotmail.com' in account:
            server = 'outlook.office365.com'
        else:
            server = 'imap.qq.com'

    if not port:
        port = 993

    return account, password, server, port


def format_chinese_date(value=None):
    """Format a date without relying on the operating system locale codec."""
    value = value or datetime.now()
    return f"{value.year:04d}年{value.month:02d}月{value.day:02d}日"
