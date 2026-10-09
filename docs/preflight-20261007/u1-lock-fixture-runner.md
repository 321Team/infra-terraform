# 권욱 U1-I3 잠금 fixture 실행기

> **2026-10-10 실행 환경 수정 후보:** CloudShell 홈 여유603MB에서 provider6.66.0 설치가 `no space left on device`로 STOP했다. 증적·source·saved Plan은 기존 HOME0700 경로에 보존하고, provider와 backend 로컬 metadata만 실행기가 새로 만든 `/tmp/fds-u1-data-*`0700 경로에 둔다. `TF_DATA_DIR`은 실행기가 내부 설정하며 사용자 상속 override는 계속 거부한다. backend 검증도 실제 init이 쓴 그 경로를 읽는다. 임시 경로는 summary에 기록하며 자동 삭제하지 않는다. 재접속/환경 종료로 임시 데이터가 사라지면 새 회차로 init한다. 원본 로그와 실패 회차를 보존하고, `/tmp` 전체 정리나 HOME 재지정은 하지 않는다. 수정본 STATIC/MOCK와 독립 리뷰·RUNTIME은 각각 별도 판정한다.

CODEX_ASSISTED. 2026-10-09. **작성·STATIC/MOCK 준비이며 AWS RUNTIME NOT_RUN.**

기존 [U1-I3 절차](gwonuk-u1-plan.md#i3-재현-절차-grant-후-검토된-시험-회차)를 한 사람이 순차 실행할 수 있도록 구현한다. 시험용 잠금이 유지되는 동안 Terraform Plan을 시도한다. 실제 Terraform 프로세스 두 개의 경쟁, 강제 종료, I5 장애 복구 전체를 검증하는 도구가 아니다. Apply 및 실제 인프라 생성은 없다.

## 대상과 승인 경계

- 실행 위치: 서울 개인 CloudShell, 사용자 `321team-gwonuk`의 기존 MFA 경로로 얻은 `FDS-IaC-Operator/321team-gwonuk` 임시 역할 환경. root·다른 사용자·장기키를 대체 경로로 쓰지 않는다.
- 계정774055931866, bucket `fds-tfstate-774055931866-ap-northeast-2`.
- state `phase2/network/terraform.tfstate`, fixture `phase2/network/terraform.tfstate.tflock` 고정. 다른 backend/workspace 또는 이미 state가 존재하는 Apply 후 환경은 미지원이며 STOP한다.
- 승인 source `81162467bb2f99a099cb7067fbc3f63e1c0dbed8`의 network6파일을 Git blob에서 새 개인 디렉터리에 추출한다. 실행기 수정 브랜치의 미검토 network 변경이나 기존 작업 폴더의 tfvars는 소비하지 않는다.
- Terraform1.16.4 공식 배포본의 출처·해시 확인은 기존 준비 절차로 수행한다. 실행기는 버전·source hash·provider lock 불변·backend 정확성을 확인하며 바이너리의 공급망 서명을 독립 검증하는 도구가 아니다. provider6.66.0 및 reviewed lock을 사용한다.
- 실행기는 AssumeRole/OTP 입력을 하지 않는다. 기존 절차로 준비한 임시 credential 환경을 소비하고 credential 값은 명령 인자·출력·로그에 넣지 않는다. 환경 전체를 저장하지 않으며 stdout/stderr 저장 전 알려진 credential 값도 제거한다. 만료까지 충분한 시간이 남은 새 세션으로 시작한다.
- 새 사용자·권한·root 사용 불필요. 실행기는 실제 S3 쓰기가 있으므로 순수 Pre-check 예외로 자기 승인하지 않고 코드 리뷰 후 소비한다.
- **작업창은 별도 실확인:** 하영 등 같은 state 실행자가 현재 실행 중이지 않고, 시험 정리·재시도 종료까지 Plan/Apply를 시작하지 않는다는 기록을 확보한다. `--window-confirmation` 문자열이나 현재 lock 부재가 작업창 합의를 만들어 주지는 않는다. PR194 편입 리뷰와 권욱의 기존 본인 역할 시험은 별개다.

## 오프라인 검증

```sh
python3 -m unittest discover -s tests -p test_u1_lock_fixture.py -v
```

테스트는 합성 객체·프로세스 응답을 사용한다. AWS/Terraform 실행·credential·S3 쓰기는0이며, 성공 경로뿐 아니라 기존 state/lock, 403, 생성 경합/timeout, ID 불일치, 권한 오류, 계획의 예상 밖 성공, lock 교체/ETag 변경, 삭제 경합/timeout, 재시도 실패/drift/잔여 lock 및 로그 credential 제거를 확인한다. 이 MOCK PASS는 실제 S3 조건부 동작이나 IAM 허용/거부 성공의 증거가 아니다.

## 실행 순서

경로는 실제 배치된 checkout·공식 바이너리의 절대 경로로 정한다. 아래 REPO/TF는 실행자가 확인한 경로를 넣는 자리다. 새로운 MFA 코드나 키를 이 명령에 넣지 않는다.

1. 중앙 기존 읽기 권한의 최신 readback으로 버킷 versioning=Enabled, 정책·역할 trust 불변을 확인하고 기존 MFA 역할 세션을 준비한다. 일반 역할 ARN 출력만으로 MFA 원본 증명을 대체하지 않는다. 실행기 코드 리뷰·작업창 근거를 함께 기록한다.
2. 기본 모드로 읽기 전용 사전 점검한다. 새 HOME0700 디렉터리에 고정 source 추출, init/validate(default workspace)/backend 대조와 state prefix·lock 읽기만 수행한다. provider 설치와 로컬 파일 생성은 있지만 AWS 변경 명령은 없다.

```sh
python3 tools/u1_lock_fixture.py --repo "$REPO" --terraform "$TF"
```

3. 위 선행조건을 갖춘 회차에만 실행한다. 기본 모드는 Plan/fixture를 실행하지 않는다. 실행 모드에서도 fresh preflight를 다시 수행한다.

```sh
python3 tools/u1_lock_fixture.py --repo "$REPO" --terraform "$TF" \
  --execute --window-confirmation '실제 작업창 확인 기록의 링크 또는 식별자'
```

4. `FIXTURE_COLLISION_RETRY_PASS`와 종료코드0, 아래 원본을 함께 확인한다. `READ_ONLY_PREFLIGHT_PASS`는 읽기 전용 점검 성공일 뿐 I3 성공이 아니다.

## 실제 시험의 판정

1. prefix가 비었고 GetObject가 정확히 NoSuchKey로 끝난 경우에만 진행한다. 403/timeout/기존 객체는 STOP. S3 요청은 expected bucket owner·서울을 고정한다.
2. UUID 포함 Terraform LockInfo fixture를 `If-None-Match: *`, AES256으로 단1회 생성한다. 409/412/권한 오류/timeout에는 덮어쓰기·자동 재시도가 없다. non-null VersionId 없으면 삭제하지 않고 STOP한다.
3. GetObject의 원본 바이트·ID·ETag를 대조한다. Plan은 lock-timeout5초, detailed-exitcode이며 **rc1 + 잠금 획득 오류 + 이번 ID**가 함께 있어야 충돌이 입증된다. 다른 rc1은 PASS가 아니다.
4. 삭제 직전 동일 바이트·ID·ETag를 재검증하고 exact fixture key를 `If-Match: 원래 ETag`로만 삭제한다. version-id 삭제, 실제 state DeleteObject, force-unlock은 코드에 없다.
5. NoSuchKey·빈 prefix 확인 후 Plan 재시도(lock-timeout60초)를 수행한다. rc2 및 고정 빈-state 설계의 managed create20/update0/delete0, 현재 잠금 부재·빈 prefix까지 모두 맞아야 PASS다. saved plan은 생성하지만 Apply하지 않는다.

조건부 쓰기와 ETag 삭제는 [AWS PutObject](https://docs.aws.amazon.com/cli/latest/reference/s3api/put-object.html) / [DeleteObject](https://docs.aws.amazon.com/cli/latest/reference/s3api/delete-object.html)를 따른다. 삭제는 versioned bucket의 현재 객체에 대한 삭제 표식 생성이며 과거 version 영구삭제를 요청하지 않는다. 작업창 중 다른 주체가 bucket versioning/정책을 변경하는 상황을 허용하지 않는다.

## 중단·복구

오류·timeout·Ctrl-C 발생 시 요약은 STOP이며 **자동 finally 삭제를 하지 않는다.** AWS에 적용됐지만 응답을 받지 못했거나 다른 프로세스가 살아 있을 수 있기 때문이다. 원래 작업창을 해제하기 전에 잔여 잠금을 확인한다.

1. 출력된 개인 evidence 경로의 execution-records.json, fixture.json, owned-lock-receipt.json(생성 응답을 수신한 경우)을 보존한다. fixture ID와 SHA256, exact bucket/key, ETag, 실행 프로세스 종료를 대조한다.
2. 기존 개인 MFA 역할로 해당 exact key만 새 로컬 경로에 GetObject 한다. NoSuchKey이면 부재로 기록하고, AccessDenied이면 부재로 취급하지 않는다. 다른 ID·바이트면 이 실행기가 정리하지 않는다.
3. timeout으로 생성 결과가 불명확할 때는 새 readback이 fixture 원문과 일치하는지부터 확인한다. 생성 응답의 ETag를 받지 못했다면 그 사실과 새 조회 ETag를 분리 기록한다. 사람이 작업창·프로세스 종료·소유 및 버킷 versioning을 확인하기 전에는 삭제하지 않는다.
4. 자기 fixture로 확인된 경우에만 기존 승인된 I3 절차에 따라 exact `.tflock`에 조건부 DeleteObject(현재 ETag·expected owner)를 한 번 수행한다. 다시412/timeout이면 재조회로 돌아가며 무조건 삭제·version 삭제·force-unlock하지 않는다. 정상 부재를 확인한 뒤 별도 회차로 재시험한다.
5. 재시도 Plan 자체의 잠금이 남았다면 fixture와 같은 것으로 취급하지 않는다. Terraform 프로세스·해당 Lock ID부터 확인하고 기존 I5 복구 절차로 분리한다. 이번 runner의 성공으로 I5를 완료 처리하지 않는다.

## 증적과 남는 작업

출력은 `$HOME/fds-u1-lock-*` 개인0700 폴더다. 명령·시각·RC/timeout·stdout/stderr SHA, 호스트·caller, 고정 source manifest, fixture 원문/ETag/version receipt, Plan과 현재 lock 조회 결과, 요약, top-level SHA256SUMS를 보존한다. `network/` 아래 backend/plugin 캐시는 manifest 대상이 아니며 원본 증적 묶음으로 오인하지 않는다. 명령 경로와 Plan 전체는 비공개로 유지한다. 공개용 파생 자료는 별도 선별·비밀 검사를 거친다.

남은 것은 코드 독립 리뷰, 실제 작업창, fresh MFA/readback 후 RUNTIME 실행과 증적 독립 편입이다. whole U1/AC4/Phase1 인수·비용 판정·Apply GO를 이번 STATIC/MOCK 준비로 변경하지 않는다. 예상 밖 source/state/권한 변화가 있으면 기존20create 기대값을 임의 수정하지 않고 재검토한다.
