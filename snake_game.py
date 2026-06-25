"""
snake_game.py
-------------
A basic Snake game built with pygame.
This file is the protected asset — it will be AES-encrypted by encrypt_game.py
and only decrypted into RAM at launch time by launcher.py.
"""

import pygame
import sys
import random

# ── Constants ────────────────────────────────────────────────────────────────
WINDOW_W, WINDOW_H = 640, 480
CELL = 20                          # grid cell size in pixels
COLS  = WINDOW_W // CELL
ROWS  = WINDOW_H // CELL
FPS   = 10

BLACK  = (  0,   0,   0)
WHITE  = (255, 255, 255)
GREEN  = ( 34, 177,  76)
DKGREEN= ( 20, 120,  50)
RED    = (200,  40,  40)
GRAY   = ( 40,  40,  40)

# ── Game logic ────────────────────────────────────────────────────────────────

def run_game():
    pygame.init()
    screen  = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("Snake — Hardware-Locked Edition")
    clock   = pygame.font.SysFont("consolas", 22)
    big     = pygame.font.SysFont("consolas", 42, bold=True)
    ticker  = pygame.time.Clock()

    def new_game():
        snake  = [(COLS // 2, ROWS // 2)]
        direction = (1, 0)
        food   = spawn_food(snake)
        score  = 0
        return snake, direction, food, score

    def spawn_food(snake):
        while True:
            pos = (random.randint(0, COLS - 1), random.randint(0, ROWS - 1))
            if pos not in snake:
                return pos

    def draw_cell(surface, col, row, color, shrink=0):
        rect = pygame.Rect(col * CELL + shrink,
                           row * CELL + shrink,
                           CELL - shrink * 2,
                           CELL - shrink * 2)
        pygame.draw.rect(surface, color, rect, border_radius=4)

    def draw_grid(surface):
        for x in range(0, WINDOW_W, CELL):
            pygame.draw.line(surface, GRAY, (x, 0), (x, WINDOW_H))
        for y in range(0, WINDOW_H, CELL):
            pygame.draw.line(surface, GRAY, (0, y), (WINDOW_W, y))

    snake, direction, food, score = new_game()
    game_over = False

    while True:
        # ── Events ────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if game_over:
                    if event.key == pygame.K_r:
                        snake, direction, food, score = new_game()
                        game_over = False
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                else:
                    mapping = {
                        pygame.K_UP:    ( 0, -1),
                        pygame.K_DOWN:  ( 0,  1),
                        pygame.K_LEFT:  (-1,  0),
                        pygame.K_RIGHT: ( 1,  0),
                        pygame.K_w:     ( 0, -1),
                        pygame.K_s:     ( 0,  1),
                        pygame.K_a:     (-1,  0),
                        pygame.K_d:     ( 1,  0),
                    }
                    if event.key in mapping:
                        nd = mapping[event.key]
                        # prevent 180-degree reversal
                        if (nd[0] + direction[0], nd[1] + direction[1]) != (0, 0):
                            direction = nd

        # ── Update ────────────────────────────────────────────────────────
        if not game_over:
            head = (snake[0][0] + direction[0], snake[0][1] + direction[1])

            # Wall collision
            if not (0 <= head[0] < COLS and 0 <= head[1] < ROWS):
                game_over = True
            # Self collision
            elif head in snake:
                game_over = True
            else:
                snake.insert(0, head)
                if head == food:
                    score += 10
                    food = spawn_food(snake)
                else:
                    snake.pop()

        # ── Draw ──────────────────────────────────────────────────────────
        screen.fill(BLACK)
        draw_grid(screen)

        # Food (pulsing red square)
        draw_cell(screen, food[0], food[1], RED, shrink=2)

        # Snake body
        for i, seg in enumerate(snake):
            color = GREEN if i == 0 else DKGREEN
            shrink = 0 if i == 0 else 2
            draw_cell(screen, seg[0], seg[1], color, shrink=shrink)

        # HUD
        hud = clock.render(f"Score: {score}   [WASD / Arrow Keys]", True, WHITE)
        screen.blit(hud, (8, 6))

        if game_over:
            over_surf = big.render("GAME OVER", True, RED)
            sub_surf  = clock.render("Press R to restart  |  ESC to quit", True, WHITE)
            score_surf= clock.render(f"Final Score: {score}", True, WHITE)
            screen.blit(over_surf,  over_surf.get_rect(center=(WINDOW_W//2, WINDOW_H//2 - 40)))
            screen.blit(score_surf, score_surf.get_rect(center=(WINDOW_W//2, WINDOW_H//2 + 10)))
            screen.blit(sub_surf,   sub_surf.get_rect(center=(WINDOW_W//2, WINDOW_H//2 + 50)))

        pygame.display.flip()
        ticker.tick(FPS)


if __name__ == "__main__":
    run_game()
