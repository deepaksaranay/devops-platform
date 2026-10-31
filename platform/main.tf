# Installs the platform components into an existing cluster:
#   ingress-nginx  - receives HTTP traffic and routes it by host name
#   argo-cd        - deploys what is in Git (GitOps)
#   kube-prometheus-stack - Prometheus, Grafana and the Prometheus operator
#
# Chart versions are pinned on purpose. If Helm says a version does not exist, run
#   helm search repo <chart> --versions
# and pick a current one.

resource "helm_release" "ingress_nginx" {
  name             = "ingress-nginx"
  namespace        = "ingress-nginx"
  create_namespace = true
  repository       = "https://kubernetes.github.io/ingress-nginx"
  chart            = "ingress-nginx"
  version          = "4.11.3"
  wait             = true
  timeout          = 600

  # Settings for a kind cluster: run on the node that has ports 80 and 443 mapped to the laptop.
  values = [yamlencode({
    controller = {
      hostPort     = { enabled = true }
      service      = { type = "NodePort" }
      nodeSelector = { "ingress-ready" = "true" }
      tolerations = [{
        key      = "node-role.kubernetes.io/control-plane"
        operator = "Equal"
        effect   = "NoSchedule"
      }]
    }
  })]
}

resource "helm_release" "argocd" {
  name             = "argocd"
  namespace        = "argocd"
  create_namespace = true
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = "7.6.12"
  wait             = true
  timeout          = 600
}

resource "helm_release" "monitoring" {
  count            = var.enable_monitoring_stack ? 1 : 0
  name             = "monitoring"
  namespace        = "monitoring"
  create_namespace = true
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  version          = "62.7.0"
  wait             = true
  timeout          = 900

  values = [yamlencode({
    # Let Prometheus pick up ServiceMonitors and rules from any namespace and label.
    prometheus = {
      prometheusSpec = {
        serviceMonitorSelectorNilUsesHelmValues = false
        podMonitorSelectorNilUsesHelmValues     = false
        ruleSelectorNilUsesHelmValues           = false
        retention                               = "2d"
      }
    }
    # Saves memory on a laptop. Real setups route alerts through Alertmanager.
    alertmanager = { enabled = false }
  })]

  set_sensitive {
    name  = "grafana.adminPassword"
    value = var.grafana_admin_password
  }
}
