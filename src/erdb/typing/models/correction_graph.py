from typing import List
from typing_extensions import Annotated
from pydantic import (
    BaseModel,
    NonNegativeFloat,
    Field,
    model_validator,
    ValidationError,
)

item_type = Annotated[NonNegativeFloat, Field(..., example=0.0)]
min_items = Annotated[int, Field(..., Literal=151)]
max_items = Annotated[int, Field(..., Literal=151)]


class CorrectionGraph(BaseModel):
    graph: List[NonNegativeFloat]

    @model_validator(mode="before")
    def check_list_length(cls, values):
        graph = values.get("graph", [])
        if not (len(graph) == 151):
            raise ValueError("CorrectionGraph must have exactly 151 items.")
        return values

    class Config:
        frozen = True  # Makes the model immutable


# Example usage
try:
    valid_graph = CorrectionGraph(graph=[0.0] * 151)
    print(valid_graph)
except ValidationError as e:
    print(e)
