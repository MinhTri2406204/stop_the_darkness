import pygame
import random
import json

pygame.init()
pygame.font.init()

GRID_SIZE = 12
CELL_SIZE = 50
GRID_PIXELS = GRID_SIZE * CELL_SIZE
INFO_WIDTH = 300  # requested 300 x 600 area for title/info
SCREEN_WIDTH = GRID_PIXELS + INFO_WIDTH
SCREEN_HEIGHT = GRID_PIXELS

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Stop the darkness')
running = True

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (30, 30, 30)
GREEN = (60, 179, 113)
BLUE = (70, 130, 180)
ORANGE = (255, 165, 0)

# Terrain colors
TERRAINS = ['rock', 'tree', 'plain', 'water', 'magic']
TERRAIN_COLORS = {
    'rock': (120, 120, 120),
    'tree': (34, 139, 34),
    'plain': (222, 184, 135),
    'water': (65, 105, 225),
    'magic': (138, 43, 226),
    'beacan': (255, 215, 0),  # special beacon cell (gold)
}

# load costs
try:
    with open("cost.json", "r", encoding="utf-8") as f:
        costs = json.load(f)
except Exception as e:
    print("Warning: could not load cost.json:", e)
    costs = {}

# Fonts
font = pygame.font.SysFont(None, 18)
level_font = pygame.font.SysFont(None, 20, bold=True)
title_font = pygame.font.SysFont(None, 40, bold=True)
res_font = pygame.font.SysFont(None, 28)
small_font = pygame.font.SysFont(None, 16)

clock = pygame.time.Clock()

# Vị trí bắt đầu (Góc dưới bên trái của lưới 12x12)
col, row = 0, GRID_SIZE - 1

# Ranh giới ban đầu của lưới 12x12
left_bound = 0
right_bound = GRID_SIZE - 1
top_bound = 0
bottom_bound = GRID_SIZE - 1

# Hướng di chuyển: (dx, dy)
# 0: Sang phải (1, 0)
# 1: Đi lên (0, -1)
# 2: Sang trái (-1, 0)
# 3: Đi xuống (0, 1)
directions = [(1, 0), (0, -1), (-1, 0), (0, 1)]
dir_index = 0  # Bắt đầu sang phải

move_timer = 0
MOVE_DELAY = 500  # ms giữa mỗi bước (đã giảm để dễ test)

# Control whether the spiral is advancing
playing = False

# Resources (set when play starts)
resources = None  # will be dict like {'wood':12,...}


dark_cells = set()
# start position tracked but not shown until playing
dark_cells.add((col, row))

cell_levels = {}

# ------------- Terrain map generation helpers -------------
# You can tweak weights to control frequency of terrains
terrain_weights = {
    'rock': 8,
    'tree': 12,
    'plain': 40,
    'water': 15,
    'magic': 5,
}
terrain_choices = []
for t, w in terrain_weights.items():
    terrain_choices.extend([t] * w)


def generate_terrain_map():
    m = {}
    for c in range(GRID_SIZE):
        for r in range(GRID_SIZE):
            m[(c, r)] = random.choice(terrain_choices)
    # place beacon in one of the 4 center cells
    center_cells = [
        (GRID_SIZE // 2 - 1, GRID_SIZE // 2 - 1),
        (GRID_SIZE // 2, GRID_SIZE // 2 - 1),
        (GRID_SIZE // 2 - 1, GRID_SIZE // 2),
        (GRID_SIZE // 2, GRID_SIZE // 2),
    ]
    beacon = random.choice(center_cells)
    m[beacon] = 'beacan'
    return m, beacon


def regenerate_map():
    global terrain_map, beacon_pos, cell_levels, dark_cells, resources
    global col, row, left_bound, right_bound, top_bound, bottom_bound, dir_index, move_timer

    terrain_map, beacon_pos = generate_terrain_map()
    # reset game spiral state
    col, row = 0, GRID_SIZE - 1
    left_bound = 0
    right_bound = GRID_SIZE - 1
    top_bound = 0
    bottom_bound = GRID_SIZE - 1
    dir_index = 0
    move_timer = 0
    # reset dark and levels
    dark_cells = {(col, row)}
    # reset all levels to 1
    cell_levels = {}
    for c in range(GRID_SIZE):
        for r in range(GRID_SIZE):
            cell_levels[(c, r)] = 1


# initial terrain map
terrain_map, beacon_pos = generate_terrain_map()
# set default level = 1 for all cells
cell_levels = {}
for c in range(GRID_SIZE):
    for r in range(GRID_SIZE):
        cell_levels[(c, r)] = 1

# Button layout in the info panel
BUTTON_W = 120
BUTTON_H = 40
BUTTON_SPACING = 20
buttons_x = GRID_PIXELS + (INFO_WIDTH - (BUTTON_W * 2 + BUTTON_SPACING)) // 2
buttons_y = SCREEN_HEIGHT // 4 + 60
play_button_rect = pygame.Rect(buttons_x, buttons_y, BUTTON_W, BUTTON_H)
regen_button_rect = pygame.Rect(buttons_x + BUTTON_W + BUTTON_SPACING, buttons_y, BUTTON_W, BUTTON_H)

# ------------- Main loop -------------
while running:
    dt = clock.tick(60)
    if playing:
        move_timer += dt

    if playing and move_timer >= MOVE_DELAY:
        move_timer = 0

        # Lấy hướng đi hiện tại
        dx, dy = directions[dir_index]
        next_col = col + dx
        next_row = row + dy

        # Kiểm tra xem có chạm vào ranh giới xoắn ốc không
        should_turn = False
        if dir_index == 0 and next_col > right_bound:     # Đang sang phải và đụng vách phải
            should_turn = True
            bottom_bound -= 1                             # Thu hẹp ranh giới dưới
        elif dir_index == 1 and next_row < top_bound:     # Đang đi lên và đụng vách trên
            should_turn = True
            right_bound -= 1                              # Thu hẹp ranh giới phải
        elif dir_index == 2 and next_col < left_bound:    # Đang sang trái và đụng vách trái
            should_turn = True
            top_bound += 1                                # Thu hẹp ranh giới trên
        elif dir_index == 3 and next_row > bottom_bound:  # Đang đi xuống và đụng vách dưới
            should_turn = True
            left_bound += 1                               # Thu hẹp ranh giới trái

        # Nếu đụng ranh giới thì đổi hướng và tính lại vị trí kế tiếp
        if should_turn:
            dir_index = (dir_index + 1) % 4
            dx, dy = directions[dir_index]
            next_col = col + dx
            next_row = row + dy

        # Di chuyển nếu chưa bị kẹt ở tâm
        if (next_col, next_row) not in dark_cells and left_bound <= right_bound and top_bound <= bottom_bound:
            if 0 <= next_col < GRID_SIZE and 0 <= next_row < GRID_SIZE:
                col, row = next_col, next_row
                dark_cells.add((col, row))

    # Xử lý sự kiện
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_x, mouse_y = event.pos

                # If click is inside info panel, check buttons first
                if mouse_x >= GRID_PIXELS:
                    # If currently playing, the panel shows resources only; ignore clicks there
                    if playing:
                        # Optionally later we could add pause button here
                        continue
                    # Not playing: check buttons
                    if play_button_rect.collidepoint(mouse_x, mouse_y):
                        # Toggle playing; when starting play initialize resources
                        was_playing = playing
                        playing = not playing
                        if playing and not was_playing:
                            resources = {'wood': 12, 'rock': 0, 'mana': 0, 'technology': 0}
                            print('Playing - resources initialized:', resources)
                        else:
                            print('Paused')
                        continue
                    if regen_button_rect.collidepoint(mouse_x, mouse_y):
                        regenerate_map()
                        print('Map regenerated')
                        continue
                    # clicked inside panel but not on buttons; ignore
                    continue

                # Click inside grid
                clicked_col = mouse_x // CELL_SIZE
                clicked_row = mouse_y // CELL_SIZE

                # Kiểm tra nằm trong lưới
                if not (0 <= clicked_col < GRID_SIZE and 0 <= clicked_row < GRID_SIZE):
                    print(f"Click ngoài lưới: ({clicked_col}, {clicked_row})")
                    continue

                # If not playing, do not allow interacting with grid (no levels, no dark)
                if not playing:
                    print("Press Play to start and enable interactions")
                    continue

                cell_key = (clicked_col, clicked_row)

                # Chặn bấm vào ô bị tô đen
                if cell_key in dark_cells:
                    print(f"Ô ({clicked_col}, {clicked_row}) đã bị bóng tối bao phủ!")
                else:
                    # Lấy level hiện tại (mặc định là 1 nếu chưa từng bấm)
                    current_level = cell_levels.get(cell_key, 1)

                    # Tối đa level 4
                    if current_level >= 4:
                        print(f"Ô {cell_key} đã đạt LEVEL TỐI ĐA (Level 4)!")
                        continue

                    # Determine cost key. map terrain name 'beacan' -> 'beacon'
                    terrain_type = terrain_map.get(cell_key, 'plain')
                    if terrain_type == 'beacan':
                        cost_key = 'beacon'
                    else:
                        cost_key = terrain_type

                    cost = costs.get(cost_key)

                    # If resources exists (playing), check and deduct; otherwise allow free upgrades (edit mode)
                    if resources is not None and cost:
                        # check resource sufficiency
                        enough = True
                        for res_name, amt in cost.items():
                            # 'mana' in cost maps to resources['mana']
                            if resources.get(res_name, 0) < amt:
                                enough = False
                                break
                        if not enough:
                            print(f"Không đủ tài nguyên để nâng ô {cell_key} ({terrain_type}) — cần {cost}")
                            continue
                        # deduct
                        for res_name, amt in cost.items():
                            resources[res_name] = resources.get(res_name, 0) - amt
                        print(f"Đã trừ tài nguyên {cost} cho ô {cell_key}; resources now: {resources}")

                    # Apply level up
                    cell_levels[cell_key] = current_level + 1
                    print(f"Ô {cell_key} đã tăng lên Level: {cell_levels[cell_key]}")

                    # Increase global cost values for this terrain type by 1 per resource key
                    # Applies to terrain types: tree, rock, plain, magic, plain_wood, plain_rock, plain_magic
                    try:
                        # only adjust if this terrain has an entry in costs
                        if cost_key in costs:
                            for rkey in list(costs[cost_key].keys()):
                                # ensure numeric
                                try:
                                    costs[cost_key][rkey] = int(costs[cost_key][rkey]) + 1
                                except Exception:
                                    pass
                            print(f"Increased costs for '{cost_key}' to: {costs[cost_key]}")
                    except Exception as e:
                        print("Error increasing costs:", e)

    screen.fill(WHITE)

    # Draw left: 1. Vẽ terrains
    for (c, r), t in terrain_map.items():
        color = TERRAIN_COLORS.get(t, (200, 200, 200))
        pygame.draw.rect(screen, color, (c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE))
        # Vẽ chữ viết tắt terrain
        # For 'beacan' we want 'B'
        label = 'B' if t == 'beacan' else t[0].upper()
        text = font.render(label, True, (255, 255, 255))
        screen.blit(text, (c * CELL_SIZE + 4, r * CELL_SIZE + 2))

    # 2. Vẽ các ô bóng tối (đè lên terrains) - only when playing
    if playing:
        for c, r in dark_cells:
            pygame.draw.rect(screen, BLACK, (c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE))

    # 3. Vẽ level trên các ô (nếu có) - only when playing
    if playing:
        for (c, r), lvl in cell_levels.items():
            if 0 <= c < GRID_SIZE and 0 <= r < GRID_SIZE:
                # If cell is dark, skip drawing level (it's covered)
                if (c, r) in dark_cells:
                    continue
                lvl_text = level_font.render(str(lvl), True, (0, 0, 0))
                screen.blit(lvl_text, (c * CELL_SIZE + CELL_SIZE - 18, r * CELL_SIZE + CELL_SIZE - 20))

    # 4. Vẽ lưới
    for i in range(GRID_SIZE + 1):
        # horizontal
        pygame.draw.line(screen, GRAY, (0, i * CELL_SIZE), (GRID_PIXELS, i * CELL_SIZE))
        # vertical
        pygame.draw.line(screen, GRAY, (i * CELL_SIZE, 0), (i * CELL_SIZE, GRID_PIXELS))

    # Draw right info panel (300 x 600)
    pygame.draw.rect(screen, DARK_GRAY, (GRID_PIXELS, 0, INFO_WIDTH, SCREEN_HEIGHT))

    # If playing, show only resources in the panel
    if playing and resources is not None:
        # Title small at top
        title_surface = title_font.render('Stop the darkness', True, WHITE)
        title_rect = title_surface.get_rect()
        title_rect.center = (GRID_PIXELS + INFO_WIDTH // 2, 40)
        screen.blit(title_surface, title_rect)

        # Draw resources list
        labels = ['Wood', 'Rock', 'Mana', 'Technology']
        keys = ['wood', 'rock', 'mana', 'technology']
        start_y = 120
        for i, k in enumerate(keys):
            y = start_y + i * 48
            name_surf = res_font.render(labels[i] + ':', True, WHITE)
            val_surf = res_font.render(str(resources.get(k, 0)), True, WHITE)
            name_rect = name_surf.get_rect()
            val_rect = val_surf.get_rect()
            name_rect.topleft = (GRID_PIXELS + 30, y)
            val_rect.topright = (GRID_PIXELS + INFO_WIDTH - 30, y)
            screen.blit(name_surf, name_rect)
            screen.blit(val_surf, val_rect)

        # Hover info: show info about terrain under mouse
        mouse_x, mouse_y = pygame.mouse.get_pos()
        hover_info_y = start_y + len(keys) * 48 + 12
        info_x = GRID_PIXELS + 20
        info_w = INFO_WIDTH - 40

        if mouse_x < GRID_PIXELS and 0 <= mouse_x < GRID_PIXELS and 0 <= mouse_y < SCREEN_HEIGHT:
            hover_col = mouse_x // CELL_SIZE
            hover_row = mouse_y // CELL_SIZE
            if 0 <= hover_col < GRID_SIZE and 0 <= hover_row < GRID_SIZE:
                ttype = terrain_map.get((hover_col, hover_row), 'plain')
                display_name = 'Beacon' if ttype == 'beacan' else ttype.capitalize()
                level = cell_levels.get((hover_col, hover_row), 1)
                next_level = level + 1

                # draw current info box
                pygame.draw.rect(screen, (50, 50, 50), (info_x, hover_info_y, info_w, 60))
                pygame.draw.rect(screen, WHITE, (info_x, hover_info_y, info_w, 60), 1)
                line1 = res_font.render(f"Terrain: {display_name}", True, WHITE)
                line2 = res_font.render(f"Level: {level}", True, WHITE)
                screen.blit(line1, (info_x + 8, hover_info_y + 6))
                screen.blit(line2, (info_x + 8, hover_info_y + 30))

                # draw next-level info box below
                box2_y = hover_info_y + 70
                pygame.draw.rect(screen, (50, 50, 50), (info_x, box2_y, info_w, 90))
                pygame.draw.rect(screen, WHITE, (info_x, box2_y, info_w, 90), 1)
                nl = res_font.render(f"Next Level: {next_level}", True, WHITE)
                screen.blit(nl, (info_x + 8, box2_y + 6))

                # compute cost after +1 for the terrain type
                cost_key = 'beacon' if ttype == 'beacan' else ttype
                cost_entry = costs.get(cost_key)
                cost_text_y = box2_y + 36
                if cost_entry:
                    # show each resource with value+1
                    cx = info_x + 8
                    for i, (rk, rv) in enumerate(cost_entry.items()):
                        try:
                            new_val = int(rv) + 1
                        except Exception:
                            new_val = rv
                        ct = small_font.render(f"{rk.capitalize()}: {new_val}", True, WHITE)
                        screen.blit(ct, (cx, cost_text_y + i * 18))
                else:
                    ct = small_font.render("Cost: -", True, WHITE)
                    screen.blit(ct, (info_x + 8, cost_text_y))

                # production per minute placeholder
                ppm = small_font.render("Production per minute: ", True, WHITE)
                screen.blit(ppm, (info_x + 8, box2_y + 70))

    else:
        # Title centered in the info panel
        title_surface = title_font.render('Stop the darkness', True, WHITE)
        title_rect = title_surface.get_rect()
        title_rect.center = (GRID_PIXELS + INFO_WIDTH // 2, SCREEN_HEIGHT // 4)
        screen.blit(title_surface, title_rect)

        # Optional: small subtitle
        subtitle = font.render('Protect the beacon!', True, (200, 200, 200))
        sub_rect = subtitle.get_rect()
        sub_rect.center = (GRID_PIXELS + INFO_WIDTH // 2, SCREEN_HEIGHT // 4 + 36)
        screen.blit(subtitle, sub_rect)

        # Draw buttons
        # Play / Pause button
        play_color = ORANGE if playing else GREEN
        pygame.draw.rect(screen, play_color, play_button_rect)
        pygame.draw.rect(screen, WHITE, play_button_rect, 2)
        play_label = 'Pause' if playing else 'Play'
        play_text = font.render(play_label, True, WHITE)
        pt_rect = play_text.get_rect()
        pt_rect.center = play_button_rect.center
        screen.blit(play_text, pt_rect)

        # Regenerate button
        pygame.draw.rect(screen, BLUE, regen_button_rect)
        pygame.draw.rect(screen, WHITE, regen_button_rect, 2)
        regen_text = font.render('Regenerate Map', True, WHITE)
        rt_rect = regen_text.get_rect()
        rt_rect.center = regen_button_rect.center
        screen.blit(regen_text, rt_rect)

        # small legend area (optional)
        legend_y = buttons_y + BUTTON_H + 30
        lx = GRID_PIXELS + 20
        for i, t in enumerate(TERRAINS + ['beacan']):
            ty = legend_y + i * 24
            color = TERRAIN_COLORS.get(t, (200, 200, 200))
            pygame.draw.rect(screen, color, (lx, ty, 18, 18))
            label = 'Beacon' if t == 'beacan' else t.capitalize()
            lbl = font.render(label, True, WHITE)
            screen.blit(lbl, (lx + 24, ty))

    pygame.display.flip()

pygame.quit()
