from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import time
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "workspace_952"
CHUNKS = WORKSPACE / "chunks"
RAW = WORKSPACE / "translations_raw"
MERGED = WORKSPACE / "merged_hant"
DIST = ROOT / "dist"

DEFAULT_GAME = Path(r"D:\SteamLibrary\steamapps\common\Limbus Company")
DEFAULT_HANT = DEFAULT_GAME / "LimbusCompany_Data" / "Lang" / "hant-LTM"
DEFAULT_LOCALIZE = (
    DEFAULT_GAME / "LimbusCompany_Data" / "Assets" / "Resources_moved" / "Localize"
)
DEFAULT_RCR = (
    Path(r"G:\我的雲端硬碟\LimbusLocalizationManager")
    / "scripts"
    / "auto_translate"
    / "workspace_952"
    / "rcr"
    / "extract"
)

DEFAULT_HISTORICAL = (
    ROOT.parents[1]
    / "LimbusLocalize_2026060701"
    / "LimbusCompany_Data"
    / "Lang"
    / "LLC_zh-CN"
)

HAN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
HANGUL_RE = re.compile(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]")
ASSET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-./:]*[A-Za-z0-9]$")
TAG_RE = re.compile(r"(<[^>]+>|\{[0-9A-Za-z_]+\}|\\n|\n)")

SKIP_FIELDS = {
    "id",
    "personalityid",
    "voicefile",
    "voicefile_kr",
    "usage",
    "model",
    "imgStr",
    "bgImage",
    "bgmKey",
    "voiceKey",
    "sound",
    "icon",
    "iconKey",
    "spriteName",
    "portrait",
    "motion",
    "filter",
    "type",
    "subType",
    "target",
}

PRIORITY_STORY = {
    *(f"E{i}B.json" for i in range(915, 928)),
    "E918A.json",
    "E919A.json",
    "E923I.json",
    "E926A.json",
    "E926I.json",
    "P10615.json",
    "P10815.json",
    "3D309I.json",
}

PRIORITY_EXACT = {
    "StageNode91-27.json",
    "DungeonNode91-27.json",
    "SkillTag.json",
    "GachaTitle-a1c8p2.json",
    "Passive_Ego-a1c9p3.json",
    "StoryTheaterDanteNote_13.json",
    "StoryTheaterDanteNoteDetail_13.json",
    "StoryTheaterMain-a1c7p1.json",
    "Skills_Abnormality-exme.json",
    "Skills_Assist-exme.json",
    "Skills_Enemy-exme.json",
    "Voice_Honglu_SCorp_10615.json",
    "Voice_Ishmael_LCD_10815.json",
    "DungeonName_Event.json",
    "HellsChickenDungeonNode.json",
    "MirrorDungeonTheme-1.json",
    "GachaTitle.json",
    "BattleKeywords.json",
    "Bufs.json",
    "BattleSpeechBubbleDlg.json",
    "Announcer.json",
}

PRIORITY_PATTERNS = (
    "exme",
    "exem",
    "Mirror7",
    "mirror7",
    "a1c9115",
    "9127",
    "91-27",
    "10615",
    "10815",
)

HISTORICAL_RELEVANT_RE = re.compile(
    r"(91-27|9127|exme|Mirror7|mirror7|a1c9p3|DanteNote_13|"
    r"DanteNoteDetail_13|StoryTheaterMain-a1c7p1|GachaTitle)"
)

HISTORICAL_FAMILY_PREFIXES = {
    "AbEvents",
    "ActionEvents",
    "BattleKeywords",
    "Bufs",
    "DungeonNode",
    "Enemies",
    "GachaTitle",
    "Passive_Ego",
    "Passives_Abnormality",
    "Passives_Assist",
    "Passives_Enemy",
    "Skills_Abnormality",
    "Skills_Assist",
    "Skills_Enemy",
    "StageNode",
    "StoryTheaterDanteNote",
    "StoryTheaterDanteNoteDetail",
    "StoryTheaterMain",
}

CONFIRMED_MISSING_FILES = {
    "DungeonNode91-27.json",
    "GachaTitle-a1c8p2.json",
    "Passive_Ego-a1c9p3.json",
    "Skills_Abnormality-exme.json",
    "Skills_Assist-exme.json",
    "Skills_Enemy-exme.json",
    "StoryTheaterDanteNote_13.json",
    "StoryTheaterDanteNoteDetail_13.json",
    "StoryTheaterMain-a1c7p1.json",
}

SKILLTAG_EXTRA = {
    "AlwaysUseEGOPassive2050911": "[\u5e38\u6642\u751f\u6548 - \u528d\u5951 \u5e2b\u7236 \u83ab\u723e\u7d22\u5c08\u7528\u6548\u679c]",
    "WhenUseEGOPassive": "[\u4f7f\u7528\u6642\u6548\u679c]",
}

UNITKEYWORD_EXTRA = {
    "UnitKeyword_S_CORP_SAL": "\u671d\u5ef7 - Sal",
}

STAGE_9127_TITLES = {
    912701: "\u9762\u8ac7",
    912702: "\u6703\u5408",
    912703: "\u5c0b\u627e\u8f49\u6298\u9ede",
    912704: "\u8aa4\u89e3",
    912705: "\u5e95\u7247",
    912706: "\u7167\u7247",
    912707: "\u7f50\u982d",
    912708: "\u7981\u5fcc",
    912709: "\u8ffd\u8e64",
    912710: "\u8ffd\u8e64 2",
    912711: "\u67d0\u4eba\u7684\u5fc3\u50cf",
    912712: "\u88ab\u651d\u9ad4",
}

TRANSLATABLE_FIELD_HINTS = {
    "content",
    "teller",
    "title",
    "place",
    "name",
    "desc",
    "description",
    "dlg",
    "undefined",
    "add",
    "min",
    "prevDesc",
    "codeName",
    "story",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: Path, data: Any, *, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
        f.write("\n")


def replace_dir_with_copy(src: Path, dst: Path) -> None:
    """Replace a generated directory, tolerating transient cloud-sync locks."""
    if dst.exists():
        last_error: Exception | None = None
        for _ in range(5):
            try:
                shutil.rmtree(dst)
                last_error = None
                break
            except OSError as exc:
                last_error = exc
                time.sleep(1.0)
        if dst.exists():
            stale = dst.with_name(f"{dst.name}_stale_{int(time.time())}")
            try:
                dst.rename(stale)
            except OSError:
                raise last_error or RuntimeError(f"Could not replace {dst}")
    shutil.copytree(src, dst)


def entries(doc: Any) -> list[dict[str, Any]]:
    if isinstance(doc, dict) and isinstance(doc.get("dataList"), list):
        return doc["dataList"]
    if isinstance(doc, list):
        return doc
    return []


def wrap_entries(template: Any, new_entries: list[dict[str, Any]]) -> Any:
    if isinstance(template, dict) and "dataList" in template:
        out = copy.deepcopy(template)
        out["dataList"] = new_entries
        return out
    return new_entries


def normalized_name(path: Path) -> str:
    name = path.name
    for prefix in ("EN_", "KR_"):
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


def relative_key(root: Path, path: Path) -> str:
    rel = path.relative_to(root).as_posix()
    parts = rel.split("/")
    parts[-1] = normalized_name(path)
    return "/".join(parts)


def family_name(file_name: str) -> str:
    stem = Path(normalized_name(Path(file_name))).stem
    stem = re.sub(r"[-_](?:a\d+c\d+(?:p\d+)?|a\d+c\d+|Mirror\d+.*|exme|exem)$", "", stem, flags=re.I)
    stem = re.sub(r"\d+-\d+$", "", stem)
    stem = re.sub(r"_\d+$", "", stem)
    return stem


def index_json(root: Path, *, prefixed: bool = False) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for path in root.rglob("*.json"):
        key = relative_key(root, path) if prefixed else normalized_name(path)
        out.setdefault(key, path)
    return out


def historical_families(root: Path | None) -> set[str]:
    if not root or not root.exists():
        return set()
    families = {family_name(path.name) for path in root.rglob("*.json")}
    return families | HISTORICAL_FAMILY_PREFIXES


def contains_han(value: str) -> bool:
    return bool(HAN_RE.search(value or ""))


def contains_hangul(value: str) -> bool:
    return bool(HANGUL_RE.search(value or ""))


def looks_like_asset(value: str) -> bool:
    s = (value or "").strip()
    if not s or len(s) > 100:
        return False
    if " " in s or "\n" in s:
        return False
    if not ASSET_RE.match(s):
        return False
    return bool(re.search(r"[_/:.\-0-9]", s)) or s.isupper()


def textish(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not looks_like_asset(value)


def is_untranslated(en_text: str, hant_text: Any) -> bool:
    if not isinstance(en_text, str) or not en_text.strip():
        return False
    if looks_like_asset(en_text):
        return False
    if not isinstance(hant_text, str) or not hant_text.strip():
        return True
    if contains_hangul(hant_text):
        return True
    if hant_text == en_text and not contains_han(hant_text) and len(hant_text) > 2:
        return True
    return False


def priority_name(name: str, rel_key: str, historical: set[str] | None = None) -> bool:
    base = Path(name).name
    if base in PRIORITY_STORY or base in PRIORITY_EXACT:
        return True
    if historical and HISTORICAL_RELEVANT_RE.search(base) and family_name(base) in historical:
        return True
    return any(token in base or token in rel_key for token in PRIORITY_PATTERNS)


def iter_translatable_strings(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in SKIP_FIELDS:
                continue
            child_path = f"{prefix}.{key}" if prefix else key
            out.extend(iter_translatable_strings(child, child_path))
    elif isinstance(value, list):
        if all(isinstance(x, str) for x in value):
            for idx, item in enumerate(value):
                if textish(item):
                    out.append((f"{prefix}[{idx}]", item))
        else:
            for idx, child in enumerate(value):
                out.extend(iter_translatable_strings(child, f"{prefix}[{idx}]"))
    elif textish(value):
        leaf = prefix.rsplit(".", 1)[-1]
        leaf = re.sub(r"\[\d+\]$", "", leaf)
        if leaf in TRANSLATABLE_FIELD_HINTS or not looks_like_asset(value):
            out.append((prefix, value))
    return out


def parse_field_path(field_path: str) -> list[str | int]:
    parts: list[str | int] = []
    for piece in field_path.split("."):
        pos = 0
        match = re.match(r"^[^\[]+", piece)
        if match:
            parts.append(match.group(0))
            pos = len(match.group(0))
        for idx_match in re.finditer(r"\[(\d+)\]", piece[pos:]):
            parts.append(int(idx_match.group(1)))
    return parts


def get_field(entry: dict[str, Any] | None, field_path: str) -> Any:
    current: Any = entry
    for part in parse_field_path(field_path):
        if isinstance(part, int):
            if not isinstance(current, list) or part >= len(current):
                return None
            current = current[part]
        else:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
    return current


def build_unit(
    *,
    file_key: str,
    source_rel: str,
    entry: dict[str, Any],
    hant_entry: dict[str, Any] | None,
    position: int,
    missing_file: bool,
    missing_entry: bool,
) -> dict[str, Any] | None:
    fields: dict[str, str] = {}
    context: dict[str, Any] = {}
    for field_path, value in iter_translatable_strings(entry):
        hant_value = get_field(hant_entry, field_path)
        if missing_file or missing_entry or is_untranslated(value, hant_value):
            fields[field_path] = value
    for key in ("id", "model", "personalityid", "voicefile", "usage"):
        if key in entry:
            context[key] = entry[key]
    if not fields:
        return None
    return {
        "file": file_key,
        "source_rel": source_rel,
        "id": entry.get("id"),
        "position": position,
        "missing_file": missing_file,
        "missing_entry": missing_entry,
        "context": context,
        "fields": fields,
    }


def analyze_sources(
    hant_root: Path,
    localize_root: Path,
    rcr_root: Path | None,
    historical_root: Path | None,
) -> dict[str, Any]:
    en_root = localize_root / "en"
    kr_root = localize_root / "kr"
    en_index = index_json(en_root, prefixed=True)
    hant_index = index_json(hant_root, prefixed=True)
    kr_index = index_json(kr_root, prefixed=True) if kr_root.exists() else {}
    rcr_index = index_json(rcr_root, prefixed=True) if rcr_root and rcr_root.exists() else {}
    historical = historical_families(historical_root)

    units: list[dict[str, Any]] = []
    skipped_nonpriority: list[str] = []
    file_stats: dict[str, dict[str, Any]] = {}

    for file_key, en_path in sorted(en_index.items()):
        base = Path(file_key).name
        is_priority = priority_name(base, file_key, historical)
        en_doc = load_json(en_path)
        en_entries = entries(en_doc)
        hant_path = hant_index.get(file_key)
        hant_entries = entries(load_json(hant_path)) if hant_path else []
        hant_by_id = {
            item.get("id"): item
            for item in hant_entries
            if isinstance(item, dict) and "id" in item
        }
        missing_file = hant_path is None
        file_units: list[dict[str, Any]] = []
        for position, entry in enumerate(en_entries):
            if not isinstance(entry, dict):
                continue
            hant_entry = hant_by_id.get(entry.get("id"))
            missing_entry = hant_entry is None
            if not is_priority and (missing_file or missing_entry):
                continue
            unit = build_unit(
                file_key=file_key,
                source_rel=en_path.relative_to(en_root).as_posix(),
                entry=entry,
                hant_entry=hant_entry,
                position=position,
                missing_file=missing_file,
                missing_entry=missing_entry,
            )
            if unit:
                if is_priority:
                    file_units.append(unit)
                else:
                    skipped_nonpriority.append(file_key)
        if file_units:
            units.extend(file_units)
            file_stats[file_key] = {
                "units": len(file_units),
                "fields": sum(len(u["fields"]) for u in file_units),
                "missing_file": missing_file,
                "rcr_present": file_key in rcr_index or base in rcr_index,
                "kr_present": file_key in kr_index or base in kr_index,
            }
        elif is_priority and missing_file:
            file_stats[file_key] = {
                "units": 0,
                "fields": 0,
                "missing_file": True,
                "copy_only": True,
                "rcr_present": file_key in rcr_index or base in rcr_index,
                "kr_present": file_key in kr_index or base in kr_index,
            }

    report = {
        "stats": {
            "en_files": len(en_index),
            "hant_files": len(hant_index),
            "kr_files": len(kr_index),
            "rcr_files": len(rcr_index),
            "historical_families": len(historical),
            "candidate_files": len(file_stats),
            "candidate_units": len(units),
            "candidate_fields": sum(len(u["fields"]) for u in units),
            "skipped_nonpriority_files": len(set(skipped_nonpriority)),
        },
        "files": dict(sorted(file_stats.items())),
        "units": units,
    }
    return report


def chunk_kind(file_key: str) -> str:
    base = Path(file_key).name
    if base in PRIORITY_STORY or "/StoryData/" in file_key or file_key.startswith("StoryData/"):
        return "story"
    if "Voice_" in base or "BattleSpeechBubble" in base:
        return "voice"
    return "ui"


def write_chunks(report: dict[str, Any], *, chunk_size: int) -> dict[str, Any]:
    if CHUNKS.exists():
        shutil.rmtree(CHUNKS)
    CHUNKS.mkdir(parents=True)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unit in report["units"]:
        groups[chunk_kind(unit["file"])].append(unit)

    chunk_docs = []
    counters = {"story": 200, "ui": 300, "voice": 400}
    for kind in ("story", "ui", "voice"):
        units = groups.get(kind, [])
        for start in range(0, len(units), chunk_size):
            cid = f"chunk_{counters[kind]}"
            counters[kind] += 1
            doc = {
                "chunk": cid,
                "kind": kind,
                "instructions": (
                    "Translate only values in fields from English to Traditional Chinese. "
                    "Keep JSON structure, ids, placeholders, tags, \\n, E.G.O, LCB/LCCB/LCE, "
                    "Gesellschaft, Maestro, and asset/model keys unchanged. "
                    "Use Limbus Traditional Mandarin naming conventions."
                ),
                "units": units[start : start + chunk_size],
            }
            save_json(CHUNKS / f"{cid}.json", doc)
            chunk_docs.append({"chunk": cid, "kind": kind, "units": len(doc["units"])})
    manifest = {"chunks": chunk_docs, "stats": report["stats"]}
    save_json(WORKSPACE / "chunks_manifest.json", manifest)
    return manifest


def command_prepare(args: argparse.Namespace) -> None:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    report = analyze_sources(
        Path(args.hant),
        Path(args.localize),
        Path(args.rcr) if args.rcr else None,
        Path(args.historical) if args.historical else None,
    )
    save_json(WORKSPACE / "analysis.json", report)
    manifest = write_chunks(report, chunk_size=args.chunk_size)
    print(json.dumps({"analysis": report["stats"], "chunks": manifest["chunks"][:10]}, ensure_ascii=False, indent=2))
    print(f"Wrote {WORKSPACE / 'analysis.json'}")
    print(f"Wrote chunks to {CHUNKS}")


def load_translations() -> dict[tuple[str, Any, int], dict[str, str]]:
    out: dict[tuple[str, Any, int], dict[str, str]] = {}
    if not RAW.exists():
        raise RuntimeError(f"{RAW} missing")
    for path in sorted(RAW.glob("chunk_*.json")):
        doc = load_json(path)
        translations = doc.get("translations") if isinstance(doc, dict) else None
        if not isinstance(translations, list):
            raise RuntimeError(f"{path} must contain {{'translations': [...]}}")
        for item in translations:
            key = (item["file"], item.get("id"), item["position"])
            fields = item.get("fields", {})
            if not isinstance(fields, dict):
                raise RuntimeError(f"{path}: fields must be an object")
            out.setdefault(key, {}).update(fields)
    return out


def set_field(entry: dict[str, Any], field_path: str, value: str) -> None:
    parts = parse_field_path(field_path)
    current: Any = entry
    for i, part in enumerate(parts[:-1]):
        nxt = parts[i + 1]
        if isinstance(part, int):
            if not isinstance(current, list):
                raise RuntimeError(f"Cannot index non-list while setting {field_path}")
            while len(current) <= part:
                current.append({} if isinstance(nxt, str) else [])
            if current[part] is None:
                current[part] = {} if isinstance(nxt, str) else []
            current = current[part]
        else:
            if not isinstance(current, dict):
                raise RuntimeError(f"Cannot key non-dict while setting {field_path}")
            if part not in current or current[part] is None:
                current[part] = {} if isinstance(nxt, str) else []
            current = current[part]
    last = parts[-1]
    if isinstance(last, int):
        if not isinstance(current, list):
            raise RuntimeError(f"Cannot index non-list while setting {field_path}")
        while len(current) <= last:
            current.append("")
        current[last] = value
    else:
        if not isinstance(current, dict):
            raise RuntimeError(f"Cannot key non-dict while setting {field_path}")
        current[last] = value


def enforce_glossary(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: enforce_glossary(child) for key, child in value.items()}
    if isinstance(value, list):
        return [enforce_glossary(child) for child in value]
    if not isinstance(value, str):
        return value
    out = value
    out = out.replace("Bamboo-hatted Kim", "\u91d1\u7b20")
    out = out.replace("Dokkaebi Arms", "\u9b3c\u602a\u81c2")
    out = out.replace("\u7af9\u7b20\u91d1", "\u91d1\u7b20")
    out = out.replace("\u7af9\u7b20 Kim", "\u91d1\u7b20")
    out = out.replace("(\ub354\ubbf8)", "(\u5360\u4f4d)")
    out = out.replace("No particular effect", "\u7121\u7279\u6b8a\u6548\u679c")
    out = out.replace("Say that you're not.", "\u8aaa\u81ea\u5df1\u4e26\u975e\u5982\u6b64\u3002")
    out = out.replace("The wind-howling path.", "\u72c2\u98a8\u547c\u5578\u7684\u9053\u8def\u3002")
    out = out.replace("The silent path.", "\u5bc2\u975c\u7121\u8072\u7684\u9053\u8def\u3002")
    out = out.replace("All Identities lose SP", "\u5168\u9ad4\u4eba\u683c\u5931\u53bb SP")
    out = out.replace("Furioso-Replica", "\u72c2\u60f3\u66f2-\u8907\u88fd\u54c1")
    out = out.replace("Aeng-du", "\u6afb\u6843")
    out = out.replace("[Sal]", "\uff08Sal\uff09")
    out = out.replace("[Crescendo]", "\uff08Crescendo\uff09")
    out = out.replace("[Lacrimosa-Crescendo]", "\uff08Lacrimosa-Crescendo\uff09")
    return out


def enforce_file_specific(file_key: str, doc: Any) -> Any:
    doc = enforce_glossary(doc)
    if file_key == "StageNode91-27.json":
        for item in entries(doc):
            if isinstance(item, dict) and item.get("id") in STAGE_9127_TITLES:
                item["title"] = STAGE_9127_TITLES[item["id"]]
    if file_key == "DungeonNode91-27.json":
        for item in entries(doc):
            if not isinstance(item, dict):
                continue
            for stage in item.get("stageList", []):
                if isinstance(stage, dict):
                    stage["title"] = STAGE_9127_TITLES.get(stage.get("id"), "\u67d0\u4eba\u7684\u5fc3\u50cf")
    if file_key == "SkillTag.json":
        current = {
            str(item.get("id")): item
            for item in entries(doc)
            if isinstance(item, dict) and "id" in item
        }
        data = entries(doc)
        for tag_id, name in SKILLTAG_EXTRA.items():
            if tag_id in current:
                current[tag_id]["name"] = name
            else:
                data.append({"id": tag_id, "name": name})
    if file_key == "UnitKeyword-exem.json":
        for item in entries(doc):
            if isinstance(item, dict) and item.get("id") in UNITKEYWORD_EXTRA:
                item["content"] = UNITKEYWORD_EXTRA[item["id"]]
    return doc


def command_merge(args: argparse.Namespace) -> None:
    analysis = load_json(WORKSPACE / "analysis.json")
    translations = load_translations()
    localize = Path(args.localize)
    en_index = index_json(localize / "en", prefixed=True)

    replace_dir_with_copy(Path(args.hant), MERGED)

    units_by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unit in analysis["units"]:
        units_by_file[unit["file"]].append(unit)

    missing_translations = []
    files_written = 0
    fields_written = 0
    for file_key in sorted(analysis["files"]):
        units = units_by_file.get(file_key, [])
        source_doc = load_json(en_index[file_key])
        source_entries = entries(source_doc)
        target = MERGED / file_key
        if target.exists():
            target_doc = load_json(target)
            target_entries = entries(target_doc)
            template = target_doc
        else:
            target_doc = copy.deepcopy(source_doc)
            target_entries = entries(target_doc)
            template = target_doc

        # Use id when available; fall back to source position for id-less story entries.
        by_id = {
            item.get("id"): item
            for item in target_entries
            if isinstance(item, dict) and "id" in item
        }
        while len(target_entries) < len(source_entries):
            target_entries.append(copy.deepcopy(source_entries[len(target_entries)]))
        processed_keys: set[tuple[str, Any, int]] = set()
        for unit in units:
            tr_key = (unit["file"], unit.get("id"), unit["position"])
            if tr_key in processed_keys:
                continue
            processed_keys.add(tr_key)
            fields = translations.get(tr_key)
            if fields is None:
                missing_translations.append(unit)
                continue
            entry = by_id.get(unit.get("id")) if unit.get("id") is not None else None
            if entry is None:
                entry = target_entries[unit["position"]]
                if not isinstance(entry, dict):
                    entry = copy.deepcopy(source_entries[unit["position"]])
                    target_entries[unit["position"]] = entry
            for field, value in fields.items():
                set_field(entry, field, value)
                fields_written += 1
        save_json(target, enforce_file_specific(file_key, wrap_entries(template, target_entries)))
        files_written += 1

    if missing_translations:
        save_json(WORKSPACE / "missing_translations.json", missing_translations)
    print(f"files_written={files_written} fields_written={fields_written} missing={len(missing_translations)}")
    if missing_translations and not args.allow_missing:
        raise SystemExit("missing translations; see workspace_952/missing_translations.json")


def scan_strings(value: Any, path: str = "") -> list[tuple[str, str]]:
    out = []
    if isinstance(value, dict):
        for key, child in value.items():
            out.extend(scan_strings(child, f"{path}.{key}" if path else str(key)))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            out.extend(scan_strings(child, f"{path}[{idx}]"))
    elif isinstance(value, str):
        out.append((path, value))
    return out


def relevant_missing_outputs(localize_root: Path, historical_root: Path | None) -> list[str]:
    en_index = index_json(localize_root / "en", prefixed=True)
    merged_index = index_json(MERGED, prefixed=True) if MERGED.exists() else {}
    historical = historical_families(historical_root)
    missing = []
    for file_key in sorted(en_index):
        base = Path(file_key).name
        if file_key in merged_index:
            continue
        if base in CONFIRMED_MISSING_FILES:
            missing.append(file_key)
            continue
        if HISTORICAL_RELEVANT_RE.search(base) and family_name(base) in historical:
            missing.append(file_key)
    return missing


def strict_placeholder_file(file_key: str) -> bool:
    base = Path(file_key).name
    if base in {
        "StageNode91-27.json",
        "DungeonNode91-27.json",
        "SkillTag.json",
        "GachaTitle-a1c8p2.json",
        "StoryTheaterDanteNote_13.json",
        "StoryTheaterDanteNoteDetail_13.json",
        "StoryTheaterMain-a1c7p1.json",
        "UnitKeyword-exem.json",
    }:
        return True
    return any(token in base for token in ("exme", "Mirror7", "a1c9p3"))


def glossary_issues_for_value(file_key: str, path: str, value: str) -> list[dict[str, Any]]:
    issues = []
    if looks_like_asset(value):
        return issues
    if strict_placeholder_file(file_key) and ("???" in value or re.fullmatch(r"\?{2,}(?:\s*\d+)?", value.strip())):
        issues.append({"file": file_key, "field": path, "problem": "placeholder_question_marks", "sample": value[:160]})
    if "Bamboo-hatted Kim" in value:
        issues.append({"file": file_key, "field": path, "problem": "glossary_bamboo_hatted_kim", "sample": value[:160]})
    if "Dokkaebi Arms" in value:
        issues.append({"file": file_key, "field": path, "problem": "glossary_dokkaebi_arms", "sample": value[:160]})
    if "\u7af9\u7b20\u91d1" in value or "\u7af9\u7b20 Kim" in value:
        issues.append({"file": file_key, "field": path, "problem": "glossary_kim_variant", "sample": value[:160]})
    if re.search(r"(?<![A-Za-z])Kim(?![A-Za-z])", value):
        issues.append({"file": file_key, "field": path, "problem": "glossary_kim_english", "sample": value[:160]})
    return issues


def reference_token_ids() -> set[str]:
    ids: set[str] = set()
    for pattern in ("SkillTag.json", "BattleKeywords*.json", "Bufs*.json", "UnitKeyword*.json"):
        for path in MERGED.glob(pattern):
            try:
                doc = load_json(path)
            except Exception:
                continue
            for item in entries(doc):
                if isinstance(item, dict) and "id" in item:
                    ids.add(str(item["id"]))
    return ids


def bracket_token_issues(file_key: str, path: str, value: str, valid_ids: set[str]) -> list[dict[str, Any]]:
    issues = []
    if looks_like_asset(value):
        return issues
    for token in re.findall(r"\[([A-Za-z0-9_]+)\]", value):
        if token not in valid_ids:
            issues.append({"file": file_key, "field": path, "problem": "unknown_bracket_token", "token": token, "sample": value[:160]})
    return issues


def command_qa(args: argparse.Namespace) -> None:
    analysis = load_json(WORKSPACE / "analysis.json")
    issues = []
    valid_token_ids = reference_token_ids()
    coverage_missing = relevant_missing_outputs(Path(args.localize), Path(args.historical) if args.historical else None)
    for file_key in coverage_missing:
        issues.append({"file": file_key, "problem": "coverage_missing"})
    by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unit in analysis["units"]:
        by_file[unit["file"]].append(unit)

    for file_key in sorted(analysis["files"]):
        units = by_file.get(file_key, [])
        path = MERGED / file_key
        try:
            doc = load_json(path)
        except Exception as exc:
            issues.append({"file": file_key, "problem": "json_parse", "error": str(exc)})
            continue
        doc_entries = entries(doc)
        by_id = {
            item.get("id"): item
            for item in doc_entries
            if isinstance(item, dict) and "id" in item
        }
        for field_path, value in iter_translatable_strings(doc):
            issues.extend(glossary_issues_for_value(file_key, field_path, value))
            issues.extend(bracket_token_issues(file_key, field_path, value, valid_token_ids))
        for unit in units:
            entry = by_id.get(unit.get("id")) if unit.get("id") is not None else None
            if entry is None and unit["position"] < len(doc_entries):
                entry = doc_entries[unit["position"]]
            if not isinstance(entry, dict):
                issues.append({"file": file_key, "id": unit.get("id"), "position": unit["position"], "problem": "entry_missing"})
                continue
            for field_path, value in iter_translatable_strings(entry):
                if contains_hangul(value):
                    issues.append({"file": file_key, "id": unit.get("id"), "position": unit["position"], "field": field_path, "problem": "hangul", "sample": value[:120]})
                if (
                    len(value.strip()) > 24
                    and not contains_han(value)
                    and re.search(r"[A-Za-z]{4,}", value)
                    and not looks_like_asset(value)
                ):
                    issues.append({"file": file_key, "id": unit.get("id"), "position": unit["position"], "field": field_path, "problem": "english_leftover", "sample": value[:160]})
    save_json(WORKSPACE / "qa_issues.json", issues)
    summary = {"issues": len(issues), "blocking": len(issues)}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if issues and not args.allow_issues:
        raise SystemExit("QA issues remain; see workspace_952/qa_issues.json")


def zip_tree(src: Path, dst: Path) -> int:
    count = 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(src.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(src).as_posix())
                count += 1
    return count


def command_package(args: argparse.Namespace) -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    zip_path = DIST / "my-patch.zip"
    count = zip_tree(MERGED, zip_path)
    size = zip_path.stat().st_size
    version = f"1780889854-patched-952-{time.strftime('%Y%m%d%H%M')}"
    manifest = {
        "format_version": 1,
        "localizations": [
            {
                "id": "hant-mypatch-952",
                "version": version,
                "name": "Canto 9.5.2 繁中補丁 (auto-translate)",
                "flag": "HANT.png",
                "icon": "",
                "description": (
                    "Limbus Company 9.5.2 繁體中文補丁\\n"
                    "- 基於官方 LTM hant-LTM 1780889854\\n"
                    "- 補 9.5.2 新增故事、事件、戰鬥、UI 與語音文字\\n"
                    "- 來源：本機 9.5.2 en/kr + RCR 2026-06-12 交叉查漏\\n"
                    "- License: CC BY-NC-SA 4.0"
                ),
                "authors": ["Auto-translate (based on official LTM + local 9.5.2 sources)"],
                "url": args.url,
                "size": size,
                "fonts": [
                    {
                        "url": "https://github.com/LimbusTraditionalMandarin/font/releases/download/1744630853/SarasaGothicTC-Bold.ttf",
                        "hash": "44563efaea921914d58e42bac4495881",
                        "name": "Context/ContextFont.ttf",
                    },
                    {
                        "url": "https://github.com/LimbusTraditionalMandarin/font/releases/download/1744630853/SarasaGothicTC-Bold.ttf",
                        "hash": "44563efaea921914d58e42bac4495881",
                        "name": "Title/TitleFont.ttf",
                    },
                ],
                "format": "new",
            }
        ],
    }
    save_json(ROOT / "localizations.json", manifest)
    report = load_json(WORKSPACE / "analysis.json")
    qa = load_json(WORKSPACE / "qa_issues.json") if (WORKSPACE / "qa_issues.json").exists() else []
    (ROOT / "report.md").write_text(
        "# 9.5.2 繁中補丁報告\n\n"
        f"- 基底：官方 hant-LTM `1780889854`\n"
        f"- 候選檔案：{report['stats']['candidate_files']}\n"
        f"- 候選 entries：{report['stats']['candidate_units']}\n"
        f"- 候選欄位：{report['stats']['candidate_fields']}\n"
        f"- Zip：`dist/my-patch.zip` ({size} bytes, {count} files)\n"
        f"- QA issues：{len(qa)}\n\n"
        "## 覆蓋策略\n\n"
        "以官方 LTM 為基底，只 overlay 9.5.2 缺檔、缺 id、英文 placeholder 欄位；"
        "不翻譯 asset/model/key 欄位。\n",
        encoding="utf-8",
    )
    print(f"wrote {zip_path} ({size} bytes, {count} files)")


def command_package(args: argparse.Namespace) -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    zip_path = DIST / "my-patch.zip"
    count = zip_tree(MERGED, zip_path)
    size = zip_path.stat().st_size
    version = f"1780889854-patched-952-{time.strftime('%Y%m%d%H%M')}"
    manifest = {
        "format_version": 1,
        "localizations": [
            {
                "id": "hant-mypatch-952",
                "version": version,
                "name": "Canto 9.5.2 \u7e41\u4e2d\u88dc\u4e01",
                "flag": "HANT.png",
                "icon": "",
                "description": (
                    "Limbus Company 9.5.2 \u7e41\u9ad4\u4e2d\u6587\u88dc\u4e01\\n"
                    "- \u57fa\u5e95\uff1a\u5b98\u65b9 LTM hant-LTM 1780889854\\n"
                    "- \u88dc\u4e0a 9.5.2 \u7f3a\u6a94\u3001\u7f3a id\u3001\u82f1\u6587 placeholder \u8207 UI/\u6230\u9b25\u6f0f\u7ffb\\n"
                    "- \u4f86\u6e90\u4ea4\u53c9\u6aa2\u67e5\uff1a\u672c\u6a5f 9.5.2 en/kr\u3001RCR 2026-06-12\u3001LLC_zh-CN \u6b77\u53f2\u8986\u84cb\u65cf\u7fa4\\n"
                    "- License: CC BY-NC-SA 4.0"
                ),
                "authors": ["Auto-translate (based on official LTM + local 9.5.2 sources)"],
                "url": args.url,
                "size": size,
                "fonts": [
                    {
                        "url": "https://github.com/LimbusTraditionalMandarin/font/releases/download/1744630853/SarasaGothicTC-Bold.ttf",
                        "hash": "44563efaea921914d58e42bac4495881",
                        "name": "Context/ContextFont.ttf",
                    },
                    {
                        "url": "https://github.com/LimbusTraditionalMandarin/font/releases/download/1744630853/SarasaGothicTC-Bold.ttf",
                        "hash": "44563efaea921914d58e42bac4495881",
                        "name": "Title/TitleFont.ttf",
                    },
                ],
                "format": "new",
            }
        ],
    }
    save_json(ROOT / "localizations.json", manifest)
    report = load_json(WORKSPACE / "analysis.json")
    qa = load_json(WORKSPACE / "qa_issues.json") if (WORKSPACE / "qa_issues.json").exists() else []
    (ROOT / "report.md").write_text(
        "# 9.5.2 \u7e41\u4e2d\u88dc\u4e01\u5831\u544a\n\n"
        f"- \u57fa\u5e95\uff1a\u5b98\u65b9 `hant-LTM` `1780889854`\n"
        f"- \u5019\u9078\u6a94\u6848\uff1a{report['stats']['candidate_files']}\n"
        f"- \u5019\u9078 entries\uff1a{report['stats']['candidate_units']}\n"
        f"- \u5019\u9078\u6b04\u4f4d\uff1a{report['stats']['candidate_fields']}\n"
        f"- \u6b77\u53f2\u8986\u84cb\u65cf\u7fa4\uff1a{report['stats'].get('historical_families', 0)}\n"
        f"- Zip\uff1a`dist/my-patch.zip` ({size} bytes, {count} files)\n"
        f"- QA issues\uff1a{len(qa)}\n\n"
        "## \u7b56\u7565\n\n"
        "\u4ee5\u5b98\u65b9 LTM \u70ba\u57fa\u5e95\uff0c\u53ea overlay 9.5.2 \u7f3a\u6a94\u3001\u7f3a id\u3001"
        "\u82f1\u6587 placeholder \u6b04\u4f4d\uff1b\u984d\u5916\u4f7f\u7528 LLC_zh-CN \u7684\u6b77\u53f2\u8986\u84cb"
        "\u6a94\u6848\u65cf\u7fa4\u78ba\u8a8d\u6f0f\u6a94\uff0c\u4e0d\u7ffb\u8b6f asset/model/key \u6b04\u4f4d\u3002\n",
        encoding="utf-8",
    )
    print(f"wrote {zip_path} ({size} bytes, {count} files)")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_sources(p: argparse.ArgumentParser) -> None:
        p.add_argument("--hant", default=str(DEFAULT_HANT))
        p.add_argument("--localize", default=str(DEFAULT_LOCALIZE))
        p.add_argument("--rcr", default=str(DEFAULT_RCR))
        p.add_argument("--historical", default=str(DEFAULT_HISTORICAL))

    p = sub.add_parser("prepare")
    add_sources(p)
    p.add_argument("--chunk-size", type=int, default=55)
    p.set_defaults(func=command_prepare)

    p = sub.add_parser("merge")
    add_sources(p)
    p.add_argument("--allow-missing", action="store_true")
    p.set_defaults(func=command_merge)

    p = sub.add_parser("qa")
    add_sources(p)
    p.add_argument("--allow-issues", action="store_true")
    p.set_defaults(func=command_qa)

    p = sub.add_parser("package")
    p.add_argument(
        "--url",
        default="https://raw.githubusercontent.com/phonchi/limbus-hant-951-patch/codex/952-patch/dist/my-patch.zip",
    )
    p.set_defaults(func=command_package)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
