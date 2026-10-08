# 중앙 AWS 읽기 전용 사전조회 접수

CODEX_ASSISTED. **AWS_READ_ONLY=COMPLETE / STAGE_A_READY=NO**. 사용자 로그인 완료와 중앙 계정 확인 후 기존 사전조회 범위에서 브라우저 CloudShell로 직접 실행했다. 자기 실행 접수이며 타인의 독립 Evidence 승인으로 표시하지 않는다.

## 실행 식별과 무결성

- 시각: 2026-10-07 **23:56:33.318~23:56:38.354 KST** (UTC 14:56:33.318~14:56:38.354).
- 대상: 채택 중앙 계정 끝1866, ap-northeast-2 CloudShell. STS identity는 해당 중앙 계정의 root. 전체 ARN·host는 비공개 원본 summary/STS에 보존한다.
- Source: PR6 원HEAD `d8a35b9e0d7077df4ddc12434738c779839f34a6`의 `scripts/collect-phase2-preflight.py` 불변.
- Source SHA256: `c25063e93f242f5cc97e6ca0952c514eb530633c387b44b2bba0ad01013f99f8`. CloudShell 전달본 해시와 일치 확인 후 실행.
- 실행: `python3 collect-phase2-preflight.py --output-parent "$HOME"`.
- CloudShell capture: `/home/cloudshell-user/fds-phase2-preflight-c3ee9scx`. summary는 명령 배열/개별 시작·종료 UTC/RC/timeout/host/platform/source SHA를 보존한다.
- 결과: `COLLECTION=COMPLETE; STAGE_A_READY=NO; AWS_MUTATION=NOT_RUN`. CLI 실패 RC를0으로 바꾸지 않고 아래 부재 결과로 분류했다. 최상위 종료 코드는 별도 보존 파일이 없으므로 개별 API RC와 collection 출력으로 판정한다.
- 원본 archive: `fds-phase2-preflight-c3ee9scx-evidence.tar.gz`, 2,210 bytes. SHA256 `8bdac7bbe9596691544e6759f81efc2dadde98b20afe10dc9aae7359518d4e46`.
- CloudShell manifest 11개 OK 후 archive를 다운로드했다. 로컬 archive SHA 일치 및 stdout/stderr 10개+summary 1개를 **11/11 재해시 일치** 확인했다. 무결성 성공은 역할/세션/AMI Runtime 성공과 별개다.
- 비공개 로컬 보존: 작업 경로 `work/phase2-sequence-20261007/private-evidence/` 아래 archive와 동명 capture 폴더. 원본 자체는 Git에 게시하지 않는다.

## 실제 결과

| API / 대상 | RC | 관측 결과 | 해석 |
|---|---:|---|---|
| STS GetCallerIdentity | 0 | 중앙 계정·root 일치 | 중앙 사전조회 identity 확인. 본인 MFA 역할 시험 아님 |
| EC2 DescribeImages / exact AMI+owner | 0 | `ami-079a2667364cee804`, owner `125523088429`, available/x86_64/ebs, CentOS Stream 10 x86_64 20260330 | metadata 확인만 완료 |
| IAM GetRole / FDS-IaC-Operator | 254 | NoSuchEntity | **ABSENT**. AccessDenied를 부재로 오인한 결과가 아님 |
| IAM GetRole / FDS-Network-Operator | 254 | NoSuchEntity | **ABSENT**. grant/readback·본인 세션 미완료 |
| SSM DescribeDocument / SSM-SessionManagerRunShell | 254 | InvalidDocument | 서울 조회에서 해당 이름 문서 없음, **NOT_FOUND_REVIEW_REQUIRED** |

모든 호출 timeout=false. 역할 부재로 attach/inline 목록 호출은 건너뛰었고, 문서 부재로 GetDocument/version 재조회도 실행하지 않았다. 다른 이름의 역할·문서나 다른 리전 전체에 대한 부재를 주장하지 않는다.

AMI CreationDate는 `2026-03-31T01:28:01.000Z`. 이미지의 root mapping 기본값은 gp2/10GiB/Encrypted=false/DeleteOnTermination=true다. 이는 **이미지 metadata**이며 실제 Relay 볼륨 설정이 아니다. 소스의 암호화/크기/삭제정책 및 생성 후 EBS 검증을 대체하지 않는다. Agent·firewalld·repo·Libreswan 내부 상태는 NOT_VERIFIED다.

## 후속 Gate와 실행 경계

1. #35 이하영: network/vpn 전체 action/ARN/tag/조건 inventory·완결 permissions와 source 검토. 현재 두 human role은 실제 부재이므로 기존 부분 simulation을 role 부여 완료로 사용할 수 없다.
2. 중앙 이권욱: 검토된 입력 이후 fresh before/ValidatePolicy/변경 delta 검증 및 기존 승인 범위의 부여·readback. 그 뒤 각 본인 MFA 역할 시험. root에서 일반 Plan/Apply를 수행하지 않는다.
3. Session document 부재는 #35/#37에 인계한다. 실제 세션에 사용할 문서의 소유·공급/생성 시점·정확 ARN/version·기록 정책을 정리한 후 해당 단계에서 검증한다. 이를 임의 문서 생성 승인이나 network plan의 새로운 선행조건으로 삼지 않는다.
4. AMI metadata 확인과 별개로 Stream10 SSM 지원 근거, exact Agent/firewalld/repo와 bootstrap 적합성은 미해결이다. #37 생성 Gate와 route 활성화 Gate를 구분한다.

AWS 구성 변경·역할 부여·인스턴스 생성·Terraform Plan/Apply·장애주입은 **NOT_RUN**. CloudShell의 수집기/증적 파일 생성만 수행했다. 기존 중앙 bootstrap·부분 simulation은 반복하지 않았으며 원본을 삭제하지 않는다. 실패/불일치 시 증적을 보존하고 다음 쓰기 단계로 진행하지 않는 절차다. Architecture Freeze와 비용/생성 GO는 HOLD다.
