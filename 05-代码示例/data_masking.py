"""
敏感数据脱敏工具
被引用方：05-数据准备 agent / 日志输出
"""
import re


class DataMasker:
    """测试数据脱敏（合规）"""

    @staticmethod
    def mask_phone(phone: str) -> str:
        """手机号脱敏: 138****8000"""
        s = str(phone or "")
        if len(s) == 11 and s.isdigit():
            return s[:3] + "****" + s[7:]
        return re.sub(r"(\d{3})\d{4}(\d{4})", r"\1****\2", s) or "***"

    @staticmethod
    def mask_email(email: str) -> str:
        """邮箱脱敏: u***@example.com"""
        s = str(email or "")
        parts = s.split("@")
        if len(parts) == 2 and parts[0]:
            return parts[0][0] + "***@" + parts[1]
        return "***"

    @staticmethod
    def mask_id_card(id_card: str) -> str:
        """身份证脱敏: 110***********1234"""
        s = str(id_card or "")
        if len(s) == 18:
            return s[:3] + "*" * 11 + s[-4:]
        return "***"

    @staticmethod
    def mask_bank_card(card_no: str) -> str:
        """银行卡脱敏: 6222****1234"""
        s = str(card_no or "")
        if len(s) >= 8:
            return s[:4] + "****" + s[-4:]
        return "***"

    @staticmethod
    def mask_password(_pwd) -> str:
        return "********"

    @classmethod
    def mask_dict(cls, data: dict, sensitive_keys=None) -> dict:
        """对字典中敏感字段做脱敏（用于日志输出）"""
        if sensitive_keys is None:
            sensitive_keys = ("password", "phone", "email", "id_card", "bank_card", "token", "secret")
        masker_map = {
            "password": cls.mask_password,
            "phone": cls.mask_phone,
            "email": cls.mask_email,
            "id_card": cls.mask_id_card,
            "bank_card": cls.mask_bank_card,
            "token": cls.mask_password,
            "secret": cls.mask_password,
        }
        out = {}
        for k, v in data.items():
            if k.lower() in sensitive_keys:
                out[k] = masker_map.get(k.lower(), cls.mask_password)(v)
            elif isinstance(v, dict):
                out[k] = cls.mask_dict(v, sensitive_keys)
            else:
                out[k] = v
        return out


if __name__ == "__main__":
    sample = {"username": "alice", "password": "S3cret!", "phone": "13800138000",
              "email": "alice@example.com", "profile": {"id_card": "110101199001011234"}}
    print(DataMasker.mask_dict(sample))
