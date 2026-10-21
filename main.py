import pygame
import random
import json
import math
from pathlib import Path

script_dir = Path(__file__).parent
file_path = script_dir / "cost.json"

pygame.init()
pygame.font.init()

GRID_SIZE = 12
CELL_SIZE = 50
GRID_PIXELS = GRID_SIZE * CELL_SIZE
INFO_WIDTH = 300 
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

# Màu Terrain 
TERRAINS = ['rock', 'tree', 'plain', 'water', 'magic']
TERRAIN_COLORS = {
    'rock': (120, 120, 120),
    'tree': (34, 139, 34),
    'plain': (222, 184, 135),
    'water': (65, 105, 225),
    'magic': (138, 43, 226),
    'beacon': (255, 215, 0),  
    'plain_wood': (255, 180, 50),   
    'plain_rock': (180, 180, 180),  
    'plain_magic': (200, 150, 255), 
    'plain_water': (173, 216, 230), 
}

# nạp chi phí từ file .json
try:
    with open(file_path, "r", encoding="utf-8") as f:
        costs = json.load(f)
except Exception as e:
    print("Warning: could not load cost.json:", e)
    costs = {}

# sản phẩm thu được theo từng phút của từng loại terrain và level
PRODUCTION_TABLE = {
    'tree': {2: 3, 3: 5, 4: 7},
    'rock': {2: 2, 3: 5, 4: 8},
    'magic': {2: 4, 3: 7, 4: 9},
}
# Map loại terrain tới khóa tài nguyên trong dict resources
TERRAIN_TO_RESOURCE = {
    'tree': 'wood',
    'rock': 'rock',
    'magic': 'mana',
}

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

# Hướng di chuyển của bóng tối: (dx, dy)
directions = [(1, 0), (0, -1), (-1, 0), (0, 1)]
dir_index = 0  

move_timer = 0
MOVE_DELAY = 5000 

# Điều kiện khi game đang chạy hoặc mới bắt đầu
playing = False
game_started = False
game_won = False  
game_lost = False  

# Tài nguyên (khi game bắt đầu)
resources = None  
resource_accum = {}

# Khởi tạo ô bóng tối
dark_cells = set()
dark_cells.add((col, row))

cell_levels = {}

# Khởi tạo terrain_map và beacon_pos
def generate_terrain_map():
    """
    Tạo map với số lượng terrain giới hạn:
    - tree: tối đa 40 ô
    - water: tối đa 30 ô
    - rock: tối đa 14 ô
    - magic: tối đa 4 ô
    """
    m = {}
    center_cells = [
        (GRID_SIZE // 2 - 1, GRID_SIZE // 2 - 1),
        (GRID_SIZE // 2, GRID_SIZE // 2 - 1),
        (GRID_SIZE // 2 - 1, GRID_SIZE // 2),
        (GRID_SIZE // 2, GRID_SIZE // 2),
    ]
    beacon = random.choice(center_cells)
    positions = [(c, r) for c in range(GRID_SIZE) for r in range(GRID_SIZE) if (c, r) != beacon]
    max_counts = {'tree': 40, 'water': 30, 'rock': 14, 'magic': 4}

    pool = []
    for terrain, cnt in max_counts.items():
        take = min(cnt, len(positions) - len(pool))
        pool.extend([terrain] * take)
    remaining = len(positions) - len(pool)
    if remaining > 0:
        pool.extend(['plain'] * remaining)
    random.shuffle(pool)
    for pos, terrain in zip(positions, pool):
        m[pos] = terrain
    m[beacon] = 'beacon'
    return m, beacon

# Tái tạo lại map và đặt lại trạng thái game
def regenerate_map():
    global terrain_map, beacon_pos, cell_levels, dark_cells, resources, resource_accum, game_won, game_lost
    global col, row, left_bound, right_bound, top_bound, bottom_bound, dir_index, move_timer

    terrain_map, beacon_pos = generate_terrain_map()
    cell_levels = {}
    for c in range(GRID_SIZE):
        for r in range(GRID_SIZE):
            t = terrain_map.get((c, r), 'plain')
            if t == 'plain' or (isinstance(t, str) and t.startswith('plain_')):
                cell_levels[(c, r)] = 0
            else:
                cell_levels[(c, r)] = 1


terrain_map, beacon_pos = generate_terrain_map()
cell_levels = {}
for c in range(GRID_SIZE):
    for r in range(GRID_SIZE):
        t = terrain_map.get((c, r), 'plain')
        if t == 'plain' or (isinstance(t, str) and t.startswith('plain_')):
            cell_levels[(c, r)] = 0
        else:
            cell_levels[(c, r)] = 1

BUTTON_W = 120
BUTTON_H = 40
BUTTON_SPACING = 20
buttons_x = GRID_PIXELS + (INFO_WIDTH - (BUTTON_W * 2 + BUTTON_SPACING)) // 2
buttons_y = SCREEN_HEIGHT // 4 + 60
play_button_rect = pygame.Rect(buttons_x, buttons_y, BUTTON_W, BUTTON_H)

pause_button_rect = pygame.Rect(GRID_PIXELS + (INFO_WIDTH - BUTTON_W) // 2, 65, BUTTON_W, BUTTON_H)
regen_button_rect = pygame.Rect(buttons_x + BUTTON_W + BUTTON_SPACING, buttons_y, BUTTON_W, BUTTON_H)

play_again_button_rect = pygame.Rect((GRID_PIXELS - 180) // 2, SCREEN_HEIGHT // 2 + 55, 180, 44)

# Hàm tính sản lượng mỗi phút cho một ô terrain_type ở level nhất định
def get_cell_production_per_minute(terrain_type, level):
    """Trả về (resource_key, amount_per_minute) cho một ô terrain_type ở level nhất định."""
    if terrain_type == 'beacon':
        return None, 0
    if terrain_type not in PRODUCTION_TABLE:
        return None, 0
    mapping = PRODUCTION_TABLE[terrain_type]
    possible_levels = sorted([l for l in mapping.keys() if l <= level])
    if not possible_levels:
        return None, 0
    use_level = possible_levels[-1]
    amount = mapping.get(use_level, 0)
    res_key = TERRAIN_TO_RESOURCE.get(terrain_type)
    return res_key, amount

# Hàm trả về danh sách các loại terrain mà một ô có thể nhận boost
def get_boost_targets(terrain_name):
    """Trả về danh sách các loại terrain mà một ô có thể nhận boost."""
    if terrain_name == 'tree':
        return ['tree']
    if terrain_name == 'rock':
        return ['rock']
    if terrain_name == 'magic':
        return ['magic']
    if terrain_name == 'plain_wood':
        return ['tree', 'rock']
    if terrain_name == 'plain_rock':
        return ['rock']
    if terrain_name == 'plain_magic':
        return ['tree', 'magic']
    if terrain_name == 'plain_water':
        return ['tree', 'rock']
    return []

# Hàm tính phần trăm boost dựa trên terrain nguồn, level nguồn và terrain mục tiêu
def get_boost_percent(source_terrain, source_level, target_terrain):
    """Hệ số nhân phần trăm từ quy tắc tăng cường liền kề.
        Quy tắc:
            - tree / rock / magic => chỉ tăng cường cùng loại.
            - tree => tăng cường sản xuất cây và đá.
            - rock => chỉ tăng cường sản xuất đá; 50% ở cấp độ 1-2 và 75% ở cấp độ 3-4.
            - magic => tăng cường sản xuất cây và ma thuật.
            - water => tăng cường sản xuất cây và đá.
            - tất cả các tổ hợp khác => 0.
        Tỷ lệ phần trăm được biểu thị dưới dạng số thập phân để nhân.
    """
    if source_level is None or source_level <= 0:
        return 0.0

    if target_terrain not in get_boost_targets(source_terrain):
        return 0.0

    if source_terrain in ('tree', 'rock', 'magic'):
        return 0.25 if source_level <= 2 else 0.50
    if source_terrain == 'plain_wood':
        return 0.25 if source_level <= 2 else 0.50
    if source_terrain == 'plain_rock':
        return 0.50 if source_level <= 2 else 0.75
    if source_terrain == 'plain_magic':
        return 0.25 if source_level <= 2 else 0.50
    if source_terrain == 'plain_water':
        return 0.25 if source_level <= 2 else 0.50 if source_level == 3 else 0.75
    return 0.0

# Hàm tính toán chi phí nâng cấp dựa trên cost_entry, loại terrain và level tiếp theo
def compute_upgrade_cost(cost_entry, terrain_type, next_level):
    """ Tính toán từ điển chi phí cuối cùng để nâng cấp lên next_level.
        Đối với các loại địa hình thông thường: final = ceil(base * (1 + 0.1 * x)) trong đó x = next_level (1..4).
        Đối với các loại địa hình khác: trả về bản sao số nguyên của chi phí cơ bản.
    """
    if not cost_entry:
        return None
    final = {}
    if isinstance(terrain_type, str) and terrain_type.startswith('plain'):
        x = max(1, min(4, int(next_level)))
        mult = 1.0 + 0.1 * x
        for rk, amt in cost_entry.items():
            try:
                base = float(amt)
                final_amt = int(math.ceil(base * mult))
            except Exception:
                final_amt = amt
            final[rk] = final_amt
    else:
        for rk, amt in cost_entry.items():
            try:
                final[rk] = int(amt)
            except Exception:
                final[rk] = amt
    return final

# Hàm tính tổng sản lượng mỗi phút trên toàn bộ lưới 3x3
def compute_total_production_per_minute():
    """ Tính tổng sản lượng mỗi phút trên toàn bộ lưới và trả về từ điển resource->amt.
        Mỗi địa hình liền kề trong khu vực 3x3 đóng góp một phần tăng cường cho sản lượng của ô mục tiêu.
        Chỉ những hàng xóm có cấp độ >=1 mới đóng góp phần tăng cường; hàng xóm cấp độ 0 thì không.
    """
    totals = {}
    for (c, r), lvl in cell_levels.items():
        terrain = terrain_map.get((c, r), 'plain')
        target = terrain if terrain != 'plain' else choose_plain_variant(c, r)

        res_key, base_amt = get_cell_production_per_minute(target, lvl)
        if not res_key or base_amt == 0:
            continue

        boost_total = 0.0
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx = c + dx
                ny = r + dy
                if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
                    continue
                neighbor_type = terrain_map.get((nx, ny), 'plain')
                if neighbor_type == 'plain':
                    neighbor_type = choose_plain_variant(nx, ny)
                neighbor_level = cell_levels.get((nx, ny), 0)
                if neighbor_level <= 0:
                    continue
                boost_total += get_boost_percent(neighbor_type, neighbor_level, target)

        final_amt = base_amt * (1.0 + boost_total)
        totals[res_key] = totals.get(res_key, 0) + final_amt

    return totals


# Hàm xác định biến thể plain dựa trên các láng giềng vuông góc
def choose_plain_variant(center_col, center_row):
    """ Trả về 'plain_rock' nếu có >=2 láng giềng vuông góc là 'rock',
        trả về 'plain_magic' nếu có >=1 láng giềng là 'magic' (theo quy tắc cập nhật),
        ngược lại trả về 'plain_wood'.
    """
    neighbors = [
        (center_col - 1, center_row),
        (center_col, center_row - 1),
        (center_col, center_row + 1),
        (center_col + 1, center_row),
    ]
    water_count = 0
    rock_count = 0
    magic_count = 0
    for nx, ny in neighbors:
        if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
            nt = terrain_map.get((nx, ny), 'plain')
            if nt == 'rock':
                rock_count += 1
            elif nt == 'magic':
                magic_count += 1
            elif nt == 'water':
                water_count += 1
    if rock_count >= 2:
        return 'plain_rock'
    if magic_count >= 1:
        return 'plain_magic'
    if water_count >=1:
        return 'plain_water'
    return 'plain_wood'

# Các ô phụ thuộc là các ô vuông góc xung quanh (trái, phải, trên, dưới)
DEPENDENCY_OFFSETS = [(-1, 0), (0, -1), (0, 1), (1, 0)]

# Hàm kiểm tra xem ô plain có thể nâng cấp lên cấp độ cao hơn hay không dựa trên các ô phụ thuộc
def can_upgrade_plain_to_higher(center_col, center_row, plain_variant, target_level):
    """ Trả về True nếu ô đất bằng phẳng tại (center_col, center_row) thuộc loại plain_variant được phép nâng cấp lên target_level.
        Quy tắc:
        - Luôn được phép nâng cấp lên cấp độ 2 (tùy thuộc vào tài nguyên/chi phí).
        - Nâng cấp lên cấp độ 3 hoặc 4 yêu cầu các địa hình phụ thuộc (cây/đá/phép thuật) tại 4 vị trí vuông góc
        phải hiện diện và ở cấp độ 4. Nếu bất kỳ vị trí phụ thuộc nào nằm ngoài giới hạn hoặc không phải là địa hình cần thiết ở cấp độ 4,
        việc nâng cấp sẽ bị chặn.
    """
    if target_level <= 2:
        return True
    mapping = {
        'plain_wood': 'tree',
        'plain_rock': 'rock',
        'plain_magic': 'magic',
        'plain_water': 'water'
    }
    req = mapping.get(plain_variant)
    if req is None:
        return False
    for dx, dy in DEPENDENCY_OFFSETS:
        nx = center_col + dx
        ny = center_row + dy
        if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
            return False
        if terrain_map.get((nx, ny)) != req:
            return False
        if cell_levels.get((nx, ny), 1) < 4:
            return False
    return True

# Hàm tính tổng phần trăm tăng cường lân cận cho một ô tại (center_col, center_row)
def compute_cell_boost_percent(center_col, center_row):
    """Tính tổng mức tăng cường lân cận (dưới dạng số thập phân, ví dụ: 0,25 => 25%) được áp dụng cho ô tại (center_col, center_row)."""
    terrain = terrain_map.get((center_col, center_row), 'plain')
    if terrain == 'plain':
        target = choose_plain_variant(center_col, center_row)
    else:
        target = terrain

    boost_total = 0.0
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx = center_col + dx
            ny = center_row + dy
            if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
                continue
            source = terrain_map.get((nx, ny), 'plain')
            if source == 'plain':
                source = choose_plain_variant(nx, ny)
            neighbor_level = cell_levels.get((nx, ny), 0)
            if neighbor_level <= 0:
                continue
            boost_total += get_boost_percent(source, neighbor_level, target)
    return boost_total


# Main loop
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
        if dir_index == 0 and next_col > right_bound:     
            should_turn = True
            bottom_bound -= 1                             
        elif dir_index == 1 and next_row < top_bound:     
            should_turn = True
            right_bound -= 1                              
        elif dir_index == 2 and next_col < left_bound:    
            should_turn = True
            top_bound += 1                               
        elif dir_index == 3 and next_row > bottom_bound:  
            should_turn = True
            left_bound += 1                               

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
                # Kiểm tra điều kiện thua: nếu tất cả các ô đều bị bóng tối bao phủ
                if len(dark_cells) >= GRID_SIZE * GRID_SIZE:
                    game_lost = True
                    playing = False
                    print('YOU LOSE! Darkness covered the entire grid.')

    # Tích lũy sản lượng tài nguyên theo thời gian
    if playing and resources is not None:
        for k in resources.keys():
            resource_accum.setdefault(k, 0.0)

        prod_totals = compute_total_production_per_minute()  # resource->per-minute
        # Cập nhật resource_accum dựa trên dt (ms) và sản lượng mỗi phút
        for res_key, per_min in prod_totals.items():
            add_amount = per_min * (dt / 60000.0)
            resource_accum[res_key] = resource_accum.get(res_key, 0.0) + add_amount
            # flush whole units to resources
            whole = int(resource_accum[res_key])
            if whole > 0:
                resources[res_key] = resources.get(res_key, 0) + whole
                resource_accum[res_key] -= whole

    # Xử lý sự kiện
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_x, mouse_y = event.pos

                # If click is inside info panel, check buttons first
                if mouse_x >= GRID_PIXELS:
                    if game_started:
                        # Pause/Resume without resetting resources or the map. A won game stays ended.
                        if pause_button_rect.collidepoint(mouse_x, mouse_y):
                            if not game_won and not game_lost:
                                playing = not playing
                                move_timer = 0
                                print('Resumed' if playing else 'Paused')
                        continue

                    # Before the game starts, show Play and Regenerate buttons
                    if play_button_rect.collidepoint(mouse_x, mouse_y):
                        playing = True
                        game_started = True
                        if resources is None:
                            resources = {'wood': 12, 'rock': 0, 'mana': 0, 'technology': 0}
                            resource_accum = {k: 0.0 for k in resources.keys()}
                        move_timer = 0
                        print('Playing - resources initialized:', resources)
                        continue
                    if regen_button_rect.collidepoint(mouse_x, mouse_y):
                        regenerate_map()
                        print('Map regenerated')
                        continue
                    # clicked inside panel but not on buttons; ignore
                    continue

                # On a loss, the only grid interaction is the Play again button.
                if game_lost:
                    if play_again_button_rect.collidepoint(mouse_x, mouse_y):
                        regenerate_map()
                        resources = {'wood': 12, 'rock': 0, 'mana': 0, 'technology': 0}
                        resource_accum = {k: 0.0 for k in resources.keys()}
                        game_started = True
                        playing = True
                        move_timer = 0
                        print('Play again - new game started.')
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
                    # Ensure the cell has a level entry (fix for water/plain variants missing levels)
                    if cell_key not in cell_levels:
                        t_init = terrain_map.get(cell_key, 'plain')
                        if t_init == 'plain' or (isinstance(t_init, str) and t_init.startswith('plain_')):
                            cell_levels[cell_key] = 0
                        else:
                            # water and other terrains default to level 1
                            cell_levels[cell_key] = 1

                    # Lấy level hiện tại
                    current_level = cell_levels.get(cell_key, 1)

                    # Tối đa level 4
                    if current_level >= 4:
                        print(f"Ô {cell_key} đã đạt LEVEL TỐI ĐA (Level 4)!")
                        continue

                    # Determine cost key. map terrain name 'beacon' -> 'beacon'
                    terrain_type = terrain_map.get(cell_key, 'plain')
                    # handle plain subtype logic: determine cost key and later set terrain if upgrade succeeds
                    plain_variant = None
                    if terrain_type == 'beacon':
                        cost_key = 'beacon'
                    elif terrain_type.startswith('plain'):
                        # if it's exactly 'plain', determine variant from neighbors; if already plain_..., keep it
                        if terrain_type == 'plain':
                            plain_variant = choose_plain_variant(clicked_col, clicked_row)
                        else:
                            plain_variant = terrain_type
                        cost_key = plain_variant
                    else:
                        cost_key = terrain_type

                    # New rule: plains can always upgrade to level 2, but to upgrade to levels 3 or 4
                    # the dependent terrains (at offsets [[0,1],[1,0],[1,2],[2,1]]) must be the matching terrain
                    # and be at level 4.
                    next_level = current_level + 1
                    if plain_variant is not None and next_level > 2:
                        allowed = can_upgrade_plain_to_higher(clicked_col, clicked_row, plain_variant, next_level)
                        if not allowed:
                            print(f"Không thể nâng ô {cell_key} lên Level {next_level}: các ô phụ thuộc chưa đạt Level 4")
                            continue

                    cost = costs.get(cost_key)

                    # compute final cost: apply plain-subtype multiplier if applicable
                    final_cost = None
                    if cost:
                        final_cost = compute_upgrade_cost(cost, cost_key, next_level)

                    # If resources exists (playing), check and deduct; otherwise allow free upgrades (edit mode)
                    if resources is not None and final_cost:
                        # check resource sufficiency
                        enough = True
                        for res_name, amt in final_cost.items():
                            # 'mana' in cost maps to resources['mana']
                            if resources.get(res_name, 0) < amt:
                                enough = False
                                break
                        if not enough:
                            print(f"Không đủ tài nguyên để nâng ô {cell_key} ({terrain_type}) — cần {final_cost}")
                            continue
                        # deduct
                        for res_name, amt in final_cost.items():
                            resources[res_name] = resources.get(res_name, 0) - amt
                        print(f"Đã trừ tài nguyên {final_cost} cho ô {cell_key}; resources now: {resources}")

                    elif resources is not None and cost is None:
                        # if there is no cost entry, allow free upgrade (previous behavior)
                        pass

                    # Apply level up
                    cell_levels[cell_key] = current_level + 1
                    print(f"Ô {cell_key} đã tăng lên Level: {cell_levels[cell_key]}")

                    # Win condition: upgrading the Beacon to level 2 ends the game.
                    if terrain_type == 'beacon' and cell_levels[cell_key] >= 2:
                        game_won = True
                        playing = False
                        print('YOU WIN! Beacon reached Level 2.')

                    # If this was a plain cell, set the chosen plain variant on successful upgrade
                    try:
                        if plain_variant is not None:
                            # set terrain subtype (plain_rock/plain_magic/plain_wood/plain_water)
                            terrain_map[cell_key] = plain_variant
                            print(f"Ô {cell_key} plain subtype set to: {plain_variant}")

                        # Increase global cost values for this terrain type by 1 per resource key
                        # Applies to terrain types: tree, rock, plain, magic, plain_wood, plain_rock, plain_magic, plain_water
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
        # Determine color while preserving existing tree/rock/magic colors
        lvl = cell_levels.get((c, r), 0)
        if t == 'plain':
            if lvl >= 1:
                pv = choose_plain_variant(c, r)
                color = TERRAIN_COLORS.get(pv, TERRAIN_COLORS.get('plain', (200, 200, 200)))
            else:
                color = TERRAIN_COLORS.get('plain', (200, 200, 200))
        elif isinstance(t, str) and t.startswith('plain_'):
            # explicit stored plain subtype: show subtype color only when level >=1
            if lvl >= 1:
                color = TERRAIN_COLORS.get(t, TERRAIN_COLORS.get('plain', (200, 200, 200)))
            else:
                color = TERRAIN_COLORS.get('plain', (200, 200, 200))
        else:
            # keep existing colors for tree/rock/magic and others
            color = TERRAIN_COLORS.get(t, (200, 200, 200))

        pygame.draw.rect(screen, color, (c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE))
        # Vẽ chữ viết tắt terrain
        # For 'beacon' we want 'B'
        label = 'B' if t == 'beacon' else t[0].upper()
        text = font.render(label, True, (255, 255, 255))
        screen.blit(text, (c * CELL_SIZE + 4, r * CELL_SIZE + 2))

    # 2. Vẽ các ô bóng tối (đè lên terrains) - only when playing
    if playing or game_lost:
        for c, r in dark_cells:
            pygame.draw.rect(screen, BLACK, (c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE))

    # 3. Vẽ level trên các ô (nếu có) - removed: levels no longer drawn on grid

    # 4. Vẽ lưới
    for i in range(GRID_SIZE + 1):
        # horizontal
        pygame.draw.line(screen, GRAY, (0, i * CELL_SIZE), (GRID_PIXELS, i * CELL_SIZE))
        # vertical
        pygame.draw.line(screen, GRAY, (i * CELL_SIZE, 0), (i * CELL_SIZE, GRID_PIXELS))

    # Draw right info panel (300 x 600)
    pygame.draw.rect(screen, DARK_GRAY, (GRID_PIXELS, 0, INFO_WIDTH, SCREEN_HEIGHT))

    # Once started, keep the resource panel visible while playing or paused
    if game_started and resources is not None:
        # Title small at top
        title_surface = title_font.render('Stop the darkness', True, WHITE)
        title_rect = title_surface.get_rect()
        title_rect.center = (GRID_PIXELS + INFO_WIDTH // 2, 40)
        screen.blit(title_surface, title_rect)

        # Pause/Resume button
        pause_color = ORANGE if playing else GREEN
        pygame.draw.rect(screen, pause_color, pause_button_rect)
        pygame.draw.rect(screen, WHITE, pause_button_rect, 2)
        pause_label = 'Pause' if playing else 'Resume'
        pause_text = font.render(pause_label, True, WHITE)
        pause_text_rect = pause_text.get_rect(center=pause_button_rect.center)
        screen.blit(pause_text, pause_text_rect)

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

        # Total production per minute
        total_prod = compute_total_production_per_minute()
        tpy = start_y + len(keys) * 48 + 6
        for i, (rk, rv) in enumerate(total_prod.items()):
            tpv = small_font.render(f"{rk.capitalize()}: {rv}", True, WHITE)
            screen.blit(tpv, (GRID_PIXELS + 30, tpy + i * 18))

        # Hover info: show info about terrain under mouse
        mouse_x, mouse_y = pygame.mouse.get_pos()
        hover_info_y = tpy + 36
        info_x = GRID_PIXELS + 20
        info_w = INFO_WIDTH - 40

        if mouse_x < GRID_PIXELS and 0 <= mouse_x < GRID_PIXELS and 0 <= mouse_y < SCREEN_HEIGHT:
            hover_col = mouse_x // CELL_SIZE
            hover_row = mouse_y // CELL_SIZE
            if 0 <= hover_col < GRID_SIZE and 0 <= hover_row < GRID_SIZE:
                ttype = terrain_map.get((hover_col, hover_row), 'plain')
                # Determine display name for plains (including plain subtypes) based on rules
                if ttype == 'beacon':
                    display_name = 'Beacon'
                    display_key = 'beacon'
                elif ttype == 'plain':
                    # evaluate plain variant based on neighbors and show friendly name
                    pv = choose_plain_variant(hover_col, hover_row)
                    display_key = pv
                    if pv == 'plain_wood':
                        display_name = 'Village'
                    elif pv == 'plain_rock':
                        display_name = 'Mining village'
                    elif pv == 'plain_magic':
                        display_name = 'Magical village'
                    elif pv == 'plain_water':
                        display_name = 'Port village'
                    else:
                        display_name = 'Village'
                elif ttype == 'plain_wood':
                    display_name = 'Village'
                    display_key = 'plain_wood'
                elif ttype == 'plain_rock':
                    display_name = 'Mining village'
                    display_key = 'plain_rock'
                elif ttype == 'plain_magic':
                    display_name = 'Magical village'
                    display_key = 'plain_magic'
                elif ttype == 'plain_water':
                    display_name = 'Port village'
                    display_key = 'plain_water'
                else:
                    display_name = ttype.capitalize()
                    display_key = ttype

                level = cell_levels.get((hover_col, hover_row), 1)
                next_level = level + 1

                # production for current level
                cur_res_key, cur_prod_amt = get_cell_production_per_minute(ttype, level)

                # draw current info box (include production)
                # make box taller to fit production line + adjacency info
                cur_box_h = 100
                pygame.draw.rect(screen, (50, 50, 50), (info_x, hover_info_y, info_w, cur_box_h))
                pygame.draw.rect(screen, WHITE, (info_x, hover_info_y, info_w, cur_box_h), 1)
                line1 = res_font.render(f"Terrain: {display_name}", True, WHITE)
                line2 = res_font.render(f"Level: {level}", True, WHITE)
                screen.blit(line1, (info_x + 8, hover_info_y + 6))
                screen.blit(line2, (info_x + 8, hover_info_y + 32))

                # Adjacent boost info
                boost_pct = compute_cell_boost_percent(hover_col, hover_row)
                boost_text = small_font.render(f"Adjacency boost: +{boost_pct*100:.0f}%", True, WHITE)
                screen.blit(boost_text, (info_x + 8, hover_info_y + 56))

                prod_label = small_font.render("Production/min:", True, WHITE)
                screen.blit(prod_label, (info_x + 8, hover_info_y + 76))
                if cur_res_key and cur_prod_amt:
                    prod_val = small_font.render(f"{cur_res_key.capitalize()}: {cur_prod_amt}", True, WHITE)
                    screen.blit(prod_val, (info_x + 140, hover_info_y + 76))
                    boosted_val = small_font.render(f"With Adj: {cur_res_key.capitalize()}: {cur_prod_amt*(1.0+boost_pct):.1f}", True, WHITE)
                    screen.blit(boosted_val, (info_x + 140, hover_info_y + 92))
                else:
                    prod_val = small_font.render("-", True, WHITE)
                    screen.blit(prod_val, (info_x + 140, hover_info_y + 76))

                # If not max level, draw next-level box below
                if level < 4:
                    box2_y = hover_info_y + cur_box_h + 10
                    pygame.draw.rect(screen, (50, 50, 50), (info_x, box2_y, info_w, 100))
                    pygame.draw.rect(screen, WHITE, (info_x, box2_y, info_w, 100), 1)
                    nl = res_font.render(f"Next Level: {next_level}", True, WHITE)
                    screen.blit(nl, (info_x + 8, box2_y + 6))

                    # compute cost after +1 for the terrain type
                    # use display_key (evaluated variant for plains) to lookup costs
                    cost_key = 'beacon' if display_key == 'beacon' else display_key
                    cost_entry = costs.get(cost_key)
                    cost_text_y = box2_y + 36
                    if cost_entry:
                        # show only wood/rock/mana (magic) if present
                        cx = info_x + 8
                        line_index = 0
                        # For plain subtypes use the new multiplier rule for display
                        if isinstance(cost_key, str) and cost_key.startswith('plain'):
                            display_costs = compute_upgrade_cost(cost_entry, cost_key, next_level)
                            for rk in ('wood', 'rock', 'mana'):
                                if rk in display_costs:
                                    try:
                                        new_val = int(display_costs[rk])
                                    except Exception:
                                        new_val = display_costs[rk]
                                    label = 'Magic' if rk == 'mana' else rk.capitalize()
                                    ct = small_font.render(f"{label}: {new_val}", True, WHITE)
                                    screen.blit(ct, (cx, cost_text_y + line_index * 18))
                                    line_index += 1
                        else:
                            for rk in ('wood', 'rock', 'mana'):
                                if rk in cost_entry:
                                    try:
                                        new_val = int(cost_entry[rk]) + 1
                                    except Exception:
                                        new_val = cost_entry[rk]
                                    label = 'Magic' if rk == 'mana' else rk.capitalize()
                                    ct = small_font.render(f"{label}: {new_val}", True, WHITE)
                                    screen.blit(ct, (cx, cost_text_y + line_index * 18))
                                    line_index += 1
                        if line_index == 0:
                            ct = small_font.render("Cost: -", True, WHITE)
                            screen.blit(ct, (info_x + 8, cost_text_y))
                    else:
                        ct = small_font.render("Cost: -", True, WHITE)
                        screen.blit(ct, (info_x + 8, cost_text_y))

                    # production per minute for next level (show what next will produce)
                    next_res_key, next_prod_amt = get_cell_production_per_minute(ttype, next_level)
                    prod_text = small_font.render("Production/min:", True, WHITE)
                    screen.blit(prod_text, (info_x + 8, box2_y + 70))
                    if next_res_key and next_prod_amt:
                        pval = small_font.render(f"{next_res_key.capitalize()}: {next_prod_amt}", True, WHITE)
                        screen.blit(pval, (info_x + 140, box2_y + 70))
                    else:
                        pval = small_font.render("-", True, WHITE)
                        screen.blit(pval, (info_x + 140, box2_y + 70))

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
        for i, t in enumerate(TERRAINS + ['beacon']):
            ty = legend_y + i * 24
            color = TERRAIN_COLORS.get(t, (200, 200, 200))
            pygame.draw.rect(screen, color, (lx, ty, 18, 18))
            label = 'Beacon' if t == 'beacon' else t.capitalize()
            lbl = font.render(label, True, WHITE)
            screen.blit(lbl, (lx + 24, ty))

    # Show a win overlay and stop all gameplay after the Beacon reaches level 2.
    if game_won:
        overlay = pygame.Surface((GRID_PIXELS, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        screen.blit(overlay, (0, 0))
        win_font = pygame.font.SysFont(None, 76, bold=True)
        detail_font = pygame.font.SysFont(None, 30, bold=True)
        win_text = win_font.render('YOU WIN!', True, (255, 215, 0))
        win_rect = win_text.get_rect(center=(GRID_PIXELS // 2, SCREEN_HEIGHT // 2 - 25))
        screen.blit(win_text, win_rect)
        detail_text = detail_font.render('Beacon reached Level 2', True, WHITE)
        detail_rect = detail_text.get_rect(center=(GRID_PIXELS // 2, SCREEN_HEIGHT // 2 + 30))
        screen.blit(detail_text, detail_rect)

    # Show a lose overlay and Play again button when darkness covers the whole grid.
    if game_lost:
        overlay = pygame.Surface((GRID_PIXELS, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, (0, 0))
        lose_font = pygame.font.SysFont(None, 76, bold=True)
        detail_font = pygame.font.SysFont(None, 28, bold=True)
        lose_text = lose_font.render('YOU LOSE!', True, (255, 80, 80))
        lose_rect = lose_text.get_rect(center=(GRID_PIXELS // 2, SCREEN_HEIGHT // 2 - 35))
        screen.blit(lose_text, lose_rect)
        detail_text = detail_font.render('Darkness covered every block', True, WHITE)
        detail_rect = detail_text.get_rect(center=(GRID_PIXELS // 2, SCREEN_HEIGHT // 2 + 10))
        screen.blit(detail_text, detail_rect)

        pygame.draw.rect(screen, GREEN, play_again_button_rect, border_radius=6)
        pygame.draw.rect(screen, WHITE, play_again_button_rect, 2, border_radius=6)
        again_text = font.render('Play again', True, WHITE)
        again_rect = again_text.get_rect(center=play_again_button_rect.center)
        screen.blit(again_text, again_rect)

    pygame.display.flip()

pygame.quit()
