# Architecture

## The path of a change (from code to users)

```
 developer
    | 1. git push / pull request
    v
 GitHub Actions  (ci.yml)
    |  test -> validate config -> secret scan -> build image -> scan image (Trivy)
    |  2. push image to ghcr.io  (tag: sha-<commit>)
    |  3. commit the new tag into deploy/overlays/dev      <-- the only thing CI "deploys"
    v
 Git repository (main)  = the desired state of the cluster
    ^
    | 4. Argo CD watches Git and compares it with the cluster
    v
 Kubernetes cluster
    |  dev:  syncs automatically
    |  prod: a person reviews and presses Sync
    v
 users  -->  ingress-nginx  -->  Service  -->  api pods  -->  PostgreSQL
```

CI never has credentials for the cluster. The cluster pulls its own state from Git.
That is the main idea of GitOps, and it is why a rollback is simply a `git revert`.

## Components

| Layer | Tool | Where |
|---|---|---|
| Application | Flask API, PostgreSQL | `app/` |
| Local run | Docker Compose | `docker-compose.yml` |
| Cluster (local) | kind | `kind/kind-config.yaml` |
| Cluster add-ons | Terraform + Helm: ingress-nginx, Argo CD, Prometheus, Grafana | `platform/` |
| App deployment | Kustomize base + dev/prod overlays | `deploy/` |
| Continuous delivery | Argo CD Applications | `argocd/` |
| CI | GitHub Actions | `.github/workflows/ci.yml` |
| Server configuration | Ansible | `ansible/` |
| Metrics and alerts | Prometheus rules, Grafana dashboard | `observability/`, `deploy/monitoring/` |
| Logs | Loki + Alloy (Compose only) | `observability/` |

## Environments

| | dev | prod |
|---|---|---|
| Namespace | `platform-dev` | `platform-prod` |
| URL | http://dev.localtest.me | http://prod.localtest.me |
| Replicas (HPA) | 1 to 2 | 3 to 10 |
| Deploy | automatic when the CI commit lands | manual Sync in Argo CD |
| Image tag | updated by CI | promoted by a pull request that edits `deploy/overlays/prod/kustomization.yaml` |
| `/debug/error` | on | off |

## Observability

- Metrics: the app exposes `/metrics`; Prometheus scrapes it (a `ServiceMonitor` in Kubernetes).
- Alerts: `ApiDown`, `HighErrorRate`, `HighLatency` (each links to the runbook).
- Logs: one JSON line per request, so they can be searched by field.
- The four golden signals: latency, traffic, errors, saturation.

## Security measures in the design

- Containers run as a non-root user, with a read-only filesystem and all Linux capabilities dropped.
- Secrets are never in Git: Kubernetes Secrets are created by hand (production: Sealed Secrets or External Secrets).
- Images and secrets are scanned in CI (Trivy, Gitleaks).
- NetworkPolicies allow only the needed traffic (if the cluster network plugin enforces them).
- `/metrics` is blocked at the public proxy in Compose.
