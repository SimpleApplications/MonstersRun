"""MonstersRun - A simple terminal runner game."""

import random
import time
import os
import sys
import json

# Game constants
TRACK_WIDTH = 40
PLAYER_CHAR = "O"
MONSTER_CHAR = "M"
OBSTACLE_CHAR = "#"
GROUND_CHAR = "="
EMPTY_CHAR = " "

JUMP_HEIGHT = 3
GRAVITY = 1
MAX_LIVES = 3
INVINCIBILITY_FRAMES = 60
HIGH_SCORE_FILE = os.path.join(os.path.dirname(__file__), ".high_score.json")


def load_high_score() -> int:
    try:
        with open(HIGH_SCORE_FILE) as f:
            return json.load(f).get("high_score", 0)
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return 0


def save_high_score(score: int) -> None:
    current = load_high_score()
    if score > current:
        with open(HIGH_SCORE_FILE, "w") as f:
            json.dump({"high_score": score}, f)


class Player:
    def __init__(self):
        self.x = 5
        self.y = 0  # 0 = ground level
        self.velocity_y = 0
        self.jumps_remaining = 2  # supports double-jump
        self.score = 0
        self.alive = True
        self.lives = MAX_LIVES
        self.invincible_frames = 0

    @property
    def is_jumping(self):
        return self.y > 0 or self.velocity_y > 0

    @property
    def invincible(self):
        return self.invincible_frames > 0

    def jump(self):
        if self.jumps_remaining > 0:
            self.velocity_y = JUMP_HEIGHT
            self.jumps_remaining -= 1

    def hit(self):
        if self.invincible:
            return
        self.lives -= 1
        if self.lives <= 0:
            self.alive = False
        else:
            self.invincible_frames = INVINCIBILITY_FRAMES

    def update(self):
        if self.y > 0 or self.velocity_y > 0:
            self.y += self.velocity_y
            self.velocity_y -= GRAVITY
            if self.y <= 0:
                self.y = 0
                self.velocity_y = 0
                self.jumps_remaining = 2  # reset on landing

        if self.invincible_frames > 0:
            self.invincible_frames -= 1

        self.score += 1


class Obstacle:
    def __init__(self, x, height=1):
        self.x = x
        self.height = height

    def update(self):
        self.x -= 1

    @property
    def active(self):
        return self.x > 0


class Monster:
    def __init__(self, x, speed=1):
        self.x = x
        self.speed = speed
        self.y = 0

    def update(self):
        self.x -= self.speed

    @property
    def active(self):
        return self.x > 0


class Game:
    def __init__(self):
        self.player = Player()
        self.obstacles = []
        self.monsters = []
        self.frame = 0
        self.running = True
        self.spawn_interval = 30
        self.difficulty = 1
        self.high_score = load_high_score()

    def spawn_obstacle(self):
        height = random.randint(1, 2)
        self.obstacles.append(Obstacle(TRACK_WIDTH - 1, height))

    def spawn_monster(self):
        speed = 1 + self.difficulty // 5
        self.monsters.append(Monster(TRACK_WIDTH - 1, speed))

    def check_collisions(self):
        px, py = self.player.x, self.player.y

        for obs in self.obstacles:
            if obs.x == px and py < obs.height:
                self.player.hit()
                return

        for mon in self.monsters:
            if mon.x == px and py == 0:
                self.player.hit()
                return

    def update(self):
        self.frame += 1
        self.difficulty = self.frame // 100 + 1
        self.spawn_interval = max(15, 30 - self.difficulty * 2)

        self.player.update()

        if self.frame % self.spawn_interval == 0:
            if random.random() < 0.6:
                self.spawn_obstacle()
            else:
                self.spawn_monster()

        for obs in self.obstacles:
            obs.update()
        for mon in self.monsters:
            mon.update()

        self.obstacles = [o for o in self.obstacles if o.active]
        self.monsters = [m for m in self.monsters if m.active]

        self.check_collisions()

    def render(self):
        rows = [list(EMPTY_CHAR * TRACK_WIDTH) for _ in range(JUMP_HEIGHT + 2)]
        ground_row = JUMP_HEIGHT + 1
        ground_index = JUMP_HEIGHT

        # Draw ground
        rows[ground_row] = list(GROUND_CHAR * TRACK_WIDTH)

        # Draw obstacles
        for obs in self.obstacles:
            if 0 <= obs.x < TRACK_WIDTH:
                for h in range(obs.height):
                    row_index = ground_index - h
                    if 0 <= row_index < len(rows):
                        rows[row_index][obs.x] = OBSTACLE_CHAR

        # Draw monsters
        for mon in self.monsters:
            if 0 <= mon.x < TRACK_WIDTH:
                rows[ground_index][mon.x] = MONSTER_CHAR

        # Draw player (blink when invincible)
        player_char = PLAYER_CHAR if not self.player.invincible or self.frame % 4 < 2 else " "
        player_row = ground_index - self.player.y
        if 0 <= player_row < len(rows):
            rows[player_row][self.player.x] = player_char

        lives_display = "♥ " * self.player.lives + "♡ " * (MAX_LIVES - self.player.lives)
        high_score_display = f"Best: {self.high_score}"

        os.system("clear" if os.name == "posix" else "cls")
        print(f"  MonstersRun  |  Score: {self.player.score}  |  {high_score_display}  |  Level: {self.difficulty}")
        print(f"  Lives: {lives_display.strip()}")
        print("+" + "-" * TRACK_WIDTH + "+")
        for row in rows:
            print("|" + "".join(row) + "|")
        print("+" + "-" * TRACK_WIDTH + "+")
        print("  [SPACE] Jump / Double-jump   [Q] Quit")

    def finish(self):
        save_high_score(self.player.score)
        new_best = self.player.score > self.high_score
        print(f"\nGame Over! Final Score: {self.player.score}" + (" -- NEW HIGH SCORE!" if new_best else ""))

    def run_auto_demo(self):
        """Run a non-interactive demo (auto-jumps to avoid obstacles)."""
        print("Running in demo mode (no TTY detected)...")
        time.sleep(1)

        while self.running and self.player.alive and self.player.score < 200:
            for obs in self.obstacles:
                if obs.x - self.player.x <= 4:
                    self.player.jump()
            for mon in self.monsters:
                if mon.x - self.player.x <= 4:
                    self.player.jump()
            self.update()
            time.sleep(0.05)

        self.finish()

    def run(self):
        if not sys.stdin.isatty():
            self.run_auto_demo()
            return

        import tty
        import termios
        import select

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            tty.setraw(fd)

            while self.running and self.player.alive:
                if select.select([sys.stdin], [], [], 0)[0]:
                    ch = sys.stdin.read(1)
                    if ch in (" ", "\n"):
                        self.player.jump()
                    elif ch.lower() == "q":
                        self.running = False
                        break

                self.update()
                self.render()
                time.sleep(0.08)

        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        self.finish()


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
