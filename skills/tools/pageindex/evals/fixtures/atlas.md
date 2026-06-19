# Project Atlas

Atlas is a distributed cache layer maintained by the platform team. It sits
between application services and the primary datastore, absorbing read traffic.

## Architecture

The system is split into a coordinator and a fleet of worker nodes that
communicate over gRPC.

### Coordinator

The coordinator handles shard assignment and health checks. It uses a Raft group
for leader election and persists assignments to etcd so a new leader can recover
state after a failover.

### Workers

Workers store cache entries in memory with an LRU eviction policy. Each worker
reports load metrics to the coordinator every five seconds and is removed from
the ring if three consecutive heartbeats are missed.

## Operations

Day-to-day runbooks live in the ops wiki; this section covers the essentials.

### Deployment

Deploys go out via the standard CI pipeline. A canary worker takes 5% of traffic
for ten minutes before a full rollout, and an automated check rolls back if error
rate climbs.

### Monitoring

Grafana dashboards track hit rate, eviction rate, and p99 latency. Alerts page
the on-call engineer when hit rate drops below 80 percent for five minutes.

## FAQ

Common questions from new team members about Atlas, how to request access, and
where to find the design docs.
