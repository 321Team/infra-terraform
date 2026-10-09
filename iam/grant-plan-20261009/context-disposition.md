# MissingContext27 판정안

원본 결과는 수정하지 않는다. 하영의 PR17 승인은 아래 최종 수용을 제외했다. 아래는 이권욱 판정을 위한 제안이며, 검토자가 실제 수용을 기록하기 전까지 PENDING이다.

| case | 원본 결정 | 해당 statement가 참조하는 누락값 | 제안 |
|---|---|---|---|
| N26-natgateway | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N26-elastic-ip | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N1-wrong-project | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N1-omitted-project | implicitDeny | aws:RequestTag/Project | 의도적 Project 생략 음성 사례로 정적 설명 수용 |
| N3 | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N5 | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N7 | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N10 | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N11-unencrypted | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N11-oversized | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N12-role | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N12-service | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N14 | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N17 | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N25 | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N20-parent-scope | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N20-request-context | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N21-parent-scope | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N21-request-context | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N22-subnet-parent-scope | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N22-subnet-request-context | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N22-eip-parent-scope | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N22-eip-request-context | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N23-subnet-parent-scope | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N23-subnet-request-context | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N23-sg-parent-scope | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |
| N23-sg-request-context | implicitDeny | 없음 | 무관한 조건값 보고로 정적 설명 수용 |

26개는 실제 Action/Resource 적용 statement에 없는 키, 1개는 의도적 Project 누락이다. 해당 판정 수용은 시뮬레이션 해석에 한정한다. 실제 역할·서비스 다중 자원 인가는 별도 단계이며 전체70 PASS로 바꾸지 않는다. 정책 변경이 없으므로 동일70-case를 재실행할 이유는 없다. 기존 Apply/Phase1 AC를 확대하지 않는다.
