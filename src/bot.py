import datetime
import enum
import logging
import math
import re
import time

from dataclasses import dataclass
from urllib.parse import urlparse

import mastodon

from apscheduler.schedulers.blocking import BlockingScheduler
from lxml import html

from . import common
from . import drawer
from . import messages

PICREW_DOMAIN = 'picrew.me'
MAX_ENTRY = 30

# Default configs
PREPARE_MINUTES = 30
NAME_REVEAL_MINUTES = 15
ANSWER_REVEAL_MINUTES = 30
ALLOW_MULTI = False


class FestivalState(enum.Enum):
    PREPARE = 0
    QUESTION_PUBLISHED = 1
    NAME_REVEALED = 2


@dataclass
class FestivalConfig:
    request_status_id: int
    picrew_link: str
    description: str | None
    prepare_end: datetime.datetime
    name_reveal_at: datetime.datetime
    answer_reveal_at: datetime.datetime
    allow_multi: bool

    state: FestivalState = FestivalState.PREPARE
    entries: set[str] = set()
    prepare_status_id: int | None = None
    question_status_id: int | None = None
    entries_status_id: int | None = None


class Bot:

    RE_PREPARE = re.compile(r'^마감: (?P<time>.+)$', re.M)
    RE_NAME_REVEAL = re.compile(r'^참가자 공개: (?P<time>.+)$', re.M)
    RE_ANSWER_REVEAL = re.compile(r'^정답 공개: (?P<time>.+)$', re.M)
    RE_ALLOW_MULTI = re.compile(r'^다중참가$', re.M)

    RE_TIME = re.compile(r'^(?:(?P<minutes>\d{1,2})분|(?P<abshour>\d{2}):(?P<absminute>\d{2}))$')
    RE_IMMEDIATE = re.compile(r'^(?:즉시|바로)$')

    def __init__(self, mastodon_instance, mastodon_access_token):
        self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')
        self.mastodon = mastodon.Mastodon(
            access_token=mastodon_access_token,
            api_base_url=mastodon_instance
        )
        self.me = self.mastodon.me()
        self.domain = self.mastodon.instance().uri
        self.logger.info(f'Bot initialized: {self.full_acct(self.me.acct)}')

        self.last_status_id: int | None = None
        self.current_festival: FestivalConfig | None = None

    def run(self):
        sched = BlockingScheduler()
        sched.add_job(self.do_job, 'interval', minutes=1)
        sched.start()

    def do_job(self):
        self.logger.debug('Checking notifications...')
        notifications = self.mastodon.notifications(types=['mention'], since_id=self.last_status_id)
        for noti in reversed(notifications):
            self.process_mention(noti.status)

        now = datetime.datetime.now().astimezone()

        if self.current_festival:
            if now >= self.current_festival.prepare_end and self.current_festival.state == FestivalState.PREPARE:
                self.logger.info('Prepare end')
                self.prepare_end()
            if now >= self.current_festival.name_reveal_at \
                    and self.current_festival.state == FestivalState.QUESTION_PUBLISHED:
                self.logger.info('Name reveal')
                self.reveal_entries()
            if now >= self.current_festival.answer_reveal_at \
                    and self.current_festival.state == FestivalState.NAME_REVEALED:
                self.logger.info('Answer reveal')
                self.reveal_answer()

    def process_mention(self, status):
        reply_visibility = status.visibility
        if reply_visibility == 'public':
            reply_visibility = 'unlisted'

        if self.search_picrew_link(status):
            self.logger.info(f'Picrew detected: {status.id}')
            if self.current_festival is None:
                self.start_festival(status)
            else:
                self.logger.info('Existing festival is not ended yet')
                # Mention that festival already running
                msg = messages.ALREADY_RUNNING
                self.mastodon.status_post(msg, in_reply_to_id=status.id, visibility=reply_visibility)
        elif status.media_attachments:
            if not self.current_festival:
                self.logger.info(f'Image detected: {status.id}, But no festival is running')
                # Mention that no festival is running
                msg = messages.NO_RUNNING
                self.mastodon.status_post(msg, in_reply_to_id=status.id, visibility=reply_visibility)
            elif self.current_festival.state != FestivalState.PREPARE:
                self.logger.info(f'Image detected: {status.id}, But not in prepare state')
                # Mention that not in prepare state
                msg = messages.NOT_IN_PREPARE
                self.mastodon.status_post(msg, in_reply_to_id=status.id, visibility=reply_visibility)

        self.last_status_id = status.id

    def start_festival(self, status):
        self.logger.info('Festival started')
        picrew_link = self.search_picrew_link(status)
        assert picrew_link is not None

        content = self.plain_text(status)
        abstime = status.created_at.astimezone()
        prepare_end, name_reveal_at, answer_reveal_at = self.parse_festival_schedule(content, abstime)
        # TODO: Check min time between each event

        allow_multi = bool(self.RE_ALLOW_MULTI.search(content))

        self.logger.info(f'Picrew link: {picrew_link}')
        self.logger.info(f'Prepare end: {prepare_end}')
        self.logger.info(f'Name reveal at: {name_reveal_at}')
        self.logger.info(f'Answer reveal at: {answer_reveal_at}')

        # Support festival description
        description = content
        description = self.RE_PREPARE.sub('', description)
        description = self.RE_NAME_REVEAL.sub('', description)
        description = self.RE_ANSWER_REVEAL.sub('', description)
        description = self.RE_ALLOW_MULTI.sub('', description)
        description = description.strip()

        self.current_festival = FestivalConfig(
            status.id,
            picrew_link,
            description or None,
            prepare_end,
            name_reveal_at,
            answer_reveal_at,
            allow_multi,
        )

        # Post that festival started
        msg = self.create_started_message(status)
        # TODO: retry on failure
        prepare_status_id = self.mastodon.status_post(msg, visibility='public').id
        self.current_festival.prepare_status_id = prepare_status_id

    def prepare_end(self):
        assert self.current_festival is not None
        assert self.current_festival.state == FestivalState.PREPARE

        self.logger.info('Prepare end')

        images: list[tuple[str, dict]] = []  # full_acct, media_attachment

        # Collect entries
        mentions = self.mastodon.notifications(types=['mention'], since_id=self.current_festival.request_status_id)
        for mention in reversed(mentions):
            status = mention.status
            for media in status.media_attachments:
                images.append((self.full_acct(status.account.acct), media))
            self.current_festival.entries.add(self.full_acct(status.account.acct))
            if len(images) >= MAX_ENTRY:
                images = images[:MAX_ENTRY]
                break

        if not self.current_festival.entries:
            # End festival
            msg = messages.FESTIVAL_CANCELLED
            self.mastodon.status_post(msg, in_reply_to_id=self.current_festival.prepare_status_id, visibility='public')
            self.current_festival = None
            return

        self.last_status_id = mentions[0].status.id

        # Generate question/answer image
        drawer.generate_images(images)

        # Forge status with question image
        media = self.upload_media(common.QUESTION_IMAGE_PATH)
        msg = messages.QUESTION

        also_reveal_entries = self.current_festival.name_reveal_at == self.current_festival.prepare_end

        if also_reveal_entries:
            # Append entries to the status
            msg += '\n' + messages.entries(list(self.current_festival.entries))

        msg += '\n\n' + ' '.join(messages.HASHTAGS)

        status_id = self.mastodon.status_post(
            msg,
            in_reply_to_id=self.current_festival.prepare_status_id,
            media_ids=[media.id],
            visibility='public').id
        self.current_festival.question_status_id = status_id

        self.current_festival.state = FestivalState.QUESTION_PUBLISHED

        if also_reveal_entries:
            self.current_festival.state = FestivalState.NAME_REVEALED
            self.current_festival.entries_status_id = status_id

    def reveal_entries(self):
        assert self.current_festival is not None
        assert self.current_festival.state == FestivalState.QUESTION_PUBLISHED

        msg = messages.entries(list(self.current_festival.entries))
        status_id = self.mastodon.status_post(
            msg,
            in_reply_to_id=self.current_festival.question_status_id,
            visibility='unlisted').id
        self.current_festival.entries_status_id = status_id

    def reveal_answer(self):
        assert self.current_festival is not None
        assert self.current_festival.state == FestivalState.NAME_REVEALED

        # Post status with answer image
        media = self.upload_media(common.ANSWER_IMAGE_PATH)
        msg = messages.ANSWER
        msg += '\n\n' + ' '.join(messages.HASHTAGS)

        self.mastodon.status_post(
            msg,
            in_reply_to_id=self.current_festival.entries_status_id,
            media_ids=[media.id],
            visibility='public')

        # End festival
        self.current_festival = None

    def create_started_message(self, status) -> str:
        assert self.current_festival is not None

        requester = self.full_acct(status.account.acct)
        picrew_link = f'{self.current_festival.picrew_link:%H:%M}'
        prepare_end = f'{self.current_festival.prepare_end:%H:%M}'
        name_reveal_at = f'{self.current_festival.name_reveal_at:%H:%M}'
        answer_reveal_at = f'{self.current_festival.answer_reveal_at:%H:%M}'
        description = self.current_festival.description

        if name_reveal_at == prepare_end:
            name_reveal_at = messages.NAME_REVEALED_AT_SAME_TIME

        msg = messages.TPL_FESTIVAL_STARTED.format(
            requester=requester,
            prepare_end=prepare_end,
            name_reveal_at=name_reveal_at,
            answer_reveal_at=answer_reveal_at,
            picrew_link=picrew_link
        )

        if description:
            msg += messages.TPL_FESTIVAL_DESCRIPTION.format(description=description)

        if messages.HASHTAGS:
            msg += '\n\n' + ' '.join(messages.HASHTAGS)

        return msg

    def upload_media(self, path: str):
        media = self.mastodon.media_post(path)
        try_count = 0
        while 'url' not in media or media.url is None:
            try_count += 1
            sleep_duration = math.log2(1 + try_count)
            time.sleep(sleep_duration)
            try:
                media = self.mastodon.media(media)
            except Exception:
                raise
        return media

    def full_acct(self, acct: str) -> str:
        if '@' in acct:
            return acct
        return f'{acct}@{self.domain}'

    @classmethod
    def parse_festival_schedule(cls, content, abstime) \
            -> tuple[datetime.datetime, datetime.datetime, datetime.datetime]:
        if prepare := cls.RE_PREPARE.search(content):
            prepare_end = cls.parse_time(abstime, prepare.group('time'), default_min=PREPARE_MINUTES)
        else:
            prepare_end = abstime + datetime.timedelta(minutes=PREPARE_MINUTES)

        if name_reveal := cls.RE_NAME_REVEAL.search(content):
            name_reveal_at = cls.parse_time(abstime, name_reveal.group('time'), default_min=NAME_REVEAL_MINUTES)
        else:
            name_reveal_at = abstime + datetime.timedelta(minutes=NAME_REVEAL_MINUTES)

        if answer_reveal := cls.RE_ANSWER_REVEAL.search(content):
            answer_reveal_at = cls.parse_time(abstime, answer_reveal.group('time'), default_min=ANSWER_REVEAL_MINUTES)
        else:
            answer_reveal_at = abstime + datetime.timedelta(minutes=ANSWER_REVEAL_MINUTES)

        return prepare_end, name_reveal_at, answer_reveal_at

    @staticmethod
    def search_picrew_link(status) -> str | None:
        html_doc = html.fromstring(status.content)
        for link in html_doc.xpath('//a'):
            href = link.attrib['href']
            if urlparse(href).netloc == PICREW_DOMAIN:
                return href

        return None

    @staticmethod
    def plain_text(status) -> str:
        html_doc = html.fromstring(status.content)

        # Replace <br> with newline
        for br in html_doc.xpath('//br'):
            br.tail = '\n' + (br.tail or '')

        # Replace <p> with newline
        for p in html_doc.xpath('//p'):
            p.tail = '\n\n' + (p.tail or '')

        return html_doc.text_content().strip()

    @classmethod
    def parse_time(cls, abstime: datetime.datetime, timestr: str, default_min: int = 0) -> datetime.datetime:
        # Ensure local timezone
        abstime = abstime.astimezone()

        if match := cls.RE_IMMEDIATE.match(timestr):
            return abstime
        elif match := cls.RE_TIME.match(timestr):
            if minutes := match.group('minutes'):
                return abstime + datetime.timedelta(minutes=int(minutes))
            elif abshour := match.group('abshour'):
                absminute = match.group('absminute')
                new_time = abstime.replace(hour=int(abshour), minute=int(absminute))
                if new_time < abstime:
                    new_time += datetime.timedelta(days=1)
                return new_time

        return abstime + datetime.timedelta(minutes=default_min)
