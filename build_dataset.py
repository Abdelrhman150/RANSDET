"""
build_dataset.py
=================
السكريبت الرئيسي اللي بيعمل كل حاجة:

1. يقرأ الملفات الأصلية من  Data/Original Files/
2. ينسخها في  version_store/original_versions/  (النسخ المرجعية)
3. ينسخها في  Data/clean/                       (ملفات سليمة)
4. يشفّرها في Data/encrypted/                   (ملفات مشفرة بـ AES + ChaCha20)
5. يعمل Minor Edit عليها في Data/clean/         (ملفات معدلة تعديل طبيعي)
6. يستخرج Features من كل زوج (أصلي ↔ حالي)
7. يحفظ features.csv في RansomwareMonitorData/  (خارج الفولدر المراقب!)

ليه features.csv في RansomwareMonitorData؟
  عشان لو Watchdog شغال بيراقب RansomwareDetection/
  وكتبنا CSV جواه → هيحصل Infinite Loop:
    ملف اتعدل → Watchdog يسجل → CSV اتعدل → Watchdog يسجل → ...

الحل: نخلي كل output files خارج الفولدر المراقب.
"""

import os
import sys
import shutil
from pathlib import Path

import pandas as pd

# =========================================================
# المسارات
# =========================================================

# المشروع الرئيسي
PROJECT_ROOT = Path(r"C:\Users\AE-Hossam\Desktop\RansomwareDetection")

# الملفات الأصلية اللي هتلاقيها جاهزة
ORIGINAL_FILES_DIR = PROJECT_ROOT / "Data" / "Original Files"

# Version Store: النسخ المرجعية للمقارنة والاسترجاع
VERSION_STORE_DIR = PROJECT_ROOT / "version_store" / "original_versions"

# Clean Data: ملفات سليمة (أصلية + معدلة تعديل طبيعي)
CLEAN_DIR = PROJECT_ROOT / "Data" / "clean"

# Encrypted Data: ملفات مشفرة
ENCRYPTED_DIR = PROJECT_ROOT / "Data" / "encrypted"

# الـ Output بره الفولدر المراقب!
OUTPUT_DIR = Path(r"C:\Users\AE-Hossam\Desktop\RansomwareMonitorData")
FEATURES_CSV = OUTPUT_DIR / "features.csv"

# =========================================================
# أنواع الملفات المدعومة
# =========================================================

# كل الأنواع اللي هنشتغل عليها
SUPPORTED_EXTENSIONS = {
    # مستندات
    '.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt',
    # نصوص
    '.txt', '.log', '.csv', '.json', '.xml',
    # صور
    '.jpg', '.jpeg', '.png',
    # مضغوط
    '.zip',
}

# =========================================================
# Imports من الملفات بتاعتنا
# =========================================================

# نضيف مسار features/ للـ Python path
sys.path.insert(0, str(PROJECT_ROOT / "features"))

from content_features import extract_all_features, MODEL_FEATURE_NAMES
from encryption_simulator import (
    encrypt_file,
    copy_file_as_normal,
    simulate_minor_edit,
    encrypt_file_preserve_header,
    encrypt_file_partial
)


def get_file_type(file_path: Path) -> str:
    """ترجع نوع الملف من الـ extension."""
    return file_path.suffix.lower().strip('.')


def collect_original_files() -> list:
    """
    تجمع كل الملفات المدعومة من فولدر Original Files.
    ترجع list من Path objects.
    """
    files = []
    for f in ORIGINAL_FILES_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(f)

    print(f"\n=== Found {len(files)} supported files ===")
    for f in files:
        size_kb = f.stat().st_size / 1024
        print(f"  [{f.suffix.upper().strip('.'): >4}]  {f.name: <55}  ({size_kb:,.1f} KB)")

    return files


def setup_directories():
    """تعمل الفولدرات لو مش موجودة."""
    for d in [VERSION_STORE_DIR, CLEAN_DIR, ENCRYPTED_DIR, OUTPUT_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    print("\n=== Directories ready ===")


def step1_copy_to_version_store(files: list):
    """
    الخطوة 1: ننسخ الملفات الأصلية في Version Store.
    دي النسخ المرجعية اللي هنقارن بيها دايماً.
    """
    print("\n=== Step 1: Copying to Version Store ===")
    for f in files:
        dest = VERSION_STORE_DIR / f.name
        shutil.copy2(str(f), str(dest))
    print(f"  Copied {len(files)} files to version_store/")


def step2_generate_scenarios(files: list) -> list:
    """
    الخطوة 2: نولّد 7 سيناريوهات لكل ملف (اثنان طبيعيان وخمسة تشفير).

    1. normal_unchanged → نسخة طبق الأصل (مافيش تعديل)
    2. normal_minor_edit → تعديل طبيعي صغير (يمثل Save)
    3. encrypted_aes → تشفير بـ AES-256-GCM
    4. encrypted_chacha20 → تشفير بـ ChaCha20-Poly1305

    ترجع list of dicts:
    [
      {
        'original': Path,      # الملف الأصلي في Version Store
        'current':  Path,      # الملف بعد السيناريو
        'label':    int,       # 0=normal, 1=ransomware
        'scenario': str,       # اسم السيناريو
        'algorithm': str,      # الخوارزمية (لو تشفير)
      },
      ...
    ]
    """
    print("\n=== Step 2: Generating scenarios ===")
    scenarios = []

    for f in files:
        original_in_store = VERSION_STORE_DIR / f.name
        file_type = get_file_type(f)
        base_name = f.stem
        ext = f.suffix

        # ---- Scenario 1: Normal (unchanged) ----
        dest_unchanged = CLEAN_DIR / f"{base_name}_unchanged{ext}"
        copy_file_as_normal(str(f), str(dest_unchanged))
        scenarios.append({
            'original':  str(original_in_store),
            'current':   str(dest_unchanged),
            'label':     0,
            'scenario':  'normal_unchanged',
            'algorithm': 'none',
            'file_name': f.name,
        })

        # ---- Scenario 2: Normal (minor edit) ----
        dest_edited = CLEAN_DIR / f"{base_name}_minor_edit{ext}"
        simulate_minor_edit(str(f), str(dest_edited))
        scenarios.append({
            'original':  str(original_in_store),
            'current':   str(dest_edited),
            'label':     0,
            'scenario':  'normal_minor_edit',
            'algorithm': 'none',
            'file_name': f.name,
        })

        # ---- Scenario 3: Encrypted (AES) ----
        dest_aes = ENCRYPTED_DIR / f"{base_name}_aes{ext}"
        encrypt_file(str(f), str(dest_aes), algorithm='aes')
        scenarios.append({
            'original':  str(original_in_store),
            'current':   str(dest_aes),
            'label':     1,
            'scenario':  'encrypted_aes',
            'algorithm': 'aes',
            'file_name': f.name,
        })

        # ---- Scenario 4: Encrypted (ChaCha20) ----
        dest_chacha = ENCRYPTED_DIR / f"{base_name}_chacha20{ext}"
        encrypt_file(str(f), str(dest_chacha), algorithm='chacha20')
        scenarios.append({
            'original':  str(original_in_store),
            'current':   str(dest_chacha),
            'label':     1,
            'scenario':  'encrypted_chacha20',
            'algorithm': 'chacha20',
            'file_name': f.name,
        })

        # ---- Scenario 5: Encrypted (Preserve Header) ----
        dest_preserve = ENCRYPTED_DIR / f"{base_name}_preserve{ext}"
        encrypt_file_preserve_header(str(f), str(dest_preserve))
        scenarios.append({
            'original':  str(original_in_store),
            'current':   str(dest_preserve),
            'label':     1,
            'scenario':  'encrypted_preserve_header',
            'algorithm': 'aes',
            'file_name': f.name,
        })

        # ---- Scenario 6: Encrypted (Partial 25%) ----
        dest_partial25 = ENCRYPTED_DIR / f"{base_name}_partial25{ext}"
        encrypt_file_partial(str(f), str(dest_partial25), percentage=0.25)
        scenarios.append({
            'original':  str(original_in_store),
            'current':   str(dest_partial25),
            'label':     1,
            'scenario':  'encrypted_partial_25',
            'algorithm': 'aes',
            'file_name': f.name,
        })

        # ---- Scenario 7: Encrypted (Partial 50%) ----
        dest_partial50 = ENCRYPTED_DIR / f"{base_name}_partial50{ext}"
        encrypt_file_partial(str(f), str(dest_partial50), percentage=0.50)
        scenarios.append({
            'original':  str(original_in_store),
            'current':   str(dest_partial50),
            'label':     1,
            'scenario':  'encrypted_partial_50',
            'algorithm': 'aes',
            'file_name': f.name,
        })

    print(f"  Generated {len(scenarios)} scenarios "
          f"({len(files)} files × 7 scenarios)")
    print(f"    Normal (unchanged):         {len(files)}")
    print(f"    Normal (minor edit):        {len(files)}")
    print(f"    Encrypted (AES):            {len(files)}")
    print(f"    Encrypted (ChaCha20):       {len(files)}")
    print(f"    Encrypted (Preserve Hdr):   {len(files)}")
    print(f"    Encrypted (Partial 25%):    {len(files)}")
    print(f"    Encrypted (Partial 50%):    {len(files)}")

    return scenarios


def step3_extract_features(scenarios: list) -> pd.DataFrame:
    """
    الخطوة 3: نستخرج الـ Features لكل سيناريو.

    لكل زوج (original, current) نحسب:
      - entropy_after, entropy_delta (before اختياري)
      - content_change_ratio
      - chi_square_after، الضغط، وملخصات النوافذ
      - structure_broken

    وبعدين نضيف:
      - file_type, scenario, algorithm, label
    """
    print("\n=== Step 3: Extracting features ===")
    rows = []
    total = len(scenarios)

    for i, s in enumerate(scenarios, 1):
        file_type = Path(s['file_name']).suffix.lower().strip('.')

        try:
            features = extract_all_features(
                original_path=s['original'],
                current_path=s['current'],
                file_type=file_type,
            )

            # نضيف المعلومات الإضافية
            features['file_name']  = s['file_name']
            features['scenario']   = s['scenario']
            features['algorithm']  = s['algorithm']
            features['label']      = s['label']

            rows.append(features)

            # Progress
            if i % 10 == 0 or i == total:
                print(f"  Processed {i}/{total} scenarios...")

        except Exception as e:
            print(f"  [ERROR] {s['file_name']} ({s['scenario']}): {e}")

    if not rows:
        raise RuntimeError("No feature rows extracted")
    df = pd.DataFrame(rows)

    # ترتيب الأعمدة بشكل منطقي
    column_order = [
        'file_name',
        'file_type',
        'file_size_before',
        'file_size_after',
        'entropy_after',
        'entropy_delta',
        'content_change_ratio',
        'chi_square_after',
        'structure_broken',
        'scenario',
        'algorithm',
        'label',
    ]

    # نرتب بالأعمدة الموجودة فعلاً
    existing_cols = [c for c in column_order if c in df.columns]
    extra_cols = [c for c in df.columns if c not in column_order]
    df = df[existing_cols + extra_cols]

    return df


def step4_save_dataset(df: pd.DataFrame):
    """
    الخطوة 4: نحفظ الـ CSV في RansomwareMonitorData/ (خارج الفولدر المراقب).
    """
    print(f"\n=== Step 4: Saving dataset ===")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(str(FEATURES_CSV), index=False, encoding='utf-8')
    print(f"  Saved to: {FEATURES_CSV}")
    print(f"  Total rows: {len(df)}")
    print(f"  Normal samples (label=0): {len(df[df['label'] == 0])}")
    print(f"  Encrypted samples (label=1): {len(df[df['label'] == 1])}")


def print_summary(df: pd.DataFrame):
    """تطبع ملخص سريع للـ Dataset."""
    print("\n" + "=" * 70)
    print("DATASET SUMMARY")
    print("=" * 70)

    print(f"\n  Total samples: {len(df)}")
    print(f"  File types: {sorted(df['file_type'].unique())}")
    print(f"  Scenarios: {sorted(df['scenario'].unique())}")

    print("\n  --- Label Distribution ---")
    for label, count in df['label'].value_counts().sort_index().items():
        label_name = "Normal" if label == 0 else "Suspicious Encryption"
        print(f"    {label} ({label_name}): {count}")

    print("\n  --- Feature Statistics ---")
    feature_cols = list(MODEL_FEATURE_NAMES)
    for col in feature_cols:
        if col in df.columns:
            print(f"\n    {col}:")
            print(f"      Normal (label=0):     "
                  f"mean={df[df['label']==0][col].mean():.4f}  "
                  f"std={df[df['label']==0][col].std():.4f}")
            print(f"      Encrypted (label=1):  "
                  f"mean={df[df['label']==1][col].mean():.4f}  "
                  f"std={df[df['label']==1][col].std():.4f}")

    print("\n" + "=" * 70)


# =========================================================
# Main
# =========================================================

def main():
    print("=" * 70)
    print("CryptoShield - Dataset Builder")
    print("=" * 70)

    # تجهيز الفولدرات
    setup_directories()

    # جمع الملفات الأصلية
    files = collect_original_files()

    if not files:
        print("\n[ERROR] No supported files found in Original Files directory!")
        print(f"  Path: {ORIGINAL_FILES_DIR}")
        return

    # الخطوة 1: نسخ للـ Version Store
    step1_copy_to_version_store(files)

    # الخطوة 2: توليد السيناريوهات
    scenarios = step2_generate_scenarios(files)

    # الخطوة 3: استخراج الـ Features
    df = step3_extract_features(scenarios)

    # الخطوة 4: حفظ الـ CSV
    step4_save_dataset(df)

    # طباعة الملخص
    print_summary(df)

    print("\n[OK] Dataset built successfully!")
    print(f"   CSV location: {FEATURES_CSV}")
    print(f"   Ready for ML training.\n")


if __name__ == "__main__":
    main()
