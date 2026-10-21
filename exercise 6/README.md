# Exercise 6: Real-Time Operations Monitoring and Alerting

> The named source document, `6-Grafana-Realtime-Monitoring-of-Quick-Commerce-App.md`, was not present in the repository or workspace when this was prepared. This implementation follows the requirements supplied in the task; compare with the original handout if it becomes available.

## What is included

- `delivery_metrics.py`: Python metrics exporter on port 8000, updating delivery gauges and a delivery-duration Summary once per second.
- `Dockerfile` and `requirements.txt`: container image and `prometheus-client` dependency.
- `prometheus.yml` and `alert_rules.yml`: Prometheus self-scrape, delivery exporter scrape, and the two required alerts.
- `dashboard.json`: importable Grafana dashboard with four Prometheus panels.
- `Jenkinsfile`: isolated Docker build and monitoring-stack smoke test, followed by cleanup.

## Windows Docker Desktop: build and run

Prerequisites: Docker Desktop using Linux containers, Python 3.10+ if running local validation, and PowerShell. Run the following in one PowerShell session from the repository root so the variables remain available:

```powershell
$project = (Resolve-Path '.\Ex 6').Path
$stack = 'ex6-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$network = "$stack-network"
$metrics = "$stack-metrics"
$prometheus = "$stack-prometheus"
$grafana = "$stack-grafana"
$image = 'ex6-delivery-metrics:local'

$venv = Join-Path $env:TEMP 'ex6-monitoring-venv'
python -m venv $venv
& "$venv\Scripts\python.exe" -m pip install -r "$project\requirements.txt"
& "$venv\Scripts\python.exe" -m py_compile "$project\delivery_metrics.py"
docker build --tag $image $project
docker network create $network

docker run --detach --name $metrics --network $network --network-alias delivery-metrics `
  --publish 8000:8000 $image

docker run --detach --name $prometheus --network $network --network-alias prometheus `
  --publish 9090:9090 `
  --mount "type=bind,source=$project\prometheus.yml,target=/etc/prometheus/prometheus.yml,readonly" `
  --mount "type=bind,source=$project\alert_rules.yml,target=/etc/prometheus/alert_rules.yml,readonly" `
  prom/prometheus:v3.5.0 --config.file=/etc/prometheus/prometheus.yml

docker run --detach --name $grafana --network $network --network-alias grafana `
  --publish 3000:3000 grafana/grafana:12.1.0
```

The containers communicate on a user-defined Docker bridge network. Prometheus scrapes `delivery-metrics:8000`; Grafana reaches Prometheus at `http://prometheus:9090`. These are container DNS names, not `localhost`, a Linux bridge IP, or host networking, so the arrangement works with Docker Desktop's Linux VM. Host ports are published only for browser access. If ports 8000, 9090, or 3000 are already occupied, change only the left-hand/host side of the corresponding `--publish` mapping.

Check the exporter from Windows:

```powershell
Invoke-RestMethod http://localhost:8000/metrics | Select-String 'total_deliveries|pending_deliveries|on_the_way_deliveries|average_delivery_time'
```

Prometheus UI: <http://localhost:9090>. Open **Status > Targets** and confirm both `prometheus` and `delivery_service` are `UP`. Query `total_deliveries` in the expression browser.

## Grafana setup

Open <http://localhost:3000> and complete the initial admin account setup. Do not commit credentials or place them in this repository. Add a Prometheus data source with URL **`http://prometheus:9090`** (the Grafana container must use the Prometheus container DNS alias); select **Save & test**.

Import `Ex 6/dashboard.json` using **Dashboards > New > Import**, then select the Prometheus data source when prompted. The dashboard includes total, pending, on-the-way, and mean delivery-time panels. The Summary average uses the same expression as the critical alert:

```promql
rate(average_delivery_time_sum[1m]) / rate(average_delivery_time_count[1m])
```

Prometheus client `Summary` metrics expose `_sum` and `_count` time series, not an `average_delivery_time` sample. The ratio of their rates is the observed mean in seconds, and is used consistently by Prometheus rules and Grafana.

## Alerts and verification

`HighPendingDeliveries` fires with `warning` severity when `pending_deliveries > 10` remains true for 15 seconds. `HighAverageDeliveryTime` fires with `critical` severity when the one-minute mean exceeds 30 seconds. In Prometheus, open **Alerts** to see pending/firing state; the query expressions can also be run in the expression browser.

The default simulator uses changing normal-range values, so either alert may not fire on demand. To test both rules, stop and replace only the metrics container with a persistent test mode (use the `$network`, `$metrics`, `$image` variables from the run block):

```powershell
docker rm --force $metrics
docker run --detach --name $metrics --network $network --network-alias delivery-metrics `
  --publish 8000:8000 --env SIMULATION_MODE=high_all $image
```

Wait about 30 seconds, refresh **Alerts**, and confirm both alerts fire. `high_pending` holds pending count at 12; `high_delivery_time` records only durations over 30 seconds; `high_all` does both. These are test modes, not production traffic. Restore the default by replacing the container again without `--env SIMULATION_MODE=...`.

## Linux commands

From the repository root, the same Docker network and container-name approach works on Linux; bind-mount source paths are resolved on the Docker host:

```sh
project="$(pwd)/Ex 6"
stack="ex6-monitoring"
network="${stack}-network"
metrics="${stack}-metrics"
prometheus="${stack}-prometheus"
grafana="${stack}-grafana"
image="ex6-delivery-metrics:local"

docker build -t ex6-delivery-metrics:local "$project"
docker network create "$network"
docker run -d --name "$metrics" --network "$network" \
  --network-alias delivery-metrics -p 8000:8000 "$image"
docker run -d --name "$prometheus" --network "$network" \
  --network-alias prometheus -p 9090:9090 \
  --mount "type=bind,src=$project/prometheus.yml,dst=/etc/prometheus/prometheus.yml,readonly" \
  --mount "type=bind,src=$project/alert_rules.yml,dst=/etc/prometheus/alert_rules.yml,readonly" \
  prom/prometheus:v3.5.0 --config.file=/etc/prometheus/prometheus.yml
docker run -d --name "$grafana" --network "$network" \
  --network-alias grafana -p 3000:3000 grafana/grafana:12.1.0
```

If using a fixed stack name a second time, remove its old containers and network first. Do not use host networking. The bind mounts use Linux paths on a Linux host; the Prometheus config and rule-file target paths remain identical to the Windows instructions.

## Jenkins pipeline

Create a Pipeline job pointed at the feature branch and use the repository's `Jenkinsfile`. Configure an agent with the label `linux-docker`, Python 3.10+, a POSIX shell, and Docker CLI access to a running Docker Engine. The pipeline validates Python syntax, builds the image from the checked-out `Ex 6` directory, starts the exporter, Prometheus, and Grafana on a per-job/per-build bridge network, checks the metrics endpoint, Prometheus target, and Grafana health endpoint, then removes its containers, network, and uniquely tagged image in `post { always { ... } }`.

The agent must have permission to use its Docker Engine/socket. Prefer a dedicated, access-controlled Docker-capable agent or a remote Docker endpoint with narrowly scoped access. Membership in the Docker group and access to `/var/run/docker.sock` are effectively host-administrator privileges; mounting the host socket into a Jenkins controller, running privileged, or changing the socket to world-writable are not safe general fixes. If Jenkins itself runs in a container, provision a separate controlled agent and explicitly assess the host access granted by any socket mount. The smoke-test containers are isolated and cleaned up; they are not intended to remain running after the build.

## Cleanup

In the PowerShell session used to start the local stack:

```powershell
docker rm --force $grafana $prometheus $metrics
docker network rm $network
docker image rm $image
```

If the original session is gone, list the relevant containers and networks first with `docker ps -a` and `docker network ls`, then remove only the names created for this stack. Do not run broad prune commands. In Linux, use `docker rm -f <grafana-container> <prometheus-container> <metrics-container>`, `docker network rm <stack-network>`, and optionally `docker image rm ex6-delivery-metrics:local`.

## Troubleshooting

- Docker build/run cannot connect to the daemon: start Docker Desktop and ensure it is using Linux containers; check `docker version` and `docker info`.
- Prometheus `delivery_service` is down: check `docker logs $metrics`, confirm both containers share `$network`, and ensure the metrics alias is `delivery-metrics` and the exporter listens on `0.0.0.0:8000`.
- Prometheus says the rule file is missing: the configuration references `/etc/prometheus/alert_rules.yml`; mount `alert_rules.yml` to that exact path.
- Grafana data source test fails: use `http://prometheus:9090` from Grafana, and verify the Prometheus container has the `prometheus` network alias on the shared network.
- Dashboard average is empty immediately after startup: wait for multiple scrapes and enough Summary observations for the one-minute rate window.
- Port bind fails: another process/container owns the host port; pick another host port while preserving the container port after the colon.
- Jenkins cannot run Docker: check the agent label, Docker Engine availability, and the agent's authorized socket/endpoint permissions; do not weaken host socket permissions.

## Submission screenshots

Capture screenshots that show: the `/metrics` endpoint with the four metric families; Prometheus **Status > Targets** with both jobs `UP`; Prometheus **Alerts** showing the two firing alerts in `high_all` mode and their severities; Grafana's successful Prometheus data-source test; the imported dashboard with all four panels populated; and a successful Jenkins build showing validation, service checks, and cleanup. Avoid exposing credentials, tokens, or unrelated desktop content.
