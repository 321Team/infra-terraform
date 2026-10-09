# 리뷰 대기 중 선행작업·담당별 잔여 — 2026-10-09

CODEX_ASSISTED. 조회 범위: infra-terraform#9/#10/#11/#12, PR19, baseline#35 전체 댓글 및 로컬 수신 원본. 전 프로젝트 전수 인수 판정이 아니다. Phase1 요구사항·AC·정본·일정·비용 결정권은 변경하지 않는다.

## 완료된 것과 아직 안 된 것

| 대상 | 현재 확인 근거 | 남은 범위 / 담당 |
|---|---|---|
| IaC 역할 부여 | PR18 main81162467, [중앙 부여 기록](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6077294756). 부여를 반복하지 않음 | 개인별 U1 잔여는 각 본인. IaC 부여를 ROSA/IAM/Marketplace 추가 권한으로 확대하지 않음 |
| 권욱 network Plan | [실행 기록](https://github.com/321Team/infra-terraform/issues/10#issuecomment-6077890819), 20 create/0 update/0 delete. PR193 증적 편입 | 권욱이 비공개 full Plan 인계, 독립 리뷰어가 실제 수신·검토 기록. [검토 입력](network-plan-review-handoff-20261009.md) 준비 완료 |
| 하영 U1 기록 | evidence PR194 merge6d7bec65, 재환 독립 승인. 기록 정정 완료 | 하영 원격37파일·N1/N2 최종 마스킹·관련 세션 만료 여부는 미확인. 비밀값 출력 없이 확인하고 새 수집회차로 원본/manifest 인계. 정확한 과거 root 로그아웃 시각은 미기록 그대로 유지 |
| N5 보완 | evidence PR196 merge3ada349c. 중앙 STATIC+SIMULATION 편입 | actual HeadObject404는 UNDETERMINED. noMFA 실제 거부 NOT_RUN. 새 장기키·테스트 사용자·MFA 해제를 만들어 시험하지 않음 |
| 잠금 시험 실행기 | [PR19](https://github.com/321Team/infra-terraform/pull/19) HEAD1a60fb08, 로컬 MOCK14 PASS | 하영 독립 리뷰 대기. 권욱은 같은 state writer가 없는 작업창 확인 후 fresh 개인 MFA/readback → preflight → I3 fixture 충돌·정리·재시도. 실제 두 Terraform 프로세스 경쟁/I5 전체와 구분 |
| CI | 조직 Actions 비활성, [확인 기록](https://github.com/321Team/infra-terraform/pull/19#issuecomment-6080023918) | CI NOT_RUN과 로컬 검증의 한계를 독립 리뷰에 포함. 조직 설정 변경을 신규 AC로 요구하지 않음 |
| 재환 Network 역할 | Stage-A actual Relay·Agent·SSM 문서 결속이 선행. 과거 조회에서는 역할 부재 | 권욱 중앙 결속·부여, 재환 본인 역할 시험은 실제 target 수신 후. 빈 ID를 합성하여 지금 권한을 부여하지 않음 |
| ROSA A1/A3 | [하영 Guardrails 문제제기](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6077911578), [기존 회신](https://github.com/321Team/fds-project-baseline/issues/35#issuecomment-6078438929) | 하영이 exact product ID/role·policy·OIDC 패턴과 실행 자료 PR 제출 → 권욱이 현재 Guardrails와 조합 검증. 현재 PR18 권한에 선반영하지 않음 |
| network Apply → VPN | actual network handoff가 VPN cloud Plan 입력 | 권욱의 기존 Freeze/비용/실행 Gate 판단 및 독립 full Plan 검토 후 별도 실행. 초기 route OFF, D22 미선택 Harbor ingress 추론 추가 없음 |

## 이번에 진행한 준비

1. 수신된 network 원본 archive/manifest60파일·network source6파일을 로컬에서 대조하고 full Plan 리뷰용 20개 주소·알려진 속성·UNKNOWN·원본 hash·검토/무효화 조건을 작성했다. 원본 보존, AWS 호출0, 자체 검토이며 독립 승인이 아니다.
2. PR19 고정 후보의 Git bundle을 로컬에서 준비했다. 자격증명·state·full Plan은 전달 묶음에 추가하지 않는다. bundle 무결성/복원은 코드 승인 또는 Runtime 성공이 아니다. 독립 리뷰 전 후보 실행 금지, 실제 업로드/CloudShell 실행은 아직 안 했다.
3. 기존 checkout에서 변경으로 표시되는 Relay RPM 원본 JSON3개에 한정해 `.gitattributes -text`를 추가했다. 원본 blob/hash를 바꾸지 않고 저장된 바이트를 보존한다. Windows/Linux에서 쓰는 Git 줄바꿈 설정 두 경우의 새 checkout을 대조한다. 실제 Linux 호스트 실행을 의미하지 않는다.
4. 과거 준비 문서의 역할 부재/Plan NOT_RUN 안내 위에 현황 링크를 추가했다. 과거 실행 당시 기록 자체는 지우거나 소급 수정하지 않는다.

## 작업창·비공개 원본 인계 시 기록할 최소 항목

- 작업창: 실행자, exact network backend/state, 다른 writer 중단의 실제 확인 근거, 시작과 종료 조건, 실패 시 잠금 소유·프로세스 확인 및 정리 완료까지 창 유지. 현재 lock 부재나 단순 로그인 여부는 합의가 아니다. 시간은 합의 후 기록한다.
- 비공개 Plan: 기존 승인된 전달 경로·수신자, archive/Plan/JSON hash, 실제 수신·자체 재해시 결과, 독립 판정과 한계. 새 공유 권한/외부 링크를 임의 생성하지 않는다.
- 후속 runtime: 대상 host/account/session/source/input·tool version, UTC/KST, 명령/RC/원본/hash, 중단·복구 결과. credential 원문과 full Plan은 GitHub 댓글에 올리지 않는다.

교육장 리포트의 사용액·예상 총비용은 권욱이 중앙 판정한다. USD400 목표/450 중단/500 상한·자부담0을 유지하며 다른 담당자에게 새 비용 승인을 요구하지 않는다. 기존 조건을 갖춘 실행 전에 판단 자료를 갱신한다.
