"""Export the bounded two-segment demonstration using existing synthetic inputs."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from elusim.optimizer import optimize_multisegment
from elusim.schemas import OptimizeMultiSegment, Simulation


def main():
    """Write gradient nodes and raw solver outputs for user inspection."""
    simulation = Simulation.model_validate(
        {
            "compounds": [
                {"id": "a", "name": "Synthetic A", "logkw": 2, "s": 4},
                {"id": "b", "name": "Synthetic B", "logkw": 2.5, "s": 4.5},
                {"id": "c", "name": "Synthetic C", "logkw": 3, "s": 5},
            ],
            "gradient": [
                {"time_min": 0, "b_percent": 5},
                {"time_min": 10, "b_percent": 95},
                {"time_min": 15, "b_percent": 95},
            ],
        }
    )
    map_demo = json.loads(
        (ROOT / "review/phase2/map-demo.json").read_text(encoding="utf-8")
    )
    result = optimize_multisegment(
        OptimizeMultiSegment(
            simulation=simulation,
            segments=2,
            min_segment_min=0.5,
            initial_candidate=map_demo["top_candidates"][0]["gradient"],
        )
    )
    nodes = result["gradient"]
    result["min_segment_min"] = 0.5
    result["segment_durations_min"] = [
        right["time_min"] - left["time_min"]
        for left, right in zip(nodes[:2], nodes[1:3])
    ]
    destination = ROOT / "review/phase2.1/multisegment-demo.json"
    destination.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
