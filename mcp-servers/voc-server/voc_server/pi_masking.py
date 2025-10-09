"""PI Masking utilities."""

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass

PHONE_TAG = "[전화번호]"
EMAIL_TAG = "[이메일]"
SSN_TAG = "[주민등록번호]"
CARD_TAG = "[카드번호]"
ADDR_TAG = "[주소]"
NAME_TAG = "[이름]"


def _s(x: str | None) -> str:
    """Convert None to empty string."""
    return x if isinstance(x, str) else ("" if x is None else str(x))


type MatchReplacer = str | Callable[[re.Match[str]], str]


def _always_true(_: str) -> bool:
    """Default predicate that always applies a rule."""

    return True


@dataclass(frozen=True)
class MaskRule:
    """Single masking rule with optional guard."""

    pattern: re.Pattern[str]
    replacer: MatchReplacer
    predicate: Callable[[str], bool] = _always_true


def _apply_rules(text: str, rules: Iterable[MaskRule]) -> str:
    """Apply masking rules sequentially."""
    for rule in rules:
        if rule.predicate(text):
            text = rule.pattern.sub(rule.replacer, text)
    return text


EMAIL_STD = re.compile(
    r"(?i)(?<!\S)[A-Za-z0-9._%+-]{1,64}\s*@\s*" r"[\w\-\uAC00-\uD7A3.]{1,253}\s*\.\s*[A-Za-z]{2,24}(?!\S)"
)
EMAIL_KR_AT = re.compile(
    r"(?i)(?<!\S)[A-Za-z0-9._%+-]{2,64}\s*(?:@|골뱅이|앳)\s*"
    r"[\w\-\uAC00-\uD7A3]{2,63}\s*(?:\.|점|닷)\s*[A-Za-z]{2,6}"
    r"(?:\s*(?:\.|점)\s*[A-Za-z]{2,6})?(?!\S)"
)
EMAIL_KR_NOAT = re.compile(
    r"(?i)(?<!\S)[A-Za-z0-9._%+-]{2,64}\s*(?:…|\.{2,3})?\s*"
    r"[\w\-\uAC00-\uD7A3]{2,63}\s*(?:\.|점|닷)\s*[A-Za-z]{2,6}"
    r"(?:\s*(?:\.|점)\s*[A-Za-z]{2,6})?(?!\S)"
)
EMAIL_DOMAIN_ASCII = re.compile(
    r"(?i)(?<![\w\uAC00-\uD7A3])(?P<dom>[\w\-\uAC00-\uD7A3]{2,63})\s*"
    r"(?:\.|점|닷)\s*(?P<tld>[A-Za-z]{2,6})(?:\s*(?:\.|점)\s*(?P<tld2>"
    r"[A-Za-z]{2,6}))?(?P<suf>\s*(?:입니다|이에요|예요|이요|인데요|요)?)"
)
EMAIL_DOMAIN_HANGUL = re.compile(
    r"(?i)(?<![\w\uAC00-\uD7A3])(?P<dom>[\w\-\uAC00-\uD7A3]{2,63})\s*"
    r"(?:\.|점|닷)?\s*(?P<tld_ko>씨오케이알|오알지|케이알|씨오|컴|넷|코)"
    r"\b(?P<suf>\s*(?:입니다|이에요|예요|이요|인데요|요)?)"
)
EMAIL_LOCAL_TOKEN = re.compile(r"(?i)(?<!\S)(?=[A-Za-z][A-Za-z0-9._%+-]{2,63}(?!\S))" r"[A-Za-z0-9._%+-]+")
EMAIL_CONTEXT_HINT = re.compile(
    r"(?i)(메일|이메일|계정|아이디|로그인|address|email|inbox|네이버|지메일|gmail|"
    r"nate|네이트|다음|daum|카카오|kakao|outlook)"
    r"|(?:\.|점|닷)\s*(com|net|org|kr|co|co\.kr|or\.kr|go\.kr)"
)

EMAIL_RULES = (
    MaskRule(EMAIL_DOMAIN_ASCII, lambda m: EMAIL_TAG + (m.group("suf") or "")),
    MaskRule(EMAIL_DOMAIN_HANGUL, lambda m: EMAIL_TAG + (m.group("suf") or "")),
    MaskRule(EMAIL_STD, EMAIL_TAG),
    MaskRule(EMAIL_KR_AT, EMAIL_TAG),
    MaskRule(EMAIL_KR_NOAT, EMAIL_TAG),
    MaskRule(
        EMAIL_LOCAL_TOKEN,
        EMAIL_TAG,
        predicate=lambda text: bool(EMAIL_CONTEXT_HINT.search(text)),
    ),
)

PHONE = re.compile(r"(?<!\d)(?:0(?:10|11|16|17|18|19|2|3\d|4\d|5\d|6\d|70))(?:[-.\s]?\d{3,4}){1,2}(?!\d)")
SSN = re.compile(r"\b\d{6}\s*-\s*\d{7}\b")
CARD = re.compile(r"(?<!\d)(?:\d[ -]*?){13,19}(?!\d)")
ADDR = re.compile(
    r"(?:서울|부산|대구|인천|광주|대전|울산|세종|제주|경기|강원|충북|충남|전북|전남|경북|경남)[^\n,]{0,40}?\d+(?:-\d+)*(?:호|층|동|가)?"
)

MISC_RULES = (
    MaskRule(PHONE, PHONE_TAG),
    MaskRule(SSN, SSN_TAG),
    MaskRule(CARD, CARD_TAG),
    MaskRule(ADDR, ADDR_TAG),
)

ROLE_TOKENS = frozenset(
    {
        "고객",
        "손님",
        "상담",
        "상담사",
        "기사",
        "대표",
        "담당자",
        "팀장",
        "부장",
        "차장",
        "과장",
        "센터",
        "직원",
        "선생",
        "교수",
        "매니저",
        "보안",
        "관리자",
        "사용자",
        "예약자",
        "운전자",
        "신청자",
        "사장",
        "회사",
        "사무소",
        "상무",
        "이사",
        "본부장",
        "부대표",
        "주임",
        "대리",
        "연구원",
        "엔지니어",
        "경비",
        "고객님",
        "손님님",
        "상담사님",
        "기사님",
        "대표님",
        "담당자님",
    }
)
SURNAMES = frozenset(
    "김이박최정강조윤장임한오서신권황안송류홍전고문양손배백허남심노하곽성차주우구민유추진목염탁변원천방공국엄표설곽여"
)
# 과도 마스킹을 막기 위한 안전 단어(서비스 도메인 일반어)
SAFE_NON_NAMES = frozenset(
    {
        "확인",
        "예약",
        "취소",
        "처리",
        "진행",
        "문의",
        "변경",
        "사용",
        "연락",
        "계정",
        "전화",
        "환불",
        "대여",
        "반납",
        "고객",
        "상담",
        "접수",
        "결제",
    }
)

NAME_NIM = re.compile(
    r"(?P<name>[가-힣]{2,4})\s*님(?=(?:께서|께|에게|한테|은|는|이|가|을|를|도|만|이고|이며|이고요|인가요|입니다|이에요|예요|이요|요|\.|,|$))"
)
NAME_BONIN = re.compile(r"(?P<name>[가-힣]{2,4})\s*본인(?=입니다|이에요|예요|인데요|이죠|입니다\.|이에요\.|예요\.)?")
NAME_LABEL = re.compile(
    r"(성함|이름|예약자|담당자|대표|계정|아이디|사용자|신청자)\s*(은|는|이|가|을|를|께서|:)?\s*(?P<name>[가-힣]{2,4})(?=[^\w]|$)"
)
NAME_INTRO = re.compile(r"저는\s*(?P<name>[가-힣]{2,4})\s*(입니다|이에요|예요)\b")
NAME_SSI = re.compile(r"(?P<name>[가-힣]{2,4})\s*씨(?=[^\w]|$)")


def _mask_email(s: str) -> str:
    s = re.sub(r"\s*(?:점|닷)\s*", ".", s, flags=re.IGNORECASE)
    s = re.sub(r"(골뱅이|앳)", "@", s, flags=re.IGNORECASE)
    return _apply_rules(s, EMAIL_RULES)


def _mask_misc(s: str) -> str:
    return _apply_rules(s, MISC_RULES)


def _is_role(token: str) -> bool:
    return token in ROLE_TOKENS


def _starts_with_surname(token: str) -> bool:
    return bool(token) and token[0] in SURNAMES and token not in SAFE_NON_NAMES


def _replace_name_strict(m: re.Match[str]) -> str:
    full = m.group(0)
    name = m.group("name")
    if not name or _is_role(name) or not _starts_with_surname(name):
        return full
    s, e = m.start("name") - m.start(), m.end("name") - m.start()
    return full[:s] + NAME_TAG + full[e:]


def _replace_name_context(m: re.Match[str]) -> str:
    full = m.group(0)
    name = m.group("name")
    if not name or _is_role(name):
        return full
    s, e = m.start("name") - m.start(), m.end("name") - m.start()
    return full[:s] + NAME_TAG + full[e:]


NAME_RULES = (
    MaskRule(NAME_LABEL, _replace_name_context),
    MaskRule(NAME_BONIN, _replace_name_context),
    MaskRule(NAME_INTRO, _replace_name_context),
    MaskRule(NAME_NIM, _replace_name_strict),
    MaskRule(NAME_SSI, _replace_name_strict),
)


def _mask_names(s: str) -> str:
    return _apply_rules(s, NAME_RULES)


def mask_pii(text: str) -> str:
    """Mask private information contained in text."""
    s = _s(text)
    s = _mask_email(s)
    s = _mask_misc(s)
    s = _mask_names(s)
    return s
