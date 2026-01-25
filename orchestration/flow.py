import argparse
import subprocess
from pathlib import Path

from prefect import flow, task

REPO_ROOT = Path(__file__).resolve().parents[1]
DBT_DIR = REPO_ROOT / "dbt"


def run_command(command: str, cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, shell=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {command}")


@task
def generate_events(endpoint: str, seed: int, count: int) -> None:
    script = REPO_ROOT / "scripts" / "generate_events.py"
    cmd = f"python {script} --endpoint {endpoint} --seed {seed} --count {count}"
    run_command(cmd, REPO_ROOT)


@task
def dbt_run() -> None:
    run_command("dbt run", DBT_DIR)


@task
def dbt_test() -> None:
    run_command("dbt test", DBT_DIR)


@flow(name="wearable_pipeline")
def pipeline_flow(
    endpoint: str,
    seed: int,
    count: int,
    skip_seed: bool,
    skip_test: bool
) -> None:
    if not skip_seed:
        generate_events(endpoint, seed, count)
    dbt_run()
    if not skip_test:
        dbt_test()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run wearable pipeline flow.")
    parser.add_argument("--endpoint", default="http://localhost:8000/events")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--skip-seed", action="store_true")
    parser.add_argument("--skip-test", action="store_true")
    args = parser.parse_args()

    pipeline_flow(
        endpoint=args.endpoint,
        seed=args.seed,
        count=args.count,
        skip_seed=args.skip_seed,
        skip_test=args.skip_test
    )
