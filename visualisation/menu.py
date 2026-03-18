import pygame
import glob
from pathlib import Path

# Brief descriptions for tactical clarity
SCENARIO_DESC = {
    "aggressive_showdown": "Immediate 80km Combat. High Action.",
    "4v4_equal": "Standard 150km BVR setup. Balanced.",
    "4v6_blue_disadvantage": "Outnumbered. Tests AI survival tactics.",
    "6v4_blue_advantage": "Numerical superiority assault.",
    "8v8_large_engagement": "Massive scale theater combat."
}

def show_scenario_menu(screen: pygame.Surface, font: pygame.font.Font) -> str | None:
    """Display an interactive menu to pick a scenario YAML."""
    scenarios = glob.glob("data/scenario_configs/*.yaml")
    scenarios.sort()
    
    if not scenarios:
        return None
        
    selected_idx = 0
    running = True
    clock = pygame.time.Clock()
    
    # Colors
    BG = (10, 15, 25)
    CYAN = (80, 255, 255)
    WHITE = (255, 255, 255)
    GREY = (100, 100, 100)
    DARK_BLUE = (20, 40, 80)
    
    # Calculate box sizes
    w, h = screen.get_size()
    box_w = 800
    box_h = 50 + len(scenarios) * 60 + 50
    bx = (w - box_w) // 2
    by = (h - box_h) // 2
    
    while running:
        screen.fill(BG)
        
        # Draw Menu Box
        pygame.draw.rect(screen, DARK_BLUE, (bx, by, box_w, box_h), border_radius=12)
        pygame.draw.rect(screen, CYAN, (bx, by, box_w, box_h), 2, border_radius=12)
        
        # Title
        title = font.render("=== SELECT TACTICAL SCENARIO ===", True, CYAN)
        screen.blit(title, (bx + (box_w - title.get_width())//2, by + 20))
        
        # Scenarios List
        y = by + 80
        for i, sc in enumerate(scenarios):
            stem = Path(sc).stem
            name = stem.replace("_", " ").title()
            desc = SCENARIO_DESC.get(stem, "Custom Scenario")
            
            if i == selected_idx:
                color = WHITE
                prefix = "  >> "
                pygame.draw.rect(screen, (40, 80, 150), (bx + 10, y - 5, box_w - 20, 50), border_radius=6)
            else:
                color = GREY
                prefix = "     "
                
            text_name = font.render(f"{prefix}{name}", True, color)
            screen.blit(text_name, (bx + 30, y + 5))
            
            # Subtle description
            font_small = pygame.font.SysFont("consolas", 14)
            text_desc = font_small.render(desc, True, (150, 180, 200) if i == selected_idx else (80, 80, 80))
            screen.blit(text_desc, (bx + 400, y + 10))
            
            y += 60
            
        # Controls Text
        help_txt = font.render("[UP/DOWN] Select  |  [ENTER] Launch  |  [ESC] Quit", True, GREY)
        screen.blit(help_txt, (bx + (box_w - help_txt.get_width())//2, y + 20))
        
        pygame.display.flip()
        
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return None
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_UP:
                    selected_idx = max(0, selected_idx - 1)
                elif ev.key == pygame.K_DOWN:
                    selected_idx = min(len(scenarios) - 1, selected_idx + 1)
                elif ev.key == pygame.K_RETURN:
                    return scenarios[selected_idx]
                elif ev.key == pygame.K_ESCAPE:
                    return None
                    
        clock.tick(30)
