# Runbook

What to do when an alert fires. Start with: **what changed recently?** (a deploy, a config change, traffic)

Useful first commands (Kubernetes):
```powershell
kubectl get pods -n platform-dev
kubectl describe pod -n platform-dev <pod>
kubectl logs -n platform-dev deploy/api --tail 50
kubectl rollout history deployment/api -n platform-dev
```

## ApiDown
**Meaning:** Prometheus cannot reach an API pod for over a minute.

1. `kubectl get pods -n <namespace>`: is the pod `Running`? `CrashLoopBackOff`? `Pending`?
2. `CrashLoopBackOff`: `kubectl logs <pod> --previous`. Usual causes: bad config, missing Secret, database unreachable.
3. `ImagePullBackOff`: wrong image tag, or the GHCR package is private.
4. `Pending`: `kubectl describe pod`: not enough CPU/memory on the node.
5. If it started right after a deploy: roll back by reverting the commit that changed the image tag. Argo CD applies the old version.

## HighErrorRate
**Meaning:** more than 5% of requests return 5xx.

1. Look at the logs: `kubectl logs deploy/api --tail 100`. The JSON lines show `status` and `path`.
2. Is the database reachable? `kubectl get pods` for `postgres`; call `/ready`.
3. One endpoint or all? Check the Grafana panel "Requests per second (by endpoint)".
4. If it began with a deploy: revert it.

## HighLatency
**Meaning:** the slowest 5% of requests take over 500 ms.

1. Is CPU high? `kubectl top pods` (needs metrics-server). Is the HPA already scaling? `kubectl get hpa`.
2. Is the database slow or full? Check `postgres` pod resources and logs.
3. A traffic spike? Compare the request rate with normal.
4. Short-term fix: raise `maxReplicas` in the overlay through Git. Long-term: find the slow query or code path.

## After an incident
Write a short blameless note: timeline, impact, cause, what fixed it, what prevents it next time.
