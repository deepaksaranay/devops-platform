variable "kubeconfig_path" {
  description = "Path to your kubeconfig file."
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "kubectl context of the cluster (kind names it kind-<cluster name>)."
  type        = string
  default     = "kind-devops-platform"
}

variable "enable_monitoring_stack" {
  description = "Install kube-prometheus-stack (Prometheus and Grafana). Needs about 2 GB of RAM."
  type        = bool
  default     = true
}

variable "grafana_admin_password" {
  description = "Admin password for Grafana. Pass it with -var or TF_VAR_grafana_admin_password."
  type        = string
  sensitive   = true
}
