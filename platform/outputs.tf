output "next_steps" {
  value = <<-EOT
    Argo CD admin password:
      kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"   (value is base64)
    Argo CD UI:   kubectl -n argocd port-forward svc/argocd-server 8081:443   then https://localhost:8081
    Grafana UI:   kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80   then http://localhost:3000
  EOT
}
