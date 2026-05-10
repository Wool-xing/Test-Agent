# SPDX-License-Identifier: MIT
"""
视觉测试辅助：模板匹配 / OCR / SSIM 视觉回归 / diff 高亮
被引用方：12-视觉游戏测试 agent / visual-test skill
"""
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# ===== 模板匹配 =====

def find_template(screen_path: str, template_path: str, threshold: float = 0.85) -> Optional[Tuple[int, int]]:
    """
    在屏幕截图中找模板图位置。
    返回模板中心坐标 (x, y)；找不到返回 None。
    """
    import cv2

    screen = cv2.imread(screen_path)
    template = cv2.imread(template_path)
    if screen is None or template is None:
        logger.error(f"图片读取失败: {screen_path} / {template_path}")
        return None

    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val < threshold:
        logger.warning(f"模板未找到（max={max_val:.3f} < {threshold}）")
        return None

    h, w = template.shape[:2]
    center = (max_loc[0] + w // 2, max_loc[1] + h // 2)
    return center


# ===== OCR =====

def ocr_image(image_path: str, lang: Optional[str] = None, engine: Optional[str] = None) -> str:
    """OCR 识别图片文字。引擎：tesseract（默认）/ paddleocr"""
    engine = (engine or os.getenv("OCR_ENGINE", "tesseract")).lower()
    lang = lang or os.getenv("TESSERACT_LANG", "chi_sim+eng")

    if engine == "paddleocr":
        try:
            from paddleocr import PaddleOCR
        except ImportError:
            logger.warning("paddleocr 未装，回退 tesseract")
            engine = "tesseract"

    if engine == "paddleocr":
        ocr = PaddleOCR(use_angle_cls=True, lang="ch")
        result = ocr.ocr(image_path, cls=True)
        return "\n".join(line[1][0] for r in result for line in (r or []))

    # tesseract
    import pytesseract
    cmd = os.getenv("TESSERACT_CMD")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
    from PIL import Image
    return pytesseract.image_to_string(Image.open(image_path), lang=lang)


def ocr_assert_contains(image_path: str, expected_text: str, **kwargs) -> bool:
    text = ocr_image(image_path, **kwargs)
    return expected_text in text


# ===== 视觉回归（SSIM） =====

def compare_images(current: str, baseline: str, threshold: Optional[float] = None) -> Dict:
    """
    SSIM 比较两图相似度。
    返回 {"similarity": float, "pass": bool, "diff_image": Optional[str]}
    """
    threshold = threshold if threshold is not None else float(os.getenv("VISUAL_SIMILARITY_THRESHOLD", "0.95"))

    import cv2
    from skimage.metrics import structural_similarity as ssim

    img_a = cv2.imread(current, cv2.IMREAD_GRAYSCALE)
    img_b = cv2.imread(baseline, cv2.IMREAD_GRAYSCALE)
    if img_a is None or img_b is None:
        return {"error": "图片读取失败", "pass": False, "similarity": 0.0}

    # 尺寸不一时缩放对齐到 baseline
    if img_a.shape != img_b.shape:
        img_a = cv2.resize(img_a, (img_b.shape[1], img_b.shape[0]))

    score, diff = ssim(img_a, img_b, full=True)
    result = {
        "similarity": round(float(score), 4),
        "pass": score >= threshold,
        "threshold": threshold,
    }
    return result


# ===== diff 高亮图 =====

def make_diff_image(current: str, baseline: str, output: str) -> str:
    """生成 diff 高亮图（红色框出差异区域）"""
    import cv2
    import numpy as np
    from skimage.metrics import structural_similarity as ssim

    img_a = cv2.imread(current)
    img_b = cv2.imread(baseline)
    if img_a.shape != img_b.shape:
        img_a = cv2.resize(img_a, (img_b.shape[1], img_b.shape[0]))

    gray_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)
    _, diff = ssim(gray_a, gray_b, full=True)
    diff = (diff * 255).astype("uint8")
    thresh = cv2.threshold(diff, 200, 255, cv2.THRESH_BINARY_INV)[1]
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    out = img_a.copy()
    for c in contours:
        if cv2.contourArea(c) < 30:
            continue
        x, y, w, h = cv2.boundingRect(c)
        cv2.rectangle(out, (x, y), (x + w, y + h), (0, 0, 255), 2)

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(output, out)
    logger.info(f"diff 高亮图: {output}")
    return output


# ===== CLI =====

def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="视觉测试工具")
    sub = parser.add_subparsers(dest="cmd")

    cmp_p = sub.add_parser("compare", help="SSIM 比较")
    cmp_p.add_argument("--current", required=True)
    cmp_p.add_argument("--baseline", required=True)
    cmp_p.add_argument("--threshold", type=float, default=None)

    diff_p = sub.add_parser("diff", help="生成 diff 高亮图")
    diff_p.add_argument("--current", required=True)
    diff_p.add_argument("--baseline", required=True)
    diff_p.add_argument("--output", required=True)

    ocr_p = sub.add_parser("ocr")
    ocr_p.add_argument("--image", required=True)
    ocr_p.add_argument("--engine", default=None)
    ocr_p.add_argument("--lang", default=None)

    args = parser.parse_args()
    if args.cmd == "compare":
        import json
        print(json.dumps(compare_images(args.current, args.baseline, args.threshold), indent=2))
    elif args.cmd == "diff":
        make_diff_image(args.current, args.baseline, args.output)
    elif args.cmd == "ocr":
        print(ocr_image(args.image, lang=args.lang, engine=args.engine))


if __name__ == "__main__":
    main()
