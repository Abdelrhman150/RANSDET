"""
content_features.py
===================
استخراج خصائص مقارنة الملفات، مع تحليل نوافذ متداخلة ونسبة الضغط.
القيم before اختيارية في الناتج وليست مدخلات افتراضية للموديل.
الخصائص الأصلية:

1. content_change_ratio  → نسبة الاختلاف بين الملف القديم والجديد
2. entropy_delta         → الفرق في مستوى العشوائية
3. chi_square_after      → مدى تجانس توزيع الـ Bytes (قرب التوزيع من Uniform)
4. structure_broken      → هل الـ Header الأصلي للملف اتدمر؟

الملفات المدعومة:
  PDF, JPG/JPEG, PNG, ZIP, DOCX, XLSX, PPTX, PPT, TXT, LOG, CSV, JSON, XML
"""

import math
import collections
import numpy as np
import zlib
from pathlib import Path


# =========================================================
# File Signatures (Magic Bytes)
# =========================================================
# كل نوع ملف ليه بصمة (Magic Bytes) في أول كام Byte
# لو البصمة دي اختفت بعد التعديل → الملف غالباً اتشفر أو اتدمر

FILE_SIGNATURES = {
    # PDF → يبدأ بـ %PDF
    'pdf':  [b'%PDF'],

    # JPEG → يبدأ بـ FF D8 FF
    'jpg':  [b'\xff\xd8\xff'],
    'jpeg': [b'\xff\xd8\xff'],

    # PNG → يبدأ بـ 89 50 4E 47
    'png':  [b'\x89PNG'],

    # ZIP → يبدأ بـ PK (50 4B 03 04)
    'zip':  [b'PK\x03\x04'],

    # Office XML (docx, xlsx, pptx) → هي في الأصل ZIP files
    # فبيبدأوا بـ PK\x03\x04
    'docx': [b'PK\x03\x04'],
    'xlsx': [b'PK\x03\x04'],
    'pptx': [b'PK\x03\x04'],

    # Old Office formats (.doc, .xls, .ppt) → يبدأوا بـ D0 CF 11 E0 (OLE2 Compound)
    'doc':  [b'\xd0\xcf\x11\xe0'],
    'xls':  [b'\xd0\xcf\x11\xe0'],
    'ppt':  [b'\xd0\xcf\x11\xe0'],
}

# أنواع الملفات النصية اللي مالهاش Magic Bytes ثابتة
# هنفحصها بطريقة تانية (نسبة الـ printable bytes)
TEXT_TYPES = {'txt', 'log', 'csv', 'json', 'xml', 'md', 'ini', 'cfg', 'py', 'js', 'html', 'css'}


# =========================================================
# 1. Entropy
# =========================================================

def calculate_entropy(data: bytes) -> float:
    """
    تحسب Shannon Entropy لمحتوى الملف.

    الفكرة:
      - نحسب احتمال ظهور كل Byte (من 0 إلى 255)
      - نطبق معادلة Shannon:  H = -Σ p(x) * log2(p(x))

    النتيجة:
      0.0 = الملف فيه تكرار شديد (كل الـ bytes نفس القيمة)
      8.0 = الملف عشوائي تماماً (كل القيم متساوية الاحتمال)

    ملفات مشفرة أو مضغوطة → entropy قريبة من 7.9 - 8.0
    ملفات نصية عادية       → entropy حوالي 4.0 - 5.5
    """
    if not data:
        return 0.0

    length = len(data)
    occurrences = collections.Counter(data)

    entropy = 0.0
    for count in occurrences.values():
        p_x = count / length
        entropy -= p_x * math.log2(p_x)

    return round(entropy, 6)


def entropy_delta(old_file_path: str, new_file_path: str) -> float:
    """
    تحسب الفرق في الـ Entropy بين النسخة السليمة والنسخة الحالية.

    entropy_after - entropy_before

    مثال:
      ملف TXT: before=4.5, after=7.9  → delta = +3.4  (مشبوه!)
      ملف ZIP: before=7.8, after=7.8  → delta = 0.0   (طبيعي)
    """
    try:
        with open(old_file_path, 'rb') as f:
            old_data = f.read()
        with open(new_file_path, 'rb') as f:
            new_data = f.read()

        old_entropy = calculate_entropy(old_data)
        new_entropy = calculate_entropy(new_data)

        return round(new_entropy - old_entropy, 6)

    except Exception as e:
        print(f"[entropy_delta] Error: {e}")
        return 0.0


def get_entropy(file_path: str) -> float:
    """تحسب entropy لملف واحد."""
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        return calculate_entropy(data)
    except Exception as e:
        print(f"[get_entropy] Error: {e}")
        return 0.0


# =========================================================
# 2. Content Change Ratio
# =========================================================

def content_change_ratio(old_file_path: str, new_file_path: str) -> float:
    """
    تقيس نسبة الاختلاف بين الملف القديم والجديد.

    الطريقة:
      1. نقرأ الملفين كـ bytes
      2. نقارن byte بـ byte في الجزء المشترك
      3. الفرق في الحجم يُعتبر تغيير أيضاً

    النتيجة: من 0.0 (متطابقين) إلى 1.0 (مختلفين تماماً)

    مثال:
      Normal save    → 0.05 - 0.15  (تغيير جزء صغير)
      Encryption     → 0.90 - 1.00  (تغيير شبه كامل)
    """
    try:
        with open(old_file_path, 'rb') as f:
            old_data = f.read()
        with open(new_file_path, 'rb') as f:
            new_data = f.read()

        len_old = len(old_data)
        len_new = len(new_data)

        if len_old == 0 and len_new == 0:
            return 0.0

        min_len = min(len_old, len_new)
        max_len = max(len_old, len_new)

        if max_len == 0:
            return 0.0

        # مقارنة سريعة باستخدام NumPy
        old_arr = np.frombuffer(old_data[:min_len], dtype=np.uint8)
        new_arr = np.frombuffer(new_data[:min_len], dtype=np.uint8)

        changed_bytes = int(np.sum(old_arr != new_arr))

        # الفرق في الحجم يُعتبر bytes متغيرة
        changed_bytes += (max_len - min_len)

        return round(changed_bytes / max_len, 6)

    except Exception as e:
        print(f"[content_change_ratio] Error: {e}")
        return 0.0


# =========================================================
# 3. Chi-Square
# =========================================================

def calculate_chi_square(data: bytes) -> float:
    """
    تحسب Chi-Square statistic لمعرفة مدى قرب توزيع الـ bytes من التوزيع المنتظم.

    الفكرة:
      - لو البيانات مشفرة (عشوائية) → كل Byte (0-255) يظهر بنفس التكرار تقريباً
      - Chi-Square تقارن التوزيع الفعلي بالتوزيع المتوقع (Uniform)

    قيمة منخفضة → توزيع قريب من Uniform → غالباً مشفر أو مضغوط
    قيمة عالية  → توزيع غير منتظم → غالباً بيانات طبيعية (نص، صور خام)

    القسمة على 256 تغير المقياس فقط، ولا تلغي الاعتماد على حجم العينة.
    """
    if not data:
        return 0.0

    length = len(data)
    expected_freq = length / 256.0

    if expected_freq == 0:
        return 0.0

    # التردد الفعلي لكل byte
    observed_freq = np.zeros(256)
    counts = collections.Counter(data)
    for byte_val, count in counts.items():
        observed_freq[byte_val] = count

    # حساب Chi-Square: Σ (observed - expected)² / expected
    chi_sq = float(np.sum(((observed_freq - expected_freq) ** 2) / expected_freq))

    # Normalize: نقسم على عدد الـ categories (256)
    # لا تلغي اعتماد الإحصاء على طول العينة
    normalized = chi_sq / 256.0

    return round(normalized, 6)


def get_chi_square(file_path: str) -> float:
    """تقرأ الملف وتحسب Chi-Square الخاص به."""
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        return calculate_chi_square(data)
    except Exception as e:
        print(f"[get_chi_square] Error: {e}")
        return 0.0


# =========================================================
# 4. Structure Broken
# =========================================================

def _check_text_structure(file_path: str) -> int:
    """
    فحص ملفات نصية (txt, log, csv, json, xml ...).

    الطريقة:
      - نحسب نسبة الـ Control Bytes (غير المطبوعة إطلاقاً مثل 0x00..0x08, 0x0B, 0x0C, 0x0E..0x1F).
      - في النص الطبيعي (سواء عربي UTF-8, CP1256, أو إنجليزي) النسبة تكون 0%.
      - في التشفير العشوائي النسبة تكون بين 10% إلى 15%.

    النتيجة:
      0 = نص سليم
      1 = هيكل النص مكسور (بيانات عشوائية مشفرة)
    """
    try:
        with open(file_path, 'rb') as f:
            sample = f.read(4096)

        if not sample:
            return 0  # ملف فاضي نعتبره سليم

        # حساب عدد Control Bytes
        control_bytes = sum(
            1 for b in sample
            if (0 <= b <= 8) or b in (11, 12) or (14 <= b <= 31)
        )

        control_ratio = control_bytes / len(sample)

        # لو النسبة أكبر من 3% → النص مشفر ومكسور الهيكل
        if control_ratio > 0.03:
            return 1

        return 0

    except Exception as e:
        print(f"[_check_text_structure] Error: {e}")
        return 1


def structure_broken(file_path: str, file_type: str) -> int:
    """
    تفحص هل الهيكل الأصلي للملف اتدمر بعد التعديل.

    الطريقة:
      - ملفات ليها Magic Bytes (PDF, JPG, PNG, ZIP, DOCX, XLSX, PPTX...)
        → نفحص أول كام Byte ونقارنهم بالبصمة المعروفة
      - ملفات نصية (TXT, LOG, CSV, JSON...)
        → نفحص نسبة الـ printable characters

    النتيجة:
      0 = الهيكل سليم
      1 = الهيكل مكسور (غالباً اتشفر)
    """
    ext = file_type.lower().strip('.')

    # --- ملفات نصية ---
    if ext in TEXT_TYPES:
        return _check_text_structure(file_path)

    # --- ملفات ليها Magic Bytes ---
    signatures = FILE_SIGNATURES.get(ext)

    if signatures is None:
        # نوع ملف مش معروف → نعتبره سليم (لا نستطيع الحكم)
        return 0

    try:
        with open(file_path, 'rb') as f:
            # نقرأ أكبر حجم Header مطلوب
            max_sig_len = max(len(sig) for sig in signatures)
            header = f.read(max_sig_len)

        # نفحص هل الـ header يبدأ بأي من البصمات المعروفة
        for sig in signatures:
            if header.startswith(sig):
                return 0  # سليم

        return 1  # مكسور

    except Exception as e:
        print(f"[structure_broken] Error: {e}")
        return 1



# =========================================================
# 5. Compression and overlapping window analysis
# =========================================================

def calculate_compression_ratio(data: bytes) -> float:
    """zlib(level=6) size / original size. Empty data -> 0.

    Values may exceed 1 because of compression overhead. Compressed files
    and encrypted bytes may both be incompressible. This is not a verdict.
    """
    return round(len(zlib.compress(data, level=6)) / len(data), 6) if data else 0.0


def _change_ratio_bytes(old: bytes, new: bytes) -> float:
    size = max(len(old), len(new))
    if not size:
        return 0.0
    common = min(len(old), len(new))
    changed = int(np.count_nonzero(
        np.frombuffer(old[:common], dtype=np.uint8) !=
        np.frombuffer(new[:common], dtype=np.uint8)))
    return round((changed + abs(len(old) - len(new))) / size, 6)


def analyze_windows(old_data: bytes, new_data: bytes,
                    window_size: int = 4096, step_size: int = 2048) -> dict:
    """Same-offset overlapping windows, including a short final window.

    Returns fixed numeric summaries rather than variable-length lists for ML.
    Chi-square / 256 is the local distribution statistic, not a probability.
    Changes in byte offsets caused by insertions can inflate change ratios.
    """
    if (isinstance(window_size, bool) or not isinstance(window_size, int) or
            isinstance(step_size, bool) or not isinstance(step_size, int) or
            window_size <= 0 or not 0 < step_size <= window_size):
        raise ValueError('Require integer window_size >= step_size > 0')
    rows = {name: [] for name in (
        'entropy_after', 'entropy_delta', 'chi_square_after', 'change_ratio')}
    total = max(len(old_data), len(new_data))
    start = 0
    while start < total:
        old = old_data[start:start + window_size]
        new = new_data[start:start + window_size]
        after = calculate_entropy(new)
        rows['entropy_after'].append(after)
        rows['entropy_delta'].append(after - calculate_entropy(old))
        rows['chi_square_after'].append(calculate_chi_square(new))
        rows['change_ratio'].append(_change_ratio_bytes(old, new))
        if start + window_size >= total:
            break
        start += step_size
    result = {'window_count': len(rows['change_ratio'])}
    for name, values in rows.items():
        for stat, operation in [('mean', np.mean), ('std', np.std),
                                ('min', np.min), ('max', np.max)]:
            result[f'window_{name}_{stat}'] = round(float(operation(values)), 6) if values else 0.0
    return result


MODEL_FEATURE_NAMES = (
    'entropy_after', 'entropy_delta', 'content_change_ratio',
    'chi_square_after', 'structure_broken', 'compression_ratio',
    'compression_ratio_delta',
) + tuple(f'window_{name}_{stat}' for name in (
    'entropy_after', 'entropy_delta', 'chi_square_after', 'change_ratio'
) for stat in ('mean', 'std', 'min', 'max'))


def extract_all_features(original_path: str, current_path: str, file_type: str,
                         *, window_size: int = 4096,
                         step_size: int = 2048,
                         include_baseline: bool = False) -> dict:
    """Compare original/current files; no classification or model training.

    Baseline columns are excluded by default but optionally returned for
    inspection/ablation. Baseline entropy is still needed to compute deltas.
    Missing/unreadable paths raise exceptions, never silently become zeros.
    Use MODEL_FEATURE_NAMES to select numeric model inputs from this dict.
    File type, sizes and window_count are metadata, not default model inputs.
    """
    old_data = Path(original_path).read_bytes()
    new_data = Path(current_path).read_bytes()
    before = calculate_entropy(old_data)
    after = calculate_entropy(new_data)
    old_compression = calculate_compression_ratio(old_data)
    compression = calculate_compression_ratio(new_data)
    result = {
        'file_type': file_type.lower().strip('.'),
        'file_size_before': len(old_data),
        'file_size_after': len(new_data),
        'entropy_after': after,
        'entropy_delta': round(after - before, 6),
        'content_change_ratio': _change_ratio_bytes(old_data, new_data),
        'chi_square_after': calculate_chi_square(new_data),
        'structure_broken': structure_broken(current_path, file_type),
        'compression_ratio': compression,
        'compression_ratio_delta': round(compression - old_compression, 6),
    }
    result.update(analyze_windows(old_data, new_data, window_size, step_size))
    if include_baseline:
        result.update(entropy_before=before,
                      chi_square_before=calculate_chi_square(old_data))
    return result
