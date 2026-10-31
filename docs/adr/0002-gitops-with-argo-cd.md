# 2. Deploy with GitOps (Argo CD)

**Status:** accepted

**Context:** A pipeline that runs `kubectl apply` needs cluster credentials stored in CI, and the cluster
can drift from what is in Git without anyone noticing.

**Decision:** CI builds and publishes the image, then commits the new tag to Git. Argo CD, running inside the
cluster, pulls the desired state from Git and applies it. Dev syncs automatically; prod needs a manual Sync.

**Consequences:** CI holds no cluster credentials. Every change is a reviewed commit, and a rollback is a
revert. The price is one more component to run, and a pipeline that is harder to follow at first.
