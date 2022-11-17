from typing import Dict, Iterator, Tuple

import erdb.loaders.schema as schema
from erdb.typing.params import ParamDict, ParamRow
from erdb.typing.enums import GoodsSortGroupID, GoodsType, ItemIDFlag
from erdb.utils.common import strip_invalid_name
from erdb.generators._base import GeneratorDataBase


def _get_category(row: ParamRow) -> str:
    G = GoodsSortGroupID
    return {
        G.GROUP_1: "Flask",
        G.GROUP_2: "Smithing Stone",
        G.GROUP_3: "Somber Smithing Stone",
        G.GROUP_4: "Glovewort",
    }[row.get_int("sortGroupId")]

class BolsteringMaterialGeneratorData(GeneratorDataBase):
    Base = GeneratorDataBase

    @staticmethod # override
    def output_file() -> str:
        return "bolstering-materials.json"

    @staticmethod # override
    def schema_file() -> str:
        return "bolstering-materials.schema.json"

    @staticmethod # override
    def element_name() -> str:
        return "BolsteringMaterials"

    # override
    def get_key_name(self, row: ParamRow) -> str:
        return strip_invalid_name(self.msgs["names"][row.index])

    main_param_retriever = Base.ParamDictRetriever("EquipParamGoods", ItemIDFlag.GOODS)

    param_retrievers = {}

    msgs_retrievers = {
        "names": Base.MsgsRetriever("GoodsName"),
        "summaries": Base.MsgsRetriever("GoodsInfo"),
        "descriptions": Base.MsgsRetriever("GoodsCaption")
    }

    lookup_retrievers = {}

    @staticmethod
    def schema_retriever() -> Tuple[Dict, Dict[str, Dict]]:
        properties, store = schema.load_properties(
            "item/properties",
            "item/definitions/ItemUserData/properties",
            "bolstering-materials/definitions/BolsteringMaterial/properties")
        store.update(schema.load_enums("item-names"))
        return properties, store

    def main_param_iterator(self, materials: ParamDict) -> Iterator[ParamRow]:
        for row in materials.values():
            if row.get("goodsType") == GoodsType.REINFORCEMENT_MATERIAL:
                yield row

    def construct_object(self, row: ParamRow) -> Dict:
        return self.get_fields_item(row) | self.get_fields_user_data(row, "locations", "remarks") | {
            "category": _get_category(row)
        }