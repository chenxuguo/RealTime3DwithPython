import sys

import pygame

WIDTH = 640
HEIGHT = 480
SPRITE_HEIGHT = 40
SPRITE_WIDTH = 40


class GameObject:
    def __init__(self, image, height, speed):
        self.speed = speed
        self.image = image
        self.pos = image.get_rect().move(height, 0)

    def move(self):
        self.pos = self.pos.move(self.speed, 0)
        if self.pos.right > 600:
            self.pos.left = 0


screen = pygame.display.set_mode((640, 480))
clock = pygame.time.Clock()     # get a pygame clock object
player = pygame.image.load('player.bmp').convert()
background = pygame.image.load('background.bmp').convert()
screen.blit(background, (0, 0))
objects = []
for x in range(16):
    o = GameObject(player, x*40, 2)
    objects.append(o)
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()
    for o in objects:
        screen.blit(background, o.pos, o.pos)
    for o in objects:
        #  o.move()
        screen.blit(o.image, o.pos)
    pygame.display.update()
    clock.tick(60)


    
