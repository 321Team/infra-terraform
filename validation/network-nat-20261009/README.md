# NAT 후보 정적·MOCK 검증 (2026-10-09)

CLAUDE_ASSISTED. [PR14](https://github.com/321Team/infra-terraform/pull/14) NAT 후보의 현재 source manifest와 helper 원본이다. **실행 승인·cloud Plan/Apply 결과가 아니다.** 과거 manifest(`validation/relay-agent-rpm-20261008/source.json`)와 증적은 변경 전 소스의 이력으로 보존한다.

| 항목 | 값 |
|---|---|
| base | main `93d71500e3e881c55f1814cd144ca41f43e77f3d` |
| manifest | [source.json](source.json) — network 6파일 / vpn 10파일, MOCK network 5 / vpn 22 |
| vpn | 파일 해시가 이전 manifest와 동일함을 생성 시 대조 |
| toolchain | Terraform 1.16.4 exe SHA256 `d1f5754b41b44c7e4ce7283780d2ccb9492f2c32c9629555686fc29fa8067349` / AWS provider 6.66.0 lock readonly |
| 실행 | `scripts/validate-components.py --manifest validation/network-nat-20261009/source.json --component <network\|vpn> --terraform <고정 1.16.4>` |
| 결과 | network·vpn 각 version/fmt/backend-example-fmt/init/validate/mock-test 6단계 RC0, `pass: true`, source 전후 동일 |
| 격리 | 자격증명 미상속, backend=false, AWS·backend·CI 미실행 |

원본: [network/](network/), [vpn/](vpn/) (`summary.json`, `capture-manifest.json`, 명령별 stdout/stderr). 바이트 보존은 `.gitattributes`의 `-text`로 고정한다.

MOCK 시험 추가: `single_nat_private_egress`(plan), `nat_targets_are_wired`(mock apply — NAT subnet/EIP, private route별 nat_gateway_id·route_table_id). NAT를 private_a에 둔 변형에서 `nat_targets_are_wired`가 실패함을 로컬 확인했다(원본 미보존, 소스 복원 후 해시 재확인).
