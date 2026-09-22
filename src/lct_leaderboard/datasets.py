from typing import Any, Dict, List


def manifest_to_datasets(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for record in manifest.get("records", []):
        rows.append(
            {
                "id": record.get("scene_id"),
                "scene_id": record.get("scene_id"),
                "parent_scene_id": record.get("parent_scene_id"),
                "version": manifest.get("dataset_version"),
                "split": record.get("split"),
                "city": record.get("city"),
                "research_bucket": record.get("research_bucket"),
                "input_path": record.get("input"),
                "input_hash": record.get("input_hash"),
                "feature_count": record.get("feature_count"),
                "restriction_count": record.get("restriction_count"),
                "oks_count": record.get("oks_count"),
                "is_active": True,
                "is_public": record.get("split") != "test",
            }
        )
    return rows
