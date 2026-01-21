# Copyright (c) 2025 TOYOTA MOTOR CORPORATION
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted (subject to the limitations in the disclaimer
# below) provided that the following conditions are met:
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * Neither the name of the copyright holder nor the names of its contributors may be used
#   to endorse or promote products derived from this software without specific
#   prior written permission.
# NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE GRANTED BY THIS
# LICENSE. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
# GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
# OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.
"""
coco_mapper.py
A tiny helper to convert between COCO category IDs and class names.

Usage:
    from coco_mapper import COCOClassMapper
    mapper = COCOClassMapper()  # By default, reads coco_categories.json in the same folder
    print(mapper.id_to_name(1))          # -> 'person'
    print(mapper.name_to_id('cat'))      # -> 17
"""

from pathlib import Path
import json
from typing import Dict


class COCOClassMapper:
    def __init__(self, mapping_file: str | Path | None = None) -> None:
        """Load mapping once and build lookup tables."""
        if mapping_file is None:
            mapping_file = Path(__file__).with_name("coco80_categories.json")
        mapping_file = Path(mapping_file).expanduser()

        try:
            with mapping_file.open(encoding="utf-8") as fp:
                categories = json.load(fp)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Mapping file not found: {mapping_file}"
            ) from e

        # Build dictionaries
        self._id2name: Dict[int, str] = {c["id"]: c["name"] for c in categories}
        self._name2id: Dict[str, int] = {c["name"]: c["id"] for c in categories}

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def id_to_name(self, cat_id: int) -> str:
        """Return class name given COCO category ID."""
        try:
            return self._id2name[cat_id]
        except KeyError as e:
            raise ValueError(f"Unknown category ID: {cat_id}") from e

    def name_to_id(self, name: str) -> int:
        """Return COCO category ID given class name (exact match)."""
        try:
            return self._name2id[name]
        except KeyError as e:
            raise ValueError(f"Unknown category name: {name}") from e

    # Python-like syntactic sugar
    def __getitem__(self, key):
        if isinstance(key, int):
            return self.id_to_name(key)
        elif isinstance(key, str):
            return self.name_to_id(key)
        raise TypeError("key must be int (ID) or str (name)")

    def __contains__(self, key):
        return key in self._id2name if isinstance(key, int) else key in self._name2id
