import logging
import os
import random
import time

from prometheus_client import Gauge, Summary, start_http_server


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

total_deliveries = Gauge(
    "total_deliveries", "Current total of completed and active deliveries"
)
pending_deliveries = Gauge(
    "pending_deliveries", "Number of deliveries waiting for a courier"
)
on_the_way_deliveries = Gauge(
    "on_the_way_deliveries", "Number of deliveries currently with a courier"
)
average_delivery_time = Summary(
    "average_delivery_time", "Observed delivery duration in seconds"
)

SIMULATION_MODES = {"normal", "high_pending", "high_delivery_time", "high_all"}


def simulated_values(mode: str, completed: int) -> tuple[int, int, int, float]:
    if mode not in SIMULATION_MODES:
        raise ValueError(
            f"SIMULATION_MODE must be one of {sorted(SIMULATION_MODES)}, got {mode!r}"
        )

    if mode in {"high_pending", "high_all"}:
        pending = 12
    else:
        pending = random.randint(0, 10)

    on_the_way = random.randint(1, 12)
    completed += random.randint(0, 2)

    if mode in {"high_delivery_time", "high_all"}:
        delivery_time = random.uniform(35, 45)
    else:
        delivery_time = random.uniform(15, 28)

    return completed + pending + on_the_way, pending, on_the_way, delivery_time


def main() -> None:
    mode = os.getenv("SIMULATION_MODE", "normal").strip().lower()
    if mode not in SIMULATION_MODES:
        raise ValueError(
            f"SIMULATION_MODE must be one of {sorted(SIMULATION_MODES)}, got {mode!r}"
        )

    start_http_server(8000, addr="0.0.0.0")
    logging.info("Prometheus metrics available on 0.0.0.0:8000/metrics (mode=%s)", mode)

    completed = 0
    while True:
        total, pending, on_the_way, delivery_time = simulated_values(mode, completed)
        completed = total - pending - on_the_way

        total_deliveries.set(total)
        pending_deliveries.set(pending)
        on_the_way_deliveries.set(on_the_way)
        average_delivery_time.observe(delivery_time)

        logging.info(
            "total=%d pending=%d on_the_way=%d delivery_time_seconds=%.2f",
            total,
            pending,
            on_the_way,
            delivery_time,
        )
        time.sleep(1)


if __name__ == "__main__":
    main()
