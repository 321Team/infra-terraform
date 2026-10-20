# ROSA inventory 읽기 4종 — 2026-10-17 실제 반영

2026-10-17 22:09:29 KST, 이권욱의 명시적 한정 승인으로 계정 `774055931866`에 managed policy `FDS-ROSA-InventoryRead`를 생성하고 `FDS-IaC-Operator`에 연결했다. 기존 정책을 교체하거나 인라인 정책을 추가한 것이 아니다. 이 파일은 실제 v1 원문과 JSON 의미가 같다.

[요청·HOLD 기록](https://github.com/321Team/infra-rosa/issues/4#issuecomment-6233908894)의 세 조회 누락과 v6 사후 수집 코드에 필요한 `tag:GetResources`를 함께 보완했다. `s3:ListAllMyBuckets`는 계정 bucket 목록 메타데이터이며 객체 읽기/쓰기 허용이 아니다. 네 동작 모두 요청 리전 `ap-northeast-2` 조건이다.

## 검증 범위

- STATIC: 실제 기존 정책과 후보 검토, Access Analyzer ValidatePolicy findings 0.
- POLICY_SIMULATION: 사전 4개 implicitDeny를 확인했다. 반영 후 후보 주입 없이 실제 연결된 역할 정책으로 서울 4개 allowed, 서울 외(us-east-1) 4개 explicitDeny, 글로벌 Route53 ListHostedZones explicitDeny — 총 9/9 기대 일치, MissingContextValues 0.
- RUNTIME(IAM): CreatePolicy/AttachRolePolicy 성공, 정책 원문·역할 연결 재조회, 전후 snapshot 비교에서 새 연결 한 개만 변경됐다. Guardrail·Trust·D1=10800·기존 사용자/그룹/role 정책은 동일하다.
- RUNTIME(하영 조회/ROSA): 이 회차 NOT_RUN. 시뮬레이션은 실제 MFA 요청·클러스터 생성 성공을 뜻하지 않는다.
- CI/REVIEW/MERGE: PR33의 최신 실제 상태를 따르며, 검사 0건은 NOT_RUN이다. 자체 작성·반영은 독립 승인이 아니다.

## 운영·복구 경계

하영은 기존 본인 MFA → `FDS-IaC-Operator` 경로로 서울 endpoint를 사용한다. 새로 전체 정상/거부 시험을 반복하거나 별도 확인 회신을 기다리는 절차를 만들지 않는다. 다음 승인된 작업에서 해당 조회의 실제 결과·종료 코드를 기존 증적에 보존한다. 계정/역할 불일치 또는 예상 외 권한 결과는 중단하고 기존 증적에 기록한다.

Route53 Guardrail은 유지했다. **현재 v6가 Route53을 계속 호출하면 그 단계의 STOP은 남는다.** 최신 요청의 Guardrail 예외와 당일 재실행 GO는 이 4종 승인에 포함되지 않는다. 새 키트에서 조회를 제외한다면 before/readback/diagnose/검사기의 입력 계약과 미수집 판정을 함께 맞추며, 빈 JSON을 실제 조회 증거로 만들지 않는다.

하영의 임의 정책 원문 관리 위임은 아직 적용하지 않았다. 현재 역할에는 permissions boundary가 없어 대상 역할만 제한한 PutRolePolicy/CreatePolicyVersion 허용으로는 권한 내용의 상한을 보장하지 못한다. 그 위임을 이 고정 읽기 정책의 적용과 혼동하지 않는다. D1=10800 고정과 기존 본인 MFA UpdateRole 허용은 유지한다.

이상 시 중앙 관리자가 **이번 `FDS-ROSA-InventoryRead` 연결만** 분리하고 재조회한다. 정책 삭제는 연결 엔터티가 없고 증적 보존이 끝난 경우에만 한다. 기존 Guardrail·Trust·다른 연결은 원복 대상으로 삼지 않는다. 실제 오류·원복은 없었다. 작업창 종료마다 회수하지 않고 검증·증적 검토 완료 후 정리 범위를 판단한다.

## 비공개 원본 추적

원본은 공개 저장소에 올리지 않는다. 아래 TGZ를 수신하고 내부 manifest를 검증했다. 해시 일치는 무결성이며 시험·AC 완료가 아니다.

| 원본 | SHA256 | 내부 manifest |
|---|---|---|
| rosa-iam-preflight-20261017T125356Z.tgz | 7f952a086abc6e788d35a2cc02a879a7ed956a8b14b790d04eb2630b9f959697 | 10/10 |
| rosa-iam-apply-20261017T130913Z.tgz | 83995d2451cecb2b042bdead1c3528e139ca64fa74bd0186cc44deb1211e22d5 | 8/8 |
| rosa-iam-postcheck-20261017T131034Z.tgz | 10647d02a178882c8457e56cdb94d369328c842eec288b24b7fb31ea6596c111 | 5/5 |

Phase1 DB/pg_hba/방화벽/NetworkManager/route/Harbor CA/OCP/Runner/DNS/LB/AC를 변경하지 않았다. 실제 자원 생성·키 발급·Apply·새 Create GO·정본 발행·티켓 종결을 수행하지 않았다.
