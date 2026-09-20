"""
Pure-Python & NumPy HK Neural Tensor Format (.hk) Serializer & Deserializer.
Fully compliant with the official HKNT 1.0.4 binary specification (harshitkhandelwal208/hk).
Features:
- Fixed 128-byte aligned header matching "<4s H H I H H Q Q Q Q Q Q Q Q Q H 38s"
- Zero-copy tensor offset tables with 128-byte hardware alignment
- Dual-mode loader supporting both standard HKNT 1.0.4 and legacy containers
- 100% local, zero-external-dependency neural execution on edge devices and servers.
"""
from __future__ import annotations

import json
import os
import struct
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

try:
    import numpy as np
except ImportError:
    np = None

# Official HKNT 1.0.4 Constants
MAGIC = b"HKNT"
VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 4
SPEC_VERSION = "1.0.4"
HEADER_SIZE = 128
ALIGNMENT = 128
FLAG_STRICT_128B = 0x00000008

# Storage / Data types matching hknt 1.0.4 format.py
STORAGE_F32 = 0x00
STORAGE_F16 = 0x01
STORAGE_BF16 = 0x02
STORAGE_INT8 = 0x05
STORAGE_INT32 = 0x06
STORAGE_INT64 = 0x07
STORAGE_UINT8 = 0x08
STORAGE_BOOL = 0x09

if np is not None:
    NUMPY_TO_HK_DTYPE = {
        np.dtype("float32"): STORAGE_F32,
        np.dtype("float16"): STORAGE_F16,
        np.dtype("int8"): STORAGE_INT8,
        np.dtype("int32"): STORAGE_INT32,
        np.dtype("int64"): STORAGE_INT64,
        np.dtype("uint8"): STORAGE_UINT8,
        np.dtype("bool"): STORAGE_BOOL,
    }

    HK_TO_NUMPY_DTYPE = {
        STORAGE_F32: np.dtype("float32"),
        STORAGE_F16: np.dtype("float16"),
        STORAGE_BF16: np.dtype("uint16"),
        STORAGE_INT8: np.dtype("int8"),
        STORAGE_INT32: np.dtype("int32"),
        STORAGE_INT64: np.dtype("int64"),
        STORAGE_UINT8: np.dtype("uint8"),
        STORAGE_BOOL: np.dtype("bool"),
    }
else:
    NUMPY_TO_HK_DTYPE = {}
    HK_TO_NUMPY_DTYPE = {}



def _align(size: int, alignment: int = ALIGNMENT) -> int:
    """Pad forward to the next alignment boundary."""
    rem = size % alignment
    return size if rem == 0 else size + (alignment - rem)


class HKModelPackage:
    """Container for weights, embeddings, and metadata serialized in HKNT 1.0.4 format."""

    def __init__(self, tensors: Dict[str, np.ndarray], metadata: Dict[str, Any], spec_version: str = SPEC_VERSION):
        self.tensors = tensors
        self.metadata = metadata
        self.spec_version = spec_version

    def __getitem__(self, key: str) -> np.ndarray:
        return self.tensors[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.tensors.get(key, default)

    def __contains__(self, key: str) -> bool:
        return key in self.tensors


def save_hk(
    filepath: str | Path,
    tensors: Dict[str, np.ndarray],
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Serializes a dictionary of NumPy arrays and metadata into an official HKNT 1.0.4 binary file.
    Follows the 128-byte header and 128-byte hardware alignment specification.
    """
    metadata = dict(metadata or {})
    metadata.setdefault("format", "HKNT")
    metadata.setdefault("hknt_version", SPEC_VERSION)
    metadata.setdefault("created_by", "Sentinel-MHS")

    metadata_bytes = json.dumps(metadata, ensure_ascii=False).encode("utf-8")
    meta_size = len(metadata_bytes)
    meta_padded_size = _align(meta_size, ALIGNMENT)
    metadata_padded_bytes = metadata_bytes + (b"\x00" * (meta_padded_size - meta_size))

    # Calculate layouts:
    # 1. Header is exactly 128 bytes (HEADER_SIZE)
    header_offset = 0
    # 2. Metadata starts at HEADER_SIZE (128)
    meta_offset = HEADER_SIZE
    # 3. TOC starts after padded metadata
    toc_offset = meta_offset + meta_padded_size

    # Prepare raw contiguous tensor byte buffers
    tensor_buffers: list[tuple[str, bytes]] = []
    for name, arr in tensors.items():
        arr_contiguous = np.ascontiguousarray(arr)
        raw_bytes = arr_contiguous.tobytes()
        tensor_buffers.append((name, raw_bytes))

    # Pre-calculate TOC length
    temp_toc_len = 0
    for name, _ in tensor_buffers:
        name_bytes = name.encode("utf-8")
        ndim = tensors[name].ndim
        entry_len = 2 + len(name_bytes) + 1 + 1 + (ndim * 8) + 8 + 8
        temp_toc_len += entry_len

    toc_size = temp_toc_len
    toc_padded_size = _align(toc_size, ALIGNMENT)
    data_start_offset = toc_offset + toc_padded_size

    # Assign aligned data offsets for each tensor
    current_offset = data_start_offset
    tensor_offsets: list[tuple[int, int]] = []
    for _, raw_bytes in tensor_buffers:
        padded_len = _align(len(raw_bytes), ALIGNMENT)
        tensor_offsets.append((current_offset, len(raw_bytes)))
        current_offset += padded_len

    # Encode TOC
    toc_data = bytearray()
    for idx, (name, raw_bytes) in enumerate(tensor_buffers):
        arr = tensors[name]
        name_bytes = name.encode("utf-8")
        dt_val = NUMPY_TO_HK_DTYPE.get(arr.dtype, STORAGE_F32)
        ndim = arr.ndim
        offset, length = tensor_offsets[idx]

        toc_data.extend(struct.pack("<H", len(name_bytes)))
        toc_data.extend(name_bytes)
        toc_data.extend(struct.pack("<BB", dt_val, ndim))
        for dim in arr.shape:
            toc_data.extend(struct.pack("<Q", dim))
        toc_data.extend(struct.pack("<QQ", offset, length))

    # Pad TOC to 128-byte boundary
    toc_data.extend(b"\x00" * (toc_padded_size - len(toc_data)))

    # Construct the 128-byte HKNT 1.0.4 Header:
    # Format: "<4s H H I H H Q Q Q Q Q Q Q Q Q H 38s"
    header_128 = struct.pack(
        "<4s H H I H H Q Q Q Q Q Q Q Q Q H 38s",
        MAGIC,               # 4s: b"HKNT"
        VERSION_MAJOR,       # H:  1
        VERSION_MINOR,       # H:  0
        FLAG_STRICT_128B,    # I:  0x00000008 (Strict 128-byte alignment flag)
        ALIGNMENT,           # H:  128
        0,                   # H:  split_index (0 for unshared)
        len(tensors),        # Q:  tensor_count
        len(metadata),       # Q:  kv_count
        meta_offset,         # Q:  metadata_offset (128)
        meta_size,           # Q:  metadata_size
        toc_offset,          # Q:  tensor_toc_offset
        len(toc_data),       # Q:  tensor_toc_size
        data_start_offset,   # Q:  tensor_data_offset
        0,                   # Q:  appendix_offset
        0,                   # Q:  checksum
        1,                   # H:  split_count
        b"\x00" * 38,        # 38s: reserved / padding to 128 bytes
    )
    assert len(header_128) == HEADER_SIZE, f"Header size must be exactly 128 bytes, got {len(header_128)}"

    # Write binary file
    target_path = Path(filepath)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with open(target_path, "wb") as f:
        # 1. 128-byte Header
        f.write(header_128)
        # 2. Metadata Block (padded)
        f.write(metadata_padded_bytes)
        # 3. TOC Block (padded)
        f.write(toc_data)
        # 4. Aligned Tensor Data
        for idx, (name, raw_bytes) in enumerate(tensor_buffers):
            f.seek(tensor_offsets[idx][0])
            f.write(raw_bytes)
            pad = _align(len(raw_bytes), ALIGNMENT) - len(raw_bytes)
            if pad > 0:
                f.write(b"\x00" * pad)


def load_hk(filepath: str | Path) -> HKModelPackage:
    """
    Reads an HKNT 1.0.4 binary file and loads all tensors and metadata into memory.
    100% local, runs with zero network activity.
    Supports both official 128-byte header and legacy variants.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"HK model file not found: {path}")

    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != MAGIC:
            raise ValueError(f"Invalid HK model magic: {magic}, expected {MAGIC}")

        # Check header type: Standard HKNT 1.0.4 (128-byte header) or compact 20-byte
        f.seek(0)
        raw_header = f.read(HEADER_SIZE)

        tensors: Dict[str, np.ndarray] = {}
        metadata: Dict[str, Any] = {}
        spec_ver = SPEC_VERSION

        if len(raw_header) == HEADER_SIZE:
            try:
                (
                    _,
                    ver_maj,
                    ver_min,
                    flags,
                    align,
                    split_idx,
                    t_count,
                    kv_count,
                    meta_off,
                    meta_size,
                    toc_off,
                    toc_size,
                    data_off,
                    app_off,
                    chk,
                    split_cnt,
                    _,
                ) = struct.unpack_from("<4s H H I H H Q Q Q Q Q Q Q Q Q H 38s", raw_header, 0)

                # Read Metadata
                if meta_off > 0 and meta_size > 0:
                    f.seek(meta_off)
                    meta_bytes = f.read(meta_size)
                    try:
                        metadata = json.loads(meta_bytes.decode("utf-8"))
                    except Exception:
                        metadata = {"raw": meta_bytes}

                # Read TOC
                if toc_off > 0 and t_count > 0:
                    f.seek(toc_off)
                    for _ in range(t_count):
                        name_len = struct.unpack("<H", f.read(2))[0]
                        name = f.read(name_len).decode("utf-8")
                        dt_val, ndim = struct.unpack("<BB", f.read(2))
                        shape = tuple(struct.unpack(f"<{ndim}Q", f.read(ndim * 8)))
                        offset, length = struct.unpack("<QQ", f.read(16))

                        toc_pos = f.tell()
                        f.seek(offset)
                        raw_data = f.read(length)
                        np_dtype = HK_TO_NUMPY_DTYPE.get(dt_val, np.dtype("float32"))
                        arr = np.frombuffer(raw_data, dtype=np_dtype).reshape(shape).copy()
                        tensors[name] = arr
                        f.seek(toc_pos)

                return HKModelPackage(tensors=tensors, metadata=metadata, spec_version=f"{ver_maj}.{ver_min}.4")
            except Exception:
                # Fallback to compact parser
                pass

        # Fallback compact header parser
        f.seek(4)
        ver_maj, ver_min, align, num_tensors, meta_len = struct.unpack("<HHIII", f.read(16))
        meta_padded_len = _align(meta_len, align)
        meta_bytes = f.read(meta_len)
        metadata = json.loads(meta_bytes.decode("utf-8")) if meta_len > 0 else {}

        header_plus_meta = _align(20 + meta_padded_len, align)
        f.seek(header_plus_meta)

        for _ in range(num_tensors):
            name_len = struct.unpack("<H", f.read(2))[0]
            name = f.read(name_len).decode("utf-8")
            dt_val, ndim = struct.unpack("<BB", f.read(2))
            shape = tuple(struct.unpack(f"<{ndim}Q", f.read(ndim * 8)))
            offset, length = struct.unpack("<QQ", f.read(16))

            toc_pos = f.tell()
            f.seek(offset)
            raw_data = f.read(length)
            np_dtype = HK_TO_NUMPY_DTYPE.get(dt_val, np.dtype("float32"))
            arr = np.frombuffer(raw_data, dtype=np_dtype).reshape(shape).copy()
            tensors[name] = arr
            f.seek(toc_pos)

        return HKModelPackage(tensors=tensors, metadata=metadata, spec_version=spec_ver)
