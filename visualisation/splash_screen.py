"""Modern cinematic splash screen for the BVR Combat Simulator."""

import time
from typing import Tuple
import pygame

class SplashScreen:
    """Handles the 3.5-second intro animation sequence."""
    
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.duration = 1.0
        self.start_time = time.time()
        
        # Colors
        self.BG = (5, 8, 12)
        self.ACCENT = (0, 255, 180)  # Cyber green/cyan
        self.GLOW = (0, 100, 80)
        self.TEXT_COLOR = (220, 240, 255)
        
        # Fonts
        pygame.font.init()
        self.title_font = pygame.font.SysFont("arial black", 72)
        self.sub_font = pygame.font.SysFont("consolas", 24)
        self.small_font = pygame.font.SysFont("consolas", 14)

    def is_finished(self) -> bool:
        return (time.time() - self.start_time) >= self.duration

    def draw(self, screen: pygame.Surface) -> None:
        elapsed = time.time() - self.start_time
        progress = min(1.0, elapsed / self.duration)
        
        screen.fill(self.BG)
        cx, cy = self.width // 2, self.height // 2
        
        # 1. Background Grid / Radar Pulse
        pulse_r = (elapsed * 800) % 1200
        pygame.draw.circle(screen, (10, 20, 30), (cx, cy), int(pulse_r), 2)
        
        # 2. Main Title (with fade + slight upward movement)
        alpha = int(min(1.0, progress * 4) * 255)
        if progress > 0.8:
            alpha = int((1.0 - (progress - 0.8) / 0.2) * 255)
            
        title_surf = self.title_font.render("BVR COMBAT SYSTEM", True, self.ACCENT)
        title_surf.set_alpha(alpha)
        title_rect = title_surf.get_rect(center=(cx, cy - 40))
        
        # Glow effect
        glow_surf = self.title_font.render("BVR COMBAT SYSTEM", True, self.GLOW)
        glow_surf.set_alpha(alpha // 2)
        screen.blit(glow_surf, (title_rect.x + 4, title_rect.y + 4))
        screen.blit(title_surf, title_rect)
        
        # 3. Subtitle
        sub_text = "INITIALIZING MULTI-AGENT ARCHITECTURE v2.0"
        sub_surf = self.sub_font.render(sub_text, True, self.TEXT_COLOR)
        sub_surf.set_alpha(alpha)
        sub_rect = sub_surf.get_rect(center=(cx, cy + 50))
        screen.blit(sub_surf, sub_rect)
        
        # 4. Loading Bar (Bottom)
        bar_w, bar_h = 600, 4
        bx = cx - bar_w // 2
        by = cy + 120
        
        # Bar background
        pygame.draw.rect(screen, (20, 30, 40), (bx, by, bar_w, bar_h))
        # Bar progress
        current_w = int(bar_w * progress)
        pygame.draw.rect(screen, self.ACCENT, (bx, by, current_w, bar_h))
        
        # 5. Boot log simulation (Left side)
        logs = [
            "CHECKING RADAR SUBSYSTEMS...",
            "LOADING PPO NEURAL WEIGHTS...",
            "INITIALIZING MISSLE KINEMATICS...",
            "DARPA AI ENGINE STANDBY...",
            "SOP ANALYSIS READY.",
            "COMMUNICATIONS LINK ESTABLISHED."
        ]
        
        log_count = int(progress * (len(logs) + 2))
        for i in range(min(log_count, len(logs))):
            log_surf = self.small_font.render(f"> {logs[i]}", True, (100, 200, 180))
            screen.blit(log_surf, (bx, by + 20 + i * 18))
            
        # 6. Scanning Lines (Retro feel)
        for i in range(0, self.height, 4):
            pygame.draw.line(screen, (0, 0, 0, 40), (0, i), (self.width, i))
        
        pygame.display.flip()
