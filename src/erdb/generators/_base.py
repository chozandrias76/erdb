from typing import Any, Callable, Iterator, NamedTuple, Optional, Tuple, Dict
from unicodedata import normalize, combining

from erdb.loaders.params import load as load_params, load_ids as load_param_ids, load_msg
from erdb.loaders.contrib import load as load_contrib
from erdb.typing.game_version import GameVersion
from erdb.typing.params import ParamDict, ParamRow
from erdb.typing.enums import ItemIDFlag
from erdb.shop import Lookup


def _remove_accents(string: str) -> str:
    nfkd_form = normalize("NFKD", string)
    return "".join(c for c in nfkd_form if not combining(c))

class GeneratorDataBase(NamedTuple):

    class ParamDictRetriever(NamedTuple):
        file_name: str
        item_id_flag: ItemIDFlag
        id_min: Optional[int]=None
        id_max: Optional[int]=None

        def get(self, version: GameVersion) -> ParamDict:
            args = [self.file_name, version, self.item_id_flag]
            args += [arg for arg in [self.id_min, self.id_max] if arg is not None]
            return (load_params if len(args) <= 3 else load_param_ids)(*args)

    class MsgsRetriever(NamedTuple):
        file_name: str

        def get(self, version: GameVersion) -> Dict[int, str]:
            return load_msg(self.file_name, version)

    class LookupRetriever(NamedTuple):
        shop_lineup_id_min: Optional[int]
        shop_lineup_id_max: Optional[int]
        material_set_id_min: Optional[int]
        material_set_id_max: Optional[int]
        recipe: bool = False

        def get(self, version: GameVersion) -> Lookup:
            Retr = GeneratorDataBase.ParamDictRetriever
            shop_param = "ShopLineupParam_Recipe" if self.recipe else "ShopLineupParam"
            shop = Retr(shop_param, ItemIDFlag.NON_EQUIPABBLE, self.shop_lineup_id_min, self.shop_lineup_id_max)
            mats = Retr("EquipMtrlSetParam", ItemIDFlag.NON_EQUIPABBLE, self.material_set_id_min, self.material_set_id_max)
            return Lookup(shop.get(version), mats.get(version))

    class UserDataRetriever(NamedTuple):
        def get(self, element_name: str, version: GameVersion) -> Dict[str, Dict]:
            return load_contrib(element_name, version)

    main_param: ParamDict
    params: Dict[str, ParamDict]
    msgs: Dict[str, Dict[int, str]]
    lookups: Dict[str, Lookup]
    user_data: Dict[str, Dict]

    schema_properties: Dict
    schema_store: Dict[str, Dict]

    @staticmethod
    def output_file() -> str:
        assert False, "output_file must be overridden"

    @staticmethod
    def schema_file() -> str:
        assert False, "schema_file must be overridden"

    @staticmethod
    def element_name() -> str:
        assert False, "element_name must be overridden"

    def get_key_name(self, row: ParamRow) -> str:
        assert False, "get_key_name must be overridden"

    def top_level_properties(self) -> Dict:
        return self.schema_properties

    main_param_retriever: ParamDictRetriever = None
    param_retrievers: Dict[str, ParamDictRetriever] = None
    msgs_retrievers: Dict[str, MsgsRetriever] = None
    lookup_retrievers: Dict[str, LookupRetriever] = None

    schema_retriever: Callable[[], Tuple[Dict, Dict[str, Dict]]] = None

    main_param_iterator: Callable[["GeneratorDataBase", ParamDict], Iterator[ParamRow]] = None
    construct_object: Callable[["GeneratorDataBase", ParamRow], Dict] = None

    def get_fields_item(self, row: ParamRow, *, summary: bool = True, description: bool = True) -> Dict[str, Any]:
        """
        Covers every common field specified in item.schema.json
        """

        assert not summary or "summaries" in self.msgs, "Summary specified, yet no summaries were parsed"
        assert not description or "descriptions" in self.msgs, "Description specified, yet no descriptions were parsed"

        # individual items might not have summaries or descriptions
        summary = summary and row.index in self.msgs["summaries"]
        description = description and row.index in self.msgs["descriptions"]

        return {
            "full_hex_id": row.index_hex,
            "id": row.index,
            "name": self.get_key_name(row),
            "summary": self.msgs["summaries"][row.index] if summary else "no summary",
            "description": self.msgs["descriptions"][row.index].split("\n") if description else ["no description"],
            "is_tradable": row.get("disableMultiDropShare") == "0", # assumption this exists for every param table
            "price_sold": row.get_int_corrected("sellValue"),       # assumption this exists for every param table
            "max_held": row.get_int("maxNum") if "maxNum" in row.keys else 999,
            "max_stored": row.get_int("maxRepositoryNum") if "maxRepositoryNum" in row.keys else 999,
        }

    def get_fields_user_data(self, row: ParamRow, *args: str) -> Dict[str, Any]:
        """
        Covers every user data field
        """
        def get_user_data(row: str, field: str):
            assert field in self.schema_properties
            return self.user_data.get(row.replace(":", ""), {}).get(field, self.schema_properties[field].get("default", {}))

        name = self.get_key_name(row)
        return {arg: get_user_data(name, arg) for arg in args}

    @classmethod
    def construct(cls, version: GameVersion) -> "GeneratorDataBase":
        def _retrieve_dict(retrievers):
            return {field_name: retrievers[field_name].get(version) for field_name in retrievers.keys()}

        main_param=cls.main_param_retriever.get(version)
        params=_retrieve_dict(cls.param_retrievers)
        msgs=_retrieve_dict(cls.msgs_retrievers)
        lookups=_retrieve_dict(cls.lookup_retrievers)
        user_data=cls.UserDataRetriever().get(cls.element_name(), version)
        properties, store = cls.schema_retriever()

        return cls(main_param, params, msgs, lookups, user_data, properties, store)

    def generate(self) -> Dict:
        main_iter = self.main_param_iterator(self.main_param)
        return {_remove_accents(self.get_key_name(row)): self.construct_object(row) for row in main_iter}