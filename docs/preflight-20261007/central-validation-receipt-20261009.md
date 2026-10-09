# 중앙 IAM 실제 검증 접수 — 2026-10-09

CODEX_ASSISTED. **READBACK=COMPLETE / VALIDATE_POLICY=12 files, findings0 / SIMULATION=64 requests, REVIEW_REQUIRED / GRANT=NOT_RUN / PLAN=NOT_RUN**.

## 실행 및 무결성

- 시각: 2026-10-09 **13:58:19.438~13:59:59.668 KST**. 서울 CloudShell, 계정 끝1866의 기존 승인 중앙 root 검증 세션. 본인 MFA Work Role 시험이 아니다.
- 정책 source: main `5b8204fad2f726b396457f0776cd85b154706aa2`. collector source: `cffc552fd9c171401c26b83092db28d07419633c`, `scripts/central-iam-validation.py` SHA256 `b09f4339ab0a8daecf095aa0c2ea6becb9e14f86fc8a7f3ca94db2bef81f39a3`.
- AWS CLI2.37.6 / Python3.14.6 / CloudShell Linux. 전달 zip SHA256 `c7fbf3ca70ff6a92d0d98294addbf8e073e07fa24ee6dfc594b903a239d426a8`를 CloudShell에서 확인 후 실행했다.
- 원본: `fds-central-iam-a85nuynw.tar.gz`, 28,984bytes, SHA256 `9ddcab14c5e92a9b3948ffa03e8e88bbbdfc64e6d80b56914eadc2624d05edde`.
- archive 다운로드 후 같은 SHA 확인, capture-manifest **175/175 재해시 일치**. 원본은 사용자 비공개 작업 경로에 보존했다. 독립 evidence publication/인수 승인으로 표시하지 않는다.
- API 호출86건: identity·before/readback·정책 조회·검증·simulation. collector RC0. IaC/Network role 조회의 NoSuchEntity RC254는 원본 보존하며 API 성공으로 바꾸지 않았다.

## 실제 역할 상태 — 과거 추정 정정

| 역할 | fresh 관측 |
|---|---|
| FDS-IaC-Operator | NoSuchEntity — 부재 |
| FDS-Network-Operator | NoSuchEntity — 부재 |
| FDS-ReadOnly-Audit | **이미 존재**, 생성2026-10-03 17:22:17 KST |

Audit에는 managed policy 부착0, inline `FDS-Inventory-ReadOnly-v1`·`FDS-ROSA-Prereq-ReadOnly-v1` 2개가 있다. trust는 기존 세 사용자와 MFA=true를 요구하고 후보의 본인 RoleSessionName 조건은 없다. 현재 상태와 새 후보를 구분하며 이 차이만으로 과거 위반을 단정하지 않는다.

권고: 기존 Audit 역할을 재생성하거나 ViewOnlyAccess로 자동 교체하지 않는다. 기존 명시적 목록은 서울 inventory/CloudShell·ROSA prerequisite 조회 위주다. `ViewOnlyAccess`는 현재 **v46**, 전 서비스 metadata 범위의 별도 확장 후보로 비교·수용해야 한다. 실제 attach는 하지 않았다. 후보 StateDeny/신규 trust도 실제 적용된 것으로 표시하지 않는다.

원본 readback SHA256:
- Inventory inline: `3a674abea587028d1f33f15958a7de45ca0e45766727228b3aa356ed49e83aa5`
- ROSA prereq inline: `df1b15bdf24fd42847d897a97ad17afa9e4c2cb6c24e87fb4e40ee81df6ee501`
- ViewOnlyAccess v46 GetPolicyVersion 응답: `538e8d1ade5ad30524be9283592fa1583f65e54bdc37f62ca9649c45e58f18aa`

## 검증 결과와 의미

ValidatePolicy: identity9개(일반 정책6·사용자 assume3), trust3개, 합계12개에서 findings0. 실제 Relay ID가 없는 Network template은 제외했다. 전체 IAM 배치/실효권한 PASS가 아니다.

64 simulation의 자동 분류:

| 분류 | 건수 | 의미 |
|---|---:|---|
| SIMULATION_MATCH | 27 | 제출한 합성 context에서 기대 판정과 일치 |
| DIAGNOSTIC_EXPECTED | 10 | 부분 자원 진단 결과 일치. 전체 서비스 요청 PASS 아님 |
| MISSING_CONTEXT_REVIEW | 22 | 필요한 context인지 원문/statement 검토 필요 |
| DIAGNOSTIC_MISMATCH_REVIEW | 5 | RequestTag를 부모 자원에 넣은 진단에서 allowed 관측 |

추가 원문 분석:

- missing22건 중16건은 Action/Resource가 일치하는 statement의 조건키 누락이 아니다. 예: DeleteNatGateway 거부 응답에 VolumeSize·s3:prefix 등이 함께 보고됐다. 이 분류는 lexical Action/Resource 대응 분석이며 IAM 조건 평가기/실효권한 증명으로 쓰지 않는다. 원본 verdict를 덮어쓰지 않았다.
- 6건은 N1-omitted-project 및 N20/N21/N22-subnet/N22-eip/N23-sg의 parent-scope다. 해당 정책의 RequestTag 조건 누락이므로 단순 음성 PASS로 바꾸지 않는다.
- 불일치5건: N20/N21/N22-subnet/N22-eip/N23-sg의 request-context. Network `CreateTaggedNetworkResources`, Vpn `CreateTaggedSgInstanceEip`의 Action·Resource 묶음이 일치했다. **합성 RequestTag를 부모 자원에 넣은 simulator 결과이며 실제 외부 자원 생성·사용 성공이 아니다.**
- [AWS EC2 SAR](https://docs.aws.amazon.com/service-authorization/latest/reference/list_ec2.html)는 새 subnet/NAT의 RequestTag와 기존 VPC/subnet/EIP/SG의 ResourceTag 조건을 구분한다. 지원되지 않는 서비스 context를 합성해 실환경 취약점으로 단정하거나, context를 제거해 나온 Deny만으로 안전성을 증명하지 않는다.

## 실행 전 처리와 적용 가능한 보완안

현재 판정은 **중앙 검증 결과 검토 필요**다. 권한 부여·본인 MFA/state-lock 시험·cloud Plan으로 자동 진행하지 않는다. 새로운 P1 차단사유가 아니다.

1. 이권욱/이하영: 16건의 무관 context 보고를 결과 검토표에 반영하고, 나머지 부모 자원 context/지원 조건의 해석을 수용한다.
2. [Action/Resource 분리 제안 diff](iam-action-resource-split.proposed.patch)를 준비했다. 실제 병합 JSON에 `git apply --check` RC0 확인. 원본 정책에는 **미적용**이며 새 정책의 AWS 검증도 미실행이다. 각 생성 Action을 해당 새 자원 ARN에만 묶고 기존 부모 ResourceTag statement는 유지하는 구조다. 권한 확대가 아니라 교차 매칭 모호성을 줄이는 제안이며, 실환경 결함이 입증됐다는 주장과 구분한다.
3. 이 제안을 채택하면 SHA256SUMS/README를 함께 갱신하고 변경 정책 ValidatePolicy 및 영향 case를 재검증한다. 지금 읽기 검증 결과를 수정안의 PASS로 재사용하지 않는다.
4. Audit는 기존 role 유지와 최소 delta를 우선 검토. 실제 role 존재를 확인한 상태에서 CreateRole을 그대로 실행하지 않는다.

비용은 이권욱/#34 교육장 리포트 기준으로 유지한다. AWS 구성·권한 부여·유료 자원 생성, Red Hat 초대·청구 연결, P1 서버/AC는 변경하지 않았다.
