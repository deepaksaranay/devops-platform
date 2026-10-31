# DevOps Platform: one app, the whole delivery chain

A small API (Flask + PostgreSQL) used to practice **everything a DevOps engineer touches**:
containers, CI/CD, GitOps, Kubernetes, infrastructure as code, configuration management,
monitoring, logging and security checks. It all runs on your laptop for free.

```
code -> GitHub Actions (test, scan, build) -> image in ghcr.io
                                   |
                  commit new tag into Git (deploy/overlays/dev)
                                   |
          Argo CD sees the change -> Kubernetes (kind) -> ingress -> API -> PostgreSQL
                                                              |
                                          Prometheus + Grafana (+ Loki logs)
```
More detail: [docs/architecture.md](docs/architecture.md). Incident steps: [docs/runbook.md](docs/runbook.md).
Design decisions: [docs/adr](docs/adr).

## Skills this covers
| Topic | Where |
|---|---|
| Docker, Compose, healthchecks, non-root image | `app/Dockerfile`, `docker-compose.yml` |
| CI: test, lint, config validation, secret scan, image scan | `.github/workflows/ci.yml` |
| Container registry (ghcr.io) | `ci.yml` build job |
| GitOps with Argo CD | `argocd/`, `gitops-bump` job |
| Kubernetes: probes, HPA, PDB, NetworkPolicy, Ingress, hardening | `deploy/base/` |
| Environments with Kustomize overlays | `deploy/overlays/` |
| Terraform + Helm to bootstrap a cluster | `platform/` |
| Ansible: roles, templates, handlers, vault | `ansible/` |
| Metrics, alerts, dashboards | `observability/`, `deploy/monitoring/` |
| Structured logs with Loki | `observability/` |
| Dependency updates, pre-commit hooks | `.github/dependabot.yml`, `.pre-commit-config.yaml` |
| Runbooks and decision records | `docs/` |

## Verification status (read this)
Checked while building this repo: the API unit tests (12), flake8, `yamllint` on every YAML file,
`kubectl kustomize` renders for dev, prod and monitoring, `terraform validate`, `ansible-playbook --syntax-check`
and `ansible-lint`, and the logic that updates the image tag.
**Not run end to end:** Docker images, Compose, the Kubernetes cluster, Helm installs, Argo CD, Loki/Alloy,
and the GitHub Actions run. You will run those, and the first run may need small fixes. That is normal and
a good way to learn. Chart and image versions are pinned to known releases; bump them if one is not found.

## Part 0 - setup
```powershell
winget install -e --id Docker.DockerDesktop
winget install -e --id Kubernetes.kind
winget install -e --id Kubernetes.kubectl
winget install -e --id Helm.Helm
winget install -e --id Hashicorp.Terraform
```
Close and reopen PowerShell. Start Docker Desktop.

Replace the placeholder user name in the files that mention your GitHub account:
```powershell
Get-ChildItem deploy,argocd,ansible -Recurse -File -Include *.yaml,*.yml |
  ForEach-Object { (Get-Content $_.FullName) -replace 'YOUR-USER','deepaksaranay' | Set-Content $_.FullName }
git add . ; git commit -m "Set GitHub user name" ; git push
```
(Use your own GitHub user name instead of `deepaksaranay` if it is different.)

## Part 1 - run it with Docker Compose
```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
Invoke-RestMethod http://localhost:8080/health
Invoke-RestMethod -Method Post -Uri http://localhost:8080/items -ContentType "application/json" -Body '{"name":"laptop"}'
Invoke-RestMethod http://localhost:8080/items
```
Add metrics, then logs:
```powershell
docker compose --profile metrics up --build -d       # Prometheus :9090, Grafana :3000 (admin/admin)
docker compose --profile metrics --profile logs up -d # + Loki and Alloy
```
In Grafana open **Platform API**. Make traffic and trigger an error:
```powershell
1..200 | ForEach-Object { Invoke-RestMethod http://localhost:8080/items | Out-Null }
1..40  | ForEach-Object { try { Invoke-RestMethod http://localhost:8080/debug/error | Out-Null } catch {} }
```
Stop: `docker compose down` (add `-v` to delete the database volume too).

## Part 2 - Kubernetes with GitOps
**1. Cluster and image**
```powershell
kind create cluster --config kind\kind-config.yaml
docker build -t ghcr.io/deepaksaranay/devops-platform-api:local app
kind load docker-image ghcr.io/deepaksaranay/devops-platform-api:local --name devops-platform
```
Ports 80 and 443 on your PC must be free.

**2. Install ingress-nginx, Argo CD and Prometheus/Grafana with Terraform**
```powershell
cd platform
$env:TF_VAR_grafana_admin_password = "choose-a-password"
terraform init
terraform plan
terraform apply
cd ..
```
No RAM to spare? Add `-var enable_monitoring_stack=false`.

**3. Create the database secret (never stored in Git)**
```powershell
kubectl create namespace platform-dev
kubectl create secret generic postgres-credentials -n platform-dev --from-literal=POSTGRES_USER=app --from-literal=POSTGRES_PASSWORD=change-me
```

**4. Tell Argo CD to watch your repository** (the repository must be public and pushed)
```powershell
kubectl apply -f argocd\app-dev.yaml
kubectl apply -f argocd\app-monitoring.yaml
kubectl get applications -n argocd
```

**5. Use it**
```powershell
Invoke-RestMethod http://dev.localtest.me/health
Invoke-RestMethod http://dev.localtest.me/version
kubectl get pods -n platform-dev
```
Argo CD UI: `kubectl -n argocd port-forward svc/argocd-server 8081:443`, open https://localhost:8081, user `admin`,
password from:
```powershell
$p = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($p))
```
Grafana: `kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80`.

**6. Production**: the same, but a person presses Sync.
```powershell
kubectl create namespace platform-prod
kubectl create secret generic postgres-credentials -n platform-prod --from-literal=POSTGRES_USER=app --from-literal=POSTGRES_PASSWORD=change-me
kubectl apply -f argocd\app-prod.yaml
```
Then open the `platform-prod` application in the Argo CD UI and press **Sync**.

## Part 3 - the CI/CD loop
1. Push this repository to GitHub. The `ci` workflow runs.
2. After a change is merged to `main`, CI builds `ghcr.io/<you>/devops-platform-api:sha-<commit>`,
   scans it, pushes it, and commits the new tag into `deploy/overlays/dev/kustomization.yaml`.
3. Argo CD notices the commit and rolls out the new version. Check `Invoke-RestMethod http://dev.localtest.me/version`.
4. **Make the package public** (GitHub profile -> Packages -> devops-platform-api -> Package settings),
   otherwise the cluster cannot pull the image.
5. **Promote to prod**: open a pull request that copies the tested tag into `deploy/overlays/prod/kustomization.yaml`,
   merge it, then press Sync on `platform-prod`.
6. **Roll back**: `git revert` the commit that changed the tag.

If branch protection blocks the bot's commit to `main`, allow GitHub Actions to bypass it or switch the
`gitops-bump` job to open a pull request.

## Part 4 - Ansible (configure a server)
Run inside WSL/Ubuntu, or against a real Linux server.
```bash
sudo apt install -y ansible
cd ansible
cp group_vars/all/vault.yml.example group_vars/all/vault.yml
nano group_vars/all/vault.yml                      # set the password
ansible-vault encrypt group_vars/all/vault.yml
ansible-playbook site.yml --ask-vault-pass --ask-become-pass --check   # dry run first
ansible-playbook site.yml --ask-vault-pass --ask-become-pass
```
Run it twice: the second run should report `changed=0` (idempotence).

## Experiments
- Delete an API pod and watch Kubernetes replace it. Scale to 4. Break the image tag and read `ImagePullBackOff`.
- Change `maxReplicas` in `deploy/overlays/dev/kustomization.yaml`, push, and watch Argo CD apply it.
- Edit a deployed resource by hand (`kubectl scale deploy api --replicas=5 -n platform-dev`) and watch Argo CD undo it (self-heal).
- Fire the alerts: call `/debug/error` many times (dev only) and watch **HighErrorRate**; follow the runbook.
- Add a failing test, open a pull request, and watch CI stop it.
- Put a fake key in a file and see Gitleaks catch it (use a clearly fake value, then remove it).

## Clean up
```powershell
kind delete cluster --name devops-platform
docker compose down -v
```

## Known limitations
- One database pod without backups; production uses a managed database.
- Secrets are created by hand. Production uses Sealed Secrets or External Secrets.
- The default kind networking may not enforce NetworkPolicies.
- No TLS on the local ingress; production uses cert-manager.
- Alertmanager is off in the cluster to save memory, so alerts show in Prometheus but are not sent anywhere.
- Loki and Alloy are only wired into Compose.
- A single `main` branch and one cluster; real teams separate accounts/clusters per environment.

## Interview questions this prepares you for
- Explain the path of a commit from laptop to users. Where does CI stop and CD start?
- Push-based vs pull-based deployment. Why GitOps? How do you roll back?
- Liveness vs readiness probe. Requests vs limits. What do HPA and PDB each do?
- Why is the database password not in Git, and what would you use in production?
- What is idempotence in Ansible, and how did you check it?
- Which signals would you alert on, and what should an alert contain? (Link to a runbook.)
