"""Контракты операций над платами."""

from backend.application.dto.boards.announce_board_command import AnnounceBoardCommand
from backend.application.dto.boards.board_command_result import BoardCommandResult
from backend.application.dto.boards.claim_board_command import ClaimBoardCommand
from backend.application.dto.boards.pair_board_command import PairBoardCommand
from backend.application.dto.boards.set_network_command import SetNetworkCommand

__all__ = [
    "AnnounceBoardCommand",
    "BoardCommandResult",
    "ClaimBoardCommand",
    "PairBoardCommand",
    "SetNetworkCommand",
]
