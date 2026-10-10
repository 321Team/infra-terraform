# rosa-prereq — ROSA HCP 계정 준비 A3 (infra-terraform#12)

상태: **LOCAL CANDIDATE / Plan·Apply 승인 없음**. `execution_enabled=false`가 기본값이라 실제 생성 계획이 만들어지지 않는다.

## 이 코드가 만드는 것

| 단계 | 자원 | 개수 | 이름 / 값 |
|---|---|---|---|
| 1 | account role | 3 | `fds-rosa-HCP-ROSA-Installer-Role`, `-Support-Role`, `-Worker-Role` |
| 1 | account role 정책 부착 | 4 | `service-role/ROSAInstallerPolicy`, `ROSASRESupportPolicy`, `ROSAWorkerInstancePolicy`, `AmazonEC2ContainerRegistryReadOnly` |
| 1 | managed OIDC config (Red Hat 쪽) | 1 | `rhcs_rosa_oidc_config` `managed=true` — S3·Secrets Manager 없음 |
| 1 | IAM OIDC provider | 1 | `oidc.op1.openshiftapps.com/<config id>`, audience `openshift`·`sts.amazonaws.com` |
| 2 | operator role + ROSA 정책 | 8 + 8 | `fds-rosa-openshift-*`, `fds-rosa-kube-system-*` (`create_operator_roles=true`일 때만) |

**만들지 않는 것:** `ocm-role`·`user-role`(ROSA CLI 담당), 클러스터(infra-rosa#4), 네트워크(#35 network).

account role 이름·trust·부착 정책은 ROSA CLI 1.2.53 `create account-roles --hosted-cp --prefix fds-rosa --mode manual` 출력(2026-10-09)과 같다. 근거: `iam/rosa-prereq-draft-20261009/README.md`.

## 실행 identity와 권한

- **apply(생성·삭제)는 중앙 실행 경로**에서 한다(rev2, `iam/rosa-prereq-draft-20261009/README.md` "중앙 실행 경로"). 위임 역할 `FDS-IaC-Operator`에는 IAM 쓰기를 붙이지 않는다. 실제 실행 주체·작업창은 실행 승인에서 정한다(미정).
- `FDS-IaC-Operator` + `FDS-IaC-RosaPrereq.json`(조회만) + Guardrails v2 후보로는 생성 후 readback과 plan refresh만 한다. 둘 다 **별도 승인 전 미부착**.
- Terraform 생성 역할·OIDC provider에는 `default_tags`로 `Project=fds-hybrid`·`ManagedBy=terraform`이 붙는다.
- Red Hat 인증은 환경변수(`RHCS_CLIENT_ID`/`RHCS_CLIENT_SECRET` 또는 `RHCS_TOKEN`)로만 넣는다. tfvars·저장소·증적에 넣지 않는다.

## 입력

| 변수 | 기본값 | 설명 |
|---|---|---|
| `execution_enabled` | `false` | 승인 후에만 `true` |
| `create_operator_roles` | `false` | 단계 2에서만 `true` |
| `rh_support_principal_arn` | 없음 | Red Hat 지원 역할 ARN. 조직 External ID가 들어 있어 **커밋하지 않는 tfvars**로 넣는다. CLI `sts_support_trust_policy.json` 값과 같아야 한다 |
| `rh_installer_principal_arn` | `arn:aws:iam::710019948333:role/RH-Managed-OpenShift-Installer` | CLI 출력과 같음 |
| `openshift_version_tag` | `4.22` | CLI가 붙이는 태그 값 |

## 실행 순서 (승인 후)

1. `terraform init -backend-config=backend.hcl` (state `phase2/rosa-prereq/terraform.tfstate`)
2. **단계 1** `terraform plan -var execution_enabled=true -var-file=<비공개>.tfvars -out=stage1.plan`
   - 확인: 생성 3+4+1+1, 변경·삭제 0, `terraform show -json`의 역할별 trust Principal·조건과 부착 정책 ARN이 승인 표(CLI manual 출력)와 1:1 일치. 표에 없는 principal·정책·IAM 자원이 있으면 STOP
3. 단계 1 apply → readback: `aws iam get-role`(3), `rosa list account-roles`, `rosa list oidc-config`, `aws iam get-open-id-connect-provider`. 실패하면 단계 2로 가지 않는다
4. 단계 2 전 대조: `rosa create operator-roles --hosted-cp --prefix fds-rosa --oidc-config-id <id> --installer-role-arn <installer arn> --mode manual` 출력의 역할 이름·namespace·service account·정책을 `main.tf` `operator_roles`와 대조. 다르면 코드 수정 후 리뷰
5. **단계 2** `terraform plan -var execution_enabled=true -var create_operator_roles=true ...` → 생성 8+8, 변경·삭제 0 확인 → apply → readback `rosa list operator-roles`
6. 부분 실패: 실제 readback + `terraform state list` + 명령 RC + `rosa list oidc-config`·OCM 연결 대조 후 다시 plan (실행 자료 §3)

## 로컬 검사 (비용 없음)

```bash
terraform init -backend=false
terraform validate
terraform test
```

`terraform test`는 mock provider만 쓴다. AWS·Red Hat 런타임 증적이 아니다.

## 정리

`terraform destroy`도 중앙 실행 경로에서, 클러스터 삭제·공유 참조 확인과 별도 승인 후에만 한다(실행 자료 §2). rev1의 Cleanup 정책은 삭제했다.
