import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    games = db.relationship('Game', backref='player', lazy=True)

    def __repr__(self):
        return '<Player: {} (is_white={})>'.format(self.username,
                                                   self.is_white)


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'),
                          nullable=False)
    player_is_white = db.Column(db.Boolean, nullable=False)
    player_won = db.Column(db.Boolean, nullable=True)
    training_game = db.Column(db.Boolean, nullable=False)
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

    # Note sure we need this
    # move_number = db.Column(db.int, nullable=False)

    def __repr__(self):
        white = False
        if self.player_move and self.player.game.player.is_white:
            white = True
        if not self.player_move and not self.player.game.player.is_white:
            white = True
        return '<Move: {} (game={}, player={}, white={})>'.format(
            self.id, self.game_id, self.player_move, white)
