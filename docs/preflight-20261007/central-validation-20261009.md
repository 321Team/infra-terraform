# PR14/15 병합 후 중앙 IAM 검증

CODEX_ASSISTED. 사용자 2026-10-09 “착수” 범위의 정책 검증·후속 준비. 대상 소스는 `5b8204fad2f726b396457f0776cd85b154706aa2`. IAM JSON은 변경하지 않는다. AWS/Red Hat Grant·청구 연결·조직 초대·Terraform Plan/Apply·P1 변경은 이 실행기 범위 밖이다.

실제 실행 결과는 [2026-10-09 중앙 검증 접수](central-validation-receipt-20261009.md)에 있다. ValidatePolicy12개 findings0, simulation64개 검토 필요. 기존 Audit 역할 존재를 확인했으며 새로 만들지 않았다.

## 실행 계약

- 대상: 기존 승인 중앙 검증 세션, AWS 계정 끝1866 / 서울. `sts get-caller-identity` 결과의 exact ARN과 `--expected-caller-arn`이 일치해야 한다. 중앙 root의 정책 검증과 개인 MFA 역할로 수행할 업무 Plan/Apply를 혼동하지 않는다.
- 경로: CloudShell HOME의 새 개인0700 디렉터리. 원본 로그는 비공개 보존. secret/state payload를 조회하거나 게시하지 않는다.
- 선행: Python3/AWS CLI, 검토한 collector/정책 SHA와 전달 archive SHA 대조. prepare는 로컬 파일만 작성하며 AWS 호출이 없다. run은 manifest 파일 집합/해시·collector hash를 검증한 뒤 호출한다.
- API 범위: STS identity, 역할/trust/정책 readback, ViewOnlyAccess 현재 버전 조회, Access Analyzer ValidatePolicy, IAM SimulateCustomPolicy. 호출 allowlist 밖의 작업은 거부한다. API 오류·timeout·identity 불일치 시 중단한다.
- 권한 없는 조회를 자원 부재로 처리하지 않는다. GetRole의 명시적 NoSuchEntity만 ABSENT다.
- ERROR/SECURITY_WARNING 발견 시 simulation으로 진행하지 않는다. WARNING/SUGGESTION도 사람이 영향·수용 사유를 검토한다.
- 실제 state 삭제·fixture 생성·자원 삭제 명령은 없다. 시뮬레이션의 DeleteObject/DeleteVpc 등은 API 작업을 실행하지 않는 문자열 입력이다.
- 부분 실패 시 원본/RC를 보존하고 해당 정책·case를 수정/재검토한다. 이 읽기 회차는 AWS rollback 대상 변경이 없다. 부여 단계의 원복은 이후 별도 검토한다.

## 준비·실행

소스 루트에서 새 출력 경로를 지정한다. 출력 경로를 덮어쓰지 않는다.

```bash
python3 scripts/central-iam-validation.py prepare --output /absolute/private/new-bundle
python3 scripts/central-iam-validation.py run \
  --bundle /absolute/private/new-bundle \
  --output-parent /absolute/private \
  --expected-caller-arn '<STS로 확인한 기존 승인 중앙 검증 ARN>'
```

64개 요청은 README P1~P15/N1~N26의 분리 사례를 포함한다. ID가 비슷해도 별도 policy SHA/action/resource/context/기대값으로 추적한다. account/resource 식별자는 시뮬레이션용 합성값이며 실제 인벤토리가 아니다. 표준 endpoint만 사용하고 TLS 검증은 유지한다.

수집 종료 RC0은 수집 성공일 수 있으며 IAM 전체 PASS가 아니다. summary의 findings/case verdict, 원본 stdout/stderr/개별 RC/시간/hash를 함께 본다. `CAPTURE_COMPLETE_REVIEW_REQUIRED`와 `VALIDATION_REVIEW_REQUIRED`는 부여 승인 상태가 아니다.

## 다중 자원·context 한계

IAM simulator의 context 입력은 AWS 서비스가 각 자원에 제공하는 실제 context와 같다고 보장되지 않는다. 부모 자원에 RequestTag를 넣거나 빼면 중첩 Allow의 결과가 달라질 수 있다. N20~N23은 부모 소유 tag 검사와 request-context 포함 검사를 쌍으로 보존하고 DIAGNOSTIC으로 표시한다. 결과를 좋은 방향으로 만들기 위해 요청을 조용히 바꾸지 않는다.

필요 context 누락으로 나온 implicitDeny는 PASS가 아니다. 실제 미태그 자원의 absent-key 의미와도 구분한다. 다중 자원 전체 호출의 안전성은 서비스 Action/Resource/condition 지원과 실제 부여 후 승인 범위의 시험까지 연결해야 한다. SCP/session/resource/endpoint policy 전체를 넣지 않은 simulation은 실제 실효권한 증명이 아니다.

근거: [AWS simulator API](https://docs.aws.amazon.com/cli/latest/reference/iam/simulate-custom-policy.html), [검증 API](https://docs.aws.amazon.com/cli/latest/reference/accessanalyzer/validate-policy.html), [simulator 한계](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_testing-policies.html).

## 후속 입력과 담당

| 담당 | 다음 작업 | 완료 경계 |
|---|---|---|
| 이권욱 | 중앙 findings·simulation 판정, ReadOnly-Audit 현재 managed policy JSON/버전 검토 | 단순 Action 포함을 최소권한 PASS로 표시하지 않음 |
| 이하영 | 중앙 검증에서 나온 정책 지적 대응, ROSA #12 full policy/trust·rosa-prereq source/lock·CLI pin 제출 | PR15는 Stage-A 정책이며 ROSA bootstrap 전체 정책 아님 |
| 이권욱·이하영 | Red Hat 대체 접근 역할명·범위·필요 연결과 회수 경로 확정 | whoami/list clusters만으로 삭제 권한을 확인했다고 하지 않음 |
| 이하영 | Harbor source10.20.10.0/24→Relay TCP443 후보 코드·시험 입력 | 후보 수신만 됨. 터널 readiness 전 route OFF |
| 이권욱 | 비용·생성/삭제창 판정 | 교육장 리포트를 #34에서 중앙 통제. 하영에게 비용 판정 재요구 없음 |

ROSA #3은 미확정 사유·Owner·Due와 #4 NO_GO를 기록하는 사전조사 범위다. 비용 이관 완료조건을 유지하고 실제 생성/복구 시험을 새 종결 조건으로 추가하지 않는다. #10의 CA_SOURCE=UNVERIFIED는 P2 이식 입력이며 P1 Push 재실행이나 신규 인수 AC를 요구하지 않는다.

정리 기준은 우리 프로젝트 소유 inventory와 공유 참조다. 계정 전체 ROSA/EC2 0건을 요구하지 않고 실제 사용한 NAT/EIP/EBS/LB/ENI/endpoint 등 잔존 자원을 확인한다. AWS/state뿐 아니라 Red Hat OIDC config/OCM 연결도 부분 실패 대조 대상이다. 비용 종료 최종 판단은 이권욱이 교육장 리포트로 한다.
