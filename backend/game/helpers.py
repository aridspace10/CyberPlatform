import random

def determine_perms_fromstr(permissions: str) -> dict | str:
    if (len(permissions.rstrip()) != 3):
        return "chmod: value given for permissions which is not of length of 3"
    ORDER = ["user", "group", "public"]
    d = {"user": {"r": False, "w": False, "x": False},
                        "group": {"r": False, "w": False, "x": False},
                        "public": {"r": False, "w": False, "x": False}}
    for idx, permission in enumerate(permissions):
        try:
            if (int(permission) > 7):
                return "chmod: value given which is higher then needed"
        except ValueError:
           return "chmod: value other then given integer given for permissions"
        permission = int(permission)
        bits = [(permission >> i) & 1 for i in range(7, -1, -1)]
        d[ORDER[idx]]["x"] = bool(bits[-1])
        d[ORDER[idx]]["w"] = bool(bits[-2])
        d[ORDER[idx]]["r"] = bool(bits[-3])
    return d

def biased_random(min_val=1, max_val=100):
    mid = (min_val + max_val) / 2
    std_dev = (max_val - min_val) / 6  # ~99.7% of values fall within range
    
    while True:
        val = random.gauss(mid, std_dev)
        if min_val <= val <= max_val:
            return round(val)
        
def biased_randint(min_val: int, max_val: int, std_factor: float = 6.0) -> int:
    """Returns a biased random int clustered around the midpoint."""
    if min_val == max_val:
        return min_val
    mid = (min_val + max_val) / 2
    std_dev = (max_val - min_val) / std_factor
    while True:
        val = random.gauss(mid, std_dev)
        if min_val <= val <= max_val:
            return round(val)