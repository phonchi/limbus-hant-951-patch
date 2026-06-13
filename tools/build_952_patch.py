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
    "RecordMemoryEvent.json",
    "Items.json",
    "Personality_Get_Condition.json",
    "DungeonName_Event.json",
    "HellsChickenDungeonNode.json",
    "IAPProduct-a1c9.json",
    "MirrorDungeonTheme-1.json",
    "GachaTitle.json",
    "StageChapterText.json",
    "TutorialMainUIText.json",
    "UnlockCode-1.json",
    "UserBanner.json",
    "UserTicket-EGOBg.json",
    "UserTicket-L.json",
    "UserTicket-R.json",
    "BattleKeywords.json",
    "Bufs.json",
    "BattleSpeechBubbleDlg.json",
    "Announcer.json",
    "ScenarioModelCodes-AutoCreated.json",
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

VISIBLE_NAME_BY_ID = {
    "BrandedKimSatgat": "\u70d9\u5370 - \u91d1\u7b20",
}

RECORD_MEMORY_TEXT_BY_ID = {
    "record_memory_stage_button_default": "\u95dc\u5361",
    "record_memory_stage_button_locked": "\u901a\u95dc 9.5-14 \u5f8c\u89e3\u9396",
    "record_memory_storybutton_default": "\u524d\u5f80\u5287\u5834",
    "record_memory_storybutton_start": "<size=75%>\u89c0\u770b\u7b2c 1 \u500b\u6d3b\u52d5\u6545\u4e8b\u95dc\u5361\u5f8c\u89e3\u9396</size>",
    "record_memory_stage_button_end_event": "\u6d3b\u52d5\u5df2\u7d50\u675f",
    "record_memory_bonus_popup_title": "\u6d3b\u52d5\u52a0\u6210\u4eba\u683c",
    "record_memory_bonusUIDesc": "\u6d3b\u52d5\u671f\u9593\uff0c\u968a\u4f0d\u4e2d\u7de8\u5165\u4e0b\u5217\u4eba\u683c\u6642\uff0c\n\u53ef\u589e\u52a0\u7372\u5f97\u7684<color=#96beee>\u300c\u7167\u7247\u300d</color>\u6578\u91cf\u3002\n\u6d3b\u52d5\u8ca8\u5e63\u7372\u5f97\u91cf\u6700\u591a\u53ef\u63d0\u5347<color=#96beee>120%</color>\u3002",
    "record_memory_scrap_guide_title": "\u6d3b\u52d5\u8ca8\u5e63\u6307\u5357",
    "record_memory_scrap_guide_desc": "\u53ef\u900f\u904e\u9996\u6b21\u901a\u95dc\u6d3b\u52d5\uff0f\u4e3b\u7dda\u6545\u4e8b\u95dc\u5361\uff0c\u6216\u901a\u95dc\u93e1\u5730\u7262\u7372\u5f97<color=#96beee>\u300c\u7167\u7247\u300d</color>\u3002\n\u904e\u7a0b\u4e2d\u4e5f\u6709\u4f4e\u6a5f\u7387\u7372\u5f97<color=#96beee>\u300c\u7167\u7247\u5305\u300d</color>\u3002\n\n\u7372\u5f97<color=#96beee>\u300c\u7167\u7247\u5305\u300d</color>\u6642\uff0c\u6703\u7acb\u5373\u8f49\u63db\u70ba 20 \u500b<color=#96beee>\u300c\u7167\u7247\u300d</color>\u3002",
    "record_memory_reward_popup_desc": "\u53ef\u900f\u904e\u4ee5\u4e0b\u65b9\u5f0f\u7372\u5f97<color=#96beee>\u300c\u7167\u7247\u300d</color>\uff1a\n\u9996\u6b21\u901a\u95dc\u6d3b\u52d5\u95dc\u5361\u8207\u4e3b\u7dda\u6545\u4e8b\u95dc\u5361\uff0c\u4ee5\u53ca\u901a\u95dc\u93e1\u5730\u7262\u3002\n\n\u53ef\u5728<color=#96beee>\u300c\u734e\u52f5\u514c\u63db\u300d</color>\u8996\u7a97\u4e2d\uff0c\n\u6d88\u8017\u5df2\u6536\u96c6\u7684<color=#96beee>\u300c\u7167\u7247\u300d</color>\u8cfc\u8cb7\u5404\u7a2e\u734e\u52f5\u3002",
    "record_memory_reward_popup_num_of_owned_items": "\u6301\u6709\u9053\u5177\u6578",
    "record_memory_rewardShopButton": "\u734e\u52f5\u514c\u63db",
}

ITEM_EXTRA_BY_ID = {
    5: {
        "desc": "\u81ea\u52d5\u8ca9\u8ce3\u6a5f\u8ca8\u5e63\u986f\u793a\u7528\uff08\u50c5\u9700\u7ffb\u8b6f name\uff09",
    },
    20046: {
        "name": "\u7167\u7247",
        "desc": "\u53ef\u5728\u734e\u52f5\u514c\u63db\u9078\u55ae\u4e2d\u8cfc\u8cb7\u5404\u7a2e\u734e\u52f5\u3002\n\n<color=#a16a3b>\uff0a\u5580\u5693\uff0a\u69cc\u5b50\u5c07\u91d8\u5b50\u6572\u5165\u7684\u8072\u97f3\u3002\u4e0d\u904e\uff0c\u7a76\u7adf\u662f\u4ec0\u9ebc\u88ab\u300c\u91d8\u300d\u4e86\u9032\u53bb\uff1f\u76f8\u6a5f\u6514\u4e0b\u67d0\u4e00\u77ac\u9593\u7684\u5149\uff0c\u5c07\u5176\u91d8\u5728\u7c97\u7cd9\u7d19\u9762\u4e0a\u4f9b\u4eba\u5c55\u793a\u3002\u7167\u7247\u662f\u70ba\u4e86\u8a18\u9304\uff0c\u9084\u662f\u70ba\u4e86\u56de\u61b6\u800c\u62cd\u4e0b\u7684\uff1f\u6216\u8a31\u7167\u7247\u7684\u540d\u7a31\uff0c\u6703\u4f9d\u7167\u5176\u7528\u9014\u800c\u6539\u8b8a\u3002\u7562\u7adf\u88ab\u69cc\u5b50\u91d8\u4f4f\u7684\u5149\u675f\uff0c\u82e5\u53ea\u88ab\u8a18\u9304\u800c\u4e0d\u88ab\u8a18\u5f97\uff0c\u672a\u514d\u592a\u904e\u53ef\u6190\u3002\u5728\u6c96\u5370\u51fa\u7684\u7167\u7247\u4e2d\uff0c\u6b7b\u53bb\u7684\u5149\u8292\u65bc\u7d55\u671b\u4e2d\u5c16\u53eb\uff0c\u7126\u9ed1\u5730\u71c3\u76e1\u3002\u90a3\u4e9b\u88ab\u91d8\u5728\u539f\u8655\u3001\u5c16\u53eb\u8457\u6d88\u901d\u7684\u6b7b\u5149\uff0c\u8a18\u9304\u4e0b\u4e86\u7167\u7247\u4e2d\u67d0\u4eba\u7684\u7b11\u5bb9\u3002</color>",
    },
    20047: {
        "name": "\u7167\u7247\u5305",
        "desc": "\u4f4e\u6a5f\u7387\u51fa\u73fe\u3002\u7372\u5f97\u6642\u6703\u7acb\u5373\u8f49\u63db\u70ba 20 \u500b\u7167\u7247\u3002\n\n<color=#a16a3b>\u300c\u9019\u88e1\u56de\u6536\u5230\u4e86\u76f8\u7576\u591a\u7167\u7247\u3002\u54e6\uff0c\u4f60\u77e5\u9053\u55ce\uff1f\u9019\u4e9b\u7167\u7247\u662f\u7531\u626d\u66f2\u7522\u751f\u7684\u7269\u8cea\u69cb\u6210\uff0c\u537b\u4ecd\u7136\u7dad\u6301\u5b58\u5728\u3002\u6709\u4e9b\u626d\u66f2\u526f\u7522\u7269\u6703\u5728\u4e8b\u4ef6\u89e3\u6c7a\u5f8c\u6d88\u5931\uff0c\u4f46\u4e5f\u6709\u4e9b\u5373\u4f7f\u4e00\u5207\u7d50\u675f\u5f8c\u4ecd\u4e0d\u6703\u6d88\u5931\u3002\u6211\u5f88\u597d\u5947\u9019\u662f\u5426\u8207\u626d\u66f2\u672c\u8eab\u7684\u6027\u8cea\u6709\u95dc\u3002\u55ef\uff0c\u6211\u5011\u78ba\u5be6\u77e5\u9053\u9019\u500b\u626d\u66f2\u60f3\u8a18\u9304\u4e26\u8a18\u4f4f\u67d0\u4e9b\u4e8b\u7269\u2026\u2026\u6240\u4ee5\u624d\u7559\u4e0b\u4e86\u7167\u7247\u3002\u6216\u8a31\u4e5f\u6b63\u56e0\u5982\u6b64\uff0c\u9019\u4e9b\u7167\u7247\u624d\u4f5c\u70ba\u67d0\u7a2e\u300c\u8a18\u9304\u300d\u7559\u4e86\u4e0b\u4f86\u3002\u9019\u503c\u5f97\u7814\u7a76\uff1a\u7a76\u7adf\u662f\u4ec0\u9ebc\u9020\u6210\u4e0d\u540c\u626d\u66f2\u4e4b\u9593\u6027\u8cea\u7684\u5dee\u7570\u3002\u55ef\uff0c\u5728LCD\u5de5\u4f5c\u61c9\u8a72\u9072\u65e9\u6703\u8b93\u6211\u5f97\u5230\u4e00\u4e9b\u898b\u89e3\u2026\u2026\u96d6\u7136\u6211\u4e0d\u592a\u60f3\u914d\u5408LCE\u3002\u300d</color>",
    },
}

PERSONALITY_CONDITION_EXTRA_BY_ID = {
    "10615_getCondition_normal": {"content": "\u7372\u5f97 S\u516c\u53f8 \u63a8\u5974\u8005 \u9d3b\u7490"},
    "Uptie S Corp. Ch'unokkun Hong Lu to Tier 3": {"content": "\u7372\u5f97 S\u516c\u53f8 \u63a8\u5974\u8005 \u9d3b\u7490"},
    "10815_getCondition_normal": {"content": "\u7372\u5f97 LCD OSIR\u5c0f\u968a \u4ee5\u5be6\u746a\u5229"},
    "10815_getCondition_gacksung": {"content": "\u5c07 LCD OSIR\u5c0f\u968a \u4ee5\u5be6\u746a\u5229 \u540c\u6b65\u5316\u81f3\u968e\u7d1a 3"},
}

SCENARIO_MODEL_EXTRA = {
    "\ub4a4\ud2c0\ub9b0N\uc0ac\uc5d1\uc2a4\ud2b8\ub77c1": {"name": "\uff1f\uff1f\uff1f", "nickName": "14\u5340\u5c45\u6c11"},
    "\ube75\uac00\uac8c\uc8fc\uc778": {"name": "\u9eb5\u5305\u5e97\u8001\u95c6", "nickName": "14\u5340\u5c45\u6c11"},
    "\ub4a4\ud2c0\ub9b0\uac80\uacc41": {"name": "\u88ab\u61b6\u8d77\u7684\u4ea1\u8005", "nickName": "\u528d\u5951\u7d44\u6bba\u624b"},
    "\ub4a4\ud2c0\ub9b0\uac80\uacc42": {"name": "\u88ab\u61b6\u8d77\u7684\u4ea1\u8005", "nickName": "\u528d\u5951\u7d44\u6bba\u624b"},
    "\ucd94\ub178\uafbc1": {"name": "\u63a8\u5974\u8005\uff1f", "nickName": "\u626d\u66f2"},
    "\ucd94\ub178\uafbc2": {"name": "\u63a8\u5974\u8005\uff1f", "nickName": "\u626d\u66f2"},
    "N\uc0ac\ud574\uacb0\uc0ac1": {"name": "N\u516c\u53f82\u7d1a\u8077\u54e1", "nickName": "N\u516c\u53f8\u91d8\u52d9\u90e8"},
    "N\uc0ac\ud574\uacb0\uc0ac2": {"name": "N\u516c\u53f82\u7d1a\u8077\u54e1", "nickName": "N\u516c\u53f8\u91d8\u52d9\u90e8"},
    "\uc784\uacbd\uc5c5": {"name": "\u6797\u6176\u696d", "nickName": "S\u516c\u53f8\u5175\u66f9\u5224\u66f8 - Sal"},
    "\uc784\uacbd\uc5c5\uacfc\uac70": {"name": "\u6797\u6176\u696d", "nickName": "S\u516c\u53f8\u5175\u66f9\u5224\u66f8 - Sal"},
    "\uc784\uacbd\uc5c5\ub4a4\ud2c0\ub9bc": {"name": "\u626d\u66f2\u7684\u6797\u6176\u696d", "nickName": "\u626d\u66f2"},
    "\ub274\uc575\ub450": {"name": "\u6afb\u6843", "nickName": "LCD"},
    "\ub274\uae40\uc0bf\uac13": {"name": "\u91d1\u7b20", "nickName": "LCD"},
    "\uae40\uc0bf\uac13\uacfc\uac70": {"name": "\u91d1\u7b20", "nickName": "S\u516c\u53f8\u8b77\u885b - Pi"},
    "\ud55c\ud638\ubc30": {"name": "\u97d3\u6d69\u57f9", "nickName": "S\u516c\u53f8"},
    "\uc5d0\uc988\ub77c\uba3c\uc9c0": {"name": "\u4ee5\u65af\u62c9", "nickName": "LCD"},
    "\uc784\uacbd\uc5c5\ub4a4\ud2c0\ub9bc\uc0ac\ub77c\uc9d0": {"name": "\u626d\u66f2\u7684\u6797\u6176\u696d", "nickName": "\u626d\u66f2"},
    "\uae40\uc0bf\uac13\uacfc\uac70\ubd80\uc0c1": {"name": "\u91d1\u7b20", "nickName": "S\u516c\u53f8\u8b77\u885b - Pi"},
    "\uae40\uc0bf\uac13\uc8c4\uc218": {"name": "\u91d1\u7b20", "nickName": "\u53d7\u70d9\u5370\u8005"},
    "\ub4a4\ud2c0\ub9b0N\uc0ac\uc5d1\uc2a4\ud2b8\ub77c2": {"name": "\uff1f\uff1f\uff1f", "nickName": "14\u5340\u5c45\u6c11"},
    "\ub274\uae40\uc0bf\uac13\uc548\uad11": {"name": "\u91d1\u7b20", "nickName": "LCD"},
    "\ub274\ub8cc\uc288\ubc18\ub2f4\ub2e4\uce68": {"name": "\u826f\u79c0", "nickName": "4\u865f\u7f6a\u4eba"},
    "\ub274\ub8cc\uc288\ub2f4\ubc30\ub2e4\uce68": {"name": "\u826f\u79c0", "nickName": "4\u865f\u7f6a\u4eba"},
}

MODEL_TELLER_MAP = {
    "\ub274\uae40\uc0bf\uac13": "\u91d1\u7b20",
    "\uae40\uc0bf\uac13\uacfc\uac70": "\u91d1\u7b20",
    "\uae40\uc0bf\uac13\uacfc\uac70\ubd80\uc0c1": "\u91d1\u7b20",
    "\uae40\uc0bf\uac13\uc8c4\uc218": "\u91d1\u7b20",
    "\ub274\uae40\uc0bf\uac13\uc548\uad11": "\u91d1\u7b20",
    "\ub274\uc575\ub450": "\u6afb\u6843",
    "\uc784\uacbd\uc5c5": "\u6797\u6176\u696d",
    "\uc784\uacbd\uc5c5\uacfc\uac70": "\u6797\u6176\u696d",
    "\uc784\uacbd\uc5c5\ub4a4\ud2c0\ub9bc": "\u626d\u66f2\u7684\u6797\u6176\u696d",
    "\uc784\uacbd\uc5c5\ub4a4\ud2c0\ub9bc\uc0ac\ub77c\uc9d0": "\u626d\u66f2\u7684\u6797\u6176\u696d",
    "\uc5d0\uc988\ub77c\uba3c\uc9c0": "\u4ee5\u65af\u62c9",
    "N\uc0ac\ud574\uacb0\uc0ac1": "N\u516c\u53f82\u7d1a\u8077\u54e1",
    "N\uc0ac\ud574\uacb0\uc0ac2": "N\u516c\u53f82\u7d1a\u8077\u54e1",
    "\ub4a4\ud2c0\ub9b0N\uc0ac\uc5d1\uc2a4\ud2b8\ub77c1": "\uff1f\uff1f\uff1f",
    "\ube75\uac00\uac8c\uc8fc\uc778": "\u9eb5\u5305\u5e97\u8001\u95c6",
    "\ub274\ub8cc\uc288\ub2f4\ubc30\ub2e4\uce68": "\u826f\u79c0",
    "\ub274\ub8cc\uc288\ubc18\ub2f4\ub2e4\uce68": "\u826f\u79c0",
    "\ucd94\ub178\uafbc1": "\u63a8\u5974\u8005\uff1f",
    "\ud55c\ud638\ubc30": "\u97d3\u6d69\u57f9",
}

MNESTIC_NAME = "\u8a18\u61b6\u9ad4\u9a57"

MNESTIC_REPLACEMENTS = {
    "Ch. 9.5 Mnestic Experience Dungeon": f"9.5\u7ae0 {MNESTIC_NAME}\u5730\u7262",
    "New Identity & \u042d.\u0413.\u041e Target Extraction - Mnestic Experience": f"\u65b0\u4eba\u683c\uff06E.G.O \u5b9a\u5411\u62bd\u53d6 - {MNESTIC_NAME}",
    "New Identity & E.G.O Target Extraction - Mnestic Experience": f"\u65b0\u4eba\u683c\uff06E.G.O \u5b9a\u5411\u62bd\u53d6 - {MNESTIC_NAME}",
    "Mnestic Experience - Special Banner": f"{MNESTIC_NAME} - \u7279\u5225\u6a6b\u5e45",
    "Mnestic Experience - Special Ticket": f"{MNESTIC_NAME} - \u7279\u5225\u5238",
    "Mnestic Experience Event Page": f"{MNESTIC_NAME}\u6d3b\u52d5\u9801\u9762",
    "Mnestic Experience Stages": f"{MNESTIC_NAME}\u95dc\u5361",
    "Mnestic Experience combat Encounters": f"{MNESTIC_NAME}\u6230\u9b25\u906d\u9047",
    "Mnestic Experience Event": f"{MNESTIC_NAME}\u6d3b\u52d5",
    "Mnestic Experience event": f"{MNESTIC_NAME}\u6d3b\u52d5",
    "Mnestic Experience": MNESTIC_NAME,
    "Obtained from the \u8a18\u61b6\u9ad4\u9a57\u6d3b\u52d5": f"\u53ef\u5f9e\u300c{MNESTIC_NAME}\u300d\u6d3b\u52d5\u7372\u5f97",
    "Clear \u8a18\u61b6\u9ad4\u9a57": f"\u901a\u95dc\u300c{MNESTIC_NAME}\u300d",
    "\u042d.\u0413.\u041e": "E.G.O",
}

FINAL_TEXT_REPLACEMENTS = {
    "效果：You can obtain the following items from this": "\u53ef\u7372\u5f97\u4ee5\u4e0b\u7269\u54c1\uff1a",
    "release commemorative Pack.": "\u767c\u552e\u7d00\u5ff5\u79ae\u5305\u3002",
    "release commemorative pack.": "\u767c\u552e\u7d00\u5ff5\u79ae\u5305\u3002",
    "效果：· Decaextraction Ticket x4": "\u00b7 \u5341\u9023\u63d0\u53d6\u5238 x4",
    "效果：· Takeoff Module - ID Uptie x 1": "\u00b7 \u8df3\u8e8d\u6210\u9577\u6a21\u7d44 - \u4eba\u683c\u540c\u6b65\u5316 x1",
    "效果：· Identity Training Ticket IV x 80": "\u00b7 \u4eba\u683c\u8a13\u7df4\u5238 IV x80",
    "效果：· Identity Training Ticket III x 20": "\u00b7 \u4eba\u683c\u8a13\u7df4\u5238 III x20",
    "效果：· Takeoff Module - E.G.O Spinning [HE] x 1": "\u00b7 \u8df3\u8e8d\u6210\u9577\u6a21\u7d44 - E.G.O \u89e3\u6790 [HE] x1",
    "新人格\uff06E.G.O \u5b9a\u5411\u62bd\u53d6": "\u65b0\u4eba\u683c\uff06E.G.O \u5b9a\u5411\u63d0\u53d6",
    "\u65b0\u4eba\u683c\uff06E.G.O \u5b9a\u5411\u62bd\u53d6": "\u65b0\u4eba\u683c\uff06E.G.O \u5b9a\u5411\u63d0\u53d6",
    "Unaffected by [ChoiSwordsmanship]": "\u4e0d\u53d7 [ChoiSwordsmanship] \u5f71\u97ff",
    "[CantDuel] with Assist Units": "[CantDuel] \u7121\u6cd5\u8207\u5354\u6230\u55ae\u4f4d\u62fc\u9ede",
    "優先指定 Sinners": "\u512a\u5148\u6307\u5b9a\u7f6a\u4eba",
    "目標的 Skill is [SupportProtect] Exclusive Skill": "\u76ee\u6a19\u7684\u6280\u80fd\u70ba [SupportProtect] \u5c08\u7528\u6280\u80fd",
    "Skill is [SupportProtect] Exclusive Skill": "\u6280\u80fd\u70ba [SupportProtect] \u5c08\u7528\u6280\u80fd",
    "[SupportProtect] Exclusive Skill": "[SupportProtect] \u5c08\u7528\u6280\u80fd",
    "this effect does not activate": "\u6b64\u6548\u679c\u4e0d\u6703\u767c\u52d5",
    "This Skill does not trigger Defense Skills": "\u6b64\u6280\u80fd\u4e0d\u6703\u89f8\u767c\u9632\u79a6\u6280\u80fd",
    "Targets the enemy that has the most [Laceration]": "\u6307\u5b9a [Laceration] \u6700\u591a\u7684\u6575\u4eba",
    "Targets the Skill Slot that has the highest \u6700\u9ad8 Power": "\u6307\u5b9a\u6700\u7d42\u5a01\u529b\u6700\u9ad8\u7684\u6280\u80fd\u69fd\u4f4d",
    "On Hit as an Unopposed Attack, or On Hit against \u76ee\u6a19 that used [SupportProtect] \u5c08\u7528\u6280\u80fd": "\u4ee5\u55ae\u65b9\u653b\u64ca\u547d\u4e2d\u6642\uff0c\u6216\u547d\u4e2d\u4f7f\u7528 [SupportProtect] \u5c08\u7528\u6280\u80fd\u7684\u76ee\u6a19\u6642",
    "On Hit as an Unopposed Attack, or On Hit a\u7372\u5f97st \u76ee\u6a19 that used [SupportProtect] \u5c08\u7528\u6280\u80fd": "\u4ee5\u55ae\u65b9\u653b\u64ca\u547d\u4e2d\u6642\uff0c\u6216\u547d\u4e2d\u4f7f\u7528 [SupportProtect] \u5c08\u7528\u6280\u80fd\u7684\u76ee\u6a19\u6642",
    "Lose 3 [ChoiSwordsmanship]": "\u5931\u53bb 3 [ChoiSwordsmanship]",
    "lose 2 [ChoiSwordsmanship]": "\u5931\u53bb 2 [ChoiSwordsmanship]",
    "Assume a different \u6545\u571f\u6230\u578b every 3 turns": "\u6bcf 3 \u56de\u5408\u63a1\u53d6\u4e0d\u540c\u7684\u6545\u571f\u6230\u578b",
    "When 3 or more other \u528d\u5951 allies are defeated": "\u7576\u5176\u4ed6\u528d\u5951\u53cb\u65b9\u9663\u4ea1\u4eba\u6578\u4e0d\u4f4e\u65bc 3 \u540d\u6642",
    "Lose this Encounter if \u672c\u55ae\u4f4d is killed": "\u82e5\u672c\u55ae\u4f4d\u6b7b\u4ea1\uff0c\u5247\u672c\u6b21\u906d\u9047\u5931\u6557",
    "進入遭遇時 for the first time": "\u9996\u6b21\u9032\u5165\u906d\u9047\u6642",
    "At 1 [Breath] 次數, lose 10 體力 instead of losing [Breath] 次數": "[Breath] \u6b21\u6578\u70ba 1 \u6642\uff0c\u4e0d\u5931\u53bb [Breath] \u6b21\u6578\uff0c\u6539\u70ba\u5931\u53bb 10 \u9ad4\u529b",
    "this effect cannot \u6df7\u4e82 \u672c\u55ae\u4f4d and does not drop \u672c\u55ae\u4f4d's \u9ad4\u529b below 1": "\u6b64\u6548\u679c\u4e0d\u6703\u4f7f\u672c\u55ae\u4f4d\u9677\u5165\u6df7\u4e82\uff0c\u4e14\u4e0d\u6703\u4f7f\u672c\u55ae\u4f4d\u9ad4\u529b\u4f4e\u65bc 1",
    "Raise \u6df7\u4e82\u95be\u503c by 10": "\u4f7f\u6df7\u4e82\u95be\u503c\u63d0\u9ad8 10",
    "Raise \u6df7\u4e82\u95be\u503c by 20% of \u50b7\u5bb3 \u9020\u6210t": "\u4f7f\u6df7\u4e82\u95be\u503c\u63d0\u9ad8\u76f8\u7576\u65bc\u9020\u6210\u50b7\u5bb3 20% \u7684\u503c",
    "Reuse this \u786c\u5e63 (once per Skill)": "\u91cd\u8907\u4f7f\u7528\u6b64\u786c\u5e63\uff08\u6bcf\u500b\u6280\u80fd 1 \u6b21\uff09",
    "for the \u6700\u5f8c\u4e00\u679a\u786c\u5e63 (once per \u786c\u5e63)": "\u7d66\u6700\u5f8c\u4e00\u679a\u786c\u5e63\uff08\u6bcf\u679a\u786c\u5e63 1 \u6b21\uff09",
    "本回合 and 下回合": "\u672c\u56de\u5408\u8207\u4e0b\u56de\u5408",
    "下回合 and": "\u4e0b\u56de\u5408\u4e26",
    " and 下回合": "\u4e26\u65bc\u4e0b\u56de\u5408",
    " on \u66b4\u64ca": "\uff08\u66b4\u64ca\u6642\uff09",
    "a\u7372\u5f97st and from \u91d1\u7b20": "\u5c0d\u91d1\u7b20\u9020\u6210\u8207\u53d7\u5230",
    "\u9020\u6210 and \u53d7\u5230 +20% \u50b7\u5bb3\uff08\u66b4\u64ca\u6642\uff09 \u5c0d\u91d1\u7b20\u9020\u6210\u8207\u53d7\u5230": "\u5c0d\u91d1\u7b20\u66b4\u64ca\u6642\u9020\u6210\u8207\u53d7\u5230\u7684\u50b7\u5bb3 +20%",
    "Yield My Flesh": "\u737b\u51fa\u543e\u8eab",
    "To Claim Their Bones": "\u4ee5\u596a\u5176\u9aa8",
    "To Where I Must Return": "\u6b78\u8fd4\u4e4b\u8655",
    "Slash Series": "\u65ac\u64ca\u9023\u6bb5",
    "效果：S Corp. commands two sorts of Taboo Hunters: The Royal Censors and the Ch'unokkuns.\nAgents of the Royal Court, the Royal Censors generally operate alone, moving undercover to pursue those who have dared to break the Taboo of Salpippyeo.\nCh'unokkuns, much like Fixer Offices, form bands within their own ranks. Once an order or a contract to hunt down a Branded is bestowed upon them, each band hunts its mark in the manner preferred by the band. The hunt for Nobi knows neither honor nor dignity.": "\u6548\u679c\uff1aS\u516c\u53f8\u6307\u63ee\u8457\u5169\u7a2e\u7981\u5fcc\u7375\u4eba\uff1a\u5fa1\u53f2\u8207\u63a8\u5974\u8005\u3002\n\u5fa1\u53f2\u4f5c\u70ba\u738b\u5ead\u7684\u4f7f\u8005\uff0c\u901a\u5e38\u55ae\u7368\u884c\u52d5\uff0c\u96b1\u533f\u8eab\u5206\u8ffd\u6355\u6562\u65bc\u6253\u7834\u300c\u6bba\u76ae\u9aa8\u300d\u7981\u5fcc\u7684\u4eba\u3002\n\u63a8\u5974\u8005\u5247\u5982\u540c\u6536\u5c3e\u4eba\u4e8b\u52d9\u6240\u4e00\u822c\uff0c\u5728\u81ea\u5df1\u7684\u884c\u5217\u4e2d\u7d44\u6210\u7375\u5718\u3002\u4e00\u65e6\u7372\u5f97\u8ffd\u7375\u70d9\u5370\u8005\u7684\u547d\u4ee4\u6216\u5951\u7d04\uff0c\u5404\u7375\u5718\u4fbf\u6703\u4ee5\u81ea\u5df1\u504f\u597d\u7684\u65b9\u5f0f\u7375\u6bba\u76ee\u6a19\u3002\u5c0d\u5974\u5a62\u7684\u7375\u6355\u4e0d\u8b1b\u69ae\u8b7d\uff0c\u4e5f\u4e0d\u8b1b\u5c0a\u56b4\u3002",
    "To cover the eyes is not to be blind.\nThese fabrics, created using Q Corp.'s Singularity, are fashioned into many forms, such as blindfolds and headbands, and are commonly used throughout the East. It is not unusual to see Fixers and employees of corporate entities in the East covering their heads and faces with these products.\nThe fabrics serve the same function as sunglasses, visors, and combat prosthetic eyes found elsewhere in the City. They scan the \u76ee\u6a19's information in real time, augment the wearer's vision, and provide tactical analysis. At times, they can also serve as a means of communication with distant allies.": "\u906e\u4f4f\u96d9\u773c\uff0c\u4e26\u4e0d\u7b49\u65bc\u5931\u660e\u3002\n\u9019\u4e9b\u4ee5Q\u516c\u53f8\u5947\u9ede\u88fd\u6210\u7684\u7e54\u7269\u6709\u773c\u7f69\u3001\u982d\u5dfe\u7b49\u591a\u7a2e\u5f62\u5f0f\uff0c\u5728\u6771\u65b9\u88ab\u5ee3\u6cdb\u4f7f\u7528\u3002\u5728\u6771\u65b9\uff0c\u770b\u898b\u6536\u5c3e\u4eba\u6216\u4f01\u696d\u54e1\u5de5\u7528\u9019\u4e9b\u7522\u54c1\u906e\u4f4f\u982d\u8207臉\uff0c\u4e26\u4e0d\u7a00\u5947\u3002\n\u9019\u4e9b\u7e54\u7269\u7684\u529f\u80fd\u985e\u4f3c\u65bc\u57ce\u5e02\u5176\u4ed6\u5730\u65b9\u7684\u592a\u967d\u773c\u93e1\u3001\u9762\u7f69\u8207\u6230\u9b25\u7528\u7fa9\u773c\u3002\u5b83\u5011\u6703\u5373\u6642\u6383\u63cf\u76ee\u6a19\u8cc7\u8a0a\uff0c\u589e\u5f37\u4f69\u6234\u8005\u7684\u8996\u89ba\uff0c\u4e26\u63d0\u4f9b\u6230\u8853\u5206\u6790\u3002\u6709\u6642\u4e5f\u80fd\u4f5c\u70ba\u8207\u9060\u65b9\u53cb\u8ecd\u806f\u7d61\u7684\u624b\u6bb5\u3002",
    "效果：The Sword of the Homeland, S Corp.'s traditional art of swordsmanship, is also divided into three branches: Sal, Pi, and Ppyeo.\nWithin their teachings exist techniques to hew and cleave through creatures of colossal stature such as Sanguns.\nTo perform them in full, a swordsman must wield a great hwando capable of bearing the strain of the techniques.": "\u6548\u679c\uff1aS\u516c\u53f8\u50b3\u7d71劍\u8853\u300c\u6545\u571f劍術\u300d\u4e5f\u5206\u70ba\u6bba\u3001\u76ae\u3001\u9aa8\u4e09\u500b\u5206\u652f\u3002\n\u5176\u6559\u7fa9\u4e2d\u5305\u542b\u80fd\u5288\u958b\u50cf\u5c71\u541b\u90a3\u822c\u5de8\u5927\u751f\u7269\u7684\u6280\u6cd5\u3002\n\u82e5\u8981\u5b8c\u6574\u65bd\u5c55\uff0c劍\u58eb\u5fc5\u9808\u63ee\u821e\u80fd\u627f\u53d7\u5176\u8ca0\u8377\u7684\u5927\u74b0\u5200\u3002",
    "效果：'There are those who persevere in training for lack of talent. Then there are those blessed with talent, only to let it rust.'\n'All men say that the title of Apex Blade can be seized only by the gifted.'\n'It matters not. Until the day comes for this blade of mine to rise high enough to meet the clouds, I shall persevere in honing my prowess.'": "\u6548\u679c\uff1a\u300c\u6709\u4eba\u56e0\u7121\u624d\u800c\u6301\u7e8c\u4fee\u7df4\u3002\u4e5f\u6709\u4eba\u660e\u660e\u5929\u8ce6\u904e\u4eba\uff0c\u537b\u4efb\u7531\u5b83\u751f\u93fd\u3002\u300d\n\u300c\u4e16\u4eba\u90fd\u8aaa\uff0c\u53ea\u6709\u5929\u624d\u624d\u80fd奪\u5f97\u528d\u5c16\u4e4b\u540d\u3002\u300d\n\u300c\u7121\u59a8\u3002\u76f4\u5230\u6211\u7684\u528d\u80fd\u8209\u81f3\u89f8\u53ca\u96f2\u7aef\u7684\u90a3\u65e5\u70ba\u6b62\uff0c\u6211\u90fd\u6703\u6301\u7e8c\u935b\u934a\u6b66\u85dd\u3002\u300d",
    "效果：One may get lost and wander onto the wrong path, but willful defiance or deviation from the flow are forbidden by \"it.\"": "\u6548\u679c\uff1a\u4eba\u6216\u8a31\u6703\u8ff7\u5931\uff0c\u8aa4\u5165\u932f\u8def\uff1b\u4f46\u84c4\u610f\u6297\u62d2\uff0c\u6216\u504f\u96e2\u6d41\u52e2\uff0c\u90fd\u662f\u300c\u5b83\u300d\u6240\u7981\u6b62\u7684\u3002",
}

FINAL_TEXT_REPLACEMENTS.update({
    "?\u8272\u0080?": "\u2026\u2026",
    "convert \u6240\u6709\u786c\u5e63 into [SuperCoin]s and \u9020\u6210 +20% \u50b7\u5bb3": "\u5c07\u6240\u6709\u786c\u5e63\u8f49\u63db\u70ba [SuperCoin]\uff0c\u4e14\u9020\u6210\u50b7\u5bb3 +20%",
    "convert \u6240\u6709\u786c\u5e63 into [SuperCoin]s": "\u5c07\u6240\u6709\u786c\u5e63\u8f49\u63db\u70ba [SuperCoin]",
    "If there is an ally at less than 50% \u9ad4\u529b on the field excluding \u672c\u55ae\u4f4d, \u7372\u5f97 1 [SupportProtect] (\u6bcf\u56de\u5408 1 \u6b21)": "\u82e5\u5834\u4e0a\u5b58\u5728\u9ad4\u529b\u4f4e\u65bc 50% \u7684\u5176\u4ed6\u53cb\u65b9\uff0c\u7372\u5f97 1 [SupportProtect]\uff08\u6bcf\u56de\u5408 1 \u6b21\uff09",
    "Limbus Company Specialized Custom Prosthetic Prototype mk5 - \u9b3c\u602a\u81c2": "Limbus Company \u7279\u88fd\u5ba2\u88fd\u7fa9\u80a2\u539f\u578b mk5 - \u9b3c\u602a\u81c2",
    "Activate additional \u6280\u80fd when conditions are met": "\u7b26\u5408\u689d\u4ef6\u6642\u767c\u52d5\u8ffd\u52a0\u6280\u80fd",
    "Special Handmade Golden Retriever-Exclusive Axe.": "\u7279\u88fd\u624b\u5de5\u91d1\u6bdb\u5c08\u7528\u65a7\u3002",
    "Can Clash with this Skill regardless of \u901f\u5ea6": "\u7121\u8996\u901f\u5ea6\u4e5f\u80fd\u8207\u6b64\u6280\u80fd\u62fc\u9ede",
    "This Skill always flips Head, hits \u66b4\u64caly, and does not \u6d88\u8017 [Breath] \u6b21\u6578": "\u6b64\u6280\u80fd\u4e00\u5b9a\u63b7\u51fa\u6b63\u9762\uff0c\u4e00\u5b9a\u66b4\u64ca\uff0c\u4e14\u4e0d\u6d88\u8017 [Breath] \u6b21\u6578",
    "Does not hit \u66b4\u64caly": "\u4e0d\u6703\u66b4\u64ca",
    "Cannot be \u6df7\u4e82ed from taking \u50b7\u5bb3 until this Skill ends": "\u76f4\u5230\u6b64\u6280\u80fd\u7d50\u675f\u70ba\u6b62\uff0c\u53d7\u5230\u50b7\u5bb3\u6642\u4e0d\u6703\u9677\u5165\u6df7\u4e82",
    "Cannot be \u6df7\u4e82ed from taking \u50b7\u5bb3": "\u53d7\u5230\u50b7\u5bb3\u6642\u4e0d\u6703\u9677\u5165\u6df7\u4e82",
    "\u6df7\u4e82ed": "\u9677\u5165\u6df7\u4e82",
    "\u50b7\u5bb3 \u9020\u6210t": "\u9020\u6210\u7684\u50b7\u5bb3",
    "\u9020\u6210t": "\u9020\u6210",
    "\u53d7\u5230s": "\u53d7\u5230",
    "\u7372\u5f97ing": "\u7372\u5f97",
    "a\u7372\u5f97st": "\u5c0d",
    "more than": "\u8d85\u904e",
    "or fewer": "\u6216\u66f4\u5c11",
    "less than": "\u4f4e\u65bc",
    "At 0": "\u7576 0",
    "At 1": "\u7576 1",
    "At 10+": "\u9054 10+",
    "At 15+": "\u9054 15+",
    "At 20+": "\u9054 20+",
    "At 25+": "\u9054 25+",
    "At 30+": "\u9054 30+",
    "At 55%": "\u9ad4\u529b 55%",
    "if \u672c\u55ae\u4f4d has": "\u82e5\u672c\u55ae\u4f4d\u64c1\u6709",
    "If \u672c\u55ae\u4f4d is defeated": "\u82e5\u672c\u55ae\u4f4d\u88ab\u64ca\u6557",
    "\u82e5\u672c\u55ae\u4f4d is defeated": "\u82e5\u672c\u55ae\u4f4d\u88ab\u64ca\u6557",
    "\u82e5\u672c\u55ae\u4f4d is \u9677\u5165\u6050\u614c": "\u82e5\u672c\u55ae\u4f4d\u9677\u5165\u6050\u614c",
    "\u82e5\u76ee\u6a19 has": "\u82e5\u76ee\u6a19\u64c1\u6709",
    "When the following conditions are met": "\u7576\u6eff\u8db3\u4ee5\u4e0b\u689d\u4ef6\u6642",
    "When in Low Morale or \u6050\u614c": "\u8655\u65bc\u58eb\u6c23\u4f4e\u843d\u6216\u6050\u614c\u6642",
    "When in [ChoiSwordsmanshipOne]": "\u8655\u65bc [ChoiSwordsmanshipOne] \u6642",
    "When in [ChoiSwordsmanshipMany]": "\u8655\u65bc [ChoiSwordsmanshipMany] \u6642",
    "When \u8fd4\u56de\u6230\u5834\u6642": "\u8fd4\u56de\u6230\u5834\u6642",
    "does not check for Unopposed Attacks": "\u4e0d\u6aa2\u67e5\u55ae\u65b9\u653b\u64ca",
    "Unopposed Attacks": "\u55ae\u65b9\u653b\u64ca",
    "Unopposed Attack": "\u55ae\u65b9\u653b\u64ca",
    "Use \"\u4ee5\u596a\u5176\u9aa8\" after being hit": "\u88ab\u547d\u4e2d\u5f8c\u4f7f\u7528\u300c\u4ee5\u596a\u5176\u9aa8\u300d",
    "use a powerful \u6280\u80fd": "\u4f7f\u7528\u5f37\u529b\u6280\u80fd",
    "equip \"\u737b\u51fa\u543e\u8eab\"": "\u88dd\u5099\u300c\u737b\u51fa\u543e\u8eab\u300d",
    "equip \"\u65ac\u64ca\u9023\u6bb5\"": "\u88dd\u5099\u300c\u65ac\u64ca\u9023\u6bb5\u300d",
    "Heal 4 SP for all allies": "\u70ba\u5168\u9ad4\u53cb\u65b9\u6062\u5fa9 4 \u9ede SP",
    "Heal 8 SP instead for LCD Units": "LCD \u55ae\u4f4d\u6539\u70ba\u6062\u5fa9 8 \u9ede SP",
    "Take -2% \u50b7\u5bb3 from Attacks": "\u53d7\u5230\u7684\u653b\u64ca\u50b7\u5bb3 -2%",
    "every \u56de\u5408": "\u6bcf\u56de\u5408",
    "each \u56de\u5408": "\u6bcf\u56de\u5408",
    "for the turn": "\u672c\u56de\u5408",
    "once per Encounter": "\u6bcf\u6b21\u906d\u9047 1 \u6b21",
    "times \u6bcf\u56de\u5408": "\u6bcf\u56de\u5408",
    "rounded down": "\u5411\u4e0b\u53d6\u6574",
    "from [Combustion], [Laceration], [Vibration], [Burst], [Sinking]": "\u4f86\u81ea [Combustion]\u3001[Laceration]\u3001[Vibration]\u3001[Burst]\u3001[Sinking]",
    "reset \u7406\u667a\u503c to 45": "\u5c07\u7406\u667a\u503c\u91cd\u8a2d\u70ba 45",
    "end Encounter": "\u7d50\u675f\u906d\u9047",
    "Move the battle to a \u4e0d\u540c\u5730\u9ede": "\u5c07\u6230\u9b25\u79fb\u81f3\u4e0d\u540c\u5730\u9ede",
    "transition into a \u4e0d\u540c\u5730\u9ede": "\u8f49\u79fb\u81f3\u4e0d\u540c\u5730\u9ede",
    "current Workshop weapon": "\u76ee\u524d\u7684\u5de5\u574a\u6b66\u5668",
    "List of weapons": "\u6b66\u5668\u5217\u8868",
    "Allas Workshop Gloves": "Allas \u5de5\u574a\u624b\u5957",
    "Nester Workshop Hammer": "Nester \u5de5\u574a\u69cc",
    "Screw Atelier Drill Hammer": "Screw \u5de5\u574a\u947d\u982d\u69cc",
    "Namir Workshop Gauntlets": "Namir \u5de5\u574a\u81c2\u7532",
    "YuRia Atelier Axe": "\u88d5\u91cc\u4e9e\u5de5\u574a\u65a7",
    "\u63b7": "\u64f2",
    "\u7372\u5f97 1 [WindBlade] for every 3 [Breath] (max 5, 2 \u6bcf\u56de\u5408)": "\u6bcf\u6709 3 [Breath]\uff0c\u7372\u5f97 1 [WindBlade]\uff08\u6700\u591a 5\uff0c\u6bcf\u56de\u5408 2 \u6b21\uff09",
    "On Base Attack \u6280\u80fd\u7d50\u675f\u6642: \u7576 15+ [WindBlade], activate \"Even the Balance - Lucent Rippling Flame\" on the \u6575\u4eba (\u6bcf\u56de\u5408 1 \u6b21)": "\u57fa\u672c\u653b\u64ca\u6280\u80fd\u7d50\u675f\u6642\uff1a\u82e5\u64c1\u6709 15+ [WindBlade]\uff0c\u5c0d\u6575\u4eba\u767c\u52d5\u300c\u5747\u52e2 - \u6f84\u660e\u6f23\u6f2a\u4e4b\u7130\u300d\uff08\u6bcf\u56de\u5408 1 \u6b21\uff09",
    "On \u9632\u79a6\u6280\u80fd Clash Lose, \u82e5\u672c\u55ae\u4f4d\u64c1\u6709 3+ [Agility], \u672c\u55ae\u4f4d cannot be \u9677\u5165\u6df7\u4e82 from taking \u50b7\u5bb3 until Defense \u6280\u80fd\u7d50\u675f\u6642, and activate \"\u4ee5\u596a\u5176\u9aa8\" \u5c0d the \u6575\u4eba after being hit (2 \u6bcf\u56de\u5408, excluding forced \u6df7\u4e82s)": "\u9632\u79a6\u6280\u80fd\u62fc\u9ede\u5931\u6557\u6642\uff1a\u82e5\u672c\u55ae\u4f4d\u64c1\u6709 3+ [Agility]\uff0c\u76f4\u5230\u9632\u79a6\u6280\u80fd\u7d50\u675f\u70ba\u6b62\uff0c\u672c\u55ae\u4f4d\u53d7\u5230\u50b7\u5bb3\u6642\u4e0d\u6703\u9677\u5165\u6df7\u4e82\uff1b\u88ab\u547d\u4e2d\u5f8c\u5c0d\u6575\u4eba\u767c\u52d5\u300c\u4ee5\u596a\u5176\u9aa8\u300d\uff08\u6bcf\u56de\u5408 2 \u6b21\uff0c\u4e0d\u542b\u5f37\u5236\u6df7\u4e82\uff09",
    "When \u7372\u5f97 [Breath] \u5f37\u5ea6/\u6b21\u6578 using \u672c\u55ae\u4f4d's own \u6280\u80fds and Coin effects": "\u900f\u904e\u672c\u55ae\u4f4d\u81ea\u8eab\u6280\u80fd\u8207\u786c\u5e63\u6548\u679c\u7372\u5f97 [Breath] \u5f37\u5ea6\uff0f\u6b21\u6578\u6642",
    "using \u672c\u55ae\u4f4d's own \u6280\u80fds and Coin effects": "\u900f\u904e\u672c\u55ae\u4f4d\u81ea\u8eab\u6280\u80fd\u8207\u786c\u5e63\u6548\u679c",
    "\u7372\u5f97 1 more of each": "\u5404\u984d\u5916\u7372\u5f97 1",
    "When 5 or more other \u528d\u5951 allies are defeated, \u7372\u5f97 2 more of each instead": "\u7576\u5176\u4ed6\u528d\u5951\u53cb\u65b9\u9663\u4ea1\u4eba\u6578\u4e0d\u4f4e\u65bc 5 \u540d\u6642\uff0c\u6539\u70ba\u5404\u984d\u5916\u7372\u5f97 2",
    "If Pride Reson. was activated": "\u82e5\u767c\u52d5\u50b2\u6162\u5171\u9cf4",
    "and 1 [CriticalDamageUp] on \u5168\u9ad4\u7f6a\u4eba and \u652f\u63f4\u55ae\u4f4d excluding \u672c\u55ae\u4f4d (for \u528d\u5951 \u76ee\u6a19s, double this effect)": "\u8207 1 [CriticalDamageUp] \u65bc\u9664\u672c\u55ae\u4f4d\u5916\u7684\u5168\u9ad4\u7f6a\u4eba\u8207\u652f\u63f4\u55ae\u4f4d\uff08\u5c0d\u528d\u5951\u76ee\u6a19\u6642\uff0c\u6b64\u6548\u679c\u52a0\u500d\uff09",
    "([Breath] on self / 4) [Agility]": "\uff08\u81ea\u8eab [Breath] / 4\uff09[Agility]",
    "施加 1 [Breath] on an ally that does not have [Breath] or has the lowest [Breath] 強度 (5 每回合)": "\u5c0d\u6c92\u6709 [Breath]\uff0c\u6216 [Breath] \u5f37\u5ea6\u6700\u4f4e\u7684 1 \u540d\u53cb\u65b9\u65bd\u52a0 1 [Breath]\uff08\u6bcf\u56de\u5408 5 \u6b21\uff09",
    "If \u91d1\u7b20 is on the field": "\u82e5\u91d1\u7b20\u5728\u5834\u4e0a",
    "\u65bd\u52a0 5 [Breath] and +2 [Breath] \u6b21\u6578 on \u5168\u9ad4\u528d\u5951\u53cb\u65b9 at the next \u56de\u5408\u958b\u59cb\u6642": "\u4e0b\u56de\u5408\u958b\u59cb\u6642\uff0c\u5c0d\u5168\u9ad4\u528d\u5951\u53cb\u65b9\u65bd\u52a0 5 [Breath]\u8207 +2 [Breath] \u6b21\u6578",
    "on the leftmost \u6280\u80fd Slot": "\u81f3\u6700\u5de6\u5074\u6280\u80fd\u69fd\u4f4d",
    "on the leftmost Slot": "\u81f3\u6700\u5de6\u5074\u69fd\u4f4d",
    "Great Hwando": "\u5927\u74b0\u5200",
    "Iron Bulwark": "\u9435\u58c1",
    "Great Mountain": "\u5927\u5c71",
    "Rend Flesh from Flesh": "\u5272\u8089\u88c2\u8eab",
    "Shift Battleform": "\u5207\u63db\u6230\u578b",
    "Bow of the Homeland - Arrowloose": "\u6545\u571f\u4e4b\u5f13 - \u653e\u77e2",
    "\u7372\u5f97 the effects of [PanicChangeLock]": "\u7372\u5f97 [PanicChangeLock] \u7684\u6548\u679c",
    "\u56de\u5408\u958b\u59cb\u6642: \u7372\u5f97 the following effects": "\u56de\u5408\u958b\u59cb\u6642\uff1a\u7372\u5f97\u4ee5\u4e0b\u6548\u679c",
    "When [ChoiSwordsmanshipShield] expires": "[ChoiSwordsmanshipShield] \u5931\u6548\u6642",
    "\u7576 0 [PhotoTransitionChoi] \u5c64\u6578, \u64a4\u9000 and \u8f49\u79fb\u81f3\u4e0d\u540c\u5730\u9ede": "[PhotoTransitionChoi] \u5c64\u6578\u70ba 0 \u6642\uff0c\u64a4\u9000\u4e26\u8f49\u79fb\u81f3\u4e0d\u540c\u5730\u9ede",
    "based on current \u6545\u571f\u6230\u578b": "\u6839\u64da\u76ee\u524d\u7684\u6545\u571f\u6230\u578b",
    "\u7372\u5f97 or lose [ChoiSwordsmanship]": "\u7372\u5f97\u6216\u5931\u53bb [ChoiSwordsmanship]",
    "Lose \u5c64\u6578": "\u5931\u53bb\u5c64\u6578",
    "equal to surplus [ChoiSwordsmanship] \u5c64\u6578 past 5": "\u6578\u503c\u7b49\u540c\u65bc\u8d85\u904e 5 \u5c64\u7684 [ChoiSwordsmanship] \u5c64\u6578",
    "At \u4f4e\u65bc 5": "\u4f4e\u65bc 5",
    "At \u8d85\u904e 5": "\u8d85\u904e 5",
    "\u547d\u4e2d\u6642 using a \u65ac\u64ca\u6280\u80fd": "\u4f7f\u7528\u65ac\u64ca\u6280\u80fd\u547d\u4e2d\u6642",
    "Turn after \u6df7\u4e82": "\u6df7\u4e82\u5f8c\u7684\u56de\u5408",
    "At Min or Max [ChoiSwordsmanship] \u5c64\u6578s": "[ChoiSwordsmanship] \u5c64\u6578\u70ba\u6700\u5c0f\u6216\u6700\u5927\u503c\u6642",
    "regardless of [ChoiSwordsmanship] \u5c64\u6578 on self": "\u7121\u8996\u81ea\u8eab [ChoiSwordsmanship] \u5c64\u6578",
    "\u9ad4\u529b 55% or lower \u9ad4\u529b": "\u9ad4\u529b 55% \u4ee5\u4e0b",
    "does not activate in the first turn of the Encounter": "\u906d\u9047\u7b2c 1 \u56de\u5408\u4e0d\u767c\u52d5",
    "In the turn where \u672c\u55ae\u4f4d equipped Envy \u6280\u80fds": "\u672c\u55ae\u4f4d\u88dd\u5099\u5ac9\u5992\u6280\u80fd\u7684\u56de\u5408",
    "\u672c\u55ae\u4f4d will not be affected by [ChoiSwordsmanship] \u5c64\u6578 adjustment effects": "\u672c\u55ae\u4f4d\u4e0d\u53d7 [ChoiSwordsmanship] \u5c64\u6578\u8abf\u6574\u6548\u679c\u5f71\u97ff",
    "reset [ChoiSwordsmanship] \u5c64\u6578 to 5": "\u5c07 [ChoiSwordsmanship] \u5c64\u6578\u91cd\u8a2d\u70ba 5",
    "This unit cannot be killed, and does not \u53d7\u5230 any \u50b7\u5bb3 from sources other than \u6280\u80fd \u50b7\u5bb3 from \u6280\u80fds attacking \u672c\u55ae\u4f4d as the main \u76ee\u6a19": "\u672c\u55ae\u4f4d\u4e0d\u6703\u6b7b\u4ea1\uff0c\u4e14\u9664\u4e86\u4ee5\u672c\u55ae\u4f4d\u70ba\u4e3b\u76ee\u6a19\u7684\u6280\u80fd\u50b7\u5bb3\u5916\uff0c\u4e0d\u6703\u53d7\u5230\u4efb\u4f55\u50b7\u5bb3",
    "This unit's \u901f\u5ea6 is fixed to 1": "\u672c\u55ae\u4f4d\u7684\u901f\u5ea6\u56fa\u5b9a\u70ba 1",
    "after entering the Encounter": "\u9032\u5165\u906d\u9047\u5f8c",
    "activate the following at the next \u56de\u5408\u958b\u59cb\u6642": "\u4e0b\u56de\u5408\u958b\u59cb\u6642\u767c\u52d5\u4ee5\u4e0b\u6548\u679c",
    "Remove self and N Corp. Class 2 Staff from the Encounter": "\u5c07\u81ea\u8eab\u8207 N\u516c\u53f82\u7d1a\u8077\u54e1\u79fb\u51fa\u906d\u9047",
    "Return Im Gyeong-eop to the Encounter": "\u8b93\u6797\u6176\u696d\u56de\u5230\u906d\u9047",
    "If the battlefield has returned from S Corp. to N Corp. this turn": "\u82e5\u6230\u5834\u5728\u672c\u56de\u5408\u5f9e S\u516c\u53f8\u8fd4\u56de N\u516c\u53f8",
    "\u6062\u5fa9 15 \u7406\u667a\u503c for \u5168\u9ad4\u7f6a\u4eba": "\u5168\u9ad4\u7f6a\u4eba\u6062\u5fa9 15 \u7406\u667a\u503c",
    "Until this Skill ends": "\u76f4\u5230\u6b64\u6280\u80fd\u7d50\u675f\u70ba\u6b62",
    "Cannot use \"\u737b\u51fa\u543e\u8eab\" until \u4e0b\u56de\u5408": "\u76f4\u5230\u4e0b\u56de\u5408\u70ba\u6b62\u7121\u6cd5\u4f7f\u7528\u300c\u737b\u51fa\u543e\u8eab\u300d",
    "excess Atk Weight beyond the # of actual \u76ee\u6a19s (in Focused Encounters, the Parts)": "\u8d85\u904e\u5be6\u969b\u76ee\u6a19\u6578\u7684\u591a\u9918\u653b\u64ca\u52a0\u6b0a\uff08\u96c6\u4e2d\u906d\u9047\u4e2d\u5247\u70ba\u90e8\u4f4d\u6578\uff09",
    "type of negative effect": "\u7a2e\u8ca0\u9762\u6548\u679c",
    "Activate [Laceration] \u65bc\u76ee\u6a19 once. Target loses 1 [Laceration] \u6b21\u6578": "\u5c0d\u76ee\u6a19\u767c\u52d5 1 \u6b21 [Laceration]\u3002\u76ee\u6a19\u5931\u53bb 1 \u5c64 [Laceration] \u6b21\u6578",
    "([Binding] x 20)% chance to \u8ce6\u4e88 [TiedRope]": "\u6709\uff08[Binding] x 20\uff09% \u6a5f\u7387\u8ce6\u4e88 [TiedRope]",
    "\u82e5\u76ee\u6a19 is \u9677\u5165\u6df7\u4e82, this effect is \u8ce6\u4e88ed without fail": "\u82e5\u76ee\u6a19\u9677\u5165\u6df7\u4e82\uff0c\u6b64\u6548\u679c\u5fc5\u5b9a\u8ce6\u4e88",
    "\u9020\u6210\u7684\u50b7\u5bb3 by this Skill": "\u6b64\u6280\u80fd\u9020\u6210\u7684\u50b7\u5bb3",
    "[Breath] Potency \u65bc\u81ea\u8eab to \u7372\u5f97": "\u81ea\u8eab [Breath] \u5f37\u5ea6\u4ee5\u7372\u5f97",
})

KNOWN_TEXT_TRANSLATIONS = {
    "N Corp.": "N\u516c\u53f8",
    "S Corp.": "S\u516c\u53f8",
    "N Corp. Service des Clous": "N\u516c\u53f8\u91d8\u52d9\u90e8",
    "District 14": "14\u5340",
    "District 14 Resident": "14\u5340\u5c45\u6c11",
    "???": "\uff1f\uff1f\uff1f",
    "Stages": "\u95dc\u5361",
    "To Theater": "\u524d\u5f80\u5287\u5834",
    "Clear 9.5-14 to Unlock": "\u901a\u95dc 9.5-14 \u5f8c\u89e3\u9396",
    "Event Closed": "\u6d3b\u52d5\u5df2\u7d50\u675f",
    "Event Currency Guide": "\u6d3b\u52d5\u8ca8\u5e63\u6307\u5357",
    "Items Owned": "\u6301\u6709\u9053\u5177\u6578",
    "Photos": "\u7167\u7247",
    "Photo Bundles": "\u7167\u7247\u5305",
    "S Corp. Ch'unokkun Hong Lu": "S\u516c\u53f8 \u63a8\u5974\u8005 \u9d3b\u7490",
    "Ch'unokkun Hong Lu": "\u63a8\u5974\u8005 \u9d3b\u7490",
    "Acquire S Corp. Ch'unokkun Hong Lu": "\u7372\u5f97 S\u516c\u53f8 \u63a8\u5974\u8005 \u9d3b\u7490",
    "Acquire LCD OSIR Team Ishmael": "\u7372\u5f97 LCD OSIR\u5c0f\u968a \u4ee5\u5be6\u746a\u5229",
    "Uptie LCE OSIR Team Ishmael to Tier 3": "\u5c07 LCD OSIR\u5c0f\u968a \u4ee5\u5be6\u746a\u5229 \u540c\u6b65\u5316\u81f3\u968e\u7d1a 3",
    "Aeng-du": "\u6afb\u6843",
    "Bamboo-hatted Kim": "\u91d1\u7b20",
    "Bakery Owner": "\u9eb5\u5305\u5e97\u8001\u95c6",
    "The Reminisced Dead": "\u88ab\u61b6\u8d77\u7684\u4ea1\u8005",
    "Blade Lineage Salsu": "\u528d\u5951\u7d44\u6bba\u624b",
    "Ch'unokkun?": "\u63a8\u5974\u8005\uff1f",
    "Class 2 Pinframing Staff": "N\u516c\u53f82\u7d1a\u8077\u54e1",
    "Service des Clous": "\u91d8\u52d9\u90e8",
    "Im Gyeong-eop": "\u6797\u6176\u696d",
    "Distorted Im Gyeong-eop": "\u626d\u66f2\u7684\u6797\u6176\u696d",
    "Han Ho-bae": "\u97d3\u6d69\u57f9",
    "S Corp. Military Commissioner  - Sal": "S\u516c\u53f8\u5175\u66f9\u5224\u66f8 - Sal",
    "S Corp. Bodyguard - Pi": "S\u516c\u53f8\u8b77\u885b - Pi",
    "The Branded": "\u53d7\u70d9\u5370\u8005",
    "Ezra": "\u4ee5\u65af\u62c9",
    "Ry\u014dsh\u016b": "\u826f\u79c0",
    "Sinner #4": "4\u865f\u7f6a\u4eba",
    "Distortion": "\u626d\u66f2",
    "A Distant World": "A Distant World",
    "Malkuth": "Malkuth",
    "Netzach": "Netzach",
    "Hod": "Hod",
    "Tiphereth": "Tiphereth",
    "Hana Assoc. North": "Hana\u5354\u6703 \u5317\u90e8",
    "!@#*%$": "!@#*%$",
    "Intervallo VII": "\u9593\u7ae0 VII",
    "Accessing the Event": "\u9032\u5165\u6d3b\u52d5",
    "Event Period": "\u6d3b\u52d5\u671f\u9593",
    "Event Encounters": "\u6d3b\u52d5\u906d\u9047",
    "Event Bonus Units": "\u6d3b\u52d5\u52a0\u6210\u55ae\u4f4d",
    "Reward Exchange": "\u734e\u52f5\u514c\u63db",
    "Photo Bundles": "\u7167\u7247\u5305",
    "1st Birthday": "1\u9031\u5e74",
    "2nd Anniversary": "2\u9031\u5e74",
    "2nd Anniversary (Special)": "2\u9031\u5e74\uff08\u7279\u5225\uff09",
    "3rd Anniversary": "3\u9031\u5e74",
    "3rd Anniversary (Special)": "3\u9031\u5e74\uff08\u7279\u5225\uff09",
    "Clear 9.5-26": "\u901a\u95dc 9.5-26",
    "The [Mnestic Experience Event Page] opens after clearing Stage 0-4 of the Main Story. You may enter the event page via the banner on the Window or the Driverside.": f"\u901a\u95dc\u4e3b\u7dda\u6545\u4e8b 0-4 \u5f8c\uff0c\u5c07\u958b\u653e\u300c{MNESTIC_NAME}\u6d3b\u52d5\u9801\u9762\u300d\u3002\u53ef\u900f\u904e\u8996\u7a97\u6216\u99d5\u99db\u5ea7\u7684\u6a6b\u5e45\u9032\u5165\u6d3b\u52d5\u9801\u9762\u3002",
    "The duration of the Mnestic Experience event is shown here.\nDuring the event, you can earn [Photos] by clearing Event Stages. You can also earn [Photos] by clearing the Mirror Dungeons or clearing Main Story Stages for the first time.\n\u203b However, [Photos] cannot be obtained in Luxcavations and Refraction Railways.": f"\u6b64\u8655\u6703\u986f\u793a\u300c{MNESTIC_NAME}\u300d\u6d3b\u52d5\u7684\u671f\u9593\u3002\n\u6d3b\u52d5\u671f\u9593\uff0c\u53ef\u900f\u904e\u901a\u95dc\u6d3b\u52d5\u95dc\u5361\u7372\u5f97\u300c\u7167\u7247\u300d\u3002\u9996\u6b21\u901a\u95dc\u93e1\u5730\u7262\u6216\u4e3b\u7dda\u6545\u4e8b\u95dc\u5361\u6642\uff0c\u4e5f\u53ef\u7372\u5f97\u300c\u7167\u7247\u300d\u3002\n\u203b \u4f46\u7d10\u7d5e\u63a1\u5149\u8207\u6298\u5c04\u9435\u9053\u7121\u6cd5\u7372\u5f97\u300c\u7167\u7247\u300d\u3002",
    "Mnestic Experience Event consists of 11 stages, including story stages, and a single dungeon. Said stages also offer batches of [Photos] as a first-time Clear bonus (only for first-time clears of each Stage).\n\nYou can earn considerably more [Photos] from Mnestic Experience Stages compared to Main Story Stages. ": f"\u300c{MNESTIC_NAME}\u300d\u6d3b\u52d5\u7531 11 \u500b\u95dc\u5361\u8207 1 \u500b\u5730\u7262\u7d44\u6210\uff0c\u5176\u4e2d\u5305\u542b\u6545\u4e8b\u95dc\u5361\u3002\u9019\u4e9b\u95dc\u5361\u4e5f\u6703\u5728\u9996\u6b21\u901a\u95dc\u6642\u63d0\u4f9b\u300c\u7167\u7247\u300d\u4f5c\u70ba\u9996\u901a\u734e\u52f5\uff08\u50c5\u9650\u5404\u95dc\u5361\u9996\u6b21\u901a\u95dc\uff09\u3002\n\n\u8207\u4e3b\u7dda\u6545\u4e8b\u95dc\u5361\u76f8\u6bd4\uff0c\u300c{MNESTIC_NAME}\u300d\u95dc\u5361\u53ef\u7372\u5f97\u66f4\u591a\u300c\u7167\u7247\u300d\u3002",
    "Having Bonus Identities on your team increases the amount of [Photos] earned from Stages and Mirror Dungeons.": "\u968a\u4f0d\u4e2d\u7de8\u5165\u52a0\u6210\u4eba\u683c\u6642\uff0c\u53ef\u589e\u52a0\u5f9e\u95dc\u5361\u8207\u93e1\u5730\u7262\u7372\u5f97\u7684\u300c\u7167\u7247\u300d\u6578\u91cf\u3002",
    "You can redeem various rewards from the [Reward Exchange] based on the number of [Photos] you have.": "\u53ef\u6839\u64da\u6301\u6709\u7684\u300c\u7167\u7247\u300d\u6578\u91cf\uff0c\u5728\u300c\u734e\u52f5\u514c\u63db\u6240\u300d\u514c\u63db\u5404\u7a2e\u734e\u52f5\u3002",
    "The [Reward Exchange]'s open duration is shown here.": "\u6b64\u8655\u6703\u986f\u793a\u300c\u734e\u52f5\u514c\u63db\u6240\u300d\u7684\u958b\u653e\u671f\u9593\u3002",
    "You can acquire the event reward Identity, Ticket Deco, banners, and various currencies from [Reward Exchange] menu.": "\u53ef\u5728\u300c\u734e\u52f5\u514c\u63db\u6240\u300d\u9078\u55ae\u4e2d\u7372\u5f97\u6d3b\u52d5\u734e\u52f5\u4eba\u683c\u3001\u8eca\u7968\u88dd\u98fe\u3001\u6a6b\u5e45\u8207\u5404\u7a2e\u8ca8\u5e63\u3002",
    "Rarely, you may obtain [Photo Bundles] from clearing Encounters. [Photo Bundles] is automatically converted to 20 [Photos] upon acquisition.": "\u901a\u95dc\u906d\u9047\u6642\uff0c\u6709\u4f4e\u6a5f\u7387\u7372\u5f97\u300c\u7167\u7247\u5305\u300d\u3002\u7372\u5f97\u300c\u7167\u7247\u5305\u300d\u6642\uff0c\u6703\u81ea\u52d5\u8f49\u63db\u70ba 20 \u500b\u300c\u7167\u7247\u300d\u3002",
    "Even after the event fully ends, you will be able to experience the Mnestic Experience combat Encounters and view its story anytime at the Driverside - [Deviazione] and Theater - [Detour Tales].": f"\u5373\u4f7f\u6d3b\u52d5\u5b8c\u5168\u7d50\u675f\uff0c\u4e5f\u53ef\u96a8\u6642\u5728\u99d5\u99db\u5ea7\u7684\u300cDeviazione\u300d\u8207\u5287\u5834\u7684\u300c\u7e5e\u9053\u6545\u4e8b\u300d\u4e2d\uff0c\u9ad4\u9a57\u300c{MNESTIC_NAME}\u300d\u7684\u6230\u9b25\u906d\u9047\u4e26\u95b1\u89bd\u5176\u6545\u4e8b\u3002",
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
    out = out.replace("Kim Satgat", "\u91d1\u7b20")
    out = out.replace("Dokkaebi Arms", "\u9b3c\u602a\u81c2")
    out = out.replace("Aeng-du", "\u6afb\u6843")
    out = out.replace("\u674f\u6597", "\u6afb\u6843")
    out = out.replace("\u7af9\u7b20\u91d1", "\u91d1\u7b20")
    out = out.replace("\u7af9\u7b20 Kim", "\u91d1\u7b20")
    out = out.replace("\u91d1<ruby=bamboo rain hat>Lib</ruby>", "\u91d1\u7b20")
    out = out.replace("\u6234\u7af9\u7b20\u7684\u91d1", "\u91d1\u7b20")
    out = out.replace("Service des Clous", "\u91d8\u52d9\u90e8")
    out = out.replace("(\ub354\ubbf8)", "(\u5360\u4f4d)")
    out = out.replace("No particular effect", "\u7121\u7279\u6b8a\u6548\u679c")
    out = out.replace("Say that you're not.", "\u8aaa\u81ea\u5df1\u4e26\u975e\u5982\u6b64\u3002")
    out = out.replace("The wind-howling path.", "\u72c2\u98a8\u547c\u5578\u7684\u9053\u8def\u3002")
    out = out.replace("The silent path.", "\u5bc2\u975c\u7121\u8072\u7684\u9053\u8def\u3002")
    out = out.replace("All Identities lose SP", "\u5168\u9ad4\u4eba\u683c\u5931\u53bb SP")
    out = out.replace("Furioso-Replica", "\u72c2\u60f3\u66f2-\u8907\u88fd\u54c1")
    out = out.replace("[Sal]", "\uff08Sal\uff09")
    out = out.replace("[Crescendo]", "\uff08Crescendo\uff09")
    out = out.replace("[Lacrimosa-Crescendo]", "\uff08Lacrimosa-Crescendo\uff09")
    for source, target in MNESTIC_REPLACEMENTS.items():
        out = out.replace(source, target)
    for source, target in FINAL_TEXT_REPLACEMENTS.items():
        out = out.replace(source, target)
    return out


def token_preserve_file(file_key: str) -> bool:
    base = Path(file_key).name
    return base in {
        "Skills_Abnormality-exme.json",
        "Skills_Assist-exme.json",
        "Skills_Enemy-exme.json",
        "Passives_Abnormality-exme.json",
        "Passives_Assist-exme.json",
        "Passives_Enemy-exme.json",
    }


def restore_bracket_tokens(source: Any, translated: Any) -> Any:
    if not isinstance(source, str) or not isinstance(translated, str):
        return translated
    source_tokens = re.findall(r"\[[A-Za-z0-9_]+\]", source)
    if not source_tokens:
        return translated
    target_spans = list(re.finditer(r"\[[^\[\]]+\]", translated))
    if len(target_spans) != len(source_tokens):
        return translated
    pieces = []
    last = 0
    for span, source_token in zip(target_spans, source_tokens):
        pieces.append(translated[last:span.start()])
        pieces.append(source_token)
        last = span.end()
    pieces.append(translated[last:])
    return "".join(pieces)


def known_translate(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    if value in KNOWN_TEXT_TRANSLATIONS:
        return KNOWN_TEXT_TRANSLATIONS[value]
    if "Mnestic Experience" in value or "\u042d.\u0413.\u041e" in value:
        out = value
        for source, target in MNESTIC_REPLACEMENTS.items():
            out = out.replace(source, target)
        return out
    return None


def known_translation_fields(unit: dict[str, Any]) -> dict[str, str] | None:
    fields: dict[str, str] = {}
    for field, value in unit.get("fields", {}).items():
        translated = known_translate(value)
        if translated is None:
            return None
        fields[field] = translated
    return fields


def file_specific_translation_fields(file_key: str, unit: dict[str, Any]) -> dict[str, str] | None:
    unit_id = unit.get("id")
    if file_key == "RecordMemoryEvent.json" and unit_id in RECORD_MEMORY_TEXT_BY_ID:
        fields = {
            field: RECORD_MEMORY_TEXT_BY_ID[unit_id]
            for field in unit.get("fields", {})
            if field == "content"
        }
        return fields or None
    if file_key == "Items.json" and unit_id in ITEM_EXTRA_BY_ID:
        extra = ITEM_EXTRA_BY_ID[unit_id]
        fields = {
            field: extra[field]
            for field in unit.get("fields", {})
            if field in extra
        }
        return fields or None
    if file_key == "Personality_Get_Condition.json" and unit_id in PERSONALITY_CONDITION_EXTRA_BY_ID:
        extra = PERSONALITY_CONDITION_EXTRA_BY_ID[unit_id]
        fields = {
            field: extra[field]
            for field in unit.get("fields", {})
            if field in extra
        }
        return fields or None
    return None


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
    if file_key == "RecordMemoryEvent.json":
        for item in entries(doc):
            if isinstance(item, dict) and item.get("id") in RECORD_MEMORY_TEXT_BY_ID:
                item["content"] = RECORD_MEMORY_TEXT_BY_ID[item["id"]]
    if file_key == "Items.json":
        for item in entries(doc):
            if isinstance(item, dict) and item.get("id") in ITEM_EXTRA_BY_ID:
                item.update(ITEM_EXTRA_BY_ID[item["id"]])
    for item in entries(doc):
        if isinstance(item, dict) and str(item.get("id")) in VISIBLE_NAME_BY_ID and "name" in item:
            item["name"] = VISIBLE_NAME_BY_ID[str(item["id"])]
        if file_key == "ScenarioModelCodes-AutoCreated.json" and isinstance(item, dict):
            extra = SCENARIO_MODEL_EXTRA.get(str(item.get("id")))
            if extra:
                item.update(extra)
        if file_key.startswith("StoryData/") and isinstance(item, dict):
            teller = MODEL_TELLER_MAP.get(str(item.get("model")))
            if teller and item.get("teller") in (None, "", "???", "\uff1f\uff1f\uff1f"):
                item["teller"] = teller
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
            fields = file_specific_translation_fields(file_key, unit)
            if fields is None:
                fields = translations.get(tr_key)
            if fields is None:
                fields = known_translation_fields(unit)
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
                if token_preserve_file(file_key) and field.endswith("desc"):
                    value = restore_bracket_tokens(unit.get("fields", {}).get(field), value)
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
    if not (token_preserve_file(file_key) and path.endswith("desc")):
        return issues
    for raw_token in re.findall(r"\[([^\[\]]+)\]", value):
        if contains_han(raw_token):
            issues.append({"file": file_key, "field": path, "problem": "translated_bracket_token", "token": raw_token, "sample": value[:160]})
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

