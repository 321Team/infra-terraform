# ROSA 최종 회수용 본인 키 생성 기간 — 2026-10-26 실제 반영 기록

ROSA destroy 실행에 필요한 하영 본인 키 생성 권한의 기존 기간이 끝나 있어, 사용자 이권욱이 **“00:00 까지 갱신해줘”**라고 승인한 기간으로 기존 인라인 정책의 날짜 두 값만 갱신했다.

## 현재 적용 정책

- AWS 계정: 774055931866, 대상 `321team-hayeoung`.
- AWS 인라인 이름은 기존 `FDS-Hayeoung-OwnAccessKey-P2-v1` 그대로다. 이 폴더의 **v3는 소스 보존 버전**이며 추가 인라인 정책을 만든 것이 아니다.
- Create 허용 시작(UTC): `2026-10-26T07:59:38.796033+00:00`.
- Create 허용 종료: **2026-10-27 00:00 KST 전**, UTC `2026-10-26T15:00:00+00:00`.
- 기존 v2 대비 `DateGreaterThanEquals`·`DateLessThan` 두 값만 다르다. 본인 Resource/PrincipalArn·MFA=true·Create 동작·본인 Update/Delete 조건은 유지했다.
- `SHA256SUMS`는 이 폴더의 정책 파일 바이트 무결성이다. 실제 GetUserPolicy와의 비교는 JSON 의미를 기준으로 했다.

## 실제 수행과 검증

중앙 root가 기존 사용자·정책 원문 불변 및 키0을 확인한 후 해당 정책1개에 PutUserPolicy를 수행했다. **HTTP200**, RequestId `3fd85d06-e82a-420c-9a58-584c86b8eae5`. 실제 GetUserPolicy가 후보와 일치하며 두 날짜 외 차이0을 재검증했다.

| 단계 | 확인한 결과 |
|---|---|
| 후보 정책 시뮬레이션 | 7/7 기대 일치 |
| 실제 부착 정책 시뮬레이션 | 7/7 기대 일치, MissingContextValues0, 사후 후보 주입 없음 |
| 정상 조건 | 본인·MFA·기간 내 Create 허용, 본인 Update/Delete 허용 |
| 거부 조건 | MFA 없음·다른 사용자 대상·기간 이전/이후 Create 거부 |
| 적용 직후 액세스키 | 0개 |
| 중앙의 키 발급·secret/MFA 수신 | 0 |
| 역할 최대 세션 | 기존 FDS-IaC-Operator 10800초를 조회했으며 변경하지 않음 |

시뮬레이션은 조건부 정책 평가다. 하영 실제 MFA 세션·키 생성·destroy 성공이나 프로젝트 인수 완료로 해석하지 않는다. 계정·역할·공용 서비스 회수는 각 실제 단계와 별도다.

## 실행·회수

하영 본인이 기존 승인된 destroy 키트 경로에서 **키0 확인 → 이번 키1개 직접 생성 → 본인 MFA 역할 세션 확보 → 즉시 키 비활성화·삭제 → 키0 확인**을 수행한다. secret을 GitHub·채팅·명령 인수·로그로 보내지 않는다.

정책의 날짜 만료는 새 Create를 제한한다. 이미 만든 키를 자동 삭제하거나 키1개 상한을 IAM이 강제하는 것은 아니다. 생성한 키와 이미 발급된 STS 세션 회수는 구분한다. 최종 일반계정 회수는 ROSA 및 필요한 자원 회수·원본 반출 뒤 중앙에서 수행한다.

## 이상 시 처리

실제 부착 값이 이 보존본과 다르거나 본인 키 상태가 예상과 다르면 추가 발급·재실행을 중단한다. 중앙에서 현재 원문과 이번 변경분을 비교한 후 두 날짜만 기존 v2 값으로 되돌릴 수 있다. 이 경우에도 이미 생성한 키의 별도 회수는 필요하다. 다른 사용자·역할·Guard·Trust·D1 및 다른 변경을 일괄 원복하지 않는다.

## 추적성

- [ROSA 회수 범위·작업창 승인](https://github.com/321Team/infra-rosa/issues/8#issuecomment-6410745369)
- [실제 IAM 갱신 결과](https://github.com/321Team/infra-rosa/issues/8#issuecomment-6411112579)
- 실제 부착 정책 canonical SHA256: `5aa8929f146a6aaf6cae2ca9f0f1c101e24d246cd9e27f1efa350c7f84194cc7`.
- 원본 반출 묶음 `KEY_WINDOW_MIDNIGHT_APPLY.tgz`: `750ad04fe96e4b74590d8e3df9b59162c267171194a1568d0d5a5dac932e457a`, 1,825B. 로컬 수신 후 내부5파일 manifest와 날짜2개 차이를 재검증했다.

정책 JSON과 이 기록만 소스에 편입한다. 운영 원본·CloudTrail 상세·인증정보는 PR에 넣지 않는다. 실제 IAM 반영과 이 PR의 독립 검토·병합은 구분하며, PR 대기는 이미 승인·반영된 권한과 ROSA 회수의 새 차단이 아니다.
