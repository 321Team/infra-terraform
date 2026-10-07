# Candidate validation — 2026-10-07 KST

| 구분 | 실제 수행 결과 | 증적 |
|---|---|---|
| STATIC network | 6단계 RC0 중 정적 검사, Terraform 1.16.4/AWS 6.66.0, error/warning 0 | [summary](network/summary.json), 각 stdout/stderr |
| MOCK network | mock provider plan 3 passed / 0 failed | [원본](network/mock-test.stdout) |
| STATIC vpn | 6단계 RC0 중 정적 검사, Terraform 1.16.4/AWS 6.66.0, error/warning 0 | [summary](vpn/summary.json), 각 stdout/stderr |
| MOCK vpn | mock provider plan 13 passed / 0 failed | [원본](vpn/mock-test.stdout) |
| HELPER OFFLINE | 자격증명 상속 제거, 변경 source/추가 auto.tfvars 차단 3건 PASS | [원본](helper-and-shell/helper-unittest.stderr) |
| SHELL STATIC | 합성 패키지명으로 렌더한 bootstrap의 bash 문법 검사 RC0 | [summary](helper-and-shell/summary.json) |
| CI / RUNTIME / cloud plan·apply | NOT_RUN | GitHub Actions 실행이나 AWS/서버 동작 결과가 아님 |
| REVIEW | 작성 측 자체 검토 수행, 새 HEAD 사람 독립 승인은 별도 | [인계·미결](../../docs/NETWORK_VPN_CANDIDATE_20261007.md) |

호스트·UTC 실행 시각·정확 명령·RC·CLI SHA·source 전후 hash는 각 summary에 있다. KST는 UTC+09:00이다. 두 root의 source/lock 15개 파일은 전후 동일하다. `capture-manifest.json`은 같은 디렉터리의 원본 파일 해시를 기록한다. helper-and-shell은 검사 당시 helper/test/template/render hash도 기록한다. Git 속성으로 이 디렉터리의 줄바꿈 변환을 막아 원본 capture bytes를 보존한다.

이 기록은 새 저장소 경로·격리 helper에서 수행한 검증이다. 앞선 로컬 v1.1/v1.2 증적과 PR #4 Stage-A 기록을 덮어쓰지 않는다. [source.json](source.json)의 로컬 ZIP hash는 출처 연결이며 ZIP을 이 저장소에 포함했다는 뜻이 아니다.

`resource-api-inventory.json`과 `passrole-reference.fragment.json`은 검토 자료이며 배포 가능한 전체 IAM 정책이 아니다. `bootstrap.MOCK.sh`는 **문법 검사 입력만**이며 실제 서버 실행/패키지 설치/Agent Online 시험에 쓰지 않았다. hash 일치는 무결성을 뜻하고 기능·승인·AC를 보장하지 않는다.
