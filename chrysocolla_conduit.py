#!/usr/bin/env python3
"""Chrysocolla Conduit — neon pipe-flow arcade for ElbowOS. Python 3 + pygame."""
import math, os, random, subprocess, sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv
if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/CHRYSOCOLLA_CONDUIT_ElbowOS.mp4")
COLS, ROWS, CELL = 5, 7, 156
OX, OY = (W - COLS * CELL) // 2, 318
N, E, S, Wb = 1, 2, 4, 8
DIRS = ((0, -1, N, S), (1, 0, E, Wb), (0, 1, S, N), (-1, 0, Wb, E))
INK, COPPER, GROOVE = (6, 18, 28), (196, 122, 58), (28, 18, 12)
FLOW, GEM, LEAK = (61, 255, 214), (255, 186, 64), (255, 72, 108)
SOLVED = [
    [E | S, N | S, S, N | S, Wb | S],
    [N | E, E | Wb, N | S, E | Wb, N | Wb],
    [Wb | S, E | S, N | E | Wb, Wb | S, N | S],
    [N | E, N | S, E | Wb, N | E, Wb | S],
    [E | Wb, N | E, Wb | E | S, E | S, N | S],
    [E | S, N | Wb, N | S | E, E | Wb, N | Wb],
    [E, E | Wb, N | E | Wb, E | Wb, Wb],
]
SINKS = {(2, 4), (0, 6), (4, 6), (2, 6)}
FIX = {(2, 0), (0, 6), (4, 6)}
OFFSETS = {
    (2, 1): 1, (2, 2): 1, (1, 2): 1, (1, 3): 2, (1, 4): 1, (2, 4): 1,
    (3, 2): 1, (3, 3): 2, (4, 3): 1, (4, 4): 1, (4, 5): 1, (3, 5): 1,
    (2, 5): 1, (2, 6): 1, (1, 6): 1, (3, 6): 1,
}


def spin(mask, k):
    for _ in range(k % 4):
        mask = ((mask & N) and E) | ((mask & E) and S) | ((mask & S) and Wb) | ((mask & Wb) and N)
    return mask


class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.font = pygame.font.SysFont("dejavusans", 64, bold=True)
        self.mid = pygame.font.SysFont("dejavusans", 36, bold=True)
        self.small = pygame.font.SysFont("dejavusans", 28, bold=True)
        flags = 0 if PLAY and not RECORD else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            self.screen = pygame.Surface((W, H))
        pygame.display.set_caption("Chrysocolla Conduit")
        self.canvas = pygame.Surface((W, H))
        self.reset()

    def reset(self):
        self.rot = [[OFFSETS.get((c, r), 0) for c in range(COLS)] for r in range(ROWS)]
        self.cx = self.cy = 2
        self.score = 0
        self.filled = set()
        self.sparks = []
        self.msg = "ROTATE THE DUCTS"
        self.plan = []
        frame = 18
        for key in OFFSETS:
            self.plan.append((frame, key[0], key[1]))
            frame += 24

    def mask(self, c, r):
        return spin(SOLVED[r][c], self.rot[r][c])

    def flow(self):
        seen, dist, q = {}, {}, [(2, 0)]
        dist[(2, 0)] = 0
        while q:
            c, r = q.pop(0)
            if (c, r) in seen:
                continue
            seen[(c, r)] = True
            m = self.mask(c, r)
            for dc, dr, bit, opp in DIRS:
                if not (m & bit):
                    continue
                nc, nr = c + dc, r + dr
                if not (0 <= nc < COLS and 0 <= nr < ROWS):
                    continue
                if self.mask(nc, nr) & opp and (nc, nr) not in dist:
                    dist[(nc, nr)] = dist[(c, r)] + 1
                    q.append((nc, nr))
        return dist

    def step_auto(self, frame):
        while self.plan and self.plan[0][0] <= frame:
            _, c, r = self.plan.pop(0)
            self.cx, self.cy = c, r
            if self.rot[r][c]:
                self.rot[r][c] = (self.rot[r][c] - 1) % 4
                self.sparks.append([OX + c * CELL + CELL // 2, OY + r * CELL + CELL // 2, 18])
        if frame % 9 == 0 and self.plan:
            self.cx, self.cy = self.plan[0][1], self.plan[0][2]

    def update_score(self, dist):
        for pos, d in dist.items():
            if pos in SINKS and pos not in self.filled and d >= 0:
                self.filled.add(pos)
                self.score += 250
                self.msg = "CHAMBER OPEN"
        self.score = max(self.score, len(dist) * 12 + len(self.filled) * 250)

    def draw_pipe(self, surf, c, r, dist, t):
        x, y = OX + c * CELL, OY + r * CELL
        rect = pygame.Rect(x + 8, y + 8, CELL - 16, CELL - 16)
        pygame.draw.rect(surf, (10, 32, 42), rect, border_radius=18)
        pygame.draw.rect(surf, (32, 78, 88), rect, 3, border_radius=18)
        m = self.mask(c, r)
        cx, cy = x + CELL // 2, y + CELL // 2
        reached = (c, r) in dist
        for dc, dr, bit, _ in DIRS:
            if not (m & bit):
                continue
            ex, ey = cx + dc * (CELL // 2 - 6), cy + dr * (CELL // 2 - 6)
            pygame.draw.line(surf, COPPER, (cx, cy), (ex, ey), 34)
            pygame.draw.line(surf, GROOVE, (cx, cy), (ex, ey), 16)
            if reached:
                pulse = 0.55 + 0.45 * math.sin(t * 0.35 + dist[(c, r)])
                col = tuple(min(255, int(v * pulse)) for v in FLOW)
                pygame.draw.line(surf, col, (cx, cy), (ex, ey), 9)
        pygame.draw.circle(surf, COPPER, (cx, cy), 18)
        pygame.draw.circle(surf, FLOW if reached else GROOVE, (cx, cy), 8)
        if (c, r) in SINKS:
            glow = GEM if (c, r) in self.filled else (90, 70, 40)
            pts = [(cx + math.cos(math.radians(a)) * 28, cy + math.sin(math.radians(a)) * 28) for a in range(0, 360, 60)]
            pygame.draw.polygon(surf, glow, pts)
            pygame.draw.polygon(surf, (255, 244, 210), pts, 3)
        if (c, r) == (2, 0):
            pygame.draw.circle(surf, FLOW, (cx, cy - 8), 14)
        if (c, r) == (self.cx, self.cy):
            pygame.draw.rect(surf, LEAK, pygame.Rect(x + 4, y + 4, CELL - 8, CELL - 8), 4, border_radius=16)

    def draw(self, frame):
        surf = self.canvas
        surf.fill(INK)
        for i in range(0, H, 48):
            shade = 8 + (i * 18) // H
            pygame.draw.line(surf, (shade, 28 + shade, 36 + shade), (0, i), (W, i), 1)
        title = self.font.render("CHRYSOCOLLA CONDUIT", True, FLOW)
        surf.blit(title, title.get_rect(center=(W // 2, 110)))
        sub = self.mid.render(self.msg, True, GEM)
        surf.blit(sub, sub.get_rect(center=(W // 2, 178)))
        dist = self.flow()
        self.update_score(dist)
        for r in range(ROWS):
            for c in range(COLS):
                self.draw_pipe(surf, c, r, dist, frame)
        alive = []
        for sp in self.sparks:
            sp[2] -= 1
            if sp[2] > 0:
                pygame.draw.circle(surf, GEM, (int(sp[0]), int(sp[1])), sp[2] // 2)
                alive.append(sp)
        self.sparks = alive
        bar = pygame.Rect(80, 1460, 920, 28)
        pygame.draw.rect(surf, (16, 40, 48), bar, border_radius=10)
        frac = min(1, len(dist) / 18)
        pygame.draw.rect(surf, FLOW, (80, 1460, int(920 * frac), 28), border_radius=10)
        score = self.font.render(f"SCORE  {self.score:04d}", True, (255, 244, 220))
        surf.blit(score, score.get_rect(center=(W // 2, 1560)))
        tag = self.mid.render("x.com/ElbowOS", True, (180, 255, 230))
        surf.blit(tag, tag.get_rect(center=(W // 2, 1760)))
        hint = self.small.render("ARROWS MOVE   SPACE ROTATE", True, (120, 170, 170))
        surf.blit(hint, hint.get_rect(center=(W // 2, 1840)))
        return surf

    def play(self):
        clock = pygame.time.Clock()
        running = True
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        running = False
                    elif ev.key == pygame.K_LEFT:
                        self.cx = max(0, self.cx - 1)
                    elif ev.key == pygame.K_RIGHT:
                        self.cx = min(COLS - 1, self.cx + 1)
                    elif ev.key == pygame.K_UP:
                        self.cy = max(0, self.cy - 1)
                    elif ev.key == pygame.K_DOWN:
                        self.cy = min(ROWS - 1, self.cy + 1)
                    elif ev.key in (pygame.K_SPACE, pygame.K_RETURN) and (self.cx, self.cy) not in FIX:
                        self.rot[self.cy][self.cx] = (self.rot[self.cy][self.cx] - 1) % 4
                    elif ev.key == pygame.K_r:
                        self.reset()
            frame = pygame.time.get_ticks() // 33
            self.screen.blit(self.draw(frame), (0, 0))
            pygame.display.flip()
            clock.tick(FPS)
        pygame.quit()

    def record(self):
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
            "-r", str(FPS), "-i", "pipe:0", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "veryfast", "-movflags", "+faststart", OUT,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            for frame in range(FPS * SECS):
                self.step_auto(frame)
                surf = self.draw(frame)
                proc.stdin.write(pygame.image.tobytes(surf, "RGB"))
        finally:
            proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "ignore")
        rc = proc.wait()
        pygame.quit()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed ({rc}):\n{err[-1500:]}")
        print("wrote", OUT)


def main():
    g = Game()
    if PLAY and not RECORD:
        g.play()
    else:
        g.record()


if __name__ == "__main__":
    main()
