from typing import Optional, Tuple
import numpy as np
import numba as nb
import chess
import chess.svg

WRONG_PIECE_COLOR_PENALTY = -1
ILLEGAL_MOVE_PENALTY_1 = -0.1
ILLEGAL_MOVE_PENALTY_2 = -0.1
LEGAL_MOVE_REWARD = 0.01


@nb.njit('int8(types.unicode_type)',cache=True)
def piece(name: str) -> int:
    pieceS = {
        'PAWN': 1,
        'pawn': -1,
        'ROOK': 2,
        'rook': -2,
        'KNIGHT': 3,
        'knight': -3,
        'BISHOP': 4,
        'bishop': -4,
        'QUEEN': 5,
        'queen': -5,
        'KING': 6,
        'king': -6,
    }

    return pieceS[name]

@nb.njit(cache=True)
def piece_to_fen(piece: int) -> str:
    piece_map = {
        1: 'p',
        -1: 'P',
        2: 'r',
        -2: 'R',
        3: 'n',
        -3: 'N',
        4: 'b',
        -4: 'B',
        5: 'q',
        -5: 'Q',
        6: 'k',
        -6: 'K',
        0: ' ',
    }

    return piece_map[piece]

@nb.njit('types.unicode_type(int8[:,:])', cache=True)
def to_fen(board: np.ndarray) -> str:
    """
    converts the board to a fen string
    """
    
    fen = ''
    for row in board:
        empty = 0
        for piece in row:
            if piece == 0:
                empty += 1
            else:
                if empty > 0:
                    fen += str(empty)
                    empty = 0
                fen += piece_to_fen(piece)
        if empty > 0:
            fen += str(empty)
        fen += '/'
    fen = fen[:-1]
    return fen


@nb.njit('int8[:,:]()',cache=True)
def generate_start_board() -> np.ndarray:
    board = np.zeros((8, 8), dtype=np.int8)

    board[0, :] = np.array([0             , 0             , 0             , piece('PAWN'), piece('ROOK'), piece('BISHOP'), piece('KNIGHT'), piece('KING')  ], dtype=np.int8)
    board[1, :] = np.array([0             , 0             , 0             , 0           , piece('PAWN'), piece('PAWN')  , piece('QUEEN') , piece('KNIGHT')], dtype=np.int8)
    board[2, :] = np.array([0             , 0             , 0             , 0           , 0           , piece('PAWN')  , piece('PAWN')  , piece('BISHOP')], dtype=np.int8)
    board[3, :] = np.array([piece('pawn')  , 0             , 0             , 0           , 0           , 0             , piece('PAWN')  , piece('ROOK')  ], dtype=np.int8)
    board[4, :] = np.array([piece('rook')  , piece('pawn')  , 0             , 0           , 0           , 0             , 0             , piece('PAWN')  ], dtype=np.int8)
    board[5, :] = np.array([piece('bishop'), piece('pawn')  , piece('pawn')  , 0           , 0           , 0             , 0             , 0             ], dtype=np.int8)
    board[6, :] = np.array([piece('knight'), piece('queen') , piece('pawn')  , piece('pawn'), 0           , 0             , 0             , 0             ], dtype=np.int8)
    board[7, :] = np.array([piece('king')  , piece('knight'), piece('bishop'), piece('rook'), piece('pawn'), 0             , 0             , 0             ], dtype=np.int8)
    
    return board

@nb.njit(cache=True)
def inbounds(x: int, y: int):
    return 0 <= x < 8 and 0 <= y < 8

@nb.njit(cache=True)
def is_starting_position(x: int, y: int, piece: int):
    initial_board = generate_start_board()
    return initial_board[y, x] == piece

@nb.njit('int8[:,:](int8[:,:], int32, int32)', cache=True)
def pawn_legal_moves(board: np.ndarray, x: int, y: int):
    moves = np.zeros((8, 8), dtype=np.int8)
    piece = board[y, x]
    is_init_pos = is_starting_position(x, y, piece)
    
    # Determine the direction the pawn is moving based on its color
    if piece > 0:  # white pawn
        direction = 1
    else:  # black pawn
        direction = -1
    
    # Check if the pawn can move one square forward
    if inbounds(y+direction, x) and board[y+direction, x] == 0:
        moves[y+direction, x] = piece
        
        # Check if the pawn can move two squares forward from its starting position
        if inbounds(y+2*direction, x) and is_init_pos and board[y+2*direction, x] == 0:
            moves[y+2*direction, x] = piece
    # Check if the pawn can move one square on the side
    if inbounds(y, x - direction) and board[y, x - direction] == 0:
        moves[y, x - direction] = piece
        
        # Check if the pawn can move two squares forward from its starting position
        if inbounds(y, x - 2*direction)  and is_init_pos and board[y, x - 2*direction] == 0:
            moves[y, x - 2*direction] = piece
    
    # Check if the pawn can capture diagonally forward
    if inbounds(y+direction, x-direction) and board[y+direction, x-direction] * piece < 0:
        moves[y+direction, x-direction] = piece
        
    # Check if the pawn can capture diagonally to its left
    if inbounds(y-direction, x-direction) and board[y-direction, x-direction] * piece < 0:
        moves[y-direction, x-direction] = piece
    # Check if the pawn can capture diagonally to its right
    if inbounds(y+direction, x+direction) and board[y+direction, x+direction] * piece < 0:
        moves[y+direction, x+direction] = piece
    
    return moves

@nb.njit('int8[:,:](int8[:,:], int32, int32)', cache=True)
def rook_legal_moves(board: np.ndarray, x: int, y: int):
    moves = np.zeros((8, 8), dtype=np.int8)
    piece = board[y, x]
    
    # Check valid moves along the x-axis
    for i in range(x + 1, 8):
        if board[y, i] == 0:
            moves[y, i] = piece
        elif board[y, i] * piece < 0:
            moves[y, i] = piece
            break
        else:
            break

    for i in range(x - 1, -1, -1):
        if board[y, i] == 0:
            moves[y, i] = piece
        elif board[y, i] * piece < 0:
            moves[y, i] = piece
            break
        else:
            break

    # Check valid moves along the y-axis
    for i in range(y + 1, 8):
        if board[i, x] == 0:
            moves[i, x] = piece
        elif board[i, x] * piece < 0:
            moves[i, x] = piece
            break
        else:
            break

    for i in range(y - 1, -1, -1):
        if board[i, x] == 0:
            moves[i, x] = piece
        elif board[i, x] * piece < 0:
            moves[i, x] = piece
            break
        else:
            break

    return moves

@nb.njit('int8[:,:](int8[:,:], int32, int32)', cache=True)
def bishop_legal_moves(board: np.ndarray, x: int, y: int):
    moves = np.zeros((8, 8), dtype=np.int8)
    piece = board[y, x]

    # Check valid moves along the top-left to bottom-right diagonal
    i, j = x + 1, y + 1
    while i < 8 and j < 8:
        if board[j, i] == 0:
            moves[j, i] = piece
        elif board[j, i] * piece < 0:
            moves[j, i] = piece
            break
        else:
            break
        i += 1
        j += 1

    i, j = x - 1, y - 1
    while i >= 0 and j >= 0:
        if board[j, i] == 0:
            moves[j, i] = piece
        elif board[j, i] * piece < 0:
            moves[j, i] = piece
            break
        else:
            break
        i -= 1
        j -= 1

    # Check valid moves along the top-right to bottom-left diagonal
    i, j = x + 1, y - 1
    while i < 8 and j >= 0:
        if board[j, i] == 0:
            moves[j, i] = piece
        elif board[j, i] * piece < 0:
            moves[j, i] = piece
            break
        else:
            break
        i += 1
        j -= 1

    i, j = x - 1, y + 1
    while i >= 0 and j < 8:
        if board[j, i] == 0:
            moves[j, i] = piece
        elif board[j, i] * piece < 0:
            moves[j, i] = piece
            break
        else:
            break
        i -= 1
        j += 1

    return moves

@nb.njit('int8[:,:](int8[:,:], int32, int32)', cache=True)
def queen_legal_moves(board: np.ndarray, x: int, y: int):
    # piece = board[y, x]
    bishop_moves = bishop_legal_moves(board,x,y)
    rook_moves = rook_legal_moves(board,x,y)
    moves = np.add(bishop_moves, rook_moves)
    # return np.where(moves != 0, piece, moves)
    return moves

@nb.njit('int8[:,:](int8[:,:], int32, int32)', cache=True)
def knight_legal_moves(board: np.ndarray, x: int, y: int):
    moves = np.zeros((8, 8), dtype=np.int8)
    piece = board[y, x]
    
    # Possible knight moves
    knight_moves = [(2,1), (2,-1), (-2,1), (-2,-1), (1,2), (1,-2), (-1,2), (-1,-2)]
    
    for move in knight_moves:
        # Determine potential square to move to
        new_x = x + move[0]
        new_y = y + move[1]
        
        # Check if the move is within the bounds of the board and is either empty or contains an opponent piece
        if inbounds(new_y, new_x) and (board[new_y, new_x] == 0 or board[new_y, new_x] * piece < 0):
            moves[new_y, new_x] = piece
            
    return moves

@nb.njit('int8[:,:](int8[:,:], int32, int32)', cache=True)
def legal_moves(board: np.ndarray, x: int, y: int):
    piece_value = board[y, x]
    
    if abs(piece_value) == piece('PAWN'):
        return pawn_legal_moves(board, x, y)
    elif abs(piece_value) == piece('ROOK'):
        return rook_legal_moves(board, x, y)
    elif abs(piece_value) == piece('KNIGHT'):
        return knight_legal_moves(board, x, y)
    elif abs(piece_value) == piece('BISHOP'):
        return bishop_legal_moves(board, x, y)
    elif abs(piece_value) == piece('QUEEN'):
        return queen_legal_moves(board, x, y)
    elif abs(piece_value) == piece('KING'):
        return np.zeros((8, 8), dtype=np.int8)
        return king_legal_moves(board, x, y)

    return np.zeros((8, 8), dtype=np.int8)

@nb.njit('int8[:,:,:](int8[:,:])', cache=True)
def board_to_observation(board: np.ndarray) -> np.ndarray:
    observation = np.zeros((6, 8, 8), dtype=np.int8)

    observation[0, :, :] = (board == piece('pawn')).astype(np.int8) - (board == piece('PAWN')).astype(np.int8)
    observation[1, :, :] = (board == piece('rook')).astype(np.int8) - (board == piece('ROOK')).astype(np.int8)
    observation[2, :, :] = (board == piece('knight')).astype(np.int8) - (board == piece('KNIGHT')).astype(np.int8)
    observation[3, :, :] = (board == piece('bishop')).astype(np.int8) - (board == piece('BISHOP')).astype(np.int8)
    observation[4, :, :] = (board == piece('queen')).astype(np.int8) - (board == piece('QUEEN')).astype(np.int8)
    observation[5, :, :] = (board == piece('king')).astype(np.int8) - (board == piece('KING')).astype(np.int8)

    return observation

@nb.njit(cache=True)
def random_legal_move(board: np.ndarray, isBlack: bool) -> Optional[Tuple[int, int, int, int]]:
    # choose random piece
    pieces = np.argwhere((board > 0) == isBlack)

    # if no pieces, return None
    if len(pieces) == 0:
        return None
    
    # random permutation of pieces
    np.random.shuffle(pieces)

    for x1, y1 in pieces:
        legal = legal_moves(board, x1, y1)

        # choose random legal move
        legal = np.argwhere(legal != 0)

        if len(legal) == 0:
            continue
        
        # choose random legal move
        x2, y2 = legal[np.random.randint(0, len(legal))]

        return (x1, y1, x2, y2)
    
    return None

@nb.njit(cache=True)
def generate_move(board: np.ndarray, x1: int, y1: int, x2: int, y2: int, isBlack: bool) -> Tuple[Optional[Tuple[int, int, int, int]], float]:
    """
    generates legal move and penalty from any illegal move, return None if no legal moves are possible
    """
    # check if move is legal
    piece = board[y1, x1]

    # check if piece is correct color
    if (piece > 0) != isBlack:
        move = random_legal_move(board, isBlack)
        if move is None:
            return None, 0
        else:
            return move, WRONG_PIECE_COLOR_PENALTY
        

    # check what are the legal moves
    legal = legal_moves(board, x1, y1)

    if legal[y2, x2] != 0:
        # legal move
        return (x1, y1, x2, y2), LEGAL_MOVE_REWARD
    else:
        # choose random legal move
        legal = np.argwhere(legal != 0)
        if len(legal) != 0:
            x2, y2 = legal[np.random.randint(0, len(legal))]
            return (x1, y1, x2, y2), ILLEGAL_MOVE_PENALTY_1
        else:
            # no legal moves, try any move
            return random_legal_move(board, isBlack), ILLEGAL_MOVE_PENALTY_2
        
    

        




def fen_to_svg(fen: str) -> str:
    return chess.svg.board(chess.Board(fen), size=500)


if __name__ == '__main__':
    board = generate_start_board()
    print(board_to_observation(board))
    board = np.zeros((8, 8), dtype=np.int8)
    # board[5,5] = piece("pawn")
    board[2,2] = piece("PAWN")
    # moves = pawn_legal_moves(board,5,5)
    moves = pawn_legal_moves(board,2,2)

    generate_move(board, 2, 2, 2, 3, True)

    print(moves)