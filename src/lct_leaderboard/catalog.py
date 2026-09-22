from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class PipeSpec:
    diameter_mm: int
    capacity_tph: float
    max_length_m: float
    new_rate_rub_per_m: float
    reconstruction_rate_rub_per_m: float


@dataclass(frozen=True)
class ChamberCost:
    min_diameter_mm: int
    max_diameter_mm: int
    cost_rub: float


@dataclass(frozen=True)
class RuleCatalog:
    cost_weight: float
    length_weight: float
    cost_scale_rub: float
    length_scale_m: float
    pipe_catalog: Dict[int, PipeSpec]
    chamber_costs: List[ChamberCost]
    unconnected_fixed_rub: float
    unconnected_per_tph_rub: float
    max_chamber_degree: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuleCatalog":
        score = data.get("score", {})
        pipes = {
            int(item["diameter_mm"]): PipeSpec(
                diameter_mm=int(item["diameter_mm"]),
                capacity_tph=float(item["capacity_tph"]),
                max_length_m=float(item["max_length_m"]),
                new_rate_rub_per_m=float(item["new_rate_rub_per_m"]),
                reconstruction_rate_rub_per_m=float(
                    item["reconstruction_rate_rub_per_m"]
                ),
            )
            for item in data.get("pipe_catalog", [])
        }
        chamber_costs = [
            ChamberCost(
                min_diameter_mm=int(item["min_diameter_mm"]),
                max_diameter_mm=int(item["max_diameter_mm"]),
                cost_rub=float(item["cost_rub"]),
            )
            for item in data.get("chamber_costs", [])
        ]
        penalty = data.get("unconnected_penalty", {})
        return cls(
            cost_weight=float(score.get("cost_weight", 0.7)),
            length_weight=float(score.get("length_weight", 0.3)),
            cost_scale_rub=float(score.get("cost_scale_rub", 25_000_000)),
            length_scale_m=float(score.get("length_scale_m", 100)),
            pipe_catalog=pipes,
            chamber_costs=chamber_costs,
            unconnected_fixed_rub=float(penalty.get("fixed_rub", 100_000_000)),
            unconnected_per_tph_rub=float(penalty.get("per_tph_rub", 500_000)),
            max_chamber_degree=int(data.get("max_chamber_degree", 4)),
        )

    def pipe(self, diameter_mm: int) -> Optional[PipeSpec]:
        return self.pipe_catalog.get(int(diameter_mm))

    def chamber_cost(self, diameter_mm: int) -> Optional[float]:
        diameter = int(diameter_mm)
        for item in self.chamber_costs:
            if item.min_diameter_mm <= diameter <= item.max_diameter_mm:
                return item.cost_rub
        return None
