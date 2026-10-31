# 3. Run everything locally with kind

**Status:** accepted

**Context:** The goal is to learn the platform, not to pay for cloud resources. Managed Kubernetes
(for example Amazon EKS) has a fixed hourly cost even when idle.

**Decision:** The cluster is a local kind cluster. The same manifests and Terraform modules for add-ons work on
a managed cluster once the kubeconfig context points to it.

**Consequences:** It is free and quick to rebuild. Differences from a real cluster remain: no cloud load
balancer, default networking may not enforce NetworkPolicies, and one machine means no real high availability.
