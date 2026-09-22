import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set

from .catalog import RuleCatalog
from .geometry import geometry_length_m


CRITICAL_CODES = {
    "INVALID_JSON_CONTRACT",
    "DUPLICATE_ID",
    "MISSING_VARIANT_SUMMARY",
    "SUMMARY_CARDINALITY_ERROR",
    "REQUIRED_FIELD_MISSING",
    "NONFINITE_NUMBER",
    "UNKNOWN_DIAMETER",
    "CAPACITY_VIOLATION",
}


@dataclass
class Issue:
    code: str
    severity: str
    message: str
    feature_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }
        if self.feature_id is not None:
            data["feature_id"] = self.feature_id
        return data


@dataclass
class Metrics:
    calculated_cost: float = 0.0
    new_network_length: float = 0.0
    chamber_construction_cost: float = 0.0
    unconnected_penalty: float = 0.0
    network_construction_cost: float = 0.0
    declared_calculated_cost: Optional[float] = None
    declared_new_network_length: Optional[float] = None
    declared_score: Optional[float] = None
    basic_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "calculated_cost": round(self.calculated_cost, 2),
            "new_network_length": round(self.new_network_length, 2),
            "chamber_construction_cost": round(self.chamber_construction_cost, 2),
            "unconnected_penalty": round(self.unconnected_penalty, 2),
            "network_construction_cost": round(self.network_construction_cost, 2),
            "declared_calculated_cost": self.declared_calculated_cost,
            "declared_new_network_length": self.declared_new_network_length,
            "declared_score": self.declared_score,
            "basic_score": None
            if self.basic_score is None
            else round(self.basic_score, 4),
        }


@dataclass
class ValidationReport:
    status: str
    accepted: bool
    variant_id: Optional[str]
    issues: List[Issue] = field(default_factory=list)
    metrics: Metrics = field(default_factory=Metrics)
    verifier_profile: str = "basic-arithmetic-v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "accepted": self.accepted,
            "variant_id": self.variant_id,
            "verifier_profile": self.verifier_profile,
            "metrics": self.metrics.to_dict(),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def validate_result_geojson(
    result_geojson: Dict[str, Any],
    catalog: RuleCatalog,
    input_geojson: Optional[Dict[str, Any]] = None,
    cost_tolerance_rub: float = 1.0,
    length_tolerance_m: float = 0.5,
) -> ValidationReport:
    issues: List[Issue] = []
    metrics = Metrics()

    if result_geojson.get("type") != "FeatureCollection":
        issues.append(
            Issue(
                code="INVALID_JSON_CONTRACT",
                severity="critical",
                message="Result must be a GeoJSON FeatureCollection.",
            )
        )
        return _report(None, issues, metrics)

    features = result_geojson.get("features")
    if not isinstance(features, list):
        issues.append(
            Issue(
                code="INVALID_JSON_CONTRACT",
                severity="critical",
                message="GeoJSON FeatureCollection must contain a features list.",
            )
        )
        return _report(None, issues, metrics)

    _check_unique_ids(features, issues)
    _check_nonfinite_numbers(result_geojson, issues)

    summaries = _features_by_object_type(features, "variant_summary")
    if not summaries:
        issues.append(
            Issue(
                code="MISSING_VARIANT_SUMMARY",
                severity="critical",
                message="Result must contain one variant_summary feature.",
            )
        )
        return _report(None, issues, metrics)

    if len(summaries) > 1:
        issues.append(
            Issue(
                code="SUMMARY_CARDINALITY_ERROR",
                severity="critical",
                message="Result contains more than one variant_summary feature.",
            )
        )

    summary = summaries[0]
    summary_props = _props(summary)
    variant_id = _as_optional_str(summary_props.get("variant_id"))

    _require_fields(
        summary,
        [
            "variant_id",
            "calculated_cost",
            "new_network_length",
            "length",
            "score",
            "unconnected_oks_ids",
        ],
        issues,
    )
    metrics.declared_calculated_cost = _as_optional_float(
        summary_props.get("calculated_cost")
    )
    metrics.declared_new_network_length = _as_optional_float(
        summary_props.get("new_network_length", summary_props.get("length"))
    )
    metrics.declared_score = _as_optional_float(summary_props.get("score"))

    oks_flow = _input_oks_flow(input_geojson)
    network_features = _features_by_object_type(features, "heat_network")
    chamber_features = _features_by_object_type(features, "heat_chamber")

    for feature in network_features:
        _validate_network_feature(feature, catalog, issues, metrics)

    for feature in chamber_features:
        _validate_chamber_feature(feature, catalog, issues, metrics)

    unconnected_ids = summary_props.get("unconnected_oks_ids") or []
    if isinstance(unconnected_ids, list):
        metrics.unconnected_penalty = _unconnected_penalty(
            unconnected_ids, oks_flow, catalog
        )
    else:
        issues.append(
            Issue(
                code="REQUIRED_FIELD_MISSING",
                severity="critical",
                message="variant_summary.unconnected_oks_ids must be a list.",
                feature_id=_feature_id(summary),
            )
        )

    metrics.calculated_cost = (
        metrics.network_construction_cost
        + metrics.chamber_construction_cost
        + metrics.unconnected_penalty
    )
    metrics.basic_score = (
        catalog.cost_weight * metrics.calculated_cost / catalog.cost_scale_rub
        + catalog.length_weight * metrics.new_network_length / catalog.length_scale_m
    )

    _compare_declared(
        metrics.declared_calculated_cost,
        metrics.calculated_cost,
        cost_tolerance_rub,
        "SUMMARY_COST_MISMATCH",
        "calculated_cost",
        summary,
        issues,
    )
    _compare_declared(
        metrics.declared_new_network_length,
        metrics.new_network_length,
        length_tolerance_m,
        "SUMMARY_LENGTH_MISMATCH",
        "new_network_length",
        summary,
        issues,
    )

    return _report(variant_id, issues, metrics)


def _validate_network_feature(
    feature: Dict[str, Any],
    catalog: RuleCatalog,
    issues: List[Issue],
    metrics: Metrics,
) -> None:
    props = _props(feature)
    _require_fields(
        feature,
        [
            "id",
            "variant_id",
            "start_node_id",
            "end_node_id",
            "flow_tph",
            "diameter",
        ],
        issues,
    )
    feature_id = _feature_id(feature)
    diameter = _as_optional_int(props.get("diameter"))
    flow = _as_optional_float(props.get("flow_tph"))

    if diameter is None:
        return

    pipe = catalog.pipe(diameter)
    if pipe is None:
        issues.append(
            Issue(
                code="UNKNOWN_DIAMETER",
                severity="critical",
                message="heat_network diameter is absent from pipe_catalog.",
                feature_id=feature_id,
            )
        )
        return

    if flow is not None and flow > pipe.capacity_tph:
        issues.append(
            Issue(
                code="CAPACITY_VIOLATION",
                severity="critical",
                message=(
                    f"flow_tph={flow} exceeds capacity_tph={pipe.capacity_tph} "
                    f"for diameter={diameter}."
                ),
                feature_id=feature_id,
            )
        )

    length = geometry_length_m(feature.get("geometry") or {})
    if length == 0:
        length = _as_optional_float(props.get("length")) or 0.0
        issues.append(
            Issue(
                code="GEOMETRY_LENGTH_FALLBACK",
                severity="warning",
                message="Line geometry is missing or empty; used declared length.",
                feature_id=feature_id,
            )
        )

    metrics.new_network_length += length
    metrics.network_construction_cost += length * pipe.new_rate_rub_per_m


def _validate_chamber_feature(
    feature: Dict[str, Any],
    catalog: RuleCatalog,
    issues: List[Issue],
    metrics: Metrics,
) -> None:
    props = _props(feature)
    _require_fields(feature, ["id", "variant_id", "diameter"], issues)
    feature_id = _feature_id(feature)
    diameter = _as_optional_int(props.get("diameter"))
    if diameter is None:
        return

    cost = catalog.chamber_cost(diameter)
    if cost is None:
        issues.append(
            Issue(
                code="UNKNOWN_CHAMBER_DIAMETER",
                severity="warning",
                message="heat_chamber diameter does not match chamber_costs.",
                feature_id=feature_id,
            )
        )
        return

    metrics.chamber_construction_cost += cost


def _check_unique_ids(features: Iterable[Dict[str, Any]], issues: List[Issue]) -> None:
    seen: Set[str] = set()
    for feature in features:
        feature_id = _feature_id(feature)
        if feature_id is None:
            continue
        if feature_id in seen:
            issues.append(
                Issue(
                    code="DUPLICATE_ID",
                    severity="critical",
                    message=f"Duplicate feature id: {feature_id}.",
                    feature_id=feature_id,
                )
            )
        seen.add(feature_id)


def _check_nonfinite_numbers(data: Any, issues: List[Issue]) -> None:
    def walk(value: Any, path: str) -> None:
        if isinstance(value, float) and not math.isfinite(value):
            issues.append(
                Issue(
                    code="NONFINITE_NUMBER",
                    severity="critical",
                    message=f"Non-finite number at {path}.",
                )
            )
        elif isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")

    walk(data, "$")


def _require_fields(
    feature: Dict[str, Any], field_names: Iterable[str], issues: List[Issue]
) -> None:
    props = _props(feature)
    feature_id = _feature_id(feature)
    for field_name in field_names:
        if field_name not in props or props[field_name] is None:
            issues.append(
                Issue(
                    code="REQUIRED_FIELD_MISSING",
                    severity="critical",
                    message=f"Required property is missing: {field_name}.",
                    feature_id=feature_id,
                )
            )


def _compare_declared(
    declared: Optional[float],
    calculated: float,
    tolerance: float,
    code: str,
    field_name: str,
    summary: Dict[str, Any],
    issues: List[Issue],
) -> None:
    if declared is None:
        return
    if abs(declared - calculated) > tolerance:
        issues.append(
            Issue(
                code=code,
                severity="warning",
                message=(
                    f"Declared {field_name}={declared:.2f}, "
                    f"recalculated={calculated:.2f}."
                ),
                feature_id=_feature_id(summary),
            )
        )


def _unconnected_penalty(
    unconnected_ids: List[Any], oks_flow: Dict[str, float], catalog: RuleCatalog
) -> float:
    total = 0.0
    for oks_id in unconnected_ids:
        flow = oks_flow.get(str(oks_id), 0.0)
        total += catalog.unconnected_fixed_rub + catalog.unconnected_per_tph_rub * flow
    return total


def _input_oks_flow(input_geojson: Optional[Dict[str, Any]]) -> Dict[str, float]:
    if not input_geojson:
        return {}
    flow: Dict[str, float] = {}
    for feature in input_geojson.get("features") or []:
        props = _props(feature)
        if props.get("object_type") == "oks_connection_point":
            feature_id = _as_optional_str(props.get("id"))
            if feature_id is not None:
                flow_value = _as_optional_float(props.get("flow_tph")) or 0.0
                flow[feature_id] = flow_value
    return flow


def _features_by_object_type(
    features: Iterable[Dict[str, Any]], object_type: str
) -> List[Dict[str, Any]]:
    return [
        feature
        for feature in features
        if _props(feature).get("object_type") == object_type
    ]


def _props(feature: Dict[str, Any]) -> Dict[str, Any]:
    props = feature.get("properties")
    return props if isinstance(props, dict) else {}


def _feature_id(feature: Dict[str, Any]) -> Optional[str]:
    props = _props(feature)
    value = props.get("id", feature.get("id"))
    return _as_optional_str(value)


def _as_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _as_optional_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_optional_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        result = float(value)
        if not math.isfinite(result):
            return None
        return result
    except (TypeError, ValueError):
        return None


def _report(
    variant_id: Optional[str], issues: List[Issue], metrics: Metrics
) -> ValidationReport:
    accepted = not any(
        issue.severity == "critical" or issue.code in CRITICAL_CODES
        for issue in issues
    )
    return ValidationReport(
        status="accepted" if accepted else "rejected",
        accepted=accepted,
        variant_id=variant_id,
        issues=issues,
        metrics=metrics,
    )
