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
   - 자동 대조: `terraform show -json stage1.plan > stage1.plan.json` → `python3 tools/rosa_prereq_check.py plan --stage 1 --support-principal <CLI 출력 값> stage1.plan.json`. `result=PASS`(exit 0)가 아니면 apply하지 않는다
3. 단계 1 apply → readback: `python3 tools/rosa_prereq_check.py readback --stage 1 --support-principal <값>`(trust·부착 정책·inline 0·OIDC provider 대조, 출력의 `oidc_host` 기록), `rosa list account-roles`, `rosa list oidc-config`. 실패하면 단계 2로 가지 않는다
4. 단계 2 전 대조: `rosa create operator-roles --hosted-cp --prefix fds-rosa --oidc-config-id <id> --installer-role-arn <installer arn> --mode manual` 출력의 역할 이름·namespace·service account·정책을 `main.tf` `operator_roles`와 대조. 다르면 코드 수정 후 리뷰
5. **단계 2** `terraform plan -var execution_enabled=true -var create_operator_roles=true ...` → `rosa_prereq_check.py plan --stage 2 --oidc-host <단계 1 값> ...`(생성 8+8, 단계 1 자원 no-op, 변경·삭제 0) → apply → `rosa_prereq_check.py readback --stage 2 ...`, `rosa list operator-roles`
6. 부분 실패: 실제 readback + `terraform state list` + 명령 RC + `rosa list oidc-config`·OCM 연결 대조 후 다시 plan (실행 자료 §3)

## 로컬 검사 (비용 없음)

```bash
terraform init -backend=false
terraform validate
terraform test
```

`terraform test`는 mock provider만 쓴다. AWS·Red Hat 런타임 증적이 아니다.

## 중앙 실행 대조 스크립트 `tools/rosa_prereq_check.py`

승인 표(ROSA CLI 1.2.53 manual 출력 기준)를 스크립트 안에 `main.tf`와 **따로** 적어 두고 비교한다. 둘 중 하나를 바꾸면 같은 PR에서 둘 다 바꾼다.

| 모드 | 하는 일 | AWS 호출 | STOP 조건 |
|---|---|---|---|
| `plan` | `terraform show -json` 결과 대조 | 없음 | Terraform 버전 불일치, 승인 목록 밖 자원, create(단계 2의 단계 1 자원은 no-op) 외 동작, 역할 이름·trust(Statement·Principal·Action·Condition)·부착 정책 ARN 불일치, inline 정책·permissions boundary, plan 시점 trust 미확정 |
| `readback` | apply 뒤 실제 IAM 대조 | 조회만(`get-role`·`list-attached-role-policies`·`list-role-policies`·OIDC provider 조회). `FDS-IaC-RosaPrereq.json`으로 가능 | 계정 불일치, 역할 없음, trust·부착 정책 불일치, inline 정책 1개 이상, `oidc.op1` provider가 1개가 아님, client ID 불일치 |

- 결과: exit 0 PASS, 1 STOP, 2 입력 오류. 출력에서 Red Hat 조직 External ID는 `<masked>`로 가린다. plan 모드는 plan JSON SHA-256을 출력한다.
- `--support-principal`은 CLI `sts_support_trust_policy.json` 값을 넣는다. 커밋하지 않는다.
- `ocm-role`·`user-role`(CLI 소유)은 대상이 아니다. manual 출력 원문과 실행 명령을 검토해 따로 대조한다.
- 오프라인 테스트: `python3 -m unittest tests/test_rosa_prereq_check.py` (정상 단계 1·2, trust principal 추가, statement 추가, 조건 연산자 변경, AdministratorAccess 부착, 승인 밖 자원, update·delete·replace, inline 정책, trust 미확정, 버전 불일치, 입력 오류, 출력 마스킹 등 18건).

## 정리

`terraform destroy`도 중앙 실행 경로에서, 클러스터 삭제·공유 참조 확인과 별도 승인 후에만 한다(실행 자료 §2). rev1의 Cleanup 정책은 삭제했다.
