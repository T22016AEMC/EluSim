"""Export synthetic phase-two calculations for user inspection."""

import csv
import json
from pathlib import Path

from elusim.optimizer import optimize_map, optimize_multisegment
from elusim.schemas import OptimizeMap, OptimizeMultiSegment, Simulation


def main():
    """Write demo calculations without interpreting the returned numbers."""
    destination = Path("review/phase2")
    destination.mkdir(parents=True, exist_ok=True)
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
    result = optimize_map(OptimizeMap(simulation=simulation))
    (destination / "map-demo.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf8"
    )
    with (destination / "map-demo.csv").open(
        "w", newline="", encoding="utf8"
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "start",
                "end",
                "time",
                "min_rs",
                "run_time",
                "all_eluted",
                "critical_pair",
            ]
        )
        for start_index, start in enumerate(result["axes"]["start_percent"]):
            for end_index, end in enumerate(result["axes"]["end_percent"]):
                for time_index, duration in enumerate(
                    result["axes"]["gradient_time_min"]
                ):
                    pair = result["critical_pair"][start_index][end_index][time_index]
                    writer.writerow(
                        [
                            start,
                            end,
                            duration,
                            result["min_rs"][start_index][end_index][time_index],
                            result["run_time"][start_index][end_index][time_index],
                            result["all_eluted"][start_index][end_index][time_index],
                            "|".join(pair) if pair else "",
                        ]
                    )
    multi = optimize_multisegment(
        OptimizeMultiSegment(
            simulation=simulation,
            segments=2,
            initial_candidate=result["top_candidates"][0]["gradient"],
        )
    )
    (destination / "multisegment-demo.json").write_text(
        json.dumps(multi, ensure_ascii=False, indent=2), encoding="utf8"
    )


if __name__ == "__main__":
    main()
