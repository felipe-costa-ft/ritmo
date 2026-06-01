import pygame

from config import FPS, WINDOW_H, WINDOW_W
from editor import create_empty_state

pygame.init()
screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
pygame.display.set_caption("TileMap tool")


editor_state = create_empty_state(300, 300, 16, 16)
clock = pygame.time.Clock()


running = True

while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    clock.tick(FPS)


pygame.quit()
