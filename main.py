import pygame
import random

pygame.init()
pygame.font.init()

GRID_SIZE = 12
CELL_SIZE = 50
SCREEN_SIZE = GRID_SIZE * CELL_SIZE

screen = pygame.display.set_mode((SCREEN_SIZE, SCREEN_SIZE))
pygame.display.set_caption('Stop the darkness')
running = True

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)

# Terrain colors
TERRAINS = ['rock', 'tree', 'plain', 'water', 'magic']
TERRAIN_COLORS = {
    'rock': (120, 120, 120),
    'tree': (34, 139, 34),
    'plain': (222, 184, 135),
    'water': (65, 105, 225),
    'magic': (138, 43, 226),
}

font = pygame.font.SysFont(None, 18)
level_font = pygame.font.SysFont(None, 20, bold=True)

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

dark_cells = set()
dark_cells.add((col, row))

cell_levels = {}

# ------------- Terrain map generation -------------
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

terrain_map = {}
for c in range(GRID_SIZE):
    for r in range(GRID_SIZE):
        terrain_map[(c, r)] = random.choice(terrain_choices)

# ------------- Main loop -------------
while running:
    dt = clock.tick(60)
    move_timer += dt

    if move_timer >= MOVE_DELAY:
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
                clicked_col = mouse_x // CELL_SIZE
                clicked_row = mouse_y // CELL_SIZE

                # Kiểm tra nằm trong lưới
                if not (0 <= clicked_col < GRID_SIZE and 0 <= clicked_row < GRID_SIZE):
                    print(f"Click ngoài lưới: ({clicked_col}, {clicked_row})")
                    continue

                cell_key = (clicked_col, clicked_row)

                # Chặn bấm vào ô bị tô đen
                if cell_key in dark_cells:
                    print(f"Ô ({clicked_col}, {clicked_row}) đã bị bóng tối bao phủ!")
                else:
                    # Lấy level hiện tại (mặc định là 0 nếu chưa từng bấm)
                    current_level = cell_levels.get(cell_key, 0)

                    # Tăng level nếu chưa đạt level 4
                    if current_level < 4:
                        cell_levels[cell_key] = current_level + 1
                        print(f"Ô {cell_key} đã tăng lên Level: {cell_levels[cell_key]}")
                    else:
                        print(f"Ô {cell_key} đã đạt LEVEL TỐI ĐA (Level 4)!")

    screen.fill(WHITE)

    # 1. Vẽ terrains
    for (c, r), t in terrain_map.items():
        color = TERRAIN_COLORS.get(t, (200, 200, 200))
        pygame.draw.rect(screen, color, (c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE))
        # Vẽ chữ viết tắt terrain
        text = font.render(t[0].upper(), True, (255, 255, 255))
        screen.blit(text, (c * CELL_SIZE + 4, r * CELL_SIZE + 2))

    # 2. Vẽ các ô bóng tối (đè lên terrains)
    for c, r in dark_cells:
        pygame.draw.rect(screen, BLACK, (c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE))

    # 3. Vẽ level trên các ô (nếu có)
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
        pygame.draw.line(screen, GRAY, (0, i * CELL_SIZE), (SCREEN_SIZE, i * CELL_SIZE))
        # vertical
        pygame.draw.line(screen, GRAY, (i * CELL_SIZE, 0), (i * CELL_SIZE, SCREEN_SIZE))

    pygame.display.flip()

pygame.quit()
