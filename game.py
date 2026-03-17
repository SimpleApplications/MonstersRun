"""MonstersRun - A simple terminal runner game."""

import random
import time
import os
import sys

# Game constants
TRACK_WIDTH = 40
PLAYER_CHAR = "O"
MONSTER_CHAR = "M"
OBSTACLE_CHAR = "#"
GROUND_CHAR = "="
EMPTY_CHAR = " "

JUMP_HEIGHT = 3
GRAVITY = 1


class Player:
    def __init__(self):
        self.x = 5
        self.y = 0  # 0 = ground level
        self.velocity_y = 0
        self.is_jumping = False
        self.score = 0
        self.alive = True

    def jump(self):
        if not self.is_jumping:
            self.velocity_y = JUMP_HEIGHT
            self.is_jumping = True

    def update(self):
        if self.is_jumping:
            self.y += self.velocity_y
            self.velocity_y -= GRAVITY
            if self.y <= 0:
                self.y = 0
                self.velocity_y = 0
                self.is_jumping = False

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
                self.player.alive = False
                return

        for mon in self.monsters:
            if mon.x == px and py == 0:
                self.player.alive = False
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

        # Draw player
        player_row = ground_index - self.player.y
        if 0 <= player_row < len(rows):
            rows[player_row][self.player.x] = PLAYER_CHAR

        os.system("clear" if os.name == "posix" else "cls")
        print(f"  MonstersRun  |  Score: {self.player.score}  |  Level: {self.difficulty}")
        print("+" + "-" * TRACK_WIDTH + "+")
        for row in rows:
            print("|" + "".join(row) + "|")
        print("+" + "-" * TRACK_WIDTH + "+")
        print("  [SPACE] Jump   [Q] Quit")

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

        print(f"Demo finished! Score: {self.player.score}")

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
                # Non-blocking input check
                if select.select([sys.stdin], [], [], 0)[0]:
                    ch = sys.stdin.read(1)
                    if ch in (" ", "\n"):
                        self.player.jump()
                    elif ch.lower() == "q":
                        self.running = False
                        break

                # Auto-jump hint for obstacles nearby
                for obs in self.obstacles:
                    if obs.x - self.player.x <= 3:
                        self.player.jump()
                for mon in self.monsters:
                    if mon.x - self.player.x <= 3:
                        self.player.jump()

                self.update()
                self.render()
                time.sleep(0.08)

        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        print(f"\nGame Over! Final Score: {self.player.score}")


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
