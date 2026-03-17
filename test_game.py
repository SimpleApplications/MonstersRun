"""Unit tests for MonstersRun."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

import game as g
from game import (
    Game,
    Monster,
    Obstacle,
    Player,
    load_high_score,
    save_high_score,
    INVINCIBILITY_FRAMES,
    MAX_LIVES,
)


# ---------------------------------------------------------------------------
# Player – jump physics
# ---------------------------------------------------------------------------

class TestPlayerJump(unittest.TestCase):
    def test_single_jump_leaves_ground(self):
        p = Player()
        p.jump()
        p.update()
        self.assertGreater(p.y, 0)

    def test_lands_after_jump(self):
        p = Player()
        p.jump()
        for _ in range(20):
            p.update()
        self.assertEqual(p.y, 0)
        self.assertFalse(p.is_jumping)

    def test_double_jump_allowed_mid_air(self):
        p = Player()
        p.jump()          # first jump
        p.update()        # now in the air
        self.assertEqual(p.jumps_remaining, 1)
        p.jump()          # second jump
        self.assertEqual(p.jumps_remaining, 0)

    def test_no_triple_jump(self):
        p = Player()
        p.jump()
        p.update()
        p.jump()
        p.update()
        prev_vy = p.velocity_y
        p.jump()          # third attempt – should be ignored
        self.assertEqual(p.velocity_y, prev_vy)

    def test_jumps_reset_on_landing(self):
        p = Player()
        p.jump()
        p.update()
        p.jump()          # use both jumps
        for _ in range(20):
            p.update()
        self.assertEqual(p.jumps_remaining, 2)

    def test_score_increments_each_update(self):
        p = Player()
        for i in range(5):
            p.update()
        self.assertEqual(p.score, 5)


# ---------------------------------------------------------------------------
# Player – lives & invincibility
# ---------------------------------------------------------------------------

class TestPlayerLives(unittest.TestCase):
    def test_starts_with_max_lives(self):
        p = Player()
        self.assertEqual(p.lives, MAX_LIVES)

    def test_hit_reduces_lives(self):
        p = Player()
        p.hit()
        self.assertEqual(p.lives, MAX_LIVES - 1)
        self.assertTrue(p.alive)

    def test_hit_three_times_kills_player(self):
        p = Player()
        for _ in range(MAX_LIVES):
            p.invincible_frames = 0   # bypass invincibility for test
            p.hit()
        self.assertFalse(p.alive)

    def test_invincibility_after_hit(self):
        p = Player()
        p.hit()
        self.assertTrue(p.invincible)
        self.assertEqual(p.invincible_frames, INVINCIBILITY_FRAMES)

    def test_hit_ignored_while_invincible(self):
        p = Player()
        p.hit()                       # first hit → invincible
        lives_after_first = p.lives
        p.hit()                       # should be ignored
        self.assertEqual(p.lives, lives_after_first)

    def test_invincibility_expires(self):
        p = Player()
        p.hit()
        for _ in range(INVINCIBILITY_FRAMES):
            p.update()
        self.assertFalse(p.invincible)


# ---------------------------------------------------------------------------
# Obstacle & Monster
# ---------------------------------------------------------------------------

class TestObstacle(unittest.TestCase):
    def test_moves_left_each_update(self):
        obs = Obstacle(10)
        obs.update()
        self.assertEqual(obs.x, 9)

    def test_inactive_when_off_screen(self):
        obs = Obstacle(1)
        obs.update()
        self.assertFalse(obs.active)

    def test_active_while_on_screen(self):
        obs = Obstacle(5)
        self.assertTrue(obs.active)


class TestMonster(unittest.TestCase):
    def test_moves_left_by_speed(self):
        mon = Monster(10, speed=2)
        mon.update()
        self.assertEqual(mon.x, 8)

    def test_inactive_when_off_screen(self):
        mon = Monster(1)
        mon.update()
        self.assertFalse(mon.active)


# ---------------------------------------------------------------------------
# Collision detection
# ---------------------------------------------------------------------------

class TestCollisions(unittest.TestCase):
    def _game_with_player_at_ground(self):
        game = Game()
        game.player.y = 0
        game.player.invincible_frames = 0
        return game

    def test_obstacle_collision_removes_life(self):
        game = self._game_with_player_at_ground()
        game.obstacles.append(Obstacle(game.player.x, height=1))
        game.check_collisions()
        self.assertEqual(game.player.lives, MAX_LIVES - 1)

    def test_no_collision_when_jumping_over_obstacle(self):
        game = self._game_with_player_at_ground()
        game.player.y = 2          # player is in the air above height-1 obstacle
        game.obstacles.append(Obstacle(game.player.x, height=1))
        game.check_collisions()
        self.assertEqual(game.player.lives, MAX_LIVES)

    def test_monster_collision_removes_life(self):
        game = self._game_with_player_at_ground()
        game.monsters.append(Monster(game.player.x))
        game.check_collisions()
        self.assertEqual(game.player.lives, MAX_LIVES - 1)

    def test_no_monster_collision_when_jumping(self):
        game = self._game_with_player_at_ground()
        game.player.y = 1
        game.monsters.append(Monster(game.player.x))
        game.check_collisions()
        self.assertEqual(game.player.lives, MAX_LIVES)

    def test_invincible_player_survives_obstacle(self):
        game = self._game_with_player_at_ground()
        game.player.invincible_frames = INVINCIBILITY_FRAMES
        game.obstacles.append(Obstacle(game.player.x, height=1))
        game.check_collisions()
        self.assertEqual(game.player.lives, MAX_LIVES)


# ---------------------------------------------------------------------------
# High score persistence
# ---------------------------------------------------------------------------

class TestHighScore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(
            suffix=".json", delete=False
        )
        self._tmp.close()
        self._orig = g.HIGH_SCORE_FILE
        g.HIGH_SCORE_FILE = self._tmp.name

    def tearDown(self):
        if os.path.exists(self._tmp.name):
            os.unlink(self._tmp.name)
        g.HIGH_SCORE_FILE = self._orig

    def test_default_high_score_is_zero(self):
        os.unlink(self._tmp.name)
        self.assertEqual(load_high_score(), 0)

    def test_save_and_load(self):
        save_high_score(500)
        self.assertEqual(load_high_score(), 500)

    def test_lower_score_does_not_overwrite(self):
        save_high_score(500)
        save_high_score(100)
        self.assertEqual(load_high_score(), 500)

    def test_higher_score_overwrites(self):
        save_high_score(100)
        save_high_score(999)
        self.assertEqual(load_high_score(), 999)

    def test_corrupted_file_returns_zero(self):
        with open(self._tmp.name, "w") as f:
            f.write("not json")
        self.assertEqual(load_high_score(), 0)


# ---------------------------------------------------------------------------
# Difficulty scaling
# ---------------------------------------------------------------------------

class TestDifficulty(unittest.TestCase):
    def test_difficulty_increases_with_frames(self):
        game = Game()
        game.frame = 98   # update() increments to 99 → difficulty 1
        game.update()
        self.assertEqual(game.difficulty, 1)
        game.frame = 198  # update() increments to 199 → difficulty 2
        game.update()
        self.assertEqual(game.difficulty, 2)

    def test_spawn_interval_decreases_with_difficulty(self):
        game = Game()
        interval_easy = max(15, 30 - 1 * 2)
        interval_hard = max(15, 30 - 5 * 2)
        self.assertGreater(interval_easy, interval_hard)

    def test_spawn_interval_floor(self):
        # At very high difficulty spawn interval should not go below 15
        game = Game()
        game.difficulty = 100
        interval = max(15, 30 - game.difficulty * 2)
        self.assertEqual(interval, 15)


if __name__ == "__main__":
    unittest.main()
