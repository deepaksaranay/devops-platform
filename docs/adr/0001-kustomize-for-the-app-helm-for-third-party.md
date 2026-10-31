# 1. Kustomize for our app, Helm for third-party software

**Status:** accepted

**Context:** We need to deploy our own app to two environments, and install well-known software
(ingress-nginx, Argo CD, Prometheus) that other people maintain.

**Decision:** Our app uses plain YAML with Kustomize overlays. Third-party software is installed with
its official Helm charts, through Terraform.

**Consequences:** The app manifests stay readable and diffs are small. Overlays show exactly what differs
between dev and prod. We depend on chart authors for the add-ons and must pin and update their versions.
