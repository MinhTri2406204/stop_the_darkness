import pygame
import random
import json
from pathlib import Path

script_dir = Path(__file__).parent
file_path = script_dir / "cost.json"

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
    with open(file_path, "r", encoding="utf-8") as f:
        costs = json.load(f)
except Exception as e:
    print("Warning: could not load cost.json:", e)
    costs = {}

# Production table (per-minute production by terrain and level)
PRODUCTION_TABLE = {
    'tree': {2: 3, 3: 5, 4: 7},
    'rock': {2: 2, 3: 5, 4: 8},
    'magic': {2: 4, 3: 7, 4: 9},
}
# Map terrain type to resource key in resources dict
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
# Float accumulators for fractional production
resource_accum = {}

# Per-cell state for plain_wood special cost rules
# plain_wood_seq_index[cell] -> integer index used to alternately add 2 or 3 when upgrading 0->1
plain_wood_seq_index = {}
# plain_wood_stored_base_costs[cell] -> dict of resource->int storing the base cost after alternation (used for later upgrades)
plain_wood_stored_base_costs = {}


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
    """Generate a terrain map while enforcing maximum counts per terrain.
    Max counts (excluding the beacon cell):
      - tree: 40
      - water: 30
      - rock: 14
      - magic: 4
    Remaining cells are 'plain'. The beacon is placed in one of the four center cells.
    """
    m = {}
    # choose beacon among center cells first
    center_cells = [
        (GRID_SIZE // 2 - 1, GRID_SIZE // 2 - 1),
        (GRID_SIZE // 2, GRID_SIZE // 2 - 1),
        (GRID_SIZE // 2 - 1, GRID_SIZE // 2),
        (GRID_SIZE // 2, GRID_SIZE // 2),
    ]
    beacon = random.choice(center_cells)

    # prepare list of all positions excluding the beacon
    positions = [(c, r) for c in range(GRID_SIZE) for r in range(GRID_SIZE) if (c, r) != beacon]

    # maximum counts for constrained terrains
    max_counts = {'tree': 40, 'water': 30, 'rock': 14, 'magic': 4}

    pool = []
    # add constrained terrains up to their limits (but not exceeding available positions)
    for terrain, cnt in max_counts.items():
        take = min(cnt, len(positions) - len(pool))
        pool.extend([terrain] * take)
    # fill the rest with plain
    remaining = len(positions) - len(pool)
    if remaining > 0:
        pool.extend(['plain'] * remaining)

    # shuffle pool and assign to positions
    random.shuffle(pool)
    for pos, terrain in zip(positions, pool):
        m[pos] = terrain

    # set beacon cell
    m[beacon] = 'beacan'
    return m, beacon


def regenerate_map():
    global terrain_map, beacon_pos, cell_levels, dark_cells, resources, resource_accum
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
    # reset all levels: plains default to 0, others default to 1
    cell_levels = {}
    for c in range(GRID_SIZE):
        for r in range(GRID_SIZE):
            if terrain_map.get((c, r), 'plain').startswith('plain'):
                cell_levels[(c, r)] = 0
            else:
                cell_levels[(c, r)] = 1


# initial terrain map
terrain_map, beacon_pos = generate_terrain_map()
# set default levels: plains default to 0, others to 1
cell_levels = {}
for c in range(GRID_SIZE):
    for r in range(GRID_SIZE):
        if terrain_map.get((c, r), 'plain').startswith('plain'):
            cell_levels[(c, r)] = 0
        else:
            cell_levels[(c, r)] = 1

# Button layout in the info panel
BUTTON_W = 120
BUTTON_H = 40
BUTTON_SPACING = 20
buttons_x = GRID_PIXELS + (INFO_WIDTH - (BUTTON_W * 2 + BUTTON_SPACING)) // 2
buttons_y = SCREEN_HEIGHT // 4 + 60
play_button_rect = pygame.Rect(buttons_x, buttons_y, BUTTON_W, BUTTON_H)
regen_button_rect = pygame.Rect(buttons_x + BUTTON_W + BUTTON_SPACING, buttons_y, BUTTON_W, BUTTON_H)


def get_cell_production_per_minute(terrain_type, level):
    """Return (resource_key, amount_per_minute) for a given terrain cell level. Returns (None, 0) if none."""
    if terrain_type == 'beacan':
        return None, 0
    if terrain_type not in PRODUCTION_TABLE:
        return None, 0
    # Find the highest mapping <= level
    mapping = PRODUCTION_TABLE[terrain_type]
    possible_levels = sorted([l for l in mapping.keys() if l <= level])
    if not possible_levels:
        return None, 0
    use_level = possible_levels[-1]
    amount = mapping.get(use_level, 0)
    res_key = TERRAIN_TO_RESOURCE.get(terrain_type)
    return res_key, amount


def get_boost_targets(terrain_name):
    """Return the list of terrain types that a source terrain can boost."""
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


def get_boost_percent(source_terrain, source_level, target_terrain):
    """Percentage multiplier from adjacency boost rules.
    Rules:
      - tree / rock / magic => boost same type only.
      - plain_wood => boosts tree and rock.
      - plain_rock => boosts rock only; 50% at level 1-2 and 75% at level 3-4.
      - plain_magic => boosts tree and magic.
      - plain_water => boosts tree and rock.
      - all other combos => 0.
    New rule: adjacency boost applies only when the source cell is at level 1.
    Percentages are expressed as decimals for multiplication.
    """
    # Only sources at level 1 provide boosts per new rule
    if source_level != 1:
        return 0.0

    if source_terrain == 'plain' and source_level is not None:
        try:
            source_terrain = choose_plain_variant(*[0, 0])
        except Exception:
            pass

    if target_terrain not in get_boost_targets(source_terrain):
        return 0.0

    if source_terrain in ('tree', 'rock', 'magic'):
        return 0.25
    if source_terrain == 'plain_wood':
        return 0.25
    if source_terrain == 'plain_rock':
        return 0.50
    if source_terrain == 'plain_magic':
        return 0.25
    if source_terrain == 'plain_water':
        return 0.25
    return 0.0


def compute_total_production_per_minute():
    """Sum production per-minute across the whole grid and return dict resource->amt.
    Each adjacent terrain within the 3x3 area contributes a boost to the target cell's output.
    """
    totals = {}
    for (c, r), lvl in cell_levels.items():
        terrain = terrain_map.get((c, r), 'plain')
        res_key, base_amt = get_cell_production_per_minute(terrain, lvl)
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
                boost_total += get_boost_percent(neighbor_type, neighbor_level, terrain)

        final_amt = base_amt * (1.0 + boost_total)
        totals[res_key] = totals.get(res_key, 0) + final_amt

    return totals


# Determine plain subtype based on orthogonal neighbors
def choose_plain_variant(center_col, center_row):
    """Return 'plain_rock' if >=2 orthogonal neighbors are 'rock',
              'plain_magic' if >=1 are 'magic' (per updated rule), 
         else 'plain_wood'."""
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
    # rock rule still requires >=2
    if rock_count >= 2:
        return 'plain_rock'
    # magic rule updated: require at least 1 orthogonal magic neighbor
    if magic_count >= 1:
        return 'plain_magic'
    if water_count >= 1:
        return 'plain_water'
    return 'plain_wood'


# New: check whether a plain subtype can upgrade beyond level 2
# Dependency positions relative to 3x3 (center at [1,1]): [[0,1],[1,0],[1,2],[2,1]] -> offsets: (-1,0),(0,-1),(0,1),(1,0)
DEPENDENCY_OFFSETS = [(-1, 0), (0, -1), (0, 1), (1, 0)]


def can_upgrade_plain_to_higher(center_col, center_row, plain_variant, target_level):
    """Return True if plain at (center_col,center_row) of type plain_variant is allowed to upgrade to target_level.
    Rules:
      - Upgrades to level 2 are always allowed (subject to resources/costs).
      - Upgrades to level 3 or 4 require the dependent terrains (tree/rock/magic) at the 4 orthogonal positions
        to be present and at level 4. If any dependency position is out-of-bounds or not the required terrain at level 4,
        the upgrade is blocked.
    """
    if target_level <= 2:
        return True
    # map plain variant to required terrain
    mapping = {
        'plain_wood': 'tree',
        'plain_rock': 'rock',
        'plain_magic': 'magic',
        'plain_water': 'water'
    }
    req = mapping.get(plain_variant)
    if req is None:
        # unknown plain variant -> block
        return False
    # check all dependency positions
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


# New helper: compute adjacency boost percent for a specific cell
def compute_cell_boost_percent(center_col, center_row):
    """Compute total adjacency boost (as decimal, e.g., 0.25 => 25%) applied to the cell at (center_col, center_row)."""
    terrain = terrain_map.get((center_col, center_row), 'plain')
    # Determine the target terrain for boost calculations (take plain variants into account)
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
            # if neighbor is plain, evaluate its plain variant for source
            if source == 'plain':
                source = choose_plain_variant(nx, ny)
            neighbor_level = cell_levels.get((nx, ny), 0)
            boost_total += get_boost_percent(source, neighbor_level, target)
    return boost_total


# ------------- Main loop -------------
while running:
    dt = clock.tick(60)
    if playing:
        move_timer += dt

    # Advance spiral movement
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

    # Production accumulation (per-frame) - convert per-minute production into per-frame and accumulate
    if playing and resources is not None:
        # ensure accumulators exist
        for k in resources.keys():
            resource_accum.setdefault(k, 0.0)

        prod_totals = compute_total_production_per_minute()  # resource->per-minute
        # accumulate fractional production
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
                            # init accumulators
                            resource_accum = {k: 0.0 for k in resources.keys()}
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
                    # Lấy level hiện tại (mặc định là 0 for plains, 1 for others)
                    current_level = cell_levels.get(cell_key, 0 if terrain_map.get(cell_key, 'plain').startswith('plain') else 1)

                    # Tối đa level 4
                    if current_level >= 4:
                        print(f"Ô {cell_key} đã đạt LEVEL TỐI ĐA (Level 4)!")
                        continue

                    # Determine cost key. map terrain name 'beacan' -> 'beacon'
                    terrain_type = terrain_map.get(cell_key, 'plain')
                    # handle plain subtype logic: determine cost key and later set terrain if upgrade succeeds
                    plain_variant = None
                    if terrain_type == 'beacan':
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

                    # SPECIAL: plain_wood custom cost rules
                    cost = None
                    if plain_variant == 'plain_wood':
                        base_entry = costs.get('plain_wood', {})
                        # Upgrading from 0 -> 1: compute stored base by adding alternately 2/3 per-cell sequence
                        if current_level == 0 and next_level == 1:
                            seq = plain_wood_seq_index.get(cell_key, 0)
                            add_val = 2 if (seq % 2) == 0 else 3
                            # compute stored base cost dict
                            stored = {}
                            for rkey, v in base_entry.items():
                                try:
                                    stored[rkey] = int(v) + add_val
                                except Exception:
                                    # non-numeric or missing -> keep original
                                    try:
                                        stored[rkey] = int(v)
                                    except Exception:
                                        stored[rkey] = v
                            plain_wood_stored_base_costs[cell_key] = stored
                            plain_wood_seq_index[cell_key] = seq + 1
                            cost = stored
                        else:
                            # Upgrading from level >=1 to higher levels: use stored base if available else base_entry
                            base = plain_wood_stored_base_costs.get(cell_key, {})
                            if not base:
                                base = base_entry
                            # cost = base + base * 20% (per resource key)
                            computed = {}
                            for rkey, v in base.items():
                                try:
                                    bv = int(v)
                                    computed[rkey] = int(bv + round(bv * 0.20))
                                except Exception:
                                    computed[rkey] = v
                            cost = computed
                    else:
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
                        # Additionally, if we updated stored base for this plain_wood cell earlier, optionally
                        # increase its stored base to stay in sync with global increments
                        if plain_variant == 'plain_wood' and cell_key in plain_wood_stored_base_costs:
                            for rkey in list(plain_wood_stored_base_costs[cell_key].keys()):
                                try:
                                    plain_wood_stored_base_costs[cell_key][rkey] = int(plain_wood_stored_base_costs[cell_key][rkey]) + 1
                                except Exception:
                                    pass
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

    # 3. Vẽ level trên các ô (nếu có) - removed: levels no longer drawn on grid

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
                if ttype == 'beacan':
                    display_name = 'Beacon'
                    display_key = 'beacan'
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

                level = cell_levels.get((hover_col, hover_row), 0 if terrain_map.get((hover_col, hover_row), 'plain').startswith('plain') else 1)
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
                    cost_key = 'beacon' if display_key == 'beacan' else display_key
                    cost_entry = costs.get(cost_key)
                    cost_text_y = box2_y + 36
                    if cost_entry:
                        # show only wood/rock/mana (magic) if present
                        cx = info_x + 8
                        line_index = 0
                        for rk in ('wood', 'rock', 'mana'):
                            if rk in cost_entry:
                                try:
                                    new_val = int(cost_entry[rk]) + 1
                                except Exception:
                                    new_val = cost_entry[rk]
                                # label mapping: 'mana' -> 'Magic' for display
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
        for i, t in enumerate(TERRAINS + ['beacan']):
            ty = legend_y + i * 24
            color = TERRAIN_COLORS.get(t, (200, 200, 200))
            pygame.draw.rect(screen, color, (lx, ty, 18, 18))
            label = 'Beacon' if t == 'beacan' else t.capitalize()
            lbl = font.render(label, True, WHITE)
            screen.blit(lbl, (lx + 24, ty))

    pygame.display.flip()

pygame.quit()
