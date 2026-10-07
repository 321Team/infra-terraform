# PR #4 고정 scaffold 정적 검증 패키지

AI 사용: CODEX_ASSISTED. 대상 입력 source `7b69552dbd22ca7c9d24095e080f41d1585dfc5c`, Terraform 1.16.4 / provider 6.66.0. **현재 판정은 `TerraformStatic=PASS`(사용자 CloudShell 실행 출력 접수)이며 PR #4는 병합 완료다.** 이전 tfvars 예제 fmt RC3 STOP·재실행 대기는 과거 이력이다. [성공 접수·승인·병합의 시점과 증거 한계](RESULT_RECEIPT_20261007.md)를 확인한다. assistant의 직접 CloudShell 실행이나 원본 capture 36개 독립 재해시 결과가 아니다.

Archive에는 source.json의 12개 원본 Terraform 파일, helper·시험·**당시** 인계 문서·README·PACKAGE_SHA256SUMS만 포함한다. 의존성/provider binary, credential, state, 기존 bootstrap collector는 없다. `fds-stage-a-static-20261007.tar.gz`, `ARCHIVE_SHA256SUMS`, `PACKAGE_SHA256SUMS`는 PR #4의 원본 bytes를 보존한다. **PACKAGE_SHA256SUMS는 압축 해제한 원본 패키지에서 검사**하며, 현재 checkout의 갱신 문서와 혼용하지 않는다. 원본 archive 내부의 대기/NOT_RUN 문구는 당시 기록이다.

현재 저장소의 source·helper·시험·갱신 문서·접수 기록은 저장소 루트에서 `sha256sum -c validation/stage-a-20261007/CHECKOUT_SHA256SUMS`로 검사한다. 이 목록은 원본 패키지 재발행이나 새 Terraform 검증 결과가 아니다. archive를 재생성·추가하지 않았으며 동일 소스 STATIC과 영향 없는 보조 시험은 반복하지 않는다. 아래는 **재현이 필요할 때** 사용하는 원본 패키지 절차다.

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
