"""
encryption_simulator.py
========================
محاكي تشفير آمن لتوليد بيانات التدريب.

مش بنستخدم Ransomware حقيقي!
بنعمل تشفير عادي باستخدام مكتبات موثوقة عشان:
  1. نعرف شكل الملف بعد التشفير
  2. نقارنه بالملف الأصلي
  3. نستخرج Features من المقارنة

الخوارزميات المستخدمة:
  - AES-GCM  (Advanced Encryption Standard)
  - ChaCha20 (Stream Cipher)

ليه أكثر من خوارزمية؟
  مش عشان نعرف اسم الخوارزمية.
  عشان الموديل ما يحفظش شكل AES بس.
  لو اتدرب على الاتنين وبعدين اكتشف تشفير بخوارزمية تالتة →
  ده دليل إنه تعلم "سلوك التشفير" مش "خوارزمية معينة".
"""

import os
import shutil
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305


def encrypt_file_aes(source_path: str, dest_path: str) -> None:
    """
    تشفّر ملف باستخدام AES-256-GCM.

    AES-GCM:
      - يعمل encryption + authentication في نفس الوقت
      - يحتاج Key (256-bit) + Nonce (96-bit)
      - الناتج = Nonce + Ciphertext + Auth Tag

    الملف الناتج يكون محتواه عشوائي تماماً بالنسبة لأي حد مش عنده الـ Key.
    وده بالضبط اللي بنحاول نكتشفه.
    """
    with open(source_path, 'rb') as f:
        plaintext = f.read()

    # Key عشوائي (256-bit = 32 bytes)
    key = os.urandom(32)
    aesgcm = AESGCM(key)

    # Nonce عشوائي (96-bit = 12 bytes)
    nonce = os.urandom(12)

    # التشفير
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    # نكتب: nonce + ciphertext في ملف جديد
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, 'wb') as f:
        f.write(nonce + ciphertext)


def encrypt_file_chacha20(source_path: str, dest_path: str) -> None:
    """
    تشفّر ملف باستخدام ChaCha20-Poly1305.

    ChaCha20:
      - Stream Cipher (مختلف عن AES اللي هو Block Cipher)
      - أسرع على الأجهزة اللي مافيهاش AES Hardware Acceleration
      - يحتاج Key (256-bit) + Nonce (96-bit)

    استخدمناه عشان الموديل يشوف pattern تاني من التشفير.
    """
    with open(source_path, 'rb') as f:
        plaintext = f.read()

    # Key عشوائي (256-bit = 32 bytes)
    key = os.urandom(32)
    chacha = ChaCha20Poly1305(key)

    # Nonce عشوائي (96-bit = 12 bytes)
    nonce = os.urandom(12)

    # التشفير
    ciphertext = chacha.encrypt(nonce, plaintext, None)

    # نكتب: nonce + ciphertext
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, 'wb') as f:
        f.write(nonce + ciphertext)


def encrypt_file(source_path: str, dest_path: str, algorithm: str = 'aes') -> str:
    """
    تشفّر ملف واحد بالخوارزمية المحددة.

    Parameters:
      source_path: مسار الملف الأصلي
      dest_path:   مسار الملف المشفر
      algorithm:   'aes' أو 'chacha20'

    Returns:
      اسم الخوارزمية المستخدمة
    """
    if algorithm.lower() == 'chacha20':
        encrypt_file_chacha20(source_path, dest_path)
        return 'chacha20'
    else:
        encrypt_file_aes(source_path, dest_path)
        return 'aes'


def copy_file_as_normal(source_path: str, dest_path: str) -> None:
    """
    تنسخ ملف كما هو (بدون تعديل).
    دي بتمثل الحالة الطبيعية: الملف ما اتغيرش.
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    shutil.copy2(source_path, dest_path)


REALISTIC_TEXT_APPENDS = [
    "\n\n--- UPDATED SECTION ---\nThis is a newly added section containing multiple paragraphs of text.\nUser copied and pasted 10 lines of notes into the file.\nLine 1: Reviewed graph theory algorithms and relation algebra examples.\nLine 2: Updated system configuration parameters for testing.\nLine 3: Verified backup integrity across protected directories.\nLine 4: Pending review by team lead before final release.\nLine 5: Added performance metrics logging.\nLine 6: Checked system resource usage during peak load.\nLine 7: Consolidated report findings.\n--- END OF SECTION ---\n",
    "\n\n--- تحديث البيانات ---\nتم إضافة هذا الجزء بواسطة المستخدم بشكل طبيعي (نسخ ولصق 10 سطور).\nسطر 1: مراجعة ملفات النظام وتقارير الأداء الفنية.\nسطر 2: إضافة الملاحظات الفنية الخاصة بمشروع كشف الفدية.\nسطر 3: تأكيد عمليات الحفظ والاسترجاع التلقائي من Version Store.\nسطر 4: التحقق من كفاءة خوارزميات الذكاء الاصطناعي.\nسطر 5: مراجعة سجل الأحداث والإنذارات.\n--- نهاية التحديث ---\n"
]


def simulate_minor_edit(source_path: str, dest_path: str) -> None:
    """
    تعديل واقعي يمثل نشاط المستخدم الطبيعي (مثل إضافة 10 سطور جديدة أو نسخ/لصق نصوص أو حفظ جديد).

    - بالنسبة للملفات النصية (txt, log, csv, json...):
      نضيف 10-15 سطر جديد حقيقي (عربي وإنجليزي) لتمثيل عملية Copy-Paste طبيعية.

    - بالنسبة للملفات الثنائية (pdf, docx, jpg...):
      نعدل جزءاً واقعياً (5% إلى 10%) يمثل إضافة ملاحظات أو حفظ مستند بعد التعديل.
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    ext = Path(source_path).suffix.lower().strip('.')

    text_extensions = {'txt', 'log', 'csv', 'json', 'xml', 'md'}

    # 1. إذا كان الملف نصياً -> نضيف سطور نصوص حقيقية (نسخ ولصق 10 سطور)
    if ext in text_extensions:
        try:
            with open(source_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            import random
            addition = random.choice(REALISTIC_TEXT_APPENDS)
            new_content = content + addition

            with open(dest_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return
        except Exception:
            pass

    # 2. للملفات الثنائية -> تعديل جزء ملائم من نهاية/محتوى الملف
    with open(source_path, 'rb') as f:
        data = bytearray(f.read())

    if len(data) == 0:
        copy_file_as_normal(source_path, dest_path)
        return

    # تعديل جزء يمثل إضافة بيانات/ملاحظات (5% من حجم الملف)
    edit_size = max(1, len(data) * 5 // 100)
    start_pos = len(data) - edit_size

    for i in range(start_pos, len(data)):
        data[i] = data[i] ^ 0x01  # تعديل بسيط للبايت يمثل حفظ جديد بدون تدمير الـ Header

    with open(dest_path, 'wb') as f:
        f.write(bytes(data))


# =========================================================
# هجمات متقدمة (Advanced Ransomware Scenarios)
# =========================================================

def encrypt_file_preserve_header(source_path: str, dest_path: str, header_size: int = 128) -> None:
    """
    يحاكي Header Preservation Attack.
    يترك أول N بايتس (الـ Header) سليمة، ويشفر الباقي.
    الهدف: خداع الـ structure_broken ليظن أن الملف سليم.
    """
    with open(source_path, 'rb') as f:
        data = f.read()
        
    if len(data) <= header_size:
        # لو الملف صغير جداً، نشفره عادي
        encrypt_file_aes(source_path, dest_path)
        return
        
    header = data[:header_size]
    plaintext = data[header_size:]
    
    key = os.urandom(32)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, 'wb') as f:
        f.write(header + nonce + ciphertext)


def encrypt_file_partial(source_path: str, dest_path: str, percentage: float = 0.25) -> None:
    """
    يحاكي Partial Encryption (Intermittent Encryption).
    يشفر جزء معين فقط من الملف (مثلاً 25% في المنتصف).
    الهدف: التشفير السريع (Fast Encryption) وتقليل الـ change_ratio وتجنب تدمير الـ Header.
    """
    with open(source_path, 'rb') as f:
        data = bytearray(f.read())
        
    if len(data) == 0:
        copy_file_as_normal(source_path, dest_path)
        return
        
    # نشفر chunk في منتصف الملف
    chunk_size = max(1, int(len(data) * percentage))
    start_pos = len(data) // 2 - chunk_size // 2
    end_pos = start_pos + chunk_size
    
    plaintext = bytes(data[start_pos:end_pos])
    
    key = os.urandom(32)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    
    # نجمع الملف: [جزء سليم قبل] + [تشفير] + [جزء سليم بعد]
    new_data = data[:start_pos] + nonce + ciphertext + data[end_pos:]
    
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, 'wb') as f:
        f.write(new_data)
