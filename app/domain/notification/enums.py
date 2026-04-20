"""Notification enums."""

from enum import StrEnum


class NotificationType(StrEnum):
    """알림 종류.

    서버 이벤트(참여 요청/승인/거절/취소, 새 메시지, 연결 요청 등) 에 매칭된다.
    프론트는 type 별로 다른 아이콘/문구/deeplink 를 보여줄 수 있다.
    """

    PARTICIPANT_PENDING = "participant_pending"  # 누가 내 모임에 참여 요청
    PARTICIPANT_APPROVED = "participant_approved"  # 내 참여가 승인됨
    PARTICIPANT_REJECTED = "participant_rejected"  # 내 참여가 거절됨
    PARTICIPANT_LEFT = "participant_left"  # 참여자가 탈퇴함 (호스트에게)
    REVIEW_REQUESTED = "review_requested"  # 모임 종료 후 회고 요청
    NEW_MESSAGE = "new_message"  # 채팅 새 메시지
    CONNECTION_REQUESTED = "connection_requested"  # 누가 팔로우 요청
    CONNECTION_ACCEPTED = "connection_accepted"  # 내 팔로우가 수락됨
