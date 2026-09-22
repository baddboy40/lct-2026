from dataclasses import dataclass
from functools import cmp_to_key
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class SubmissionScoreInput:
    team_id: str
    dataset_id: str
    accepted: bool
    cost: float
    length: float
    runtime_seconds: float = 0.0


@dataclass(frozen=True)
class DatasetScore:
    team_id: str
    dataset_id: str
    score: float
    cost: float
    length: float
    runtime_seconds: float
    accepted: bool


@dataclass(frozen=True)
class LeaderboardEntry:
    team_id: str
    rank: int
    total_score: float
    total_runtime_seconds: float
    total_cost: float
    total_length: float


def score_dataset(
    submissions: Iterable[SubmissionScoreInput],
    cost_weight: float = 0.7,
    length_weight: float = 0.3,
) -> List[DatasetScore]:
    rows = list(submissions)
    accepted = [
        row for row in rows if row.accepted and row.cost > 0 and row.length > 0
    ]
    if not accepted:
        return [
            DatasetScore(
                team_id=row.team_id,
                dataset_id=row.dataset_id,
                score=0.0,
                cost=row.cost,
                length=row.length,
                runtime_seconds=row.runtime_seconds,
                accepted=False,
            )
            for row in rows
        ]

    min_cost = min(row.cost for row in accepted)
    min_length = min(row.length for row in accepted)
    scores = []
    for row in rows:
        score = 0.0
        if row in accepted:
            score = cost_weight * min_cost / row.cost + length_weight * min_length / row.length
        scores.append(
            DatasetScore(
                team_id=row.team_id,
                dataset_id=row.dataset_id,
                score=score,
                cost=row.cost,
                length=row.length,
                runtime_seconds=row.runtime_seconds,
                accepted=row in accepted,
            )
        )
    return scores


def build_leaderboard(
    dataset_scores: Iterable[DatasetScore],
    dataset_ids: Iterable[str],
    equality_threshold: float = 0.005,
) -> List[LeaderboardEntry]:
    dataset_count = len(list(dataset_ids))
    if dataset_count == 0:
        return []

    grouped: Dict[str, List[DatasetScore]] = {}
    for row in dataset_scores:
        grouped.setdefault(row.team_id, []).append(row)

    entries: List[LeaderboardEntry] = []
    for team_id, rows in grouped.items():
        total_score = sum(row.score for row in rows) / dataset_count
        entries.append(
            LeaderboardEntry(
                team_id=team_id,
                rank=0,
                total_score=total_score,
                total_runtime_seconds=sum(row.runtime_seconds for row in rows),
                total_cost=sum(row.cost for row in rows),
                total_length=sum(row.length for row in rows),
            )
        )

    sorted_entries = sorted(
        entries,
        key=cmp_to_key(
            lambda left, right: _compare_entries(
                left, right, equality_threshold=equality_threshold
            )
        ),
    )
    return [
        LeaderboardEntry(
            team_id=item.team_id,
            rank=index + 1,
            total_score=item.total_score,
            total_runtime_seconds=item.total_runtime_seconds,
            total_cost=item.total_cost,
            total_length=item.total_length,
        )
        for index, item in enumerate(sorted_entries)
    ]


def choose_best_variant(
    reports: Iterable[dict], cost_weight: float = 0.7, length_weight: float = 0.3
) -> Optional[dict]:
    accepted = [report for report in reports if report.get("accepted")]
    if not accepted:
        return None

    def key(report: dict) -> float:
        metrics = report.get("metrics", {})
        cost = float(metrics.get("calculated_cost", 0.0))
        length = float(metrics.get("new_network_length", 0.0))
        return cost_weight * cost / 25_000_000 + length_weight * length / 100

    return min(accepted, key=key)


def _compare_entries(
    left: LeaderboardEntry, right: LeaderboardEntry, equality_threshold: float
) -> int:
    score_diff = left.total_score - right.total_score
    if abs(score_diff) > equality_threshold:
        return -1 if score_diff > 0 else 1

    for left_value, right_value in (
        (left.total_runtime_seconds, right.total_runtime_seconds),
        (left.total_cost, right.total_cost),
        (left.total_length, right.total_length),
    ):
        if left_value < right_value:
            return -1
        if left_value > right_value:
            return 1

    if left.team_id < right.team_id:
        return -1
    if left.team_id > right.team_id:
        return 1
    return 0
