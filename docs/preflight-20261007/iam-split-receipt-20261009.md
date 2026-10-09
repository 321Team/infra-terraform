# IAM Action·Resource 분리 후보 — 2026-10-09

CODEX_ASSISTED. 사용자 “착수”에 따른 PR #16 후속. Phase 2 사전 정책 검증 범위다. Phase 1 인수조건·Runtime·정본을 변경하지 않는다. 비용 판정은 #34에서 이권욱이 교육장 리포트로 통제한다.

## 소스와 변경

- 시작 main: `2f127c0adc70e8149a4492704b0683e25070e86f` (PR #16 merge).
- 정책 소스: `d857c63c6e5b3800b746511ffa8b913e350d27ce`.
- `FDS-IaC-Network`의 생성 statement를 6개, `FDS-IaC-Vpn`은 3개로 분리. 각 Action에 해당하는 새 자원 ARN만 남긴다.
- Effect/Condition 동일. 부모 VPC·Subnet·EIP·SG의 ResourceTag 조건, AMI·ENI·volume·PassRole·state·Guardrails·trust는 유지한다.
- 원본 Action×Resource×Effect×Condition 조합 기준 추가 0개, Network 30개/VPN 6개 제거. 정적 비교는 IAM 엔진 검증을 대체하지 않는다.
- PR #16의 `iam-action-resource-split.proposed.patch`는 이전 main 대상의 역사적 제안으로 보존한다. 현재 정책에 재적용하는 파일이 아니다.
- 수집기 변경은 위 정책 source pin과 소유 부모 진단 6개 추가뿐이다. 기존 64개 요청의 Action/Resource/Context/기대값은 유지했다. MissingContext를 채워 PASS를 만들지 않는다.
- 테스트 환경의 AWS_CA_BUNDLE이 tamper 테스트를 가리지 않게 해당 테스트만 환경을 격리했다. 별도 override 거부 테스트 4개 subcase로 운영 통제 유지를 확인했다.

## STATIC / 로컬 검사

- 정책 문법·크기·중복 Sid·inventory action coverage 검사 PASS.
- 수집기 실패경계 unittest 8개 PASS(override test 내부 4개 subcase 포함). 실제 AWS 호출 없는 검사다.
- 정책 SHA256SUMS 16개와 지정 commit의 Git blob 16개 일치.
- 준비된 요청 70개, bundle manifest 85개 파일 확인.
- [기계 판독 정적 확인](iam-split-static.json).

## 다중 자원 권한의 범위

[AWS EC2 SAR](https://docs.aws.amazon.com/service-authorization/latest/reference/list_ec2.html)은 CreateSubnet/CreateRouteTable의 부모 VPC, NAT의 기존 subnet/EIP, RunInstances의 기존 SG/subnet에 ResourceTag 조건을 제시한다. 새 자원 생성의 RequestTag 조건을 이 부모 ARN에 동시에 배치하지 않도록 분리한다.

현재 Terraform NAT는 `allocation_id`+`subnet_id`, public zonal 경로다. [CreateNatGateway API](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_CreateNatGateway.html)의 AvailabilityMode 기본값은 zonal, VpcId는 regional NAT용이다. 따라서 regional NAT VPC 권한을 이번 분리에 추가하지 않는다. 이 근거는 코드/문서 검토이며 실제 역할 세션의 EC2 다중 자원 인가 성공을 증명하지 않는다. 추후 역할 부여 및 실제 인벤토리 준비 후 서비스 DryRun/Stage-A 통제 시험에서 재확인한다.

## 중앙 실행

실제 실행: **2026-10-09 14:54:07~14:56:26 KST**, 서울 중앙 계정 끝1866, 기존 승인 root 검증 세션. source `d857c63c6e5b3800b746511ffa8b913e350d27ce`, collector commit `3695b10f8ba758aefc09b46d5612e9dee3b26491`.

- ValidatePolicy **12개 findings 0**. Relay template은 실제 instance binding 미확정이므로 제외한 기존 계약을 유지한다.
- Simulation **70개**: `SIMULATION_MATCH=27`, `DIAGNOSTIC_EXPECTED=16`, `MISSING_CONTEXT_REVIEW=27`, 명시적 기대값 불일치 분류 0. **70 PASS로 표시하지 않는다.**
- 기존 64개 중 raw EvalDecision이 달라진 것은 정확히 5개: N20-request-context, N21-request-context, N22-subnet-request-context, N22-eip-request-context, N23-sg-request-context. 모두 allowed → implicitDeny. 나머지 59개 raw 결정 동일.
- 소유 부모+요청 태그의 새 positive 6개는 모두 allowed. 기존 부모 ResourceTag 허용과 AMI/ENI/volume 허용을 이번 분리가 훼손한 결과는 관측되지 않았다. 다중 자원 실제 API 성공을 뜻하지 않는다.
- MissingContext 27개 중 26개는 해당 Action/Resource와 일치하는 statement가 참조하지 않는 키였다. 1개 `N1-omitted-project`는 의도적으로 Project 입력을 생략한 음성 사례. 이 구분은 Action/NotAction·Resource/NotResource 및 Condition 키의 정적 적용범위 비교이며, 조건식을 재구현한 별도 IAM 엔진 판정이 아니다. 원본 REVIEW_REQUIRED는 보존하고 독립 리뷰에서 수용 여부를 확인한다.
- fresh role readback은 IaC/Network 부재, Audit 존재(기존 inline 2개/managed 0개). 실제 IAM 설정 완료로 볼 수 없다.
- 수집기 RC0, API92회: RC0 90회 + GetRole NoSuchEntity RC254 2회. 별도 실패 은폐 없음.

증적 추적:
- 입력 zip SHA256: `5ec6d1af7b4d4255d3eb6e66f4b78b320cbaf6c759d26666b7088eb8d18aa0f0`.
- 수집기 SHA256: `ec7275fd219e88c8b083a0bc9988a01dc882c9b34ef1c5950a2bd2cba29fb4c6`.
- CloudShell 원본 `/home/cloudshell-user/fds-central-iam-l258eb6_`, 로컬 비공개 원본 `work/phase2-sequence-20261007/private-evidence/fds-central-iam-l258eb6_`.
- 원본 archive SHA256: `d3d9305d657c2332148c8565a1676e3a096376f5af934bb2d1f913e1e4f17fc3`.
- 다운로드 후 archive SHA와 capture **187/187 파일 hash·파일 집합 일치**. 개별 argv/RC/시각/stdout/stderr는 원본에 보존한다. SHA 일치는 무결성 확인이며 인수 PASS가 아니다.
- [공개 검증 접수표](iam-split-verification.json): 입력/출력 manifest hash, 자동분류, context 적용범위와 전후 결정 차이. 원본은 Git에 게시하지 않는다.

독립 리뷰 재현: policy commit에서 SHA256SUMS를 확인하고 collector commit의 prepare로 새 묶음을 만든다. 원본 archive 해시를 대조한 뒤 capture-manifest의 파일 집합/해시, summary의 입력 manifest hash와 source hash를 비교한다. original64 각 request의 PolicyInputList 이외 필드는 이전 bundle과 동일하다. 새 AWS 재실행은 필요한 변경/새 근거가 있을 때만 수행한다.

## 후속 및 경계

1. 이하영: 새 정책 HEAD와 원본 결과 독립 리뷰. PR #16의 수집기 승인을 이번 정책 변경 승인으로 확대하지 않는다.
2. 이권욱: 검토 잔여/역할별 before snapshot/부여와 복구 diff를 확인한 뒤 Grant를 별도 판정한다.
3. Grant 후 개인 MFA 역할의 AssumeRole/readback 및 실제 서비스 인가 확인 → 승인된 Stage-A Plan → Plan 리뷰 → Apply를 각각 구분한다.
4. 기존 Audit 역할은 inline 2개가 있는 현행 자원이다. ViewOnlyAccess 신규 부착이나 trust 교체를 자동 수행하지 않는다.

이 실행의 AWS 변경·Grant·Terraform Plan/Apply·ROSA 생성은 모두 미실행이다. 원상복구할 AWS 정책 변경은 없다. 후보 소스는 PR 거절/수정 또는 병합 후 별도 revert로 되돌릴 수 있다. 원본 로그는 보존한다.
