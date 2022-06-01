from scripts import er_params
from typing import Dict, List, Tuple
from scripts.er_params.enums import ItemIDFlag, Affinity, WeaponClass
from scripts.erdb_common import GeneratorDataBase, get_schema_properties, get_schema_enums, parse_description

ParamRow = er_params.ParamRow
ParamDict = er_params.ParamDict

def _is_elem_true(row: ParamRow, list_param: str, elem: str) -> bool:
    return row.get_bool(list_param + elem)

def _get_classes(row: ParamRow) -> List[WeaponClass]:
    return [c for c in list(WeaponClass) if _is_elem_true(row, "canMountWep_", c)]

def _get_affinities(row: ParamRow) -> List[Affinity]:
    return [a for a in list(Affinity) if _is_elem_true(row, "configurableWepAttr", a.zfill(2))]

def iterate_ashes_of_war(self: GeneratorDataBase, ashes_of_war: ParamDict):
    for row in ashes_of_war.values():
        yield row

def make_ash_of_war_object(self: GeneratorDataBase, row: ParamRow) -> Dict:
    summaries = self.msgs["summaries"]
    descriptions = self.msgs["descriptions"]

    return {
        "full_hex_id": row.index_hex,
        "id": row.index,
        "name": row.name,
        "summary": summaries[row.index],
        "description": parse_description(descriptions[row.index]),
        "is_tradable": row.get("disableMultiDropShare") == "0",
        "price_sold": row.get_int_corrected("sellValue"),
        "max_held": 999,
        "max_stored": 999,
        # locations -- cannot autogenerate, make sure not to overwrite
        # remarks -- cannot autogenerate, make sure not to overwrite
        "classes": [*map(str, _get_classes(row))],
        "default_affinity": str(Affinity(row.get("defaultWepAttr"))),
        "affinities": [*map(str, _get_affinities(row))],
        "skill_id": row.get_int("swordArtsParamId")
    }

def get_ash_of_war_schema() -> Tuple[Dict, Dict[str, Dict]]:
    properties, store = get_schema_properties("item", "ashes-of-war/definitions/AshOfWar")
    store.update(get_schema_enums("ash-of-war-names", "affinity-names", "armament-class-names", "skill-names"))
    return properties, store

class AshOfWarGeneratorData(GeneratorDataBase):
    Base = GeneratorDataBase

    output_file: str = "ashes-of-war.json"
    schema_file: str = "ashes-of-war.schema.json"
    element_name: str = "AshesOfWar"

    main_param_retriever = Base.ParamDictRetriever("EquipParamGem", ItemIDFlag.ACCESSORIES, id_min=10000)

    param_retrievers = {}

    msgs_retrievers = {
        "summaries": Base.MsgsRetriever("GemInfo"),
        "descriptions": Base.MsgsRetriever("GemCaption")
    }

    lookup_retrievers = {}

    schema_retriever = get_ash_of_war_schema
    main_param_iterator = iterate_ashes_of_war
    construct_object = make_ash_of_war_object