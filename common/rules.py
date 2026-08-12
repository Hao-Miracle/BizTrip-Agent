"""
分类规则数据 —— 单一数据源，所有模块统一引用。

包含：
- DOMAIN_RULES: 域名匹配规则（按发件人域名分类）
- KEYWORD_RULES: 关键词匹配规则（按主题/正文关键词分类）
- SPAM_DOMAINS: 垃圾/无关域名黑名单
"""

# 域名匹配 —— 发件人域名包含以下关键词即归类
DOMAIN_RULES = {
    '机票': [
        'qunar.com', 'ctrip.com', 'fliggy.com', 'alitrip.com',
        'airchina', 'ceair.com', 'csair.com', 'chinamobile.com',
        'bookings.com', 'expedia', 'skyscanner', 'trip.com',
    ],
    '火车票': [
        '12306.cn', 'zhixing.com', 'tiexing.com',
    ],
    '酒店': [
        'booking.com', 'agoda.com', 'airbnb.com',
        'meituan.com', 'dianping.com', 'elong.com', 'huazhuhotels.com',
    ],
    '网约车': [
        'didiglobal.com', 'didipinduo.com', 'xiaojukeji.com', 'uber.com',
        'gaode.com', 'shouqiev.com', 'amap.com',
    ],
    '发票': [
        'crestv.cn', 'fapiao.com', 'invoice.', 'txffp.com',
    ],
    '门票': [
        'damai.cn', 'maoyan.com', 'taobao.com/ticket', 'showstart.com',
    ],
}

# 关键词匹配 —— 主题包含以下关键词即归入对应类别
KEYWORD_RULES = {
    '机票': ['机票', '航班', '登机', '值机', '航空', 'flight', 'boarding'],
    '火车票': ['火车票', '高铁', '动车', '12306', '车票', 'train'],
    '酒店': ['酒店', '民宿', '入住', '预订成功', 'booking confirmation', 'hotel'],
    '网约车': ['滴滴', '高德打车', '打车', '网约车', '行程', '快车', '专车', '出租车'],
    '发票': ['发票', 'invoice', '报销', '电子凭证', 'receipt', 'fapiao'],
    '门票': ['门票', '演出', '景点', '展览', '入场券', 'ticket'],
}

# 广告/无关域名黑名单 —— 包含这些域名的直接跳过
SPAM_DOMAINS = [
    'job51', '51job', 'steampowered', 'email.apple.com',
    'amazon', 'jd.com', 'taobao.com', 'tmall.com', 'pinduoduo',
    'weixin', 'alipay', '10000@', '10086@', 'cmbchina', '2ksports',
]
