variable "create_session_document" {
  type        = bool
  default     = false
  description = "Create-only opt-in after #35 confirms the regional account document is absent and accepts ownership in vpn state. Never auto-import or overwrite."
}
variable "document_absence_readback_reference" {
  type        = string
  default     = ""
  description = "Latest actual absence/owner review reference; not ABSENT_OR_UNAVAILABLE or AccessDenied."
}
locals {
  session_preferences_content = jsonencode({
    schemaVersion = "1.0"
    description   = "Phase 2 adopted regional session preferences; #35 owns source and readback"
    sessionType   = "Standard_Stream"
    inputs = {
      s3BucketName               = ""
      s3KeyPrefix                = ""
      cloudWatchLogGroupName     = ""
      cloudWatchStreamingEnabled = false
      kmsKeyId                   = ""
      runAsEnabled               = false
    }
  })
}
resource "aws_ssm_document" "session_preferences" {
  count           = var.create_session_document ? 1 : 0
  name            = "SSM-SessionManagerRunShell"
  document_type   = "Session"
  document_format = "JSON"
  content         = local.session_preferences_content
  lifecycle {
    prevent_destroy = true
    precondition {
      condition     = var.execution_enabled && terraform.workspace == "default" && length(trimspace(var.document_absence_readback_reference)) > 0
      error_message = "Create only after actual absence and #35 account-wide ownership review. Historical unavailable results are insufficient."
    }
  }
}
output "session_document_source" {
  value = {
    name                                          = "SSM-SessionManagerRunShell"
    content_sha256                                = sha256(local.session_preferences_content)
    managed_here                                  = var.create_session_document
    actual_owner_default_version_content_readback = "NOT_VERIFIED"
  }
}
