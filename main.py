import pygame
pygame.init()

screen = pygame.display.set_mode((900, 601))
pygame.display.set_caption('Stop the darkness')
running = True

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)

clock = pygame.time.Clock()
CELL_SIZE = 50

# Vị trí bắt đầu (Góc dưới bên trái của lưới 12x12)
col, row = 0, 11

# Ranh giới ban đầu của lưới 12x12
left_bound = 0
right_bound = 11
top_bound = 0
bottom_bound = 11

# Hướng di chuyển: (dx, dy)
# 0: Sang phải (1, 0)
# 1: Đi lên (0, -1)
# 2: Sang trái (-1, 0)
# 3: Đi xuống (0, 1)
directions = [(1, 0), (0, -1), (-1, 0), (0, 1)]
dir_index = 0  # Bắt đầu sang phải

move_timer = 0
MOVE_DELAY = 5000  # Cứ 5000ms nhảy 1 ô

dark_cells = set()
dark_cells.add((col, row))

cell_levels = {}

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
                cell_key = (clicked_col, clicked_row)

                # Chặn bấm vào ô bị tô đen
                if (clicked_col, clicked_row) in dark_cells:
                    print(f"Ô ({clicked_col}, {clicked_row}) đã bị bóng tối bao phủ!")
                else:
                    # Lấy level hiện tại (mặc định là 0 nếu chưa từng bấm)
                    current_level = cell_levels.get(cell_key, 0)

                    # 2. Tăng level nếu chưa đạt level 4
                    if current_level < 4:
                        cell_levels[cell_key] = current_level + 1
                        print(f"Ô {cell_key} đã tăng lên Level: {cell_levels[cell_key]}")
                    else:
                        print(f"Ô {cell_key} đã đạt LEVEL TỐI ĐA (Level 4)!")
    screen.fill(WHITE)

    # 1. Vẽ các ô bóng tối
    for c, r in dark_cells:
        pygame.draw.rect(screen, BLACK, (c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE))

    # 2. Vẽ lưới
    for i in range(13):
        pygame.draw.line(screen, GRAY, (0, i * CELL_SIZE), (600, i * CELL_SIZE))
    # for i in range(19):
        pygame.draw.line(screen, GRAY, (i * CELL_SIZE, 0), (i * CELL_SIZE, 600))

    pygame.display.flip()

pygame.quit()