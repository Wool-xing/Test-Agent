# SPDX-License-Identifier: MIT
"""
神圣性与跨文化禁忌矩阵 — Phase 5.

覆盖 15 个 locale 的禁忌维度:
  - 禁忌词 (宗教/政治/社会敏感词)
  - 禁忌色 (丧葬/喜庆/宗教颜色)
  - 禁忌数 (不吉数字/楼层/日期)
  - 禁忌节日组合 (节日营销限制/斋月/纪念日)
  - 神圣场景规则 (宗教场所/葬礼/儿童/纪念)

被引用方: i18n_checker.py (taboo audit) / testcase-designer / 全球化产品合规.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ── Severity ──

class Severity(str, Enum):
    CRITICAL = "critical"   # 宗教亵渎 / 法律红线
    HIGH = "high"           # 严重文化冒犯
    MEDIUM = "medium"       # 潜在误解或不适

# ── Taboo category ──

class TabooCategory(str, Enum):
    WORD = "word"
    COLOR = "color"
    NUMBER = "number"
    HOLIDAY = "holiday"
    SACRED_CONTEXT = "sacred_context"


@dataclass
class TabooEntry:
    """Single taboo item with locale, category, severity, and remediation."""
    locale: str
    category: TabooCategory
    item: str
    severity: Severity
    reason: str
    remediation: str = ""
    contexts: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# TABOO WORDS — words/phrases that may offend or violate norms
# ═══════════════════════════════════════════════════════════════

TABOO_WORDS: list[dict[str, Any]] = [
    # ── zh-CN ──
    {"locale": "zh-CN", "word": "台独", "severity": Severity.CRITICAL, "reason": "分裂国家言论，违反《反分裂国家法》", "contexts": ["政治", "地图标注", "内容审核"]},
    {"locale": "zh-CN", "word": "藏独", "severity": Severity.CRITICAL, "reason": "分裂主义，危害国家统一", "contexts": ["政治", "国际内容"]},
    {"locale": "zh-CN", "word": "法轮功", "severity": Severity.CRITICAL, "reason": "被依法取缔的邪教组织", "contexts": ["宗教", "内容审核"]},
    {"locale": "zh-CN", "word": "天安门事件", "severity": Severity.CRITICAL, "reason": "敏感历史话题", "contexts": ["历史", "政治", "UGC"]},
    {"locale": "zh-CN", "word": "六四", "severity": Severity.CRITICAL, "reason": "敏感日期/事件引用", "contexts": ["日期", "历史", "数字"]},
    {"locale": "zh-CN", "word": "大法", "severity": Severity.HIGH, "reason": "与邪教组织关联词", "contexts": ["宗教", "健康"]},

    # ── zh-TW ──
    {"locale": "zh-TW", "word": "大陸妹", "severity": Severity.HIGH, "reason": "对大陆女性的歧视性称呼", "contexts": ["日常用语", "餐饮"]},
    {"locale": "zh-TW", "word": "支那", "severity": Severity.CRITICAL, "reason": "对中国的侮辱性称呼", "contexts": ["政治", "历史"]},

    # ── ja-JP ──
    {"locale": "ja-JP", "word": "部落民", "severity": Severity.CRITICAL, "reason": "部落歧视问题 (burakumin)，高度敏感", "contexts": ["社会", "户籍", "婚姻"]},
    {"locale": "ja-JP", "word": "気違い", "severity": Severity.HIGH, "reason": "对精神疾患的歧视用语 (禁止播出词)", "contexts": ["健康", "日常用语"]},
    {"locale": "ja-JP", "word": "めくら", "severity": Severity.HIGH, "reason": "对视觉障碍者的歧视用语", "contexts": ["日常用语", "健康"]},
    {"locale": "ja-JP", "word": "つんぼ", "severity": Severity.HIGH, "reason": "对听觉障碍者的歧视用语", "contexts": ["日常用语", "健康"]},
    {"locale": "ja-JP", "word": "天皇批判", "severity": Severity.CRITICAL, "reason": "对天皇的直接批判可能引发极右翼激烈反应", "contexts": ["政治", "媒体"]},

    # ── ko-KR ──
    {"locale": "ko-KR", "word": "빨갱이", "severity": Severity.CRITICAL, "reason": "赤色分子，朝鲜战争遗留仇恨用语", "contexts": ["政治", "社会"]},
    {"locale": "ko-KR", "word": "짱깨", "severity": Severity.HIGH, "reason": "对中国人的歧视性称呼", "contexts": ["日常用语"]},
    {"locale": "ko-KR", "word": "쪽바리", "severity": Severity.HIGH, "reason": "对日本人的歧视性称呼", "contexts": ["日常用语", "历史"]},

    # ── ar-SA ──
    {"locale": "ar-SA", "word": "كفر", "severity": Severity.CRITICAL, "reason": "异教徒/不信道者，亵渎指控可能触发法律后果", "contexts": ["宗教"]},
    {"locale": "ar-SA", "word": "شرك", "severity": Severity.CRITICAL, "reason": "以物配主，伊斯兰教最严重指控", "contexts": ["宗教", "神学"]},
    {"locale": "ar-SA", "word": "إلحاد", "severity": Severity.CRITICAL, "reason": "无神论，在部分伊斯兰国家为刑事犯罪", "contexts": ["宗教", "哲学"]},
    {"locale": "ar-SA", "word": "سب النبي", "severity": Severity.CRITICAL, "reason": "亵渎先知，可触发死刑 (沙特/巴基斯坦)", "contexts": ["宗教", "法律"]},

    # ── he-IL ──
    {"locale": "he-IL", "word": "שואה", "severity": Severity.CRITICAL, "reason": "大屠杀 (Holocaust)，不可轻率使用或比较", "contexts": ["历史", "政治", "比喻"]},
    {"locale": "he-IL", "word": "נאצי", "severity": Severity.HIGH, "reason": "纳粹比喻在以色列高度冒犯", "contexts": ["政治", "比喻"]},

    # ── hi-IN ──
    {"locale": "hi-IN", "word": "गोमांस", "severity": Severity.CRITICAL, "reason": "牛肉话题，印度教视为神圣不可侵犯", "contexts": ["食品", "餐饮", "宗教"]},
    {"locale": "hi-IN", "word": "beef", "severity": Severity.CRITICAL, "reason": "牛肉话题，印度教视为神圣不可侵犯", "contexts": ["食品", "餐饮", "宗教"]},
    {"locale": "hi-IN", "word": "जाति", "severity": Severity.HIGH, "reason": "种姓 (caste) 话题高度敏感，避免正面讨论", "contexts": ["社会", "婚姻", "就业"]},
    {"locale": "hi-IN", "word": "दलित", "severity": Severity.HIGH, "reason": "达利特 (贱民) 称呼可能被视为歧视", "contexts": ["社会", "法律"]},
    {"locale": "hi-IN", "word": "राम मंदिर", "severity": Severity.HIGH, "reason": "罗摩庙争议，印度教-穆斯林冲突焦点", "contexts": ["宗教", "政治", "历史"]},

    # ── th-TH ──
    {"locale": "th-TH", "word": "หมิ่นพระบรมเดชานุภาพ", "severity": Severity.CRITICAL, "reason": "冒犯君主罪 (lèse-majesté)，泰国刑法第112条，最高15年", "contexts": ["政治", "君主"]},
    {"locale": "th-TH", "word": "พระพุทธรูป", "severity": Severity.HIGH, "reason": "佛像不可用于装饰/商业/亵渎用途", "contexts": ["宗教", "商品", "艺术"]},

    # ── en-US ──
    {"locale": "en-US", "word": "nigger", "severity": Severity.CRITICAL, "reason": "种族歧视语 (N-word)，历史创伤极深", "contexts": ["种族", "日常用语", "媒体"]},
    {"locale": "en-US", "word": "faggot", "severity": Severity.CRITICAL, "reason": "对 LGBTQ+ 群体的仇恨用语", "contexts": ["性别", "日常用语"]},
    {"locale": "en-US", "word": "retard", "severity": Severity.HIGH, "reason": "对智力障碍者的歧视用语", "contexts": ["健康", "日常用语"]},
    {"locale": "en-US", "word": "9/11 joke", "severity": Severity.CRITICAL, "reason": "911 恐怖袭击不可用于玩笑/轻率引用", "contexts": ["历史", "幽默", "媒体"]},
    {"locale": "en-US", "word": "trail of tears", "severity": Severity.HIGH, "reason": "印第安人血泪史，不可轻率引用", "contexts": ["历史", "比喻"]},

    # ── en-GB ──
    {"locale": "en-GB", "word": "Paki", "severity": Severity.CRITICAL, "reason": "对南亚裔的极强种族歧视语", "contexts": ["种族", "日常用语"]},
    {"locale": "en-GB", "word": "fenian", "severity": Severity.HIGH, "reason": "北爱尔兰冲突相关的宗派歧视语", "contexts": ["宗教", "政治", "北爱尔兰"]},

    # ── de-DE ──
    {"locale": "de-DE", "word": "Heil Hitler", "severity": Severity.CRITICAL, "reason": "纳粹礼/口号，德国刑法第86a条禁止", "contexts": ["政治", "符号"]},
    {"locale": "de-DE", "word": "Jude als Schimpfwort", "severity": Severity.CRITICAL, "reason": "反犹主义用语，德国刑法第130条 (煽动仇恨)", "contexts": ["种族", "宗教"]},
    {"locale": "de-DE", "word": "Reichskristallnacht", "severity": Severity.CRITICAL, "reason": "水晶之夜术语已被官方弃用，应使用 Novemberpogrome", "contexts": ["历史", "教育"]},

    # ── es-ES ──
    {"locale": "es-ES", "word": "sudaca", "severity": Severity.HIGH, "reason": "对南美人的歧视性称呼", "contexts": ["种族", "日常用语"]},
    {"locale": "es-ES", "word": "ETA glorification", "severity": Severity.CRITICAL, "reason": "美化ETA恐怖组织，对受害者极大不敬", "contexts": ["政治", "巴斯克"]},
    {"locale": "es-ES", "word": "moro", "severity": Severity.MEDIUM, "reason": "对北非/穆斯林裔的轻蔑称呼", "contexts": ["种族", "日常用语"]},

    # ── ru-RU ──
    {"locale": "ru-RU", "word": "чурка", "severity": Severity.HIGH, "reason": "对中亚/高加索裔的种族歧视语", "contexts": ["种族", "日常用语"]},
    {"locale": "ru-RU", "word": "голубое сало", "severity": Severity.HIGH, "reason": "蓝色脂肪 (对 LGBT 群体的隐性歧视语)", "contexts": ["性别", "媒体"]},
    {"locale": "ru-RU", "word": "ЛГБТ-пропаганда", "severity": Severity.CRITICAL, "reason": "LGBT 宣传话题受法律严格限制", "contexts": ["性别", "法律", "未成年人"]},

    # ── pt-BR ──
    {"locale": "pt-BR", "word": "macaco", "severity": Severity.CRITICAL, "reason": "对黑人的种族歧视语 (巴西足球场常见)", "contexts": ["种族", "体育"]},
    {"locale": "pt-BR", "word": "paraíba", "severity": Severity.MEDIUM, "reason": "对东北部巴西人的地域歧视语", "contexts": ["地域", "日常用语"]},
    {"locale": "pt-BR", "word": "favela glorification", "severity": Severity.MEDIUM, "reason": "美化贫民窟可能淡化暴力/贫困现实", "contexts": ["社会", "文化"]},

    # ── fr-FR ──
    {"locale": "fr-FR", "word": "sale juif", "severity": Severity.CRITICAL, "reason": "反犹主义用语，违反法国反仇恨法", "contexts": ["宗教", "种族"]},
    {"locale": "fr-FR", "word": "Charlie Hebdo caricature", "severity": Severity.CRITICAL, "reason": "查理周刊讽刺话题高度敏感，涉及宗教/恐怖主义", "contexts": ["媒体", "宗教", "言论自由"]},
    {"locale": "fr-FR", "word": "nègre", "severity": Severity.CRITICAL, "reason": "对黑人的强种族歧视语", "contexts": ["种族", "殖民历史"]},
]


# ═══════════════════════════════════════════════════════════════
# TABOO COLORS — color associations with death/mourning/religion
# ═══════════════════════════════════════════════════════════════

TABOO_COLORS: list[dict[str, Any]] = [
    # White = death/mourning in East Asian cultures
    {"locale": "zh-CN", "color": "white", "context": "丧葬、婚礼请柬、红包", "severity": Severity.HIGH, "reason": "白色=丧葬色；婚礼/喜庆禁用纯白装饰；红包绝不用白封"},
    {"locale": "zh-TW", "color": "white", "context": "丧葬、节庆", "severity": Severity.HIGH, "reason": "白色=丧事，春节/婚礼禁用全白"},
    {"locale": "ja-JP", "color": "white", "context": "丧葬、礼品包装", "severity": Severity.HIGH, "reason": "白色=葬礼色；送礼不可纯白包装"},
    {"locale": "ko-KR", "color": "white", "context": "丧葬", "severity": Severity.HIGH, "reason": "白色=丧服色；婚礼用白色已西化但传统上争议"},
    {"locale": "hi-IN", "color": "white", "context": "丧葬、婚礼", "severity": Severity.CRITICAL, "reason": "白色=寡妇色/丧葬色；婚礼穿白=不吉；已婚女性禁全白"},
    {"locale": "th-TH", "color": "white", "context": "丧葬", "severity": Severity.HIGH, "reason": "白色=葬礼色；日常穿白可能被联想丧事"},

    # Red
    {"locale": "de-DE", "color": "red", "context": "政治符号", "severity": Severity.HIGH, "reason": "红色+特定符号=极左/纳粹联想"},
    {"locale": "ko-KR", "color": "red", "context": "名字书写", "severity": Severity.CRITICAL, "reason": "红笔写人名=诅咒死亡 (源自刑场名单传统)"},
    {"locale": "zh-CN", "color": "red", "context": "名字书写", "severity": Severity.HIGH, "reason": "红笔写人名=不祥 (古代死刑判决用朱笔)"},
    {"locale": "ja-JP", "color": "red", "context": "名字书写", "severity": Severity.HIGH, "reason": "红笔写人名=不吉 (赤文字=死者名簿)"},
    {"locale": "pt-BR", "color": "red", "context": "宗教", "severity": Severity.MEDIUM, "reason": "部分福音派不喜红色=魔鬼色"},

    # Black
    {"locale": "hi-IN", "color": "black", "context": "节庆礼品", "severity": Severity.HIGH, "reason": "黑色=不吉/邪恶；礼品/节日禁用纯黑包装"},
    {"locale": "zh-CN", "color": "black", "context": "节庆", "severity": Severity.MEDIUM, "reason": "春节/婚礼禁用全黑装饰"},
    {"locale": "th-TH", "color": "black", "context": "日常", "severity": Severity.MEDIUM, "reason": "黑色=丧葬色；喜庆场合避免"},

    # Green
    {"locale": "ar-SA", "color": "green", "context": "宗教", "severity": Severity.CRITICAL, "reason": "绿色=伊斯兰神圣色；不可用于亵渎/不洁用途 (如马桶/鞋)"},
    {"locale": "he-IL", "color": "green", "context": "宗教", "severity": Severity.HIGH, "reason": "绿色=伊斯兰色；在特定犹太宗教语境中避免混淆"},

    # Yellow
    {"locale": "de-DE", "color": "yellow", "context": "历史", "severity": Severity.HIGH, "reason": "黄色六角星=纳粹时期的犹太标识，极其敏感"},
    {"locale": "es-ES", "color": "yellow", "context": "文化", "severity": Severity.MEDIUM, "reason": "黄色=不吉 (剧场/斗牛传统)"},
    {"locale": "fr-FR", "color": "yellow", "context": "历史", "severity": Severity.MEDIUM, "reason": "黄色=嫉妒/背叛 (jaune=叛徒)"},

    # Blue
    {"locale": "ar-SA", "color": "blue", "context": "宗教", "severity": Severity.MEDIUM, "reason": "蓝色 (azraq) 在某些伊斯兰传统中=不详/邪恶之眼"},

    # Purple/Violet
    {"locale": "th-TH", "color": "purple", "context": "丧葬", "severity": Severity.MEDIUM, "reason": "紫色=泰国王室丧服色 (王太后/国王葬礼)"},
    {"locale": "pt-BR", "color": "purple", "context": "宗教", "severity": Severity.MEDIUM, "reason": "紫色=天主教四旬期/受难/葬礼色"},
    {"locale": "it-IT", "color": "purple", "context": "戏剧/活动", "severity": Severity.MEDIUM, "reason": "紫色=戏剧开幕前不吉色 (源自四旬期禁止演出)"},
]


# ═══════════════════════════════════════════════════════════════
# TABOO NUMBERS — unlucky/forbidden numbers per culture
# ═══════════════════════════════════════════════════════════════

TABOO_NUMBERS: list[dict[str, Any]] = [
    # 4 — death homophone (CN/JP/KR/TW/VN)
    {"locale": "zh-CN", "number": 4, "context": "楼层/房号/手机号/定价", "severity": Severity.HIGH, "reason": "四=sǐ (死) 谐音；医院/酒店常跳4楼；避免4结尾定价"},
    {"locale": "zh-TW", "number": 4, "context": "楼层/房号/定价", "severity": Severity.HIGH, "reason": "四=sǐ (死) 谐音"},
    {"locale": "ja-JP", "number": 4, "context": "楼层/病房/礼品数量", "severity": Severity.HIGH, "reason": "四=shi (死)；医院无4号病房；送礼禁4件"},
    {"locale": "ko-KR", "number": 4, "context": "楼层/房号", "severity": Severity.HIGH, "reason": "四=sa (死) 谐音；医院/酒店跳4楼，用F代替"},

    # 9 — suffering
    {"locale": "ja-JP", "number": 9, "context": "定价/礼品/房间", "severity": Severity.HIGH, "reason": "九=ku (苦)；医院无9号病房；避免9结尾价格"},

    # 13 — unlucky Western
    {"locale": "en-US", "number": 13, "context": "楼层/房号/日期", "severity": Severity.MEDIUM, "reason": "13=不吉 (最后的晚餐)；许多建筑跳13楼"},
    {"locale": "en-GB", "number": 13, "context": "楼层/日期", "severity": Severity.MEDIUM, "reason": "13号星期五=不吉日"},
    {"locale": "de-DE", "number": 13, "context": "楼层", "severity": Severity.MEDIUM, "reason": "13=Unglückszahl (不吉数)"},
    {"locale": "pt-BR", "number": 13, "context": "楼层/号码", "severity": Severity.MEDIUM, "reason": "13=azar (厄运)；部分建筑跳过13"},

    # 666 — evil
    {"locale": "en-US", "number": 666, "context": "定价/编号/UPC", "severity": Severity.HIGH, "reason": "666=兽的数字 (启示录13:18)；福音派强烈反感"},
    {"locale": "en-GB", "number": 666, "context": "编号/定价", "severity": Severity.HIGH, "reason": "666=Number of the Beast"},
    {"locale": "pt-BR", "number": 666, "context": "编号/定价", "severity": Severity.HIGH, "reason": "666= número da besta；福音派强烈反感"},
    {"locale": "es-ES", "number": 666, "context": "编号", "severity": Severity.HIGH, "reason": "666=número de la bestia"},

    # 17 — Italian unlucky
    {"locale": "it-IT", "number": 17, "context": "楼层/日期/号码", "severity": Severity.HIGH, "reason": "17=VIXI (拉丁'我活过'=已死)；酒店/飞机跳17"},

    # 8 — auspicious (reverse: avoiding 8 in taboo contexts)
    {"locale": "zh-CN", "number": 8, "context": "丧葬/悼念定价", "severity": Severity.HIGH, "reason": "8=bā (发) 发财；但丧葬场合用8=极大冒犯 (寓意死者'发')"},
    {"locale": "zh-TW", "number": 8, "context": "丧葬", "severity": Severity.HIGH, "reason": "丧礼红包禁8数字"},

    # 7 — sacred in Abrahamic, unlucky in some East Asian
    {"locale": "ja-JP", "number": 7, "context": "丧葬礼品", "severity": Severity.MEDIUM, "reason": "七=shichi (质/死)；避免7件葬礼品"},
    {"locale": "zh-CN", "number": 7, "context": "丧葬月份 (农历七月)", "severity": Severity.HIGH, "reason": "农历七月=鬼月；避免在此期间发布喜庆/婚庆/搬家营销"},

    # 0
    {"locale": "zh-CN", "number": 0, "context": "红包/压岁钱", "severity": Severity.HIGH, "reason": "0=零 (líng) = 无/空；红包金额禁以0结尾"},

    # 14
    {"locale": "zh-CN", "number": 14, "context": "楼层/房号", "severity": Severity.MEDIUM, "reason": "一四=yāo sì (要死)；部分建筑跳过14楼"},
    {"locale": "ja-JP", "number": 14, "context": "楼层/房号", "severity": Severity.MEDIUM, "reason": "十四=jū shi (重死)"},

    # 39 — Afghan taboo
    {"locale": "ar-SA", "number": 39, "context": "号码/地址", "severity": Severity.HIGH, "reason": "39 在部分阿拉伯/阿富汗文化中=皮条客/不道德含义"},
]


# ═══════════════════════════════════════════════════════════════
# TABOO HOLIDAY COMBINATIONS — sensitive date/marketing rules
# ═══════════════════════════════════════════════════════════════

TABOO_HOLIDAYS: list[dict[str, Any]] = [
    # Chinese holidays
    {"locale": "zh-CN", "period": "清明节 (4月4-5日前后)", "restriction": "禁止喜庆营销、婚礼推广、'快乐'问候", "severity": Severity.HIGH, "reason": "清明节=扫墓祭祖；不可喜庆"},
    {"locale": "zh-CN", "period": "农历七月 (鬼月)", "restriction": "避免婚庆/搬家/开业/晚间户外活动推广", "severity": Severity.HIGH, "reason": "鬼月=阴气重；重大喜庆活动禁忌"},
    {"locale": "zh-CN", "period": "9月18日 (九一八)", "restriction": "禁止娱乐性营销、日系品牌推广", "severity": Severity.CRITICAL, "reason": "国耻日；娱乐/日本品牌推广极度冒犯"},
    {"locale": "zh-CN", "period": "12月13日 (南京大屠杀死难者国家公祭日)", "restriction": "全国禁止娱乐活动、游戏/直播停服", "severity": Severity.CRITICAL, "reason": "国家级公祭日；网站灰色调；娱乐全禁"},
    {"locale": "zh-CN", "period": "5月12日 (汶川地震纪念日)", "restriction": "避免喜庆营销", "severity": Severity.HIGH, "reason": "重大灾难纪念日"},

    # Japanese
    {"locale": "ja-JP", "period": "お盆 (8月13-16日)", "restriction": "避免促销'回家'之外的商业主题", "severity": Severity.MEDIUM, "reason": "盂兰盆节=祖先归家；家庭团聚期"},
    {"locale": "ja-JP", "period": "8月6日/9日 (广岛/长崎原爆纪念日)", "restriction": "禁止娱乐性营销；避免核/爆炸相关图像", "severity": Severity.CRITICAL, "reason": "原爆纪念日；全国默哀"},

    # Islamic
    {"locale": "ar-SA", "period": "斋月 (Ramadan, 伊历9月)", "restriction": "日间禁饮食营销；穿着/广告避免暴露；工作时间调整", "severity": Severity.CRITICAL, "reason": "斋月=穆斯林最神圣月份；白天饮食广告=严重冒犯"},
    {"locale": "ar-SA", "period": "阿舒拉节 (Ashura, 伊历1月10日)", "restriction": "避免喜庆/音乐/娱乐营销 (什叶派=哀悼日)", "severity": Severity.HIGH, "reason": "阿舒拉=什叶派哀悼日；娱乐营销极不妥"},
    {"locale": "ar-SA", "period": "宰牲节 (Eid al-Adha)", "restriction": "避免猪/酒/非清真食品推广", "severity": Severity.CRITICAL, "reason": "宰牲节=伊斯兰至圣节日之一"},

    # Jewish
    {"locale": "he-IL", "period": "赎罪日 (Yom Kippur, 犹太历提市黎月10日)", "restriction": "全国停摆24h；禁止任何商业推广/电子通讯/驾车/餐饮", "severity": Severity.CRITICAL, "reason": "赎罪日=犹太最神圣日；全国禁食禁行禁商"},
    {"locale": "he-IL", "period": "安息日 (Shabbat, 周五日落→周六日落)", "restriction": "避免在此期间推送通知/商业邮件/食物配送推广", "severity": Severity.HIGH, "reason": "安息日=禁工作/禁电子设备 (正统派)"},
    {"locale": "he-IL", "period": "大屠杀纪念日 (Yom HaShoah)", "restriction": "娱乐场所关闭；避免娱乐/促销/轻松内容", "severity": Severity.CRITICAL, "reason": "全国哀悼日；警报响起时全国停车默哀"},

    # Indian
    {"locale": "hi-IN", "period": "排灯节 (Diwali) 前禁酒/禁肉期", "restriction": "避免酒类/非素食营销", "severity": Severity.HIGH, "reason": "排灯节=印度教最重要节日；部分区域禁酒禁肉"},
    {"locale": "hi-IN", "period": "胡里节 (Holi)", "restriction": "避免攻击性/宗教对立色彩营销", "severity": Severity.MEDIUM, "reason": "胡里节=色彩节；注意颜色使用不触及宗教敏感性"},

    # Thai
    {"locale": "th-TH", "period": "12月5日 (拉玛九世诞辰/泰国父亲节)", "restriction": "避免批评/调侃君主；避免黄色以外的视觉主色", "severity": Severity.CRITICAL, "reason": "先王诞辰=国定假日；黄色=王室色 (周一出生色)"},
    {"locale": "th-TH", "period": "宋干节 (Songkran, 4月13-15日)", "restriction": "避免严肃/商务主题推广", "severity": Severity.MEDIUM, "reason": "宋干节=泼水节/新年；全民狂欢期"},

    # Western
    {"locale": "en-US", "period": "9月11日 (911)", "restriction": "禁止任何与火灾/坍塌/爆炸相关的促销/玩笑", "severity": Severity.CRITICAL, "reason": "9/11 恐怖袭击纪念日；任何关联促销=极大冒犯"},
    {"locale": "en-US", "period": "阵亡将士纪念日 (Memorial Day, 5月最后周一)", "restriction": "避免'庆祝'措辞；宜用'纪念/缅怀'", "severity": Severity.HIGH, "reason": "纪念阵亡军人；非庆祝性节日"},
    {"locale": "en-GB", "period": "11月11日 (Remembrance Day)", "restriction": "避免商业促销；佩戴红色罂粟花 (poppy)", "severity": Severity.HIGH, "reason": "一战终战纪念日；全国默哀2分钟"},
    {"locale": "de-DE", "period": "11月9日 (Kristallnacht 水晶之夜纪念)", "restriction": "禁止任何与纳粹/种族相关的营销/玩笑", "severity": Severity.CRITICAL, "reason": "反犹暴力纪念日；与11月9日(柏林墙倒塌)同日但性质完全不同"},
    {"locale": "ru-RU", "period": "5月9日 (胜利日/Victory Day)", "restriction": "避免贬低/轻率引用二战/苏联；避免纳粹符号", "severity": Severity.CRITICAL, "reason": "胜利日=俄罗斯最神圣节日；任何轻率引用=对老兵的极大冒犯"},
    {"locale": "fr-FR", "period": "11月13日 (巴黎恐袭纪念日)", "restriction": "禁止与恐怖袭击相关的玩笑/营销", "severity": Severity.CRITICAL, "reason": "2015巴黎恐袭；130人死亡"},

    # Korean
    {"locale": "ko-KR", "period": "三一节 (3月1日)", "restriction": "避免日本文化/品牌推广", "severity": Severity.HIGH, "reason": "韩国独立运动纪念日；反日情绪高"},
    {"locale": "ko-KR", "period": "光复节 (8月15日)", "restriction": "避免日本相关营销", "severity": Severity.HIGH, "reason": "韩国光复/日本投降日"},

    # Brazilian
    {"locale": "pt-BR", "period": "圣周 (Semana Santa, 复活节前一周)", "restriction": "避免狂欢节风格/过度性感/肉类营销 (周五禁肉)", "severity": Severity.HIGH, "reason": "天主教圣周=严肃期；禁止狂欢风格"},
]


# ═══════════════════════════════════════════════════════════════
# SACRED CONTEXTS — scenarios with inviolable boundaries
# ═══════════════════════════════════════════════════════════════

SACRED_CONTEXTS: list[dict[str, Any]] = [
    {"locale": "*", "context": "葬礼/追悼会", "rule": "禁用喜庆色彩/欢乐音乐/促销文案", "severity": Severity.CRITICAL, "reason": "全球通用丧葬礼仪"},
    {"locale": "*", "context": "儿童用户 (U13/16)", "rule": "禁用数据收集/行为广告/成人内容/UGC裸露", "severity": Severity.CRITICAL, "reason": "COPPA/GDPR-K/各国未成年人保护法"},
    {"locale": "*", "context": "宗教场所 (教堂/清真寺/寺庙/犹太会堂)", "rule": "禁用GPS游戏/AR体验/推送通知/铃声", "severity": Severity.CRITICAL, "reason": "亵渎神圣空间"},
    {"locale": "*", "context": "孕妇/围产期", "rule": "避免死亡/恐怖/酒精/烟草主题推送", "severity": Severity.HIGH, "reason": "孕期心理健康保护"},
    {"locale": "*", "context": "临终/安宁疗护", "rule": "禁止'治愈''奇迹'误导性医疗文案", "severity": Severity.CRITICAL, "reason": "临终患者保护；反虚假医疗承诺"},

    # Locale-specific sacred contexts
    {"locale": "zh-CN", "context": "天安门广场", "rule": "禁用AR游戏/Pokemon-style打卡/不敬自拍滤镜", "severity": Severity.CRITICAL, "reason": "国家象征/政治敏感性"},
    {"locale": "ar-SA", "context": "麦加/麦地那非穆斯林禁入区", "rule": "绝对禁止GPS游戏/AR/虚拟打卡/非穆斯林推送", "severity": Severity.CRITICAL, "reason": "伊斯兰圣城；非穆斯林禁止进入"},
    {"locale": "ja-JP", "context": "靖国神社/原爆圆顶馆", "rule": "禁止游戏/娱乐/拍照打卡推广", "severity": Severity.CRITICAL, "reason": "政治/历史高度敏感场所"},
    {"locale": "he-IL", "context": "哭墙 (Western Wall)", "rule": "禁止AR滤镜/游戏/不敬自拍", "severity": Severity.CRITICAL, "reason": "犹太教至圣之地"},
    {"locale": "hi-IN", "context": "瓦拉纳西恒河河坛 (Varanasi Ghats)", "rule": "禁止泳装/酒精/牛肉/游戏推广", "severity": Severity.CRITICAL, "reason": "印度教圣城；生死轮回之地"},
    {"locale": "th-TH", "context": "大皇宫/玉佛寺", "rule": "禁止不敬自拍/AR游戏/暴露衣着", "severity": Severity.CRITICAL, "reason": "泰国至圣王室/佛教场所"},
    {"locale": "ja-JP", "context": "伊势神宫", "rule": "禁止无人机/AR游戏/商业拍摄", "severity": Severity.HIGH, "reason": "日本神道至圣之地"},
    {"locale": "zh-CN", "context": "殡仪馆/火葬场/墓地", "rule": "禁止游戏/直播/打卡/营销推送 (基于位置)", "severity": Severity.CRITICAL, "reason": "丧葬场所；任何娱乐/商业行为=极大冒犯"},
    {"locale": "it-IT", "context": "梵蒂冈/圣彼得大教堂", "rule": "禁止AR游戏/暴露衣着/商业营销", "severity": Severity.CRITICAL, "reason": "天主教圣地"},
]


# ═══════════════════════════════════════════════════════════════
# Query helpers
# ═══════════════════════════════════════════════════════════════

def get_taboo_words(locale: str | None = None) -> list[dict[str, Any]]:
    """Return taboo words, optionally filtered by locale."""
    if locale is None:
        return TABOO_WORDS
    return [w for w in TABOO_WORDS if w["locale"] == locale]


def get_taboo_colors(locale: str | None = None) -> list[dict[str, Any]]:
    """Return taboo colors, optionally filtered by locale."""
    if locale is None:
        return TABOO_COLORS
    return [c for c in TABOO_COLORS if c["locale"] == locale]


def get_taboo_numbers(locale: str | None = None) -> list[dict[str, Any]]:
    """Return taboo numbers, optionally filtered by locale."""
    if locale is None:
        return TABOO_NUMBERS
    return [n for n in TABOO_NUMBERS if n["locale"] == locale]


def get_taboo_holidays(locale: str | None = None) -> list[dict[str, Any]]:
    """Return taboo holiday periods, optionally filtered by locale."""
    if locale is None:
        return TABOO_HOLIDAYS
    return [h for h in TABOO_HOLIDAYS if h["locale"] == locale]


def get_sacred_contexts(locale: str | None = None) -> list[dict[str, Any]]:
    """Return sacred context rules, optionally filtered by locale."""
    if locale is None:
        return SACRED_CONTEXTS
    return [s for s in SACRED_CONTEXTS if s["locale"] == locale or s["locale"] == "*"]


def get_supported_locales() -> list[str]:
    """Return all unique locales covered by the taboo matrix."""
    all_locales: set[str] = set()
    for source in [TABOO_WORDS, TABOO_COLORS, TABOO_NUMBERS, TABOO_HOLIDAYS, SACRED_CONTEXTS]:
        for entry in source:
            loc = entry.get("locale", "")
            if loc and loc != "*":
                all_locales.add(loc)
    return sorted(all_locales)


def get_matrix_summary() -> dict[str, Any]:
    """Return summary statistics of the taboo matrix."""
    return {
        "locales_covered": len(get_supported_locales()),
        "taboo_words": len(TABOO_WORDS),
        "taboo_colors": len(TABOO_COLORS),
        "taboo_numbers": len(TABOO_NUMBERS),
        "taboo_holidays": len(TABOO_HOLIDAYS),
        "sacred_contexts": len(SACRED_CONTEXTS),
        "total_entries": len(TABOO_WORDS) + len(TABOO_COLORS) + len(TABOO_NUMBERS) + len(TABOO_HOLIDAYS) + len(SACRED_CONTEXTS),
    }
