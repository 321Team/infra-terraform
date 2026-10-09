# Network Plan 독립 검토 인계 준비 — 2026-10-09

CODEX_ASSISTED. 작성·원 실행자 이권욱. **LOCAL 원본 무결성/자체 대조 PASS, 독립 Plan REVIEW=PENDING, Apply=NOT_RUN.** 이 문서는 전체 비공개 Plan의 대체 자료나 신규 생성 승인이 아니다.

## 원본과 재현 기준

- 실행 원본: 2026-10-09 17:57:05–17:57:57 KST, [infra-terraform#10](https://github.com/321Team/infra-terraform/issues/10#issuecomment-6077890819).
- 고정 source `81162467bb2f99a099cb7067fbc3f63e1c0dbed8` = 원 실행 `5fb64bdf186645b64664080bd09f9c5babb78fcd` 전체 Git tree 일치. 원 source manifest network6파일과 Git blob SHA256 일치.
- Terraform1.16.4 / AWS provider6.66.0 / 서울 / default workspace / network state. 새 Plan 실행 없음.
- 원본 archive SHA256 `6b1ef479633624f06fb9c66f372852a041815b680ea776ca86db78cd04442935`; 원본 manifest60개와 파일 집합 일치 재확인. 원본 변경0.
- saved Plan SHA256 `18b65922fc358fca901e05e5d890b0605851ed58d1c455161e2c8c9e9dabfc40`.
- Plan JSON SHA256 `0edf0406eba2282ef4871660149bf714acd49871de34b1e85516d6d82f1ac02b`. JSON은 당시 saved Plan에서 생성한 원본이며 이번에 Terraform show를 재실행한 것은 아니다.
- [evidence PR193](https://github.com/321Team/fds-project-evidence/pull/193) merge `b6aa39383c55ae877bb4044b4cd6efb9037d7845`는 선별 증적 편입이다. 전체 binary/JSON은 기존 개인 비공개 보관 경로에 유지한다.

## 검토할 20개 변경

| resource address | action | 원본의 알려진 주요 값 |
|---|---|---|
| `aws_eip.nat` | create | `{"domain": "vpc"}` |
| `aws_internet_gateway.transport` | create | `{}` |
| `aws_nat_gateway.platform` | create | `{"connectivity_type": "public"}` |
| `aws_route.private_egress["private_a"]` | create | `{"destination_cidr_block": "0.0.0.0/0"}` |
| `aws_route.private_egress["private_b"]` | create | `{"destination_cidr_block": "0.0.0.0/0"}` |
| `aws_route.private_egress["private_c"]` | create | `{"destination_cidr_block": "0.0.0.0/0"}` |
| `aws_route.transport_internet` | create | `{"destination_cidr_block": "0.0.0.0/0"}` |
| `aws_route_table.subnet["private_a"]` | create | `{}` |
| `aws_route_table.subnet["private_b"]` | create | `{}` |
| `aws_route_table.subnet["private_c"]` | create | `{}` |
| `aws_route_table.subnet["public_transport_a"]` | create | `{}` |
| `aws_route_table_association.subnet["private_a"]` | create | `{}` |
| `aws_route_table_association.subnet["private_b"]` | create | `{}` |
| `aws_route_table_association.subnet["private_c"]` | create | `{}` |
| `aws_route_table_association.subnet["public_transport_a"]` | create | `{}` |
| `aws_subnet.project["private_a"]` | create | `{"availability_zone_id": "apne2-az1", "cidr_block": "10.20.10.0/24", "map_public_ip_on_launch": false}` |
| `aws_subnet.project["private_b"]` | create | `{"availability_zone_id": "apne2-az2", "cidr_block": "10.20.20.0/24", "map_public_ip_on_launch": false}` |
| `aws_subnet.project["private_c"]` | create | `{"availability_zone_id": "apne2-az3", "cidr_block": "10.20.30.0/24", "map_public_ip_on_launch": false}` |
| `aws_subnet.project["public_transport_a"]` | create | `{"availability_zone_id": "apne2-az1", "cidr_block": "10.20.110.0/24", "map_public_ip_on_launch": false}` |
| `aws_vpc.project` | create | `{"cidr_block": "10.20.0.0/16", "enable_dns_hostnames": true, "enable_dns_support": true}` |

VPC precondition=PASS, subnet4개 postcondition=UNKNOWN이다. 생성되는 ID·route target의 actual 값은 Apply 전 UNKNOWN이며 configuration references로 연결을 검토해야 한다. public transport 기본경로는 IGW, private_a/b/c 기본경로는 단일 public NAT에 연결된다. NAT subnet은 public_transport_a, EIP는 NAT 전용이다. On-Prem route·Relay·ROSA·IAM 변경은 이 network Plan에 없다. network_handoff.stage_a_ready=false를 유지한다.

## 독립 검토자가 해야 할 일

1. 기존 승인된 비공개 전달 경로에서 archive·manifest·saved Plan·Plan JSON·source manifest·실행 기록을 수신하고 위 hash를 직접 확인한다. 이 저장소에는 full Plan/state/credential을 올리지 않는다. **수신 경로·수신자·실제 수신 여부는 아직 미확인**이다.
2. 전체 resource_changes의 action/before/after/after_unknown/sensitive, embedded configuration의 참조·의존성, prior_state·output·check를 검토한다. 원본 Plan binary를 show할 때는 동일 검증된 Terraform/provider 환경에서 로컬로만 처리하고 Apply하지 않는다.
3. 20 create/0 update/0 delete, 태그·CIDR·AZ-ID·public-IP=false, NAT/IGW/route/association 연결과 root 범위 밖 변경 부재를 확인한다. 일부 요약 표만 읽고 전체 Plan APPROVED로 기록하지 않는다.
4. 검토자·시각·source SHA·Plan hash·확인한 원본 목록·차단사항/한계·판정을 #10에 남긴다. 작성/실행자의 자체 확인과 독립 검토를 분리한다.

## Apply 전 별도 Gate

실행 직전 current source/input/state/정책·권한 변화와 기존 Hard Gate를 다시 확인한다. 변화 또는 Plan 유효성 상실 시 새 회차로 Plan/검토하며 이 오래된 파일을 자동 Apply하지 않는다. 권욱의 교육장 리포트 기반 비용 판정과 실제 작업창, #34 Freeze 등 기존 Gate는 이 문서로 완료되지 않는다. 비용 입력은 NAT1·NAT 공인 IPv4 1 및 처리량, 다른 AZ 이용 시 cross-AZ 경로이고 금액은 임의 산정하지 않는다. VPN의 EC2/EBS/Relay IPv4는 별도 Plan이다.

Apply 후에는 실제 VPC/subnet/AZ-ID/route-table association/NAT/IGW와 state·현재 lock 정리를 검증한 뒤 network_handoff를 소비한다. Plan의 UNKNOWN을 actual ID로 채우거나 이 자료를 Phase1 인수·U1 전체·I5 완료로 사용하지 않는다.
