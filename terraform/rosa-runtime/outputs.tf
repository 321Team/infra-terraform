output "rosa_runtime_handoff" {
  description = "Non-secret identity for infra-rosa#4 Ready readback, #5-#8 and #12. Not a Ready, Basic Ready or Security result."
  value = {
    cluster_id      = rhcs_cluster_rosa_hcp.this.id
    cluster_name    = rhcs_cluster_rosa_hcp.this.name
    state           = rhcs_cluster_rosa_hcp.this.state
    current_version = rhcs_cluster_rosa_hcp.this.current_version
    api_url         = rhcs_cluster_rosa_hcp.this.api_url
    console_url     = rhcs_cluster_rosa_hcp.this.console_url
    domain          = rhcs_cluster_rosa_hcp.this.domain
    private         = rhcs_cluster_rosa_hcp.this.private
    subnet_ids      = rhcs_cluster_rosa_hcp.this.aws_subnet_ids
    machine_pool = {
      id            = rhcs_hcp_machine_pool.workers.id
      name          = rhcs_hcp_machine_pool.workers.name
      replicas      = rhcs_hcp_machine_pool.workers.replicas
      instance_type = rhcs_hcp_machine_pool.workers.aws_node_pool.instance_type
      subnet_id     = rhcs_hcp_machine_pool.workers.subnet_id
    }
    registry_trust_keys = local.registry_additional_trusted_ca == null ? [] : sort(keys(local.registry_additional_trusted_ca))
  }
}
