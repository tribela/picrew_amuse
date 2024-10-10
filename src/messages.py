ALREADY_RUNNING = "이미 진행중인 픽락관이 있습니다"
NO_RUNNING = "진행중인 픽락관이 없습니다"
NOT_IN_PREPARE = "참가신청이 마감되었습니다"

FESTIVAL_CANCELLED = "참가자가 부족하여 픽락관이 취소되었습니다"

NAME_REVEALED_AT_SAME_TIME = "문제 공개와 동시에"

TPL_FESTIVAL_STARTED = (
    '픽락관이 시작되었습니다\n'
    '참가신청 마감: {prepare_end}\n'
    '참가자 공개: {name_reveal_at}\n'
    '정답 공개: {answer_reveal_at}\n'
    '주최자: {requester}\n'
    '피크루 링크: {picrew_link}'
)

TPL_FESTIVAL_DESCRIPTION = (
    '\n\n개최자 메시지:\n'
    '{description}'
)

QUESTION = '문제를 공개합니다'
ANSWER = (
    '정답을 공개합니다\n'
    '다음에 또 만나요!'
)


def entries(entries: list[str]) -> str:
    return (
        '참가자 목록:\n'
        + '\n'.join(map(lambda x: f'- {x}', entries))
    )


HASHTAGS = ['#픽락관']
