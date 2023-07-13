import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from sqlalchemy_utils.types.choice import ChoiceType

db = SQLAlchemy()


class Player(db.Model):
    CONDITIONS = [
        ('control', 'control'),
        ('immediate', 'immediate'),
        ('delayed', 'delayed')
    ]

    STAGES = [('consent', 'consent'),
            ('instructions', 'instructions'), 
            ('pretest', 'pretest')
            ('training', 'training'),
            ('testing', 'testing'), 
            ('posttest', 'posttest')
            ('survey', 'survey'),
            ('done', 'done')]

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    games = db.relationship('Game', backref='player', lazy=True)
    condition = db.Column(ChoiceType(CONDITIONS))
    stage = db.Column(ChoiceType(STAGES), default='consent')
    consent_start = db.Column(db.DateTime, default=datetime.datetime.utcnow) # keep the time in utc, convert in excel
    instructions_start = db.Column(db.DateTime, default=None)
    training_start = db.Column(db.DateTime, default=None)
    testing_start = db.Column(db.DateTime, default=None)
    survey_start = db.Column(db.DateTime, default=None)
    experiment_end = db.Column(db.DateTime, default=None)

    def __repr__(self):
        return '<Player: {}>'.format(self.username)


class Game(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'),
                          nullable=False)
    player_is_white = db.Column(db.Boolean, nullable=False)
    player_won = db.Column(db.Boolean, nullable=True)
    training_game = db.Column(db.Boolean, nullable=False)
    game_difficulty = db.Column(db.Integer, nullable=False)
    size = db.Column(db.Integer, default=8)
    moves = db.relationship('Move', backref='game', lazy=True)

    # do not need the opponent column until we have multiple opponents
    # opponent = db.Column(db.String(80), nullable=True)

    def __repr__(self):
        return '<Game: {} (player: {}, player won: {})>'.format(
            self.id, self.player_id, self.player_won)


class Move(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    player_move = db.Column(db.Boolean, nullable=False)
    datetime = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    location = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Float, nullable=True)
    hint_location = db.Column(db.Integer, nullable=True)
    raw_move_scores = db.Column(db.Text, nullable=True)
    is_hint = db.Column(db.Boolean, nullable=True)

    # Note sure we need this
    # move_number = db.Column(db.int, nullable=False)

    def __repr__(self):
        white = False
        if self.player_move and self.game.player_is_white:
            white = True
        if not self.player_move and not self.game.player_is_white:
            white = True
        return '<Move: {} (game={}, player={}, white={}, loc={}, score={})>'.format(
            self.id, self.game_id, self.player_move, white, self.location, self.score)


class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    event = db.Column(db.Text, nullable=True)


class MctsCache(db.Model):
    __table_args__ = (
        UniqueConstraint("board", "human", "difficulty"),
    )
    id = db.Column(db.Integer, primary_key=True)
    board = db.Column(db.Text, nullable=False)
    human = db.Column(db.Boolean, nullable=False)
    move = db.Column(db.Integer, nullable=False)
    scores = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.Integer, nullable=False)
