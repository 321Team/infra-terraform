# PR7 Agent RPM 리뷰 후속

CODEX_ASSISTED. 2026-10-08 KST. 작성자 이권욱의 수정/검증 기록이며 독립 APPROVE가 아니다.
원본 지적: [이재환 리뷰5450116916](https://github.com/321Team/infra-terraform/pull/7#pullrequestreview-5450116916).

## 변경과 보안 경계

- AWS 고정 key UID self-signature에서 SHA1(digest algorithm2)을 확인했다. **실제 Stream9 RPM import 실패는 아직 재현하지 못했다.** 해당 의존성을 제거하는 리뷰어 제안대로 system RPM key import를 제거했다.
- 동일한 3.3.5390.0 payload SHA256, 독립 keyring의 정확한 fingerprint, detached GPG 검증 및 정확한 VALIDSIG가 모두 성공해야 로컬 RPM을 설치한다. RPM 헤더 서명 유무/실패를 추정해 무서명이라고 판정하지 않는다.
- `localpkg_gpgcheck=0`은 이미 검증된 로컬 RPM을 설치하는 단일 DNF 명령에만 적용한다. 의존성을 포함한 저장소 패키지 `*.gpgcheck=1`, TLS `*.sslverify=1`은 유지한다. 시스템 crypto-policy, RPM keyring, 저장소 설정을 변경하지 않는다. LEGACY/SHA1 허용, 전역 `--nogpgcheck`, SELinux 해제는 없다.
- 실패 표시는 사전조건 확인 전부터 활성화했다. 초기 실패는 `evidence=NOT_CREATED`, 임시 디렉터리 생성 이후는 실제 경로를 남긴다.
- MOCK의 RPM import는 항상 실패하도록 바꿨다. 성공 경로가 이 호출에 의존하지 않는지 확인하고, GPG key import 실패/로컬 패키지 설치 실패도 중단해야 한다.

## 수행한 검증

`validation/relay-agent-rpm-20261008/`에 새 source manifest, 공식 payload 다운로드 hash, GPG 출력, 명령·종료코드·UTC 시각과 원본 출력 해시를 보존한다. 기존 `relay-stream9-20261008` 증적은 과거 소스의 기록으로 유지한다.

- bootstrap MOCK: 3개 시험/15개 시나리오 PASS. 잘못된 key·서명·hash·패키지, 설치/서비스 실패에서 성공선언을 차단한다.
- 실제 공식 RPM: 고정 SHA256 일치, pinned signer의 detached GPG signature PASS. 로컬 Windows GPG 경로/agent 초기 오류를 별도 원본으로 보존하고 경로 수정 및 public-key 검증용 `--no-autostart` 사용 후 성공했다. 이 Windows 옵션은 Linux bootstrap에 추가하지 않았다.
- Terraform1.16.4/AWS provider6.66.0: 격리 복사본에서 fmt/init backend=false/validate 및 VPN provider MOCK22개 PASS. AWS 자격증명 상속/Cloud Plan/Apply 없음.
- Stream9 disposable-userland 실행 및 CI: **NOT RUN**. 저장소 Actions 설정에서 `Disable actions`, `This setting has been disabled by organization administrators`를 확인했다. CI0건을 PASS로 표시하지 않는다. 이 PR에서 조직 정책을 바꾸지 않았다.

## 독립 실행 및 완료조건

관리자 정책상 허용된 Docker 호스트의 새 개인 작업 경로에서, 재리뷰할 exact HEAD를 체크아웃한다. 운영 서버/Relay나 AWS 자격증명이 있는 컨테이너를 사용하지 않는다. Docker 실행 권한과 공식 quay.io/S3/CentOS 저장소 HTTPS 접근이 필요하다.

```bash
set -euo pipefail
evidence=$(mktemp -d)
git rev-parse HEAD > "$evidence/source-head.txt"
date -u +%FT%TZ > "$evidence/started-utc.txt"
docker pull quay.io/centos/centos:stream9
image=$(docker image inspect quay.io/centos/centos:stream9 --format '{{index .RepoDigests 0}}')
printf '%s\n' "$image" > "$evidence/container-image.txt"
docker run --rm --security-opt no-new-privileges \
  --mount "type=bind,source=$PWD,target=/source,readonly" \
  --mount "type=bind,source=$evidence,target=/evidence" \
  "$image" bash /source/tests/relay-agent-stream9.sh 2>&1 | tee "$evidence/container.log"
```

스크립트는 실제 bootstrap에서 검증·설치 블록을 추출해 사용한다. DEFAULT crypto-policy를 확인하고, 설치 전에 리뷰 원문의 rpm import/Kv/dnf assumeno 명령별 원본·종료코드를 수집한다. 진단 명령의 실패는 데이터이며, 최종 판정은 **실제 소스의 패키지 설치 종료코드0 + 설치 버전 일치 + DEFAULT 유지**이다. `--assumeno` 종료코드만으로 서명 실패라고 판단하지 않는다.

실패 시 비정상 종료하고 증적 디렉터리를 보존한다. 컨테이너는 `--rm`으로 정리되며 호스트 OS/package/보안 설정을 변경하지 않는다. 최종 마커 `PACKAGE_USERLAND=PASS`는 서비스 시작·실제 AMI first boot·Agent Online·VPN Runtime 검증을 의미하지 않는다. 이미지 digest, exact HEAD, 원본 로그를 PR에 연결하고 이하영/이재환의 재검토를 받아야 이 병합 전 확인사항을 닫을 수 있다.

새 workflow는 읽기 전용 token, SHA 고정 actions, 12분 제한, 7일 artifact 보존을 사용한다. 조직 관리자가 허용하기 전 실행되지 않는다. 승인된 검증 호스트의 위 명령으로도 같은 스크립트를 실행할 수 있다.

PR6의 후보 SHA/manifest/hash는 이 수정이 반영된 PR7 HEAD로 함께 갱신한다. `accepted_execution_sha`, `accepted_execution_manifest_sha256`, `execution_approval_reference`는 계속 null이다. 독립 재리뷰·Lead 병합·기존 Freeze/실행 Gate가 별도로 남는다.
