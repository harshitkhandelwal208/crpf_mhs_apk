"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CipherVault — Encryption Engine                                           ║
║  Core cryptographic algorithms for text and image encryption               ║
╚══════════════════════════════════════════════════════════════════════════════╝

ALGORITHM DOCUMENTATION (Developer Reference)
═══════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────┐
│  TEXT CIPHER: Deterministic Symbol-Pair Substitution                       │
│                                                                           │
│  TYPE: Monoalphabetic substitution cipher using 2-character tokens         │
│                                                                           │
│  MECHANISM:                                                                │
│    1. Define a set S of 32 special characters:                             │
│       S = {! @ # $ % ^ & * ( ) - _ = + [ ] { } | ; : ' , . < > ? / ` ~}  │
│                                                                           │
│    2. Compute Cartesian product S × S → 1024 unique 2-char tokens         │
│       Example tokens: "!@", "#$", "^&", etc.                              │
│                                                                           │
│    3. Deterministic shuffle with seed=42 (Fisher-Yates via Python random)  │
│       This ensures identical mapping on any machine without key exchange   │
│                                                                           │
│    4. Map each printable ASCII character (95 chars) to a unique token:     │
│       'a' → token[0], 'b' → token[1], ... 'Z' → token[51], etc.          │
│                                                                           │
│    5. Separator: chr(1) (SOH — Start of Heading, non-printable)           │
│       Placed between tokens for unambiguous parsing during decryption      │
│                                                                           │
│  SECURITY NOTES:                                                           │
│    - NOT cryptographically secure (no key, deterministic mapping)          │
│    - Equivalent to a codebook cipher — vulnerable to frequency analysis   │
│    - Suitable for obfuscation / educational purposes only                  │
│    - The fixed seed means anyone with this code can decrypt                │
│                                                                           │
│  COMPLEXITY:                                                               │
│    - Encryption: O(n) where n = plaintext length                           │
│    - Decryption: O(n) where n = number of tokens                           │
│    - Space: O(1) — fixed 95-entry lookup tables                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  IMAGE CIPHER: Visual Encryption via RGB Extraction + Base64 Storage       │
│                                                                           │
│  TYPE: Data separation cipher — visual data stripped from carrier          │
│                                                                           │
│  MECHANISM:                                                                │
│    ENCRYPTION:                                                             │
│      1. Load image → convert to RGB color space (3 channels, 8-bit each)  │
│      2. Extract ALL pixel RGB values in raster-scan order (L→R, T→B):     │
│         pixel(0,0).R, pixel(0,0).G, pixel(0,0).B, pixel(1,0).R, ...      │
│      3. Pack into byte array → Base64 encode (6-bit → ASCII, ~33% bloat)  │
│      4. Replace original image with solid WHITE image (same dimensions)    │
│      5. Encrypt original filename using the text cipher above              │
│      6. Generate short filename: "encrypted_{MD5_hash[:8]}_[WxH].png"     │
│      7. Store metadata in sidecar .meta file:                              │
│         - ORIGINAL: original filename                                      │
│         - ENCRYPTED: cipher-encoded filename                               │
│         - RGB_BASE64: full color data                                      │
│                                                                           │
│    DECRYPTION:                                                             │
│      1. Load white encrypted image (to get dimensions)                     │
│      2. Read .meta sidecar file                                            │
│      3. Decode Base64 → raw RGB bytes                                      │
│      4. Reconstruct pixel array in same raster-scan order                  │
│      5. Restore original filename from metadata                            │
│      6. Save as "{original_name}_restored.png"                             │
│                                                                           │
│  SECURITY NOTES:                                                           │
│    - Visual encryption only — .meta file contains ALL recoverable data    │
│    - No actual cryptographic protection on pixel data                      │
│    - Filename is cipher-obfuscated but not encrypted                       │
│    - Both .png and .meta files needed for decryption                       │
│                                                                           │
│  HASH ALGORITHM: MD5 (128-bit, truncated to 8 hex chars = 32 bits)        │
│    - Used ONLY for short filename generation, NOT for security             │
│    - Collision risk is acceptable for this use case                        │
│                                                                           │
│  ENCODING: Base64 (RFC 4648)                                               │
│    - Maps 3 bytes → 4 ASCII chars (A-Z, a-z, 0-9, +, /)                  │
│    - Padding with '=' for non-multiple-of-3 lengths                       │
│    - Chosen for safe text-file storage of binary pixel data                │
└─────────────────────────────────────────────────────────────────────────────┘
"""

import random
import string
import base64
import hashlib
import os
from datetime import datetime
from PIL import Image


# ═══════════════════════════════════════════════════════════════════════════════
#  TEXT CIPHER — Symbol-Pair Substitution Engine
# ═══════════════════════════════════════════════════════════════════════════════

# ── Step 1: Define the special character alphabet ──
# 32 ASCII special characters used as cipher alphabet
# Each token is built from pairs of these, giving 32² = 1024 possible tokens
SPECIALS = list('!@#$%^&*()-_=+[]{}|;:\',.<>?/`~\\\\"')

# ── Step 2: Build the plaintext character set ──
# All unique printable ASCII characters (lowercase + uppercase + digits + space + punctuation)
# Duplicates removed via seen-set to ensure each char maps to exactly one token
_raw = (string.ascii_lowercase + string.ascii_uppercase +
        string.digits + " " + string.punctuation)
_seen: set = set()
CHARSET = [c for c in _raw if not (c in _seen or _seen.add(c))]

# ── Step 3: Generate and shuffle token pool ──
# Cartesian product S × S produces 1024 unique 2-character tokens
# Deterministic shuffle with seed=42 ensures reproducible mapping
_pool = [a + b for a in SPECIALS for b in SPECIALS]  # |_pool| = 1024
random.seed(42)
random.shuffle(_pool)  # Fisher-Yates shuffle, seeded for determinism

# ── Step 4: Build bidirectional lookup tables ──
# ENC_MAP: plaintext char → cipher token  (used for encryption)
# DEC_MAP: cipher token → plaintext char  (used for decryption)
ENC_MAP: dict[str, str] = {}
DEC_MAP: dict[str, str] = {}
for _i, _ch in enumerate(CHARSET):
    _tok = _pool[_i]
    ENC_MAP[_ch] = _tok
    DEC_MAP[_tok] = _ch

# ── Step 5: Define token separator ──
# chr(1) = SOH (Start of Heading) — non-printable ASCII control character
# Guaranteed never to appear in user input or in any cipher token
# Allows unambiguous splitting of cipher text back into individual tokens
SEP = chr(1)


def encrypt_text(plain: str) -> str:
    """
    Encrypt plaintext using symbol-pair substitution.
    
    Algorithm: Each character → lookup in ENC_MAP → 2-char token
    Tokens joined by non-printable separator chr(1)
    
    Time: O(n)  |  Space: O(n)  where n = len(plain)
    """
    return SEP.join(ENC_MAP.get(ch, "??") for ch in plain)


def decrypt_text(cipher: str) -> str:
    """
    Decrypt cipher text back to plaintext.
    
    Algorithm: Split by chr(1) → lookup each token in DEC_MAP → original char
    Unknown tokens replaced with '?'
    
    Time: O(n)  |  Space: O(n)  where n = number of tokens
    """
    return "".join(DEC_MAP.get(tok, "?") for tok in cipher.split(SEP))


# ═══════════════════════════════════════════════════════════════════════════════
#  IMAGE CIPHER — Visual Encryption via RGB Extraction + Base64
# ═══════════════════════════════════════════════════════════════════════════════

def encrypt_image(input_path: str, output_dir: str) -> dict:
    """
    Encrypt an image file.
    
    Algorithm Pipeline:
      1. PIL.Image.open() → convert to RGB (3×8-bit channels)
      2. Raster-scan all pixels → extract (R,G,B) tuples
      3. Pack into bytearray → base64.b64encode() → ASCII string
      4. Generate replacement: solid white image, same (W×H)
      5. Filename encryption: original name → text cipher → MD5[:8] hash
      6. Write .meta sidecar with ORIGINAL, ENCRYPTED, RGB_BASE64 fields
    
    Args:
        input_path: Absolute path to source image
        output_dir: Directory to save encrypted output
    
    Returns:
        dict with keys: status, filename, original, encrypted_name,
                       dimensions, pixels, size_kb, message, actual_path
    """
    try:
        img = Image.open(input_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        width, height = img.size
        total_pixels = width * height

        # ── RGB extraction: raster-scan order (left→right, top→bottom) ──
        pixels = img.load()
        rgb_bytes = bytearray()
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                rgb_bytes.append(r)
                rgb_bytes.append(g)
                rgb_bytes.append(b)

        # ── Base64 encoding: 3 raw bytes → 4 ASCII chars (~33% size increase) ──
        rgb_base64 = base64.b64encode(rgb_bytes).decode('ascii')

        # ── Visual encryption: replace with blank white image ──
        white_img = Image.new('RGB', (width, height), color='white')

        # ── Filename cipher: encrypt original name, then MD5 hash for short ID ──
        original_filename = os.path.splitext(os.path.basename(input_path))[0]
        encrypted_filename_cipher = encrypt_text(original_filename)

        # MD5 hash (truncated to 8 hex chars) for filesystem-safe short name
        hash_id = hashlib.md5(encrypted_filename_cipher.encode()).hexdigest()[:8]
        short_filename = f"encrypted_{hash_id}_[{width}x{height}].png"
        final_output_path = os.path.join(output_dir, short_filename)

        white_img.save(final_output_path)

        # ── Sidecar metadata file: stores all recoverable data ──
        meta_file = final_output_path + ".meta"
        with open(meta_file, 'w') as f:
            f.write(f"ORIGINAL:{original_filename}\n")
            f.write(f"ENCRYPTED:{encrypted_filename_cipher}\n")
            f.write(f"RGB_BASE64:{rgb_base64}\n")

        output_size = os.path.getsize(final_output_path) / 1024

        return {
            'status': 'success',
            'filename': short_filename,
            'original': original_filename,
            'encrypted_name': (encrypted_filename_cipher[:80] + "..."
                               if len(encrypted_filename_cipher) > 80
                               else encrypted_filename_cipher),
            'dimensions': f"{width} × {height}",
            'pixels': total_pixels,
            'size_kb': f"{output_size:.2f}",
            'message': "Image encrypted successfully",
            'actual_path': final_output_path,
            'meta_path': meta_file,
        }

    except FileNotFoundError:
        raise ValueError(f"Image file not found: {input_path}")
    except Exception as e:
        raise ValueError(f"Encryption error: {str(e)}")


def decrypt_image(input_path: str, output_dir: str) -> dict:
    """
    Decrypt an encrypted image file.
    
    Algorithm Pipeline:
      1. Load encrypted .png (white image) → get (W×H) dimensions
      2. Parse .meta sidecar → extract ORIGINAL name + RGB_BASE64 data
      3. base64.b64decode() → raw RGB byte array
      4. Reconstruct pixel grid in raster-scan order
      5. Save as "{original_name}_restored.png"
    
    Args:
        input_path: Path to encrypted .png file (must have .meta sidecar)
        output_dir: Directory to save restored image
    
    Returns:
        dict with keys: status, filename, original, dimensions,
                       pixels, size_kb, message, actual_path
    """
    try:
        img = Image.open(input_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        width, height = img.size
        total_pixels = width * height

        # ── Parse metadata sidecar ──
        meta_file = input_path + ".meta"
        if not os.path.exists(meta_file):
            raise ValueError(
                "Metadata file (.meta) not found — cannot decrypt without it!"
            )

        original_filename = None
        encrypted_name = None
        rgb_base64 = None

        with open(meta_file, 'r') as f:
            for line in f:
                if line.startswith("ORIGINAL:"):
                    original_filename = line.replace("ORIGINAL:", "").strip()
                elif line.startswith("ENCRYPTED:"):
                    encrypted_name = line.replace("ENCRYPTED:", "").strip()
                elif line.startswith("RGB_BASE64:"):
                    rgb_base64 = line.replace("RGB_BASE64:", "").strip()

        if not original_filename or not rgb_base64:
            raise ValueError("Invalid or corrupted metadata file")

        # ── Base64 decode: ASCII → raw RGB bytes ──
        rgb_bytes = base64.b64decode(rgb_base64)

        # ── Pixel reconstruction: raster-scan order ──
        reconstructed = Image.new('RGB', (width, height))
        pixels = reconstructed.load()

        idx = 0
        for y in range(height):
            for x in range(width):
                if idx + 2 < len(rgb_bytes):
                    r = rgb_bytes[idx]
                    g = rgb_bytes[idx + 1]
                    b = rgb_bytes[idx + 2]
                    pixels[x, y] = (r, g, b)
                    idx += 3

        final_output_path = os.path.join(
            output_dir, f"{original_filename}_restored.png"
        )
        reconstructed.save(final_output_path)

        output_size = os.path.getsize(final_output_path) / 1024
        output_filename = os.path.basename(final_output_path)

        return {
            'status': 'success',
            'filename': output_filename,
            'original': original_filename,
            'dimensions': f"{width} × {height}",
            'pixels': total_pixels,
            'size_kb': f"{output_size:.2f}",
            'message': "Image decrypted successfully",
            'actual_path': final_output_path,
        }

    except FileNotFoundError:
        raise ValueError(f"Encrypted image not found: {input_path}")
    except Exception as e:
        raise ValueError(f"Decryption error: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
#  HKNT 1.0.4 BINARY PACKAGE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

try:
    import numpy as np
    from backend.app.ai.hk_format import save_hk, load_hk, HKModelPackage
except ImportError:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
    try:
        import numpy as np
        from app.ai.hk_format import save_hk, load_hk, HKModelPackage
    except ImportError:
        save_hk = None
        load_hk = None


def export_cipher_to_hk(filepath: str, text_payload: str = "", metadata: dict = None) -> str:
    """
    Serializes encrypted payloads into the official HKNT 1.0.4 binary format (.hk).
    Conforms to 128-byte aligned header and hardware SIMD boundaries.
    """
    if save_hk is None:
        raise RuntimeError("HKNT 1.0.4 serializer unavailable (numpy or hk_format missing).")

    # Support flexible parameter ordering (payload, filepath) or (filepath, payload)
    if not filepath.endswith(".hk") and (text_payload.endswith(".hk") or ".hk" in text_payload):
        filepath, text_payload = text_payload, filepath

    meta = dict(metadata or {})
    meta.setdefault("format", "HKNT-1.0.4")
    meta.setdefault("hknt_version", "1.0.4")
    meta.setdefault("app", "CipherVault / CRPF MHS Desktop")
    meta.setdefault("created_at", datetime.now().isoformat())
    meta.setdefault("payload_type", "text_cipher")

    # Encode characters as uint8 / int32 tensor
    encoded_bytes = text_payload.encode("utf-8")
    tensor_arr = np.frombuffer(encoded_bytes, dtype=np.uint8) if len(encoded_bytes) > 0 else np.zeros((1,), dtype=np.uint8)

    tensors = {
        "cipher_payload": tensor_arr,
    }

    save_hk(filepath, tensors=tensors, metadata=meta)
    return filepath


def import_cipher_from_hk(filepath: str) -> dict:
    """
    Loads encrypted payloads directly from an HKNT 1.0.4 binary package.
    """
    if load_hk is None:
        raise RuntimeError("HKNT 1.0.4 deserializer unavailable.")

    pkg = load_hk(filepath)
    raw_arr = pkg.get("cipher_payload")
    if raw_arr is not None:
        payload_text = bytes(raw_arr.tobytes()).decode("utf-8", errors="replace")
    else:
        payload_text = ""

    return {
        "text": payload_text,
        "metadata": pkg.metadata,
        "spec_version": pkg.spec_version,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  UTILITY: Algorithm metadata for UI display
# ═══════════════════════════════════════════════════════════════════════════════

ALGORITHM_INFO = {
    'text': {
        'name': 'Symbol-Pair Substitution Cipher',
        'type': 'Monoalphabetic Substitution',
        'token_count': len(_pool),
        'charset_size': len(CHARSET),
        'special_count': len(SPECIALS),
        'mapping_count': len(ENC_MAP),
        'separator': 'chr(1) — SOH control byte',
        'seed': 42,
    },
    'image': {
        'name': 'RGB Extraction + Base64 Visual Cipher',
        'type': 'Data Separation / Visual Encryption',
        'color_space': 'RGB (3 × 8-bit channels)',
        'encoding': 'Base64 (RFC 4648)',
        'hash': 'MD5 (truncated to 32 bits)',
        'scan_order': 'Raster (left→right, top→bottom)',
    },
    'format': {
        'name': 'HKNT 1.0.4 Neural Tensor Format',
        'spec': '1.0.4',
        'alignment': '128-byte hardware alignment',
        'header_size': '128 bytes',
        'compatible': 'Android APK & Desktop Suite',
    }
}
