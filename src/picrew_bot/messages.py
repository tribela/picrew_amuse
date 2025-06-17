HASHTAGS = ['#픽락관']
HASHTAGS_LINE = '\n\n' + ' '.join(HASHTAGS) if HASHTAGS else ''

ALREADY_RUNNING = "이미 진행중인 픽락관이 있습니다"
NO_RUNNING = "진행중인 픽락관이 없습니다"
NOT_IN_PREPARE = "참가신청이 마감되었습니다"

FESTIVAL_CANCELLED = "참가자가 부족하여 픽락관이 취소되었습니다"
FESTIVAL_FAILED = '픽락관 생성에 실패했습니다'
FESTIVAL_TOO_LONG = '기간이 너무 깁니다. {duration} 이내로 설정해주세요'

NAME_REVEALED_AT_SAME_TIME = "문제 공개와 동시에"

ANSWER = (
    '정답을 공개합니다\n'
    '다음에 또 만나요!'
    + HASHTAGS_LINE
)


def question(with_entries: list[str] | None) -> str:
    return (
        '문제를 공개합니다'
        + (('\n' + entries(with_entries)) if with_entries else '')
        + HASHTAGS_LINE
    )


def festival_started(
        requester: str,
        picrew_link: str,
        prepare_end: str,
        name_reveal_at: str,
        answer_reveal_at: str,
        description: str | None) -> str:
    return (
        f'픽락관이 시작되었습니다\n'
        f'참가신청 마감: {prepare_end}\n'
        f'참가자 공개: {name_reveal_at}\n'
        f'정답 공개: {answer_reveal_at}\n'
        f'주최자: {requester}\n'
        f'피크루 링크: {picrew_link}\n'
        + (f'\n개최자 메시지:\n{description}\n' if description else '')
        + '참가하시려면 이 메시지에 DM으로 이미지를 보내주세요'
        + HASHTAGS_LINE
    )


def entries(entries: list[str]) -> str:
    return (
        '참가자 목록:\n'
        + '\n'.join(map(lambda x: f'- {x}', entries))
    )
