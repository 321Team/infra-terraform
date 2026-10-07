# PR #4 고정 scaffold 정적 검증 패키지

AI 사용: CODEX_ASSISTED. 대상 입력 source `7b69552dbd22ca7c9d24095e080f41d1585dfc5c`, Terraform 1.16.4 / provider 6.66.0. 이전 CloudShell 실행은 version·본문 fmt RC0 후 tfvars 예제 fmt RC3으로 STOP했다. 이 후보는 relay 속성 공백만 수정했으며 실제 fmt/init/validate 재실행 대기다. 값·나머지 입력 11개·lock·backend 4개·helper·시험은 동일하다. unittest는 보조 코드 MOCK 시험이다.

Archive에는 source.json의 12개 원본 Terraform 파일, helper·시험·인계 문서·이 README·PACKAGE_SHA256SUMS만 포함한다. 의존성/provider binary, credential, state, 기존 bootstrap collector를 포함하지 않는다. Archive checksum은 이 경로의 ARCHIVE_SHA256SUMS 및 인계 코멘트에서 확인한다. 최종 PR HEAD는 해당 코멘트에 고정한다. 원본 Terraform 입력의 HEAD와 실행 보조 코드의 최종 HEAD를 구분한다.

CloudShell에서 새 archive를 받은 후 다음 순서로 실행한다. 현재 세션의 Terraform 1.16.4 실제 절대경로를 먼저 지정한다. 다른 세션의 설치 경로를 가정하지 않는다. 첫 단계 hash/압축 해제/내부 manifest가 실패하면 멈춘다. 쉘 strict 옵션을 켜지 않는다. 이미 PASS한 보조 시험 8건은 helper·시험 변경이 없으므로 반복하지 않는다. 최초 보조 시험은 `python3 -m unittest discover -s tests -p 'test_stage_a_static.py' -v`로 별도 실행할 수 있다.

```bash
(
cd "$HOME" || exit 1
umask 077
# 전달받은 archive SHA-256으로 sha256sum -c - 를 먼저 실행한다.
# 실제 확인한 절대경로로 이 값을 지정한 후 실행한다.
stage_a_tf_binary="/actual/path/to/terraform-1.16.4"
[ -x "$stage_a_tf_binary" ] || { printf 'STOP: Terraform 경로를 확인\n'; exit 1; }
stage_a_run_dir=$(mktemp -d "$HOME/fds-stage-a-static-run.XXXXXX") || exit 1
tar --no-same-owner -xzf "$HOME/fds-stage-a-static-20261007.tar.gz" -C "$stage_a_run_dir" || exit 1
cd "$stage_a_run_dir/fds-stage-a-static-20261007" || exit 1
sha256sum -c validation/stage-a-20261007/PACKAGE_SHA256SUMS || exit 1
python3 scripts/validate-stage-a.py --terraform "$stage_a_tf_binary"
stage_a_static_rc=$?
printf 'STAGE_A_STATIC_RC=%s\n' "$stage_a_static_rc"
exit "$stage_a_static_rc"
)
```

helper는 별도 개인 복사본으로 동작한다. Root·일반 IAM·MFA role 중 어떤 CloudShell 세션이든 이 정적 실행에는 AWS credential을 사용하지 않는다. AWS identity 확인 API도 실행하지 않는다. 개인 업무 role 권한을 대신 증명하지 않는다. 반환 RC·summary JSON·capture manifest RC를 보내고 로그는 실패 원인 확인에 필요한 부분만 공유한다. 전체 state나 credential을 출력하지 않는다.

판정·중단·복구·network/VPN 후속 구현 인계는 [상세 문서](../../docs/STAGE_A_STATIC_HANDOFF_20261007.md)를 따른다. `TerraformStatic=PASS`도 backend/runtime/Stage-A GO나 apply 승인이 아니다. 실패할 경우 capture를 보존하고 자동 재시도·lock 변경·provider mirror 변경을 하지 않는다.
