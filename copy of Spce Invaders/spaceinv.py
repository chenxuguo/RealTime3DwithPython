# _*_ coding: utf-8 _*_

import pygame
import numpy as np
import random
import os.path
import json
import base64
import hashlib
from cryptography.fernet import Fernet
from io import BytesIO
from sys import exit


class SpaceInvaders:
    """
    Space Invaders Game
    (c)Kalle & Eellis 2022
    """
    def __init__(self, screen):
        pygame.font.init()
        pygame.mixer.init()

        # set up display surfaces
        self.screen = screen
        self.screen_size = np.array(self.screen.get_size())
        self.mid_screen = self.screen_size // 2
        self.background_color = (0, 0, 0)
        self.screen_titles = screen.copy()
        self.screen_titles.set_colorkey(self.background_color)
        self.screen_credits = self.screen.copy()
        self.screen_credits.set_colorkey(self.background_color)
        self.screen_instructions = self.screen.copy()
        self.screen_instructions.set_colorkey(self.background_color)
        self.screen_info = screen.copy()
        self.screen_info.setcolorkey(self.background_color)
        self.title_color = (220, 220, 160)
        self.score_color = (200, 200, 0)
        self.angle = 0
        self.angle_add = 0
        self.info_screen = 'titles'
        self.info_screen_next = 'credits'
        self.f = Fernet(base64.urlsafe_b64encode(hashlib.md5('<password here>'.encode()).hexdigest().encode("utf-8")))
        self.namehints = {'p':'png', 'j':'jpg', 'o':'ogg', 'm':'mp3','w':'wav','t':'txt'}

        # load data files - images
        (fileobj, namehint) = self.load_dat('ship p')
        self.ship_pic = pygame.image.load(fileobj, namehint).convert()
        self.ship_pic.set_colorkey((255,255,255))
        shield_size = int(np.max(np.asarray(self.ship_pic.get_size()) * 1.6))
        (fileobj, namehint) = self.load_dat('shield_small p')
        self.ship_shield_pic = pygame.transform.scale(pygame.image.load(fileobj, namehint).convert(), (shield_size, shield_size))
        self.ship_shield_pic.set_colorkey((0,0,0))
        self.ship_shield_pic.set_alpha(96)
        (fileobj, namehint) = self.load_dat('alien 1 p')
        self.alien1_pic = pygame.image.load(fileobj, namehint).convert()
        self.alien1_pic.set_colorkey((255,255,255))
        (fileobj, namehint) = self.load_dat('alien 2 p')
        self.alien2_pic = pygame.image.load(fileobj, namehint).convert()
        self.alien2_pic.set_colorkey((0,0,0))
        (fileobj, namehint) = self.load_dat('alien 3 p')
        self.alien3_pic = pygame.image.load(fileobj, namehint).convert()
        self.alien3_pic.set_colorkey((0,0,0))
        (fileobj, namehint) = self.load_dat('alien 4 p')
        self.alien4_pic = pygame.image.load(fileobj, namehint).convert()
        self.alien4_pic.set_colorkey((0,0,0))
        (fileobj, namehint) = pygame.image.load('alien 5 p')
        self.alien5_pic = pygame.image.load(fileobj, namehint).convert()
        self.alien5_pic.set_colorkey((0,0,0))
        (fileobj, namehint) = self.load_dat('alien 6 p')
        self.alien6_pic = pygame.image.load(fileobj, namehint).convert()
        self.alien6_pic.set_colorkey((0,0,0))
        (fileobj, namehint) = self.load_dat('alien 7 p')
        self.alien7_pic = pygame.image.load(fileobj, namehint)
        self.alien7_pic.set_colorkey((0,0,0))
        (fileobj, namehint) = self.load_dat('alien 8 p')
        self.alien8_pic = pygame.image.load(fileobj, namehint).convert()
        self.alien8_pic.set_colorkey((0,0,0))
        (fileobj, namehint) = self.load_dat('alien 9 p')
        self.alien9_pic = pygame.image.load(fileobj, namehint).convert()
        self.alien9_pic.set_colorkey((0,0,0))
        (fileobj, namehint) = self.load_dat('alien 10 p')
        self.alien10_pic = pygame.image.load(fileobj, namehint).convert()
        self.alien10_pic.set_colorkey((0,0,0))
        (fileobj, namehint) = self.load_dat('alien 11 p')
        self.alien11_pic = pygame.image.load(fileobj, namehint).convert()
        self.alien11_pic.set_colorkey((0,0,0))
        self.alien11_pic.set_colorkey((0,0,0))
        (fileobj, namehint) = self.load_dat('alien 12 p')
        self.alien12_pic = pygame.image.load(fileobj, namehint).convert()
        self.alien12_pic.set_colorkey((0,0,0))
        (fileobj, namehint) = self.load_dat('explosion alien w')
        self.alien1_sound_explosion = pygame.mixer.Sound(fileobj)
        self.alien1_sound_explosion.set_volume(0.2)
        (fileobj, namehint) = self.load_dat('alien boss 1 p')
        self.boss1_pic = pygame.image.load(fileobj, namehint).convert()
        self.alien_boss1_hit_area = pygame.Rect(206 * 2 // 3, 358 * 2 //3, 100 * 2//3, 57 * 2 // 3)
        self.alien_boss1_pic = pygame.transform.scale(self.alien_boss1_pic, np.array(self.alien_boss1_pic.get_size()) * 2 // 3)
        self.pic_colorkey(self.alien_boss1_pic, (36, 36, 36))
        self.alien_boss1_cannon_pos = np.array([[self.alien_boss_1_pic.get_size()[0] * 0.2 - 10,
                                self.alien_boss1_pic.get_size()[1] - 5],
                                [self.alien_boss1_pic.get_size()[0] * 0.8 - 10,
                                 self.alien_boss1_pic_get_size()[1] - 5]], dtype = np.float)
        (fileobj, namehint) = self.load_dat('alien boss 2 p')
        self.alien_boss2_pic = pygame.image.load(fileobj, namehint).convert()
        self.alien_boss2_pic.set_colorkey((0,0,0))
        self.alien_boss2_hitarea = pygame.Rect(87, 300, 106, 65)
        self.alien_boss2_cannon_pos = np.array([[self.alien_boss2_pic.get_size()[0] * 0.43 - 10, self.alien_boss2_pic.get_size()[1] - 25], [self.alien_boss2_pic.get_size()[0] * 0.57 - 10,
                                                                                                                                            self.alien_boss2_pic.get_size()[1] - 25]], dtype = np.float)
        (fileobj, namehint) = self.load_dat("alien boss 3 p")
        self.alien_boss3_pic = pygame.image.load(fileobj, namehint)
        self.alien_boss3_pic.set_colorkey((0,0,0))
        self.alien_boss3_hit_area = pygame.Rect(135, 210, 52, 45)
        self.alien_boss3_cannon_pos = np.array([[-10, 225], [110, 210], [192, 210], [312, 225]],dtype=np.float)
        (fileobj, namehint) = self.load_dat('alien boss 4 p')
        self.alien_boss4_pic = pygame.image.load(fileobj, namehint).convert()
        self.alien_boss4_pic.set_colorkey((0,0,0))
        self.alien_boss4_hit_area = pygame.Rect(153, 340, 72, 35)
        self.alien_boss4_cannon_pos = np.array([[27, 368], [146, 350], [212, 350], [321, 368]],dtype = np.float)
        (fileobj, namehint) = self.load_dat('alien_ufo p')
        self.alien_ufo_pic = pygame.image.load(fileobj, namehint).convert()
        self.alien_ufo_pic.set_colorkey((0,0,0))
        (fileobj, namehint) = self.load_dat('alien_ufo p')
        self.alien_ufo_pic = pygame.image.load(fileobj, namehint).convert()
        self.alien_ufo_pic.set_colorkey((0,0,0))
        (fileobj, namehint) = self.load_dta('bullet_small p')
        self.bullet_alien1_pic = pygame.image.load(fileobj, namehint).convert()
        self.bullet_alien1_pic = pygame.tranform.flip(pygame.transform.scale(self.bullet_alien1_pic, (np.array(self.bullet_alien1_pic.get_size()) / 2.6).astype(np.int16), 0,1)


                                                                             ))
        



