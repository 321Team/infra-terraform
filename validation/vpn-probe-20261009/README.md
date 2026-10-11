# vpn-probe 후보 정적·MOCK 검증 (2026-10-09)

CLAUDE_ASSISTED. #37 T3·T6 시험 출발지 `terraform/vpn-probe`의 현재 source manifest와 helper 원본입니다. **실행 승인·IAM 부여·cloud Plan/Apply 결과가 아닙니다.** network·vpn root는 바꾸지 않았으므로 기존 manifest(`validation/network-nat-20261009/source.json`)가 그대로 유효합니다.

| 항목 | 값 |
|---|---|
| base | main `81162467bb2f99a099cb7067fbc3f63e1c0dbed8` |
| manifest | [source.json](source.json) — vpn-probe 7파일, MOCK 7 |
| AMI | `ami-0870825cefcaafcc8` (AL2023 표준 x86_64, 소유자 `137112412989`). 2026-10-09 CloudShell 조회값(재환 실행), 출처는 [IAM README](../../iam/vpn-probe-20261009/README.md) |
| toolchain | Terraform 1.16.4 exe SHA256 `d1f5754b41b44c7e4ce7283780d2ccb9492f2c32c9629555686fc29fa8067349`. 공식 zip `5c736ed6…3a7054`는 releases.hashicorp.com `terraform_1.16.4_SHA256SUMS`와 일치하고, exe는 기존 증적의 exe 해시와 같습니다. AWS provider 6.66.0은 lock readonly로 설치했고 `signed by HashiCorp`입니다 |
| 실행 | `scripts/validate-components.py --manifest validation/vpn-probe-20261009/source.json --component vpn-probe --terraform <고정 1.16.4>` |
| 결과 | version/fmt/backend-example-fmt/init/validate/mock-test 6단계 RC0, validate error 0·warning 0, `7 passed, 0 failed`, `pass: true`, source 전후 동일 |
| 격리 | 자격증명 미상속, backend=false |
| 미실행 | AWS 호출·backend·cloud Plan/Apply·CI·중앙 validate-policy·시뮬레이션은 **NOT RUN** |

원본: [vpn-probe/](vpn-probe/) (`summary.json`, `capture-manifest.json`, 명령별 stdout/stderr). 실행 호스트와 UTC 시각은 `summary.json`에 있습니다. 바이트 보존은 `.gitattributes`의 `-text`로 고정합니다.

MOCK 7건:
- `disabled_candidate_is_rejected`: `execution_enabled=false` 기본값 거부
- `missing_window_reference_is_rejected`
- `bad_expiry_is_rejected`
- `probe_controls`: t3.medium·고정 AMI·IMDSv2·gp3 8GiB 암호화·공인 IP 없음·태그·SG egress 443/5432/22
- `wrong_profile_is_rejected`
- `public_or_wrong_subnet_is_rejected`
- `wrong_ami_is_rejected`

hash 일치는 무결성을 뜻할 뿐이며, 기능·승인·AC를 보장하지 않습니다.
